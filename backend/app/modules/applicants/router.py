"""Applicant profiles for individuals (Direct) and agencies."""

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.crypto import blind_index
from app.core.db import get_db, utcnow
from app.modules.applicants import service as svc
from app.modules.applicants.access import load_applicant, scope_for_direct, scope_for_org
from app.modules.applicants.models import Applicant, Gender, MaritalStatus, VisaType
from app.modules.audit.service import audit
from app.modules.auth.models import User
from app.modules.auth.security import current_user
from app.modules.organizations.access import OrgContext, org_access
from app.modules.organizations.models import DIRECT_ORG_ID, Membership, OrgRole

router = APIRouter(tags=["applicants"])

member_active = org_access(OrgRole.agent, require_active=True)
any_member = org_access(OrgRole.agent)
MAX_DIRECT_APPLICANTS = 20  # an individual applies for self and family, not hundreds
EMAIL = r"^$|^[^@\s]+@[^@\s]+\.[^@\s]+$"
BGD_ID = r"^$|^[A-Za-z0-9]{6,20}$"
ONLY_MANAGERS = "শুধু এজেন্সির Owner বা Manager দায়িত্ব ভাগ করতে পারেন।"


# ── Schemas ──


class ApplicantBase(BaseModel):
    surname: str = Field(min_length=1, max_length=80)
    given_name: str = Field(min_length=1, max_length=120)
    gender: Gender
    date_of_birth: date
    place_of_birth: str | None = Field(default=None, max_length=120)
    nationality: str = Field(default="BGD", min_length=3, max_length=3)
    marital_status: MaritalStatus | None = None
    father_name: str | None = Field(default=None, max_length=160)
    mother_name: str | None = Field(default=None, max_length=160)
    spouse_name: str | None = Field(default=None, max_length=160)
    passport_issue_date: date | None = None
    passport_expiry_date: date
    passport_issue_place: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL)
    present_address: str | None = Field(default=None, max_length=400)
    permanent_address: str | None = Field(default=None, max_length=400)
    occupation: str | None = Field(default=None, max_length=120)
    visa_type: VisaType
    notes: str | None = Field(default=None, max_length=4000)
    bgd_application_id: str | None = Field(default=None, max_length=20, pattern=BGD_ID)
    ivac_mission: str | None = Field(default=None, max_length=160)
    expected_journey_date: date | None = None
    port_of_arrival: str | None = Field(default=None, max_length=80)
    port_of_exit: str | None = Field(default=None, max_length=80)


class ApplicantIn(ApplicantBase):
    passport_number: str = Field(min_length=6, max_length=20)
    nid_number: str | None = Field(default=None, max_length=25)


class ApplicantUpdate(BaseModel):
    """Every field optional; only the ones sent are changed."""

    surname: str | None = Field(default=None, min_length=1, max_length=80)
    given_name: str | None = Field(default=None, min_length=1, max_length=120)
    gender: Gender | None = None
    date_of_birth: date | None = None
    place_of_birth: str | None = Field(default=None, max_length=120)
    nationality: str | None = Field(default=None, min_length=3, max_length=3)
    marital_status: MaritalStatus | None = None
    father_name: str | None = Field(default=None, max_length=160)
    mother_name: str | None = Field(default=None, max_length=160)
    spouse_name: str | None = Field(default=None, max_length=160)
    passport_number: str | None = Field(default=None, min_length=6, max_length=20)
    passport_issue_date: date | None = None
    passport_expiry_date: date | None = None
    passport_issue_place: str | None = Field(default=None, max_length=120)
    nid_number: str | None = Field(default=None, max_length=25)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL)
    present_address: str | None = Field(default=None, max_length=400)
    permanent_address: str | None = Field(default=None, max_length=400)
    occupation: str | None = Field(default=None, max_length=120)
    visa_type: VisaType | None = None
    notes: str | None = Field(default=None, max_length=4000)
    bgd_application_id: str | None = Field(default=None, max_length=20, pattern=BGD_ID)
    ivac_mission: str | None = Field(default=None, max_length=160)
    expected_journey_date: date | None = None
    port_of_arrival: str | None = Field(default=None, max_length=80)
    port_of_exit: str | None = Field(default=None, max_length=80)


class ApplicantSummary(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    surname: str
    given_name: str
    date_of_birth: date
    passport_masked: str
    passport_expiry_date: date
    visa_type: VisaType
    assigned_to: uuid.UUID | None
    created_at: datetime | None


class ApplicantOut(ApplicantBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    passport_number: str
    nid_number: str | None
    assigned_to: uuid.UUID | None
    created_by: uuid.UUID | None
    created_at: datetime | None
    updated_at: datetime | None


class ApplicantSaved(BaseModel):
    applicant: ApplicantOut
    warnings: list[str]


class AssignIn(BaseModel):
    user_id: uuid.UUID | None


PLAIN_FIELDS = set(ApplicantBase.model_fields) - {"phone"}


def summary(a: Applicant) -> ApplicantSummary:
    return ApplicantSummary(
        id=a.id, organization_id=a.organization_id, surname=a.surname, given_name=a.given_name,
        date_of_birth=a.date_of_birth, passport_masked=f"******{a.passport_last3}",
        passport_expiry_date=a.passport_expiry_date, visa_type=a.visa_type,
        assigned_to=a.assigned_to, created_at=a.created_at,
    )


def full(a: Applicant) -> ApplicantOut:
    return ApplicantOut(
        **{k: getattr(a, k) for k in ApplicantBase.model_fields},
        id=a.id, organization_id=a.organization_id,
        passport_number=svc.passport_number(a), nid_number=svc.nid_number(a),
        assigned_to=a.assigned_to, created_by=a.created_by,
        created_at=a.created_at, updated_at=a.updated_at,
    )


def _clean(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _apply(a: Applicant, data: dict) -> None:
    """Copy validated fields onto the model (normalising text, phone, passport, NID)."""
    for key, value in data.items():
        if key in PLAIN_FIELDS:
            value = _clean(value)
            if key in ("surname", "given_name") and value:
                value = str(value).upper()  # as printed in the passport
            if key in ("nationality", "bgd_application_id") and value:
                value = str(value).upper()
            setattr(a, key, value)
    if "phone" in data:
        a.phone = svc.clean_phone(data["phone"])
    if data.get("passport_number"):
        svc.set_passport(a, svc.normalise_passport(data["passport_number"]))
    if "nid_number" in data:
        nid = _clean(data["nid_number"])
        svc.set_nid(a, svc.normalise_nid(str(nid)) if nid else None)
    if not a.surname or not a.given_name:
        raise HTTPException(status_code=422, detail="নাম খালি রাখা যাবে না।")


def _save(db: Session, a: Applicant, request: Request, user: User, action: str) -> ApplicantSaved:
    # checks must see the database, not this pending change (works with or without autoflush)
    with db.no_autoflush:
        try:
            warnings = svc.check_dates(
                a.date_of_birth, a.passport_issue_date, a.passport_expiry_date
            )
            svc.ensure_unique_passport(db, a)
        except HTTPException:
            db.rollback()  # never leave a half-applied change in the session
            raise
        warnings += svc.soft_duplicate_warnings(db, a)
        elsewhere = svc.exists_in_other_scope(db, a)
    db.flush()
    audit(db, action, actor_id=user.id, target_type="applicant", target_id=a.id,
          detail={"org": str(a.organization_id)}, request=request)
    if elsewhere:  # visible to superadmins in the audit log only
        audit(db, "applicant.duplicate_elsewhere", actor_id=user.id, target_type="applicant",
              target_id=a.id, detail={"org": str(a.organization_id)}, request=request)
    try:
        db.commit()
    except IntegrityError:  # concurrent duplicate insert
        db.rollback()
        raise HTTPException(status_code=409, detail=svc.DUPLICATE_PASSPORT) from None
    return ApplicantSaved(applicant=full(a), warnings=warnings)


def _create(
    db: Session, body: ApplicantIn, org_id: uuid.UUID, user: User, request: Request
) -> ApplicantSaved:
    a = Applicant(
        id=uuid.uuid4(), organization_id=org_id, created_by=user.id,
        dedupe_scope=svc.dedupe_scope(org_id, user.id),
    )
    _apply(a, body.model_dump())  # validates before the object enters the session
    db.add(a)
    return _save(db, a, request, user, "applicant.create")


def _search(q, text: str | None):  # noqa: ANN001, ANN202 — SQLAlchemy Select in/out
    if not text or not text.strip():
        return q
    t = text.strip()
    conds = [
        func.lower(Applicant.surname).contains(t.lower()),
        func.lower(Applicant.given_name).contains(t.lower()),
    ]
    compact = t.replace(" ", "").upper()
    if svc.PASSPORT_RE.match(compact):  # exact passport match through the blind index
        conds.append(Applicant.passport_index == blind_index(f"passport:{compact}"))
    return q.where(or_(*conds))


def _list(db: Session, q, text: str | None) -> list[ApplicantSummary]:  # noqa: ANN001
    q = _search(q.where(Applicant.archived_at.is_(None)), text)
    return [summary(a) for a in db.scalars(q.order_by(Applicant.created_at.desc()).limit(500))]


# ── Individuals (B2C, Direct organization) ──


@router.post("/applicants", response_model=ApplicantSaved, status_code=201)
def create_direct(
    body: ApplicantIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ApplicantSaved:
    count = db.scalar(
        scope_for_direct(select(func.count(Applicant.id)), user).where(
            Applicant.archived_at.is_(None)
        )
    )
    if (count or 0) >= MAX_DIRECT_APPLICANTS:
        raise HTTPException(status_code=409, detail="সর্বোচ্চ সংখ্যক আবেদনকারী যোগ করা হয়ে গেছে।")
    return _create(db, body, DIRECT_ORG_ID, user, request)


@router.get("/applicants", response_model=list[ApplicantSummary])
def list_direct(
    q: str | None = Query(default=None, max_length=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ApplicantSummary]:
    return _list(db, scope_for_direct(select(Applicant), user), q)


# ── Agencies ──


@router.post("/orgs/{org_id}/applicants", response_model=ApplicantSaved, status_code=201)
def create_for_org(
    body: ApplicantIn,
    request: Request,
    ctx: OrgContext = Depends(member_active),
    db: Session = Depends(get_db),
) -> ApplicantSaved:
    saved = _create(db, body, ctx.org.id, ctx.user, request)
    if ctx.role == OrgRole.agent:  # agents own what they create
        a = db.get(Applicant, saved.applicant.id)
        assert a is not None
        a.assigned_to = ctx.user.id
        db.commit()
        saved.applicant.assigned_to = ctx.user.id
    return saved


@router.get("/orgs/{org_id}/applicants", response_model=list[ApplicantSummary])
def list_for_org(
    q: str | None = Query(default=None, max_length=100),
    mine: bool = False,
    ctx: OrgContext = Depends(any_member),
    db: Session = Depends(get_db),
) -> list[ApplicantSummary]:
    query = scope_for_org(select(Applicant), ctx)
    if mine:
        query = query.where(Applicant.assigned_to == ctx.user.id)
    return _list(db, query, q)


# ── Single applicant (both kinds) ──


@router.get("/applicants/{applicant_id}", response_model=ApplicantOut)
def get_applicant(
    applicant_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ApplicantOut:
    a, _ = load_applicant(db, applicant_id, user)
    audit(db, "applicant.view", actor_id=user.id, target_type="applicant", target_id=a.id,
          request=request)  # every read of passport data is logged
    db.commit()
    return full(a)


@router.patch("/applicants/{applicant_id}", response_model=ApplicantSaved)
def update_applicant(
    applicant_id: uuid.UUID,
    body: ApplicantUpdate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ApplicantSaved:
    a, _ = load_applicant(db, applicant_id, user, write=True)
    data = body.model_dump(exclude_unset=True)
    for required in ("gender", "date_of_birth", "passport_expiry_date", "visa_type"):
        if required in data and data[required] is None:
            raise HTTPException(status_code=422, detail="প্রয়োজনীয় ঘর খালি রাখা যাবে না।")
    try:
        _apply(a, data)
    except HTTPException:
        db.rollback()
        raise
    return _save(db, a, request, user, "applicant.update")


@router.delete("/applicants/{applicant_id}", status_code=204)
def archive_applicant(
    applicant_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    a, ctx = load_applicant(db, applicant_id, user, write=True)
    if ctx is not None and not ctx.at_least(OrgRole.manager):
        raise HTTPException(status_code=403, detail="শুধু Owner বা Manager আবেদনকারী মুছতে পারেন।")
    a.archived_at = utcnow()
    audit(db, "applicant.archive", actor_id=user.id, target_type="applicant", target_id=a.id,
          detail={"org": str(a.organization_id)}, request=request)
    db.commit()
    return Response(status_code=204)


@router.post("/applicants/{applicant_id}/assign", response_model=ApplicantSummary)
def assign_applicant(
    applicant_id: uuid.UUID,
    body: AssignIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ApplicantSummary:
    a, ctx = load_applicant(db, applicant_id, user, write=True)
    if ctx is None or not ctx.at_least(OrgRole.manager):
        raise HTTPException(status_code=403, detail=ONLY_MANAGERS)
    if body.user_id is not None:
        member = db.scalar(
            select(Membership.id).where(
                Membership.organization_id == a.organization_id,
                Membership.user_id == body.user_id,
                Membership.is_active.is_(True),
            )
        )
        if member is None:
            raise HTTPException(status_code=422, detail="এই ব্যক্তি এজেন্সির সক্রিয় সদস্য নন।")
    a.assigned_to = body.user_id
    audit(db, "applicant.assign", actor_id=user.id, target_type="applicant", target_id=a.id,
          detail={"to": str(body.user_id) if body.user_id else None}, request=request)
    db.commit()
    return summary(a)
