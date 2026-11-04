"""BGD form parsing. The layout mirrors `pdftotext -layout` output of the real form;
every value here is invented test data, not a real person."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.modules.bgd import parser

PAD = " " * 67
FUTURE = (date.today() + timedelta(days=2000)).strftime("%d-%b-%Y").upper()
SAMPLE = f"""
                                                                  ASST HIGH COMMISSION OF INDIA KHULNA

                                                                             TESTBGD0001

{PAD}A. Personal Particulars (As in Passport)

Web Registration Date : 01-OCT-2026 Application Id : TESTBGD0001  Surname (As in Passport)            TESTER

{PAD}Given Name (As in Passport)         ANNA MARIA

{PAD}Previous/other Name if any          Not Applicable

{PAD}Gender                              FEMALE                      Marital Status                              SINGLE

{PAD}Date of Birth                       05-MAR-1990                 Religion                                    OTHERS

{PAD}Place of Birth Town/City            SAMPLETOWN                  Country of Birth                            BANGLADESH

{PAD}Citizenship /National ID No         1234567890                  Educational Qualification                   GRADUATE

{PAD}B. Passport Details

{PAD}Passport No.             X01234567                  Date of Issue ( dd/mm/yyyy )                        10-JAN-2024

{PAD}Place of Issue           DHAKA                      Date of Expiry ( dd/mm/yyyy )                       {FUTURE}

{PAD}Country of Issue                                    Place of Issue

{PAD}C. Applicant's Contact Details

{PAD}Present                  HOUSE 1, ROAD 2            Phone No                         01700000000

{PAD}Address                  SAMPLE AREA                Mobile /Cell No                  8801700000000

{PAD}                         SAMPLETOWN, BANGLADESH 1000   Email address                 TEST@EXAMPLE.COM

{PAD}Permanent                VILLAGE TEST
{PAD}Address                  SAMPLE UPAZILA
{PAD}                         SAMPLETOWN

{PAD}D. Family Details

{PAD}Father's           TEST FATHER                      BANGLADESH                       BANGLADESH             SAMPLETOWN

{PAD}Mother's           TEST MOTHER                      BANGLADESH                       BANGLADESH             SAMPLETOWN

E. Details of Visa Sought      (Visa shall be valid from the Date of Issue and not from the Date of Journey)

Type Of Visa Required          MEDICAL VISA                              No of Entries             DOUBLE

Period of Visa ( Month)        6 Month                                   Expected Date of Journey  20-DEC-2026

Port Of Arrival                BY ROAD BENAPOLE                          Port of Exit              BY ROAD BENAPOLE

Places to be Visited           KOLKATA

G. Profession/Occupation Details :

Present Occupation             SERVICE                                 Designation/Rank
"""


def test_parse_sample() -> None:
    d = parser.parse(SAMPLE)
    assert d.application_id == "TESTBGD0001"
    assert d.registration_date == date(2026, 10, 1)
    assert d.ivac_mission == "ASST HIGH COMMISSION OF INDIA KHULNA"
    assert (d.surname, d.given_name, d.gender) == ("TESTER", "ANNA MARIA", "female")
    assert d.date_of_birth == date(1990, 3, 5) and d.marital_status == "single"
    assert d.place_of_birth == "SAMPLETOWN" and d.nid_number == "1234567890"
    assert d.passport_number == "X01234567" and d.passport_issue_place == "DHAKA"
    assert d.passport_issue_date == date(2024, 1, 10)
    assert d.phone == "01700000000" and d.email == "test@example.com"
    assert d.present_address == "HOUSE 1, ROAD 2, SAMPLE AREA, SAMPLETOWN, BANGLADESH 1000"
    assert d.permanent_address == "VILLAGE TEST, SAMPLE UPAZILA, SAMPLETOWN"
    assert (d.father_name, d.mother_name, d.spouse_name) == ("TEST FATHER", "TEST MOTHER", None)
    assert d.visa_type == "medical" and d.visa_entries == "DOUBLE"
    assert d.expected_journey_date == date(2026, 12, 20)
    assert d.port_of_arrival == "BY ROAD BENAPOLE" and d.occupation == "SERVICE"
    assert d.missing == []


def test_not_a_bgd() -> None:
    d = parser.parse("Bank statement\nAccount   12345")
    assert not parser.looks_like_bgd(d)


# ── API ──

PDF = b"%PDF-1.4\n" + b"0" * 64


@pytest.fixture(autouse=True)
def docs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(get_settings(), "documents_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
def me(client: TestClient) -> TestClient:
    body = {"email": "me@example.com", "password": "correct horse battery", "full_name": "Me"}
    assert client.post("/api/v1/auth/register", json=body).status_code == 201
    return client


@pytest.fixture
def fake_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parser, "available", lambda: True)
    monkeypatch.setattr(parser, "pdf_text", lambda data: SAMPLE)


def test_parse_endpoint(me: TestClient, fake_pdf: None) -> None:
    r = me.post("/api/v1/bgd/parse", files={"file": ("f.pdf", PDF, "application/pdf")})
    assert r.status_code == 200, r.text
    assert r.json()["application_id"] == "TESTBGD0001"
    png = me.post("/api/v1/bgd/parse", files={"file": ("p.png", b"\x89PNG\r\n\x1a\n", "x")})
    assert png.status_code == 415


def test_create_from_bgd_then_compare(me: TestClient, fake_pdf: None) -> None:
    bgd = me.post("/api/v1/bgd/parse", files={"file": ("f.pdf", PDF, "application/pdf")}).json()
    keys = ("surname", "given_name", "gender", "date_of_birth", "passport_number",
            "passport_expiry_date", "visa_type", "nid_number", "ivac_mission",
            "expected_journey_date", "port_of_arrival", "port_of_exit")
    body = {k: bgd[k] for k in keys} | {"bgd_application_id": bgd["application_id"]}
    body["given_name"] = "ANNA"  # a typo to be caught
    r = me.post("/api/v1/applicants", json=body)
    assert r.status_code == 201, r.text
    a = r.json()["applicant"]
    assert a["bgd_application_id"] == "TESTBGD0001" and a["port_of_exit"] == "BY ROAD BENAPOLE"

    doc = me.post(f"/api/v1/applicants/{a['id']}/documents", data={"kind": "bgd_form"},
                  files={"file": ("f.pdf", PDF, "application/pdf")}).json()
    r = me.post(f"/api/v1/bgd/documents/{doc['id']}")
    assert r.status_code == 200, r.text
    fields = {m["field"] for m in r.json()["mismatches"]}
    assert "given_name" in fields and "passport_number" not in fields
    assert "bgd_application_id" not in fields
