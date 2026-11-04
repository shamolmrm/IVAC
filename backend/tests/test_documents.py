from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.main import app
from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document

PASSWORD = "correct horse battery"
PDF = b"%PDF-1.4\n% test document\n%%EOF\n"
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(autouse=True)
def docs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(get_settings(), "documents_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
def browser(client: TestClient):
    extra: list[TestClient] = []

    def make(email: str) -> TestClient:
        c = TestClient(app)
        extra.append(c)
        body = {"email": email, "password": PASSWORD, "full_name": "Test"}
        assert c.post("/api/v1/auth/register", json=body).status_code == 201
        return c

    yield make
    for c in extra:
        c.close()


def applicant(c: TestClient, visa: str = "tourist") -> str:
    body = {
        "surname": "Uddin", "given_name": "Rahim", "gender": "male",
        "date_of_birth": "1990-05-17", "passport_number": "BX0123456",
        "passport_expiry_date": (date.today() + timedelta(days=2000)).isoformat(),
        "visa_type": visa,
    }
    r = c.post("/api/v1/applicants", json=body)
    assert r.status_code == 201, r.text
    return r.json()["applicant"]["id"]


def upload(c: TestClient, aid: str, kind: str, data: bytes, name: str = "file.pdf"):  # noqa: ANN201
    return c.post(
        f"/api/v1/applicants/{aid}/documents",
        data={"kind": kind},
        files={"file": (name, data, "application/octet-stream")},
    )


def test_upload_is_encrypted_and_downloadable(browser, docs_dir: Path, db_session: Session) -> None:
    me = browser("me@example.com")
    aid = applicant(me)
    r = upload(me, aid, "passport_bio", PDF, "../../etc/passport scan.pdf")
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["content_type"] == "application/pdf"
    assert doc["original_name"] == "passport scan.pdf"  # path parts stripped

    files = list(docs_dir.rglob("*.bin"))
    assert len(files) == 1
    assert PDF not in files[0].read_bytes()  # encrypted at rest

    d = me.get(f"/api/v1/documents/{doc['id']}/download")
    assert d.status_code == 200 and d.content == PDF
    assert d.headers["cache-control"] == "private, no-store"
    assert "attachment" in d.headers["content-disposition"]
    actions = {e.action for e in db_session.scalars(select(AuditEvent))}
    assert {"document.upload", "document.download"} <= actions


def test_checklist_follows_visa_type(browser) -> None:
    me = browser("me@example.com")
    aid = applicant(me, "medical")
    r = me.get(f"/api/v1/applicants/{aid}/documents").json()
    kinds = [i["kind"] for i in r["checklist"]]
    assert kinds == ["passport_bio", "photo", "bgd_form", "nid", "medical_letter"]
    assert r["complete"] is False
    for kind, data in (("passport_bio", PDF), ("photo", JPG), ("bgd_form", PDF + b"1"),
                       ("nid", PNG), ("medical_letter", PDF + b"2")):
        assert upload(me, aid, kind, data).status_code == 201
    assert me.get(f"/api/v1/applicants/{aid}/documents").json()["complete"] is True


def test_rejects_bad_files(browser, monkeypatch: pytest.MonkeyPatch) -> None:
    me = browser("me@example.com")
    aid = applicant(me)
    assert upload(me, aid, "passport_bio", b"MZ\x90\x00 evil exe").status_code == 415
    assert upload(me, aid, "photo", PDF).status_code == 415  # photo must be an image
    assert upload(me, aid, "passport_bio", b"").status_code == 422
    assert upload(me, aid, "bogus", PDF).status_code == 422
    monkeypatch.setattr(get_settings(), "document_max_bytes", 10)
    assert upload(me, aid, "passport_bio", PDF).status_code == 413
    monkeypatch.setattr(get_settings(), "document_max_bytes", 10 * 1024 * 1024)
    assert upload(me, aid, "passport_bio", PDF).status_code == 201
    assert upload(me, aid, "bgd_form", PDF).status_code == 409  # identical file again


def test_other_users_cannot_access(browser, docs_dir: Path, db_session: Session) -> None:
    me = browser("me@example.com")
    other = browser("other@example.com")
    aid = applicant(me)
    doc_id = upload(me, aid, "passport_bio", PDF).json()["id"]
    assert other.get(f"/api/v1/documents/{doc_id}/download").status_code == 404
    assert other.get(f"/api/v1/applicants/{aid}/documents").status_code == 404
    assert upload(other, aid, "photo", JPG).status_code == 404
    assert other.delete(f"/api/v1/documents/{doc_id}").status_code == 404

    assert me.delete(f"/api/v1/documents/{doc_id}").status_code == 204
    assert list(docs_dir.rglob("*.bin")) == []  # bytes removed
    assert me.get(f"/api/v1/documents/{doc_id}/download").status_code == 404
    row = db_session.scalar(select(Document))
    assert row is not None and row.archived_at is not None  # record kept for the audit trail


def test_tampered_file_is_refused(browser, docs_dir: Path) -> None:
    me = browser("me@example.com")
    aid = applicant(me)
    doc_id = upload(me, aid, "passport_bio", PDF).json()["id"]
    path = next(docs_dir.rglob("*.bin"))
    blob = bytearray(path.read_bytes())
    blob[-1] ^= 0xFF
    path.write_bytes(bytes(blob))
    assert me.get(f"/api/v1/documents/{doc_id}/download").status_code == 410
