"""Passport OCR: prefill a new applicant, or compare an uploaded passport with the profile.

Results are returned, never stored: plain passport data must not sit unencrypted anywhere.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.cache import KeyValueStore, get_redis, hit_rate_limit
from app.core.config import get_settings
from app.core.db import get_db
from app.modules.applicants import service as applicant_svc
from app.modules.audit.service import audit
from app.modules.auth.models import User
from app.modules.auth.security import current_user
from app.modules.documents import storage
from app.modules.documents.models import DocKind
from app.modules.documents.router import _load_doc, sniff
from app.modules.ocr import engine

router = APIRouter(prefix="/ocr", tags=["ocr"])
OCR_PER_MINUTE = 10


class PassportData(BaseModel):
    surname: str
    given_name: str
    passport_number: str
    nationality: str
    issuing_country: str
    date_of_birth: date | None
    passport_expiry_date: date | None
    gender: str | None
    checks: dict[str, bool]
    valid: bool


class Mismatch(BaseModel):
    field: str
    profile: str | None
    passport: str | None


class CompareOut(BaseModel):
    passport: PassportData
    mismatches: list[Mismatch]


NOT_READ = "পাসপোর্টের নিচের দুই লাইনের লেখা (MRZ) পড়া যায়নি। পরিষ্কার, সোজা ও পুরো পাতার ছবি দিন।"


async def _limit(user: User, store: KeyValueStore) -> None:
    if await hit_rate_limit(store, f"rl:ocr:{user.id}", OCR_PER_MINUTE):
        raise HTTPException(status_code=429, detail="এক মিনিট পরে আবার চেষ্টা করুন।")


async def _read(data: bytes) -> PassportData:
    content_type = sniff(data)
    if content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=415, detail="পাসপোর্টের JPG বা PNG ছবি দিন।")
    if not engine.available():
        raise HTTPException(status_code=503, detail="OCR সেবা এখন চালু নেই।")
    try:
        result = await run_in_threadpool(engine.read_passport, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="ছবিটি খোলা যাচ্ছে না।") from exc
    if result is None:
        raise HTTPException(status_code=422, detail=NOT_READ)
    return PassportData(**result.as_dict())


@router.post("/passport", response_model=PassportData)
async def read_upload(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> PassportData:
    """Read a passport photo to prefill a new applicant. The image is not kept."""
    await _limit(user, store)
    limit = get_settings().document_max_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="ফাইল ১০ MB-এর বেশি হতে পারবে না।")
    result = await _read(data)
    audit(db, "ocr.passport", actor_id=user.id, detail={"valid": result.valid}, request=request)
    db.commit()
    return result


def _fmt(value: object) -> str | None:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, date) else str(value).strip().upper()


@router.post("/documents/{doc_id}", response_model=CompareOut)
async def read_document(
    doc_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> CompareOut:
    """Read an uploaded passport page and compare it with the applicant profile."""
    await _limit(user, store)
    doc, a, _ = _load_doc(db, doc_id, user)
    if doc.kind != DocKind.passport_bio:
        raise HTTPException(status_code=422, detail="শুধু পাসপোর্টের তথ্য পাতা পড়া যায়।")
    try:
        data = storage.load(doc.storage_key, doc.id)
    except Exception as exc:  # noqa: BLE001 — missing or tampered file
        raise HTTPException(status_code=410, detail="ফাইলটি পড়া যাচ্ছে না।") from exc
    result = await _read(data)

    profile = {
        "surname": a.surname,
        "given_name": a.given_name,
        "passport_number": applicant_svc.passport_number(a),
        "date_of_birth": a.date_of_birth,
        "passport_expiry_date": a.passport_expiry_date,
        "gender": a.gender.value,
        "nationality": a.nationality,
    }
    read = result.model_dump()
    mismatches = [
        Mismatch(field=k, profile=_fmt(v), passport=_fmt(read[k]))
        for k, v in profile.items()
        if read[k] is not None and _fmt(read[k]) != _fmt(v)
    ]
    audit(db, "ocr.document", actor_id=user.id, target_type="applicant", target_id=a.id,
          detail={"document": str(doc.id), "valid": result.valid,
                  "mismatches": [m.field for m in mismatches]}, request=request)
    db.commit()
    return CompareOut(passport=result, mismatches=mismatches)
