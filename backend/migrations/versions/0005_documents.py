"""documents (encrypted uploads)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = (
    "passport_bio", "photo", "bgd_form", "nid", "bank_statement", "address_proof",
    "previous_visa", "medical_letter", "invitation_letter", "student_letter", "other",
)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "applicant_id", sa.Uuid(), sa.ForeignKey("applicants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id", sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "kind", sa.Enum(*KINDS, name="doc_kind", native_enum=False, length=24),
            nullable=False,
        ),
        sa.Column("original_name", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(40), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(120), nullable=False, unique=True),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_documents_applicant_id", "documents", ["applicant_id"])
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])


def downgrade() -> None:
    op.drop_table("documents")
