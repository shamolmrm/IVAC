"""applicant fields from the online application form (BGD)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("applicants", sa.Column("bgd_application_id", sa.String(20), nullable=True))
    op.add_column("applicants", sa.Column("ivac_mission", sa.String(160), nullable=True))
    op.add_column("applicants", sa.Column("expected_journey_date", sa.Date(), nullable=True))
    op.add_column("applicants", sa.Column("port_of_arrival", sa.String(80), nullable=True))
    op.add_column("applicants", sa.Column("port_of_exit", sa.String(80), nullable=True))
    op.create_index("ix_applicants_bgd_application_id", "applicants", ["bgd_application_id"])


def downgrade() -> None:
    op.drop_index("ix_applicants_bgd_application_id", table_name="applicants")
    for col in ("port_of_exit", "port_of_arrival", "expected_journey_date", "ivac_mission",
                "bgd_application_id"):
        op.drop_column("applicants", col)
