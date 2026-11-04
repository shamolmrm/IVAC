import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import sms
from app.modules.auth.models import PhoneOtp
from app.modules.auth.phone_router import normalise_phone

PASSWORD = "correct horse battery"


def register(client: TestClient, email: str = "a@example.com") -> None:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Rahim Uddin"},
    )
    assert r.status_code == 201, r.text


@pytest.fixture
def texts(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(sms, "sms_enabled", lambda: True)
    monkeypatch.setattr(sms, "send_sms", lambda phone, msg: sent.append((phone, msg)))
    return sent


def code_in(msg: str) -> str:
    m = re.search(r"\d{6}", msg)
    assert m
    return m.group(0)


def test_normalise_phone() -> None:
    for raw in ("01712345678", "+8801712345678", "8801712345678", "017-1234 5678"):
        assert normalise_phone(raw) == "+8801712345678"
    for raw in ("01212345678", "0171234567", "+911712345678", "abc"):
        assert normalise_phone(raw) is None


def test_phone_verification_flow(client: TestClient, db_session: Session, texts: list) -> None:
    register(client)
    r = ask(client, "01712345678")
    assert r.status_code == 202, r.text
    assert texts[0][0] == "+8801712345678"
    code = code_in(texts[0][1])
    otp = db_session.scalar(select(PhoneOtp))
    assert otp and code not in otp.code_hash  # only a hash is stored

    r = check(client, code)
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == "+8801712345678" and r.json()["phone_verified"] is True
    # single use
    assert check(client, code).status_code == 400


def test_wrong_codes_burn_the_otp(client: TestClient, texts: list) -> None:
    register(client)
    ask(client, "01712345678")
    code = code_in(texts[0][1])
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert check(client, wrong).status_code == 400
    # the right code no longer works after 5 failures
    assert check(client, code).status_code == 400


def test_resend_is_throttled(client: TestClient, texts: list) -> None:
    register(client)
    assert ask(client, "01712345678").status_code == 202
    assert ask(client, "01712345678").status_code == 429
    assert len(texts) == 1


def test_number_can_belong_to_one_account_only(
    client: TestClient, texts: list
) -> None:
    register(client, "a@example.com")
    ask(client, "01712345678")
    check(client, code_in(texts[0][1]))
    client.post("/api/v1/auth/logout")

    register(client, "b@example.com")
    r = ask(client, "+8801712345678")
    assert r.status_code == 409


def test_invalid_number_and_disabled_sms(client: TestClient, texts: list) -> None:
    register(client)
    assert ask(client, "0123456789").status_code == 422


def test_sms_off_by_default(client: TestClient) -> None:
    register(client)
    assert client.get("/api/v1/auth/features").json() == {"email": False, "sms": False}
    assert ask(client, "01712345678").status_code == 503


def test_requires_login(client: TestClient) -> None:
    assert ask(client, "01712345678").status_code == 401


def ask(client: TestClient, phone: str):
    return client.post("/api/v1/auth/phone/request", json={"phone": phone})


def check(client: TestClient, code: str):
    return client.post("/api/v1/auth/phone/verify", json={"code": code})
