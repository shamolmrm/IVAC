"""Applicant documents: encrypted upload, checklist, download, removal."""

import hashlib
import logging
import re
import uuid
from datetime import datetime

from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.modules.applicants.access import load_applicant
from app.modules.applicants.models import VisaType
from app.modules.audit.service import audit
from app.modules.auth.models import User
from app.modules.auth.security import current_user
from app.modules.documents import storage
from app.modules.documents.models import DocKind, Document
from app.modules.organizations.models import OrgRole

log = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])

MAX_PER_APPLICANT = 40
IMAGE_ONLY = {DocKind.photo}

# General checklist (not an official list; IVAC rules change — the UI says so).
COMMON = [DocKind.passport_bio, DocKind.photo, DocKind.bgd_form, DocKind.nid]
CHECKLIST: dict[VisaType, list[DocKind]] = {
    VisaType.tourist: [*COMMON, DocKind.bank_statement],
    VisaType.medical: [*COMMON, DocKind.medical_letter],
    VisaType.medical_attendant: [*COMMON, DocKind.medical_letter],
    VisaType.business: [*COMMON, DocKind.invitation_letter, DocKind.bank_statement],
    VisaType.student: [*COMMON, DocKind.student_letter],
    VisaType.entry: COMMON,
    VisaType.other: COMMON,
}


class DocumentOut(BaseModel):
    id: uuid.UUID
    kind: DocKind
    original_name: str
    content_type: str
    size: int
    created_at: datetime | None


class ChecklistItem(BaseModel):
    kind: DocKind
    done: bool


class DocumentsOut(BaseModel):
    documents: list[DocumentOut]
    checklist: list[ChecklistItem]
    complete: bool


def sniff(data: bytes) -> str | None:
    """Content type from the file's own bytes (never trust the client's claim)."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def _safe_name(name: str | None, content_type: str) -> str:
    base = re.sub(r"[^\w.\- ]", "_", (name or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
    base = base.strip(" .")[:150] or "document"
    ext = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}[content_type]
    return base if base.lower().endswith(ext) else f"{base}{ext}"


def _out(d: Document) -> DocumentOut:
    return DocumentOut(id=d.id, kind=d.kind, original_name=d.original_name,
                       content_type=d.content_type, size=d.size, created_at=d.created_at)


def _active(db: Session, applicant_id: uuid.UUID) -> list[Document]:
    return list(db.scalars(
        select(Document)
        .where(Document.applicant_id == applicant_id, Document.archived_at.is_(None))
        .order_by(Document.created_at.desc())
    ))


@router.get("/applicants/{applicant_id}/documents", response_model=DocumentsOut)
def list_documents(
    applicant_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> DocumentsOut:
    a, _ = load_applicant(db, applicant_id, user)
    docs = _active(db, a.id)
    have = {d.kind for d in docs}
    items = [ChecklistItem(kind=k, done=k in have) for k in CHECKLIST[a.visa_type]]
    return DocumentsOut(documents=[_out(d) for d in docs], checklist=items,
                        complete=all(i.done for i in items))


@router.post("/applicants/{applicant_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    applicant_id: uuid.UUID,
    request: Request,
    kind: DocKind = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    a, _ = load_applicant(db, applicant_id, user, write=True)
    limit = get_settings().document_max_bytes
    data = await file.read(limit + 1)
    if not data:
        raise HTTPException(status_code=422, detail="ফাইলটি খালি।")
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="ফাইল ১০ MB-এর বেশি হতে পারবে না।")
    content_type = sniff(data)
    if content_type is None:
        raise HTTPException(status_code=415, detail="শুধু JPG, PNG বা PDF ফাইল দেওয়া যাবে।")
    if kind in IMAGE_ONLY and content_type == "application/pdf":
        raise HTTPException(status_code=415, detail="ছবির জন্য JPG বা PNG দিন।")
    if len(_active(db, a.id)) >= MAX_PER_APPLICANT:
        raise HTTPException(status_code=409, detail="এই আবেদনকারীর জন্য সর্বোচ্চ সংখ্যক ফাইল আছে।")
    digest = hashlib.sha256(data).hexdigest()
    same = db.scalar(select(Document.id).where(
        Document.applicant_id == a.id, Document.sha256 == digest, Document.archived_at.is_(None)
    ))
    if same:
        raise HTTPException(status_code=409, detail="এই ফাইলটি আগেই আপলোড করা হয়েছে।")

    doc_id = uuid.uuid4()
    key = storage.save(a.organization_id, doc_id, data)
    doc = Document(
        id=doc_id, applicant_id=a.id, organization_id=a.organization_id, kind=kind,
        original_name=_safe_name(file.filename, content_type), content_type=content_type,
        size=len(data), sha256=digest, storage_key=key, uploaded_by=user.id, created_at=utcnow(),
    )
    db.add(doc)
    audit(db, "document.upload", actor_id=user.id, target_type="applicant", target_id=a.id,
          detail={"document": str(doc_id), "kind": kind, "size": len(data)}, request=request)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)  # no orphan files
        raise
    return _out(doc)


def _load_doc(db: Session, doc_id: uuid.UUID, user: User, *, write: bool = False):  # noqa: ANN202
    doc = db.get(Document, doc_id)
    if doc is None or doc.archived_at is not None:
        raise HTTPException(status_code=404, detail="ফাইল পাওয়া যায়নি।")
    try:
        a, ctx = load_applicant(db, doc.applicant_id, user, write=write)
    except HTTPException:
        raise HTTPException(status_code=404, detail="ফাইল পাওয়া যায়নি।") from None
    return doc, a, ctx


@router.get("/documents/{doc_id}/download")
def download_document(
    doc_id: uuid.UUID,
    request: Request,
    inline: bool = False,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    doc, a, _ = _load_doc(db, doc_id, user)
    try:
        data = storage.load(doc.storage_key, doc.id)
    except (FileNotFoundError, ValueError, InvalidTag) as exc:  # missing or tampered
        log.error("document %s unreadable: %s", doc.id, exc)
        raise HTTPException(status_code=410, detail="ফাইলটি পড়া যাচ্ছে না।") from exc
    audit(db, "document.download", actor_id=user.id, target_type="applicant", target_id=a.id,
          detail={"document": str(doc.id)}, request=request)
    db.commit()
    disposition = "inline" if inline else "attachment"
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{doc.original_name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(
    doc_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    doc, a, ctx = _load_doc(db, doc_id, user, write=True)
    if ctx is not None and not ctx.at_least(OrgRole.manager) and doc.uploaded_by != user.id:
        raise HTTPException(status_code=403, detail="শুধু আপলোডকারী বা Manager ফাইল মুছতে পারেন।")
    doc.archived_at = utcnow()
    audit(db, "document.delete", actor_id=user.id, target_type="applicant", target_id=a.id,
          detail={"document": str(doc.id), "kind": doc.kind}, request=request)
    db.commit()
    storage.delete(doc.storage_key)  # personal data: remove the bytes, keep the audit record
    return Response(status_code=204)
