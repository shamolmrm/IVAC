"""Validation, normalisation and duplicate detection for applicants."""

import re
import uuid
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.crypto import blind_index, decrypt, encrypt
from app.modules.applicants.models import Applicant
from app.modules.auth.phone_router import normalise_phone
from app.modules.organizations.models import DIRECT_ORG_ID

PASSPORT_RE = re.compile(r"^[A-Z0-9]{6,12}$")
NID_RE = re.compile(r"^(\d{10}|\d{13}|\d{17})$")
SIX_MONTHS = timedelta(days=183)
DUPLICATE_PASSPORT = "এই পাসপোর্ট নম্বর দিয়ে আগেই একজন আবেদনকারী আছে।"
SAME_PERSON = (
    "একই নাম ও জন্মতারিখের আরেকজন আবেদনকারী আছেন (ভিন্ন পাসপোর্ট)। "
    "একই ব্যক্তি কি না যাচাই করুন।"
)


def normalise_passport(raw: str) -> str:
    value = re.sub(r"[\s\-]", "", raw).upper()
    if not PASSPORT_RE.match(value):
        raise HTTPException(status_code=422, detail="পাসপোর্ট নম্বর সঠিক নয় (শুধু ইংরেজি অক্ষর ও সংখ্যা)।")
    return value


def normalise_nid(raw: str) -> str:
    value = re.sub(r"[\s\-]", "", raw)
    if not NID_RE.match(value):
        raise HTTPException(status_code=422, detail="NID নম্বর ১০, ১৩ বা ১৭ সংখ্যার হতে হবে।")
    return value


def dedupe_scope(org_id: uuid.UUID, creator_id: uuid.UUID) -> str:
    return f"direct:{creator_id}" if org_id == DIRECT_ORG_ID else str(org_id)


def check_dates(
    dob: date, issue: date | None, expiry: date, today: date | None = None
) -> list[str]:
    """Raise for impossible dates; return warnings for risky ones."""
    today = today or date.today()
    if not (date(1900, 1, 1) <= dob < today):
        raise HTTPException(status_code=422, detail="জন্মতারিখ সঠিক নয়।")
    if issue and not (dob < issue <= today):
        raise HTTPException(status_code=422, detail="পাসপোর্ট ইস্যুর তারিখ সঠিক নয়।")
    if issue and expiry <= issue:
        raise HTTPException(status_code=422, detail="মেয়াদ শেষের তারিখ ইস্যুর তারিখের পরে হতে হবে।")
    if expiry <= today:
        raise HTTPException(status_code=422, detail="পাসপোর্টের মেয়াদ শেষ। নতুন পাসপোর্ট দিয়ে আবেদন করুন।")
    warnings = []
    if expiry - today < SIX_MONTHS:
        warnings.append("পাসপোর্টের মেয়াদ ৬ মাসের কম আছে। ভিসা আবেদনে সমস্যা হতে পারে।")
    return warnings


def set_passport(a: Applicant, number: str) -> None:
    a.passport_enc = encrypt(number)
    a.passport_index = blind_index(f"passport:{number}")
    a.passport_last3 = number[-3:]


def set_nid(a: Applicant, number: str | None) -> None:
    a.nid_enc = encrypt(number) if number else None
    a.nid_index = blind_index(f"nid:{number}") if number else None


def passport_number(a: Applicant) -> str:
    return decrypt(a.passport_enc)


def nid_number(a: Applicant) -> str | None:
    return decrypt(a.nid_enc) if a.nid_enc else None


def clean_phone(raw: str | None) -> str | None:
    if not raw or not raw.strip():
        return None
    phone = normalise_phone(raw)
    if phone is None:
        raise HTTPException(status_code=422, detail="সঠিক বাংলাদেশি মোবাইল নম্বর দিন (01XXXXXXXXX)।")
    return phone


def ensure_unique_passport(db: Session, a: Applicant) -> None:
    """Hard rule: one active applicant per passport within the same scope."""
    clash = db.scalar(
        select(Applicant.id).where(
            Applicant.dedupe_scope == a.dedupe_scope,
            Applicant.passport_index == a.passport_index,
            Applicant.archived_at.is_(None),
            Applicant.id != a.id,
        )
    )
    if clash:
        raise HTTPException(
            status_code=409, detail=DUPLICATE_PASSPORT, headers={"X-Duplicate-Of": str(clash)}
        )


def soft_duplicate_warnings(db: Session, a: Applicant) -> list[str]:
    """Same name + date of birth with a different passport inside the same scope."""
    same_person = db.scalar(
        select(func.count(Applicant.id)).where(
            Applicant.dedupe_scope == a.dedupe_scope,
            Applicant.archived_at.is_(None),
            Applicant.id != a.id,
            Applicant.date_of_birth == a.date_of_birth,
            func.lower(Applicant.surname) == a.surname.lower(),
            func.lower(Applicant.given_name) == a.given_name.lower(),
        )
    )
    return [SAME_PERSON] if same_person else []


def exists_in_other_scope(db: Session, a: Applicant) -> bool:
    """Same passport in another agency / individual. Never revealed to the caller."""
    return bool(
        db.scalar(
            select(Applicant.id).where(
                Applicant.passport_index == a.passport_index,
                Applicant.dedupe_scope != a.dedupe_scope,
                Applicant.archived_at.is_(None),
            )
        )
    )
