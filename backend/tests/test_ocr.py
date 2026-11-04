import io
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.modules.ocr import engine
from app.modules.ocr.mrz import check_digit, find_lines, parse_td3

# ICAO 9303 published specimen (fictional person, "Utopia")
L1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
L2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
TODAY = date(2010, 1, 1)


def test_check_digit() -> None:
    assert check_digit("L898902C3") == 6
    assert check_digit("740812") == 2
    assert check_digit("120415") == 9


def test_parse_specimen() -> None:
    r = parse_td3(L1, L2, today=TODAY)
    assert r.valid, r.checks
    assert (r.surname, r.given_name) == ("ERIKSSON", "ANNA MARIA")
    assert r.passport_number == "L898902C3"
    assert r.nationality == "UTO" and r.issuing_country == "UTO"
    assert r.date_of_birth == date(1974, 8, 12)
    assert r.passport_expiry_date == date(2012, 4, 15)
    assert r.gender == "female"


def test_repairs_ocr_lookalikes() -> None:
    # OCR read digit-zero as O in the dates and 8 as B in the passport number
    noisy = "L89B902C36UTO74O8122F12O4159ZE184226B<<<<<1O"
    r = parse_td3(L1, noisy, today=TODAY)
    assert r.valid, r.checks
    assert r.passport_number == "L898902C3"
    assert r.date_of_birth == date(1974, 8, 12)


def test_detects_wrong_digits() -> None:
    bad = L2[:13] + "7408132" + L2[20:]  # birth date changed, check digit not
    assert parse_td3(L1, bad, today=TODAY).checks["date_of_birth"] is False


def test_find_lines_in_noisy_text() -> None:
    text = f"REPUBLIC\nsome noise 123\n{L1[:40]} \n {L2.replace('<', '«')}\n"
    lines = find_lines(text)
    assert lines is not None
    assert lines[0].startswith("P<UTOERIKSSON") and len(lines[0]) == 44
    assert lines[1] == L2


def _mrz_image() -> bytes:
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    if font_path.exists():
        font = ImageFont.truetype(str(font_path), 48)
    else:
        font = ImageFont.load_default(48)
    img = Image.new("L", (1700, 500), 255)
    d = ImageDraw.Draw(img)
    d.text((40, 300), L1, font=font, fill=0)
    d.text((40, 380), L2, font=font, fill=0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.skipif(not engine.available(), reason="tesseract not installed")
def test_tesseract_reads_rendered_mrz() -> None:
    r = engine.read_passport(_mrz_image())
    assert r is not None
    assert r.passport_number == "L898902C3"
    assert r.checks["passport_number"] and r.checks["date_of_birth"]


# ── API ──

PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def docs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(get_settings(), "documents_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
def me(client: TestClient) -> TestClient:
    body = {"email": "me@example.com", "password": PASSWORD, "full_name": "Me"}
    assert client.post("/api/v1/auth/register", json=body).status_code == 201
    return client


@pytest.fixture
def fake_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "available", lambda: True)
    monkeypatch.setattr(engine, "read_passport", lambda data: parse_td3(L1, L2, today=TODAY))


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def test_prefill_endpoint(me: TestClient, fake_ocr: None) -> None:
    r = me.post("/api/v1/ocr/passport", files={"file": ("p.png", PNG, "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["passport_number"] == "L898902C3" and r.json()["valid"] is True
    pdf = me.post("/api/v1/ocr/passport", files={"file": ("p.pdf", b"%PDF-1.4", "x")})
    assert pdf.status_code == 415


def test_compare_with_profile(me: TestClient, fake_ocr: None) -> None:
    body = {
        "surname": "Eriksson", "given_name": "Anna Maria", "gender": "female",
        "date_of_birth": "1974-08-12", "passport_number": "L898902C3",
        "passport_expiry_date": (date.today() + timedelta(days=900)).isoformat(),
        "visa_type": "tourist", "nationality": "UTO",
    }
    aid = me.post("/api/v1/applicants", json=body).json()["applicant"]["id"]
    doc = me.post(f"/api/v1/applicants/{aid}/documents", data={"kind": "passport_bio"},
                  files={"file": ("p.png", PNG, "image/png")}).json()
    r = me.post(f"/api/v1/ocr/documents/{doc['id']}")
    assert r.status_code == 200, r.text
    # only the expiry date differs (the specimen expired in 2012)
    assert [m["field"] for m in r.json()["mismatches"]] == ["passport_expiry_date"]


def test_ocr_requires_access(me: TestClient, fake_ocr: None) -> None:
    body = {
        "surname": "Eriksson", "given_name": "Anna", "gender": "female",
        "date_of_birth": "1974-08-12", "passport_number": "L898902C3",
        "passport_expiry_date": (date.today() + timedelta(days=900)).isoformat(),
        "visa_type": "tourist",
    }
    aid = me.post("/api/v1/applicants", json=body).json()["applicant"]["id"]
    doc = me.post(f"/api/v1/applicants/{aid}/documents", data={"kind": "passport_bio"},
                  files={"file": ("p.png", PNG, "image/png")}).json()
    me.post("/api/v1/auth/logout")
    assert me.post(f"/api/v1/ocr/documents/{doc['id']}").status_code == 401
    other = {"email": "x@example.com", "password": PASSWORD, "full_name": "Other User"}
    assert me.post("/api/v1/auth/register", json=other).status_code == 201
    assert me.post(f"/api/v1/ocr/documents/{doc['id']}").status_code == 404
