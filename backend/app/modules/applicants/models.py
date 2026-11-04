import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Gender(enum.StrEnum):
    male = "male"
    female = "female"
    other = "other"


class MaritalStatus(enum.StrEnum):
    single = "single"
    married = "married"
    divorced = "divorced"
    widowed = "widowed"


class VisaType(enum.StrEnum):
    tourist = "tourist"
    medical = "medical"
    medical_attendant = "medical_attendant"
    business = "business"
    student = "student"
    entry = "entry"
    other = "other"


def _enum(e: type[enum.StrEnum], name: str) -> Enum:
    return Enum(e, name=name, native_enum=False, length=24)


class Applicant(TimestampMixin, Base):
    """One person applying for a visa. Belongs to exactly one organization (tenant).

    Passport and NID numbers are stored encrypted (`*_enc`) with a keyed blind index (`*_index`)
    for exact-match lookups and duplicate detection. Only the last 3 characters are kept in
    clear (`passport_last3`) for lists.
    """

    __tablename__ = "applicants"
    __table_args__ = (
        Index(
            "uq_applicant_scope_passport",
            "dedupe_scope",
            "passport_index",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
            sqlite_where=text("archived_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Duplicate-check scope: the agency id, or "direct:<user id>" for individual applicants
    dedupe_scope: Mapped[str] = mapped_column(String(64))

    # Identity (as printed in the passport)
    surname: Mapped[str] = mapped_column(String(80))
    given_name: Mapped[str] = mapped_column(String(120))
    gender: Mapped[Gender] = mapped_column(_enum(Gender, "gender"))
    date_of_birth: Mapped[date] = mapped_column(Date, index=True)
    place_of_birth: Mapped[str | None] = mapped_column(String(120))
    nationality: Mapped[str] = mapped_column(String(3), default="BGD")
    marital_status: Mapped[MaritalStatus | None] = mapped_column(
        _enum(MaritalStatus, "marital_status")
    )
    father_name: Mapped[str | None] = mapped_column(String(160))
    mother_name: Mapped[str | None] = mapped_column(String(160))
    spouse_name: Mapped[str | None] = mapped_column(String(160))

    # Passport (number encrypted)
    passport_enc: Mapped[str] = mapped_column(String(200))
    passport_index: Mapped[str] = mapped_column(String(64), index=True)
    passport_last3: Mapped[str] = mapped_column(String(3))
    passport_issue_date: Mapped[date | None] = mapped_column(Date)
    passport_expiry_date: Mapped[date] = mapped_column(Date)
    passport_issue_place: Mapped[str | None] = mapped_column(String(120))

    # National ID (encrypted, optional)
    nid_enc: Mapped[str | None] = mapped_column(String(200))
    nid_index: Mapped[str | None] = mapped_column(String(64), index=True)

    # Contact & other
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(254))
    present_address: Mapped[str | None] = mapped_column(String(400))
    permanent_address: Mapped[str | None] = mapped_column(String(400))
    occupation: Mapped[str | None] = mapped_column(String(120))
    visa_type: Mapped[VisaType] = mapped_column(_enum(VisaType, "visa_type"))
    notes: Mapped[str | None] = mapped_column(Text)

    # From the online application form (BGD…): needed when booking the appointment
    bgd_application_id: Mapped[str | None] = mapped_column(String(20), index=True)
    ivac_mission: Mapped[str | None] = mapped_column(String(160))
    expected_journey_date: Mapped[date | None] = mapped_column(Date)
    port_of_arrival: Mapped[str | None] = mapped_column(String(80))
    port_of_exit: Mapped[str | None] = mapped_column(String(80))

    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
