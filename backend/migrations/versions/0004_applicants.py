"""applicants (passport / NID encrypted, blind-indexed for duplicate checks)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=24)


def _ts(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _user_fk(name: str) -> sa.Column:
    return sa.Column(name, sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"))


def upgrade() -> None:
    op.create_table(
        "applicants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        _user_fk("created_by"),
        _user_fk("assigned_to"),
        sa.Column("dedupe_scope", sa.String(64), nullable=False),
        sa.Column("surname", sa.String(80), nullable=False),
        sa.Column("given_name", sa.String(120), nullable=False),
        sa.Column("gender", _enum("gender", "male", "female", "other"), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("place_of_birth", sa.String(120)),
        sa.Column("nationality", sa.String(3), nullable=False, server_default="BGD"),
        sa.Column(
            "marital_status", _enum("marital_status", "single", "married", "divorced", "widowed")
        ),
        sa.Column("father_name", sa.String(160)),
        sa.Column("mother_name", sa.String(160)),
        sa.Column("spouse_name", sa.String(160)),
        sa.Column("passport_enc", sa.String(200), nullable=False),
        sa.Column("passport_index", sa.String(64), nullable=False),
        sa.Column("passport_last3", sa.String(3), nullable=False),
        sa.Column("passport_issue_date", sa.Date()),
        sa.Column("passport_expiry_date", sa.Date(), nullable=False),
        sa.Column("passport_issue_place", sa.String(120)),
        sa.Column("nid_enc", sa.String(200)),
        sa.Column("nid_index", sa.String(64)),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(254)),
        sa.Column("present_address", sa.String(400)),
        sa.Column("permanent_address", sa.String(400)),
        sa.Column("occupation", sa.String(120)),
        sa.Column(
            "visa_type",
            _enum(
                "visa_type", "tourist", "medical", "medical_attendant", "business", "student",
                "entry", "other",
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    for col in ("organization_id", "created_by", "assigned_to", "date_of_birth",
                "passport_index", "nid_index"):
        op.create_index(f"ix_applicants_{col}", "applicants", [col])
    op.create_index(
        "uq_applicant_scope_passport",
        "applicants",
        ["dedupe_scope", "passport_index"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("applicants")
