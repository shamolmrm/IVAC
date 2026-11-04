"""Super admin: review and approve or suspend agencies."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.audit.service import audit
from app.modules.auth.models import User
from app.modules.auth.security import superadmin
from app.modules.organizations.models import Membership, Organization, OrgKind, OrgStatus
from app.modules.organizations.router import OrgOut, org_out

router = APIRouter(prefix="/admin/orgs", tags=["admin"])


class AdminOrgOut(OrgOut):
    members: int
    owner_email: str | None


class StatusIn(BaseModel):
    status: OrgStatus


def _admin_out(db: Session, org: Organization) -> AdminOrgOut:
    members = db.scalar(
        select(func.count(Membership.id)).where(
            Membership.organization_id == org.id, Membership.is_active.is_(True)
        )
    )
    owner = db.get(User, org.created_by) if org.created_by else None
    return AdminOrgOut(
        **org_out(org).model_dump(), members=members or 0,
        owner_email=owner.email if owner else None,
    )


@router.get("", response_model=list[AdminOrgOut])
def list_orgs(
    status: OrgStatus | None = None,
    _: User = Depends(superadmin),
    db: Session = Depends(get_db),
) -> list[AdminOrgOut]:
    q = select(Organization).where(Organization.kind == OrgKind.agency)
    if status:
        q = q.where(Organization.status == status)
    orgs = db.scalars(q.order_by(Organization.created_at.desc()).limit(500)).all()
    return [_admin_out(db, o) for o in orgs]


@router.post("/{org_id}/status", response_model=AdminOrgOut)
def set_status(
    org_id: uuid.UUID,
    body: StatusIn,
    request: Request,
    admin: User = Depends(superadmin),
    db: Session = Depends(get_db),
) -> AdminOrgOut:
    org = db.get(Organization, org_id)
    if org is None or org.kind != OrgKind.agency:
        raise HTTPException(status_code=404, detail="এজেন্সিটি পাওয়া যায়নি।")
    old = org.status
    org.status = body.status
    audit(db, "org.status", actor_id=admin.id, target_type="org", target_id=org.id,
          detail={"from": old, "to": body.status}, request=request)
    db.commit()
    return _admin_out(db, org)
