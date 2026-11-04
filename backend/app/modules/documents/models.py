import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DocKind(enum.StrEnum):
    passport_bio = "passport_bio"  # passport photo/data page
    photo = "photo"  # applicant photograph
    bgd_form = "bgd_form"  # printed online application form (BGD number)
    nid = "nid"  # national ID card
    bank_statement = "bank_statement"
    address_proof = "address_proof"  # utility bill etc.
    previous_visa = "previous_visa"
    medical_letter = "medical_letter"  # hospital / doctor letter (medical visas)
    invitation_letter = "invitation_letter"  # business / conference invitation
    student_letter = "student_letter"  # admission letter (student visas)
    other = "other"


class Document(Base):
    """An uploaded file. The bytes live encrypted on disk under `storage_key`."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[DocKind] = mapped_column(Enum(DocKind, name="doc_kind", native_enum=False,
                                               length=24))
    original_name: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(40))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(120), unique=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
