"""Agencies, staff memberships and invitations."""

import logging
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core import mailer
from app.core.config import get_settings
from app.core.db import as_utc, get_db, utcnow
from app.modules.audit.service import audit
from app.modules.auth.models import User
from app.modules.auth.security import current_user, sha256
from app.modules.organizations.access import OrgContext, org_access
from app.modules.organizations.models import (
    ROLE_RANK,
    Invite,
    Membership,
    Organization,
    OrgKind,
    OrgRole,
    OrgStatus,
)

log = logging.getLogger(__name__)
router = APIRouter(tags=["organizations"])

INVITE_TTL = timedelta(days=7)
MAX_ORGS_PER_USER = 3
BAD_INVITE = "আমন্ত্রণটি সঠিক নয়, বাতিল হয়েছে অথবা মেয়াদ শেষ।"

any_member = org_access()
manager_up = org_access(OrgRole.manager)
manager_active = org_access(OrgRole.manager, require_active=True)
owner_only = org_access(OrgRole.owner)


# ── Schemas ──


class OrgIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=300)
    trade_license: str | None = Field(default=None, max_length=60)


class OrgUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=300)
    trade_license: str | None = Field(default=None, max_length=60)


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str
    status: OrgStatus
    phone: str | None
    address: str | None
    trade_license: str | None
    created_at: datetime | None
    my_role: OrgRole | None = None


class MemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    role: OrgRole
    is_active: bool
    joined_at: datetime | None


class MemberUpdate(BaseModel):
    role: OrgRole | None = None
    is_active: bool | None = None


class InviteIn(BaseModel):
    email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: OrgRole


class InviteOut(BaseModel):
    id: uuid.UUID
    email: str
    role: OrgRole
    created_at: datetime | None
    expires_at: datetime


class InviteCreated(InviteOut):
    link: str
    emailed: bool


class InvitePreview(BaseModel):
    organization: str
    role: OrgRole
    email: str


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


def org_out(org: Organization, role: OrgRole | None = None) -> OrgOut:
    return OrgOut(
        id=org.id, name=org.name, status=org.status, phone=org.phone, address=org.address,
        trade_license=org.trade_license, created_at=org.created_at, my_role=role,
    )


def invite_out(inv: Invite) -> InviteOut:
    return InviteOut(
        id=inv.id, email=inv.email, role=inv.role, created_at=inv.created_at,
        expires_at=inv.expires_at,
    )


def _active_owner_count(db: Session, org_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count(Membership.id)).where(
            Membership.organization_id == org_id,
            Membership.role == OrgRole.owner,
            Membership.is_active.is_(True),
        )
    ) or 0


# ── Agencies ──


@router.post("/orgs", response_model=OrgOut, status_code=201)
def create_org(
    body: OrgIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> OrgOut:
    created = db.scalar(
        select(func.count(Organization.id)).where(Organization.created_by == user.id)
    )
    if (created or 0) >= MAX_ORGS_PER_USER:
        raise HTTPException(status_code=409, detail="আপনি সর্বোচ্চ সংখ্যক এজেন্সি খুলে ফেলেছেন।")
    org = Organization(
        name=body.name.strip(), kind=OrgKind.agency, status=OrgStatus.pending,
        phone=body.phone, address=body.address, trade_license=body.trade_license,
        created_by=user.id,
    )
    db.add(org)
    db.flush()
    db.add(Membership(organization_id=org.id, user_id=user.id, role=OrgRole.owner))
    audit(db, "org.create", actor_id=user.id, target_type="org", target_id=org.id,
          detail={"name": org.name}, request=request)
    db.commit()
    return org_out(org, OrgRole.owner)


@router.get("/orgs/mine", response_model=list[OrgOut])
def my_orgs(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[OrgOut]:
    rows = db.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(
            Membership.user_id == user.id,
            Membership.is_active.is_(True),
            Organization.kind == OrgKind.agency,
        )
        .order_by(Organization.created_at)
    ).all()
    return [org_out(org, role) for org, role in rows]


@router.get("/orgs/{org_id}", response_model=OrgOut)
def get_org(ctx: OrgContext = Depends(any_member)) -> OrgOut:
    return org_out(ctx.org, ctx.role)


@router.patch("/orgs/{org_id}", response_model=OrgOut)
def update_org(
    body: OrgUpdate,
    request: Request,
    ctx: OrgContext = Depends(owner_only),
    db: Session = Depends(get_db),
) -> OrgOut:
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(ctx.org, key, value.strip() if isinstance(value, str) else value)
    audit(db, "org.update", actor_id=ctx.user.id, target_type="org", target_id=ctx.org.id,
          detail={"fields": sorted(changes)}, request=request)
    db.commit()
    return org_out(ctx.org, ctx.role)


# ── Members ──


@router.get("/orgs/{org_id}/members", response_model=list[MemberOut])
def list_members(
    ctx: OrgContext = Depends(manager_up), db: Session = Depends(get_db)
) -> list[MemberOut]:
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == ctx.org.id)
        .order_by(Membership.created_at)
    ).all()
    return [
        MemberOut(
            id=m.id, user_id=u.id, full_name=u.full_name, email=u.email, role=m.role,
            is_active=m.is_active, joined_at=m.created_at,
        )
        for m, u in rows
    ]


@router.patch("/orgs/{org_id}/members/{member_id}", response_model=MemberOut)
def update_member(
    member_id: uuid.UUID,
    body: MemberUpdate,
    request: Request,
    ctx: OrgContext = Depends(owner_only),
    db: Session = Depends(get_db),
) -> MemberOut:
    m = db.get(Membership, member_id)
    if m is None or m.organization_id != ctx.org.id:
        raise HTTPException(status_code=404, detail="সদস্য পাওয়া যায়নি।")
    if m.user_id == ctx.user.id:
        raise HTTPException(status_code=400, detail="নিজের ভূমিকা নিজে বদলানো যায় না।")
    was_owner = m.role == OrgRole.owner and m.is_active
    if body.role is not None:
        m.role = body.role
    if body.is_active is not None:
        m.is_active = body.is_active
    db.flush()
    if was_owner and _active_owner_count(db, ctx.org.id) == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="এজেন্সিতে অন্তত একজন সক্রিয় Owner থাকতে হবে।")
    audit(db, "org.member_update", actor_id=ctx.user.id, target_type="membership",
          target_id=m.id, detail={"org": str(ctx.org.id), **body.model_dump(exclude_unset=True)},
          request=request)
    db.commit()
    u = db.get(User, m.user_id)
    assert u is not None
    return MemberOut(
        id=m.id, user_id=u.id, full_name=u.full_name, email=u.email, role=m.role,
        is_active=m.is_active, joined_at=m.created_at,
    )


# ── Invites ──


@router.post("/orgs/{org_id}/invites", response_model=InviteCreated, status_code=201)
def create_invite(
    body: InviteIn,
    request: Request,
    ctx: OrgContext = Depends(manager_active),
    db: Session = Depends(get_db),
) -> InviteCreated:
    # managers may only invite agents; nobody can grant a role above their own
    if ROLE_RANK[body.role] > ROLE_RANK[ctx.role] or (
        ctx.role == OrgRole.manager and body.role != OrgRole.agent
    ):
        raise HTTPException(status_code=403, detail="এই ভূমিকায় আমন্ত্রণ পাঠানোর অনুমতি আপনার নেই।")
    email = body.email.strip().lower()
    already = db.scalar(
        select(Membership.id)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.organization_id == ctx.org.id,
            User.email == email,
            Membership.is_active.is_(True),
        )
    )
    if already:
        raise HTTPException(status_code=409, detail="এই ব্যক্তি আগেই এজেন্সির সদস্য।")
    now = utcnow()
    db.execute(  # one live invite per email per agency
        update(Invite)
        .where(
            Invite.organization_id == ctx.org.id, Invite.email == email,
            Invite.accepted_at.is_(None), Invite.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    token = secrets.token_urlsafe(32)
    inv = Invite(
        organization_id=ctx.org.id, email=email, role=body.role, token_hash=sha256(token),
        invited_by=ctx.user.id, expires_at=now + INVITE_TTL, created_at=now,
    )
    db.add(inv)
    audit(db, "org.invite_create", actor_id=ctx.user.id, target_type="org", target_id=ctx.org.id,
          detail={"email": email, "role": body.role}, request=request)
    db.commit()

    s = get_settings()
    link = f"{s.public_url}/invite?token={token}"
    emailed = False
    if mailer.email_enabled():
        try:
            mailer.send_email(
                email,
                f"{s.brand_name}: {ctx.org.name} এজেন্সিতে আমন্ত্রণ",
                f"{ctx.user.full_name} আপনাকে {ctx.org.name} এজেন্সিতে যোগ দেওয়ার আমন্ত্রণ "
                f"জানিয়েছেন।\n\nযোগ দিতে এই লিংকে যান (৭ দিন বৈধ):\n{link}\n",
            )
            emailed = True
        except Exception as exc:
            log.error("invite email failed: %s", exc)
    return InviteCreated(**invite_out(inv).model_dump(), link=link, emailed=emailed)


@router.get("/orgs/{org_id}/invites", response_model=list[InviteOut])
def list_invites(
    ctx: OrgContext = Depends(manager_up), db: Session = Depends(get_db)
) -> list[InviteOut]:
    rows = db.scalars(
        select(Invite)
        .where(
            Invite.organization_id == ctx.org.id,
            Invite.accepted_at.is_(None), Invite.revoked_at.is_(None),
            Invite.expires_at > utcnow(),
        )
        .order_by(Invite.created_at.desc())
    ).all()
    return [invite_out(i) for i in rows]


@router.delete("/orgs/{org_id}/invites/{invite_id}", status_code=204)
def revoke_invite(
    invite_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(manager_up),
    db: Session = Depends(get_db),
) -> Response:
    inv = db.get(Invite, invite_id)
    if inv is None or inv.organization_id != ctx.org.id:
        raise HTTPException(status_code=404, detail="আমন্ত্রণ পাওয়া যায়নি।")
    inv.revoked_at = inv.revoked_at or utcnow()
    audit(db, "org.invite_revoke", actor_id=ctx.user.id, target_type="org", target_id=ctx.org.id,
          detail={"email": inv.email}, request=request)
    db.commit()
    return Response(status_code=204)


def _live_invite(db: Session, token: str) -> tuple[Invite, Organization]:
    inv = db.scalar(select(Invite).where(Invite.token_hash == sha256(token)))
    if (
        inv is None or inv.accepted_at or inv.revoked_at or as_utc(inv.expires_at) < utcnow()
    ):
        raise HTTPException(status_code=400, detail=BAD_INVITE)
    org = db.get(Organization, inv.organization_id)
    if org is None or org.status == OrgStatus.suspended:
        raise HTTPException(status_code=400, detail=BAD_INVITE)
    return inv, org


@router.post("/invites/preview", response_model=InvitePreview)
def preview_invite(
    body: TokenIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> InvitePreview:
    inv, org = _live_invite(db, body.token)
    return InvitePreview(organization=org.name, role=inv.role, email=inv.email)


@router.post("/invites/accept", response_model=OrgOut)
def accept_invite(
    body: TokenIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> OrgOut:
    inv, org = _live_invite(db, body.token)
    if inv.email != user.email:
        raise HTTPException(
            status_code=403,
            detail=f"এই আমন্ত্রণ {inv.email} ঠিকানার জন্য। ওই ইমেইলের অ্যাকাউন্ট দিয়ে লগইন করুন।",
        )
    m = db.scalar(
        select(Membership).where(
            Membership.organization_id == org.id, Membership.user_id == user.id
        )
    )
    if m is None:
        m = Membership(organization_id=org.id, user_id=user.id, role=inv.role)
        db.add(m)
    else:
        m.role, m.is_active = inv.role, True
    inv.accepted_at = utcnow()
    # the invite link proved they can read this mailbox
    user.email_verified_at = user.email_verified_at or utcnow()
    audit(db, "org.invite_accept", actor_id=user.id, target_type="org", target_id=org.id,
          detail={"role": inv.role}, request=request)
    db.commit()
    return org_out(org, m.role)
