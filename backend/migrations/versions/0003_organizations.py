"""organizations (agencies + built-in Direct), memberships, invites

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIRECT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=16)


def _ts(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


ROLE = ("owner", "manager", "agent")


def upgrade() -> None:
    orgs = op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("kind", _enum("org_kind", "direct", "agency"), nullable=False),
        sa.Column(
            "status", _enum("org_status", "pending", "active", "suspended"), nullable=False
        ),
        sa.Column("phone", sa.String(20)),
        sa.Column("address", sa.String(300)),
        sa.Column("trade_license", sa.String(60)),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_organizations_status", "organizations", ["status"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", _enum("org_role", *ROLE), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _ts("created_at"),
        _ts("updated_at"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    op.create_table(
        "invites",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("role", _enum("org_role", *ROLE), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("invited_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        _ts("created_at"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_invites_organization_id", "invites", ["organization_id"])

    op.bulk_insert(
        orgs,
        [{"id": DIRECT_ORG_ID, "name": "Direct applicants", "kind": "direct", "status": "active"}],
    )


def downgrade() -> None:
    op.drop_table("invites")
    op.drop_table("memberships")
    op.drop_table("organizations")
