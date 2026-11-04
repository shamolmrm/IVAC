"""BGD (online visa application form PDF): prefill a new applicant, or compare with a profile.

Results are returned, never stored here; the applicant form decides what is saved.
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
from app.modules.bgd import parser
from app.modules.documents import storage
from app.modules.documents.models import DocKind
from app.modules.documents.router import _load_doc, sniff

router = APIRouter(prefix="/bgd", tags=["bgd"])
PER_MINUTE = 20
NOT_BGD = ("এটি ভারতীয় ভিসার অনলাইন আবেদন ফর্মের (BGD…) PDF মনে হচ্ছে না। "
           "ফর্ম পূরণের পর ওয়েবসাইট থেকে যে PDF ডাউনলোড হয়, সেটিই দিন (স্ক্যান বা ছবি নয়)।")


class BgdOut(BaseModel):
    application_id: str | None
    registration_date: date | None
    ivac_mission: str | None
    surname: str | None
    given_name: str | None
    gender: str | None
    date_of_birth: date | None
    place_of_birth: str | None
    marital_status: str | None
    nid_number: str | None
    passport_number: str | None
    passport_issue_date: date | None
    passport_issue_place: str | None
    passport_expiry_date: date | None
    phone: str | None
    email: str | None
    present_address: str | None
    permanent_address: str | None
    father_name: str | None
    mother_name: str | None
    spouse_name: str | None
    occupation: str | None
    visa_type: str | None
    visa_type_raw: str | None
    visa_entries: str | None
    visa_period: str | None
    expected_journey_date: date | None
    port_of_arrival: str | None
    port_of_exit: str | None
    places_to_visit: str | None
    missing: list[str]


class Mismatch(BaseModel):
    field: str
    profile: str | None
    document: str | None


class CompareOut(BaseModel):
    bgd: BgdOut
    mismatches: list[Mismatch]


# profile fields that the BGD form also carries
COMPARED = (
    "surname", "given_name", "gender", "date_of_birth", "place_of_birth", "marital_status",
    "father_name", "mother_name", "spouse_name", "passport_number", "passport_issue_date",
    "passport_issue_place", "passport_expiry_date", "nid_number", "email", "visa_type",
    "bgd_application_id", "ivac_mission", "expected_journey_date", "port_of_arrival",
    "port_of_exit",
)


async def _limit(user: User, store: KeyValueStore) -> None:
    if await hit_rate_limit(store, f"rl:bgd:{user.id}", PER_MINUTE):
        raise HTTPException(status_code=429, detail="এক মিনিট পরে আবার চেষ্টা করুন।")


async def _read(data: bytes) -> BgdOut:
    if sniff(data) != "application/pdf":
        raise HTTPException(status_code=415, detail="BGD ফর্মের PDF ফাইল দিন।")
    if not parser.available():
        raise HTTPException(status_code=503, detail="PDF পড়ার সেবা এখন চালু নেই।")
    try:
        text = await run_in_threadpool(parser.pdf_text, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="PDF ফাইলটি খোলা যাচ্ছে না।") from exc
    result = parser.parse(text)
    if not parser.looks_like_bgd(result):
        raise HTTPException(status_code=422, detail=NOT_BGD)
    return BgdOut(**result.as_dict())


@router.post("/parse", response_model=BgdOut)
async def parse_upload(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> BgdOut:
    """Read a BGD PDF to prefill a new applicant. The file is not kept by this call."""
    await _limit(user, store)
    limit = get_settings().document_max_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="ফাইল ১০ MB-এর বেশি হতে পারবে না।")
    result = await _read(data)
    audit(db, "bgd.parse", actor_id=user.id, detail={"missing": result.missing}, request=request)
    db.commit()
    return result


def _fmt(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = getattr(value, "value", value)  # enums
    return " ".join(str(text).split()).upper()


@router.post("/documents/{doc_id}", response_model=CompareOut)
async def compare_document(
    doc_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> CompareOut:
    """Read an uploaded BGD form and compare it with the applicant profile."""
    await _limit(user, store)
    doc, a, _ = _load_doc(db, doc_id, user)
    if doc.kind != DocKind.bgd_form:
        raise HTTPException(status_code=422, detail="শুধু BGD ফর্ম যাচাই করা যায়।")
    try:
        data = storage.load(doc.storage_key, doc.id)
    except Exception as exc:  # noqa: BLE001 — missing or tampered file
        raise HTTPException(status_code=410, detail="ফাইলটি পড়া যাচ্ছে না।") from exc
    bgd = await _read(data)

    found = bgd.model_dump() | {"bgd_application_id": bgd.application_id}
    profile = {k: getattr(a, k, None) for k in COMPARED}
    profile["passport_number"] = applicant_svc.passport_number(a)
    profile["nid_number"] = applicant_svc.nid_number(a)
    mismatches = [
        Mismatch(field=k, profile=_fmt(profile[k]), document=_fmt(found[k]))
        for k in COMPARED
        if found.get(k) not in (None, "") and _fmt(found[k]) != _fmt(profile[k])
    ]
    audit(db, "bgd.document", actor_id=user.id, target_type="applicant", target_id=a.id,
          detail={"document": str(doc.id), "mismatches": [m.field for m in mismatches]},
          request=request)
    db.commit()
    return CompareOut(bgd=bgd, mismatches=mismatches)
