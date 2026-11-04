"""Who may see or change an applicant. Every applicant endpoint goes through here.

- Direct (B2C) applicants: only the user who created them (and superadmins).
- Agency applicants: owners and managers see all of their agency's applicants;
  agents see only applicants assigned to them or created by them.
Anyone else gets 404 so that the record's existence is not revealed.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import Select, or_
from sqlalchemy.orm import Session

from app.modules.applicants.models import Applicant
from app.modules.auth.models import User
from app.modules.organizations.access import OrgContext, load_context
from app.modules.organizations.models import DIRECT_ORG_ID, OrgRole

NOT_FOUND = "আবেদনকারী পাওয়া যায়নি।"


def scope_for_org(q: Select, ctx: OrgContext) -> Select:
    """Limit an applicant query to what this staff member may see in their agency."""
    q = q.where(Applicant.organization_id == ctx.org.id)
    if ctx.role == OrgRole.agent:
        q = q.where(or_(Applicant.assigned_to == ctx.user.id, Applicant.created_by == ctx.user.id))
    return q


def scope_for_direct(q: Select, user: User) -> Select:
    return q.where(Applicant.organization_id == DIRECT_ORG_ID, Applicant.created_by == user.id)


def load_applicant(
    db: Session, applicant_id: uuid.UUID, user: User, *, write: bool = False
) -> tuple[Applicant, OrgContext | None]:
    """Return the applicant and (for agency applicants) the caller's org context."""
    a = db.get(Applicant, applicant_id)
    if a is None or a.archived_at is not None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if user.is_superadmin:
        return a, None
    if a.organization_id == DIRECT_ORG_ID:
        if a.created_by != user.id:
            raise HTTPException(status_code=404, detail=NOT_FOUND)
        return a, None
    try:
        ctx = load_context(db, a.organization_id, user)
    except HTTPException:
        raise HTTPException(status_code=404, detail=NOT_FOUND) from None
    if ctx.role == OrgRole.agent and user.id not in (a.assigned_to, a.created_by):
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if write and ctx.org.status.value != "active":
        raise HTTPException(status_code=403, detail="এজেন্সিটি সক্রিয় নয়।")
    return a, ctx
