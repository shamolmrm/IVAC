"""Tenant isolation: the single place that decides who may act inside an organization.

Every organization-scoped endpoint must go through `org_access`. Non-members get 404, not 403,
so the existence of another agency is never revealed.
"""

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.models import User
from app.modules.auth.security import current_user
from app.modules.organizations.models import (
    ROLE_RANK,
    Membership,
    Organization,
    OrgKind,
    OrgRole,
    OrgStatus,
)

NOT_FOUND = "এজেন্সিটি পাওয়া যায়নি।"


@dataclass
class OrgContext:
    org: Organization
    user: User
    role: OrgRole  # superadmins act as owner

    def at_least(self, role: OrgRole) -> bool:
        return ROLE_RANK[self.role] >= ROLE_RANK[role]


def load_context(db: Session, org_id: uuid.UUID, user: User) -> OrgContext:
    org = db.get(Organization, org_id)
    if org is None or org.kind != OrgKind.agency:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if user.is_superadmin:
        return OrgContext(org=org, user=user, role=OrgRole.owner)
    m = db.scalar(
        select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == user.id,
            Membership.is_active.is_(True),
        )
    )
    if m is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return OrgContext(org=org, user=user, role=m.role)


def org_access(min_role: OrgRole = OrgRole.agent, *, require_active: bool = False):
    """Dependency factory: membership with at least `min_role` in the path's `org_id`."""

    def dependency(
        org_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> OrgContext:
        ctx = load_context(db, org_id, user)
        if not ctx.at_least(min_role):
            raise HTTPException(status_code=403, detail="এই কাজের অনুমতি আপনার নেই।")
        if require_active and ctx.org.status != OrgStatus.active:
            raise HTTPException(
                status_code=403, detail="এজেন্সিটি এখনো অনুমোদিত হয়নি বা স্থগিত আছে।"
            )
        return ctx

    return dependency
