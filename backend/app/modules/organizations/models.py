import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin

# Individual (B2C) applicants belong to this built-in organization. Created by migration 0003.
DIRECT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class OrgKind(enum.StrEnum):
    direct = "direct"  # the built-in home of individual applicants
    agency = "agency"


class OrgStatus(enum.StrEnum):
    pending = "pending"  # waiting for super admin approval
    active = "active"
    suspended = "suspended"


class OrgRole(enum.StrEnum):
    owner = "owner"  # everything in the agency, incl. staff and billing
    manager = "manager"  # applicants, assignment, invites agents
    agent = "agent"  # only the applicants assigned to them


ROLE_RANK = {OrgRole.agent: 0, OrgRole.manager: 1, OrgRole.owner: 2}


def _enum(e: type[enum.StrEnum], name: str) -> Enum:
    return Enum(e, name=name, native_enum=False, length=16)


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[OrgKind] = mapped_column(_enum(OrgKind, "org_kind"), default=OrgKind.agency)
    status: Mapped[OrgStatus] = mapped_column(
        _enum(OrgStatus, "org_status"), default=OrgStatus.pending, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(300))
    trade_license: Mapped[str | None] = mapped_column(String(60))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Membership(TimestampMixin, Base):
    """A staff member of an organization."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_membership"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[OrgRole] = mapped_column(_enum(OrgRole, "org_role"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Invite(Base):
    """Invitation for a person (by email) to join an organization. Token stored hashed."""

    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(254))
    role: Mapped[OrgRole] = mapped_column(_enum(OrgRole, "org_role"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
