import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import mailer
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import AuthSession, User

PASSWORD = "correct horse battery"


def register(client: TestClient, email: str = "a@example.com", name: str = "Rahim Uddin") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, str]]:
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mailer, "email_enabled", lambda: True)
    monkeypatch.setattr(mailer, "send_email", lambda to, s, b: sent.append((to, s, b)))
    return sent


def token_from(body: str) -> str:
    match = re.search(r"token=([\w-]+)", body)
    assert match
    return match.group(1)


def test_register_logs_in_and_hashes_password(client: TestClient, db_session: Session) -> None:
    user = register(client, "Rahim@Example.com")
    assert user["email"] == "rahim@example.com"
    assert user["email_verified"] is False and user["is_superadmin"] is False
    assert client.get("/api/v1/auth/me").json()["id"] == user["id"]
    stored = db_session.scalar(select(User))
    assert stored is not None and stored.password_hash.startswith("$argon2")
    # session token is stored hashed, never raw
    token = client.cookies.get("ivac_session")
    assert token and db_session.get(AuthSession, token) is None


def test_duplicate_email_rejected(client: TestClient) -> None:
    register(client)
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "A@example.com", "password": PASSWORD, "full_name": "Other"},
    )
    assert r.status_code == 409


def test_weak_password_and_bad_email_rejected(client: TestClient) -> None:
    for body in (
        {"email": "a@example.com", "password": "short", "full_name": "Rahim"},
        {"email": "not-an-email", "password": PASSWORD, "full_name": "Rahim"},
        {"email": "a@example.com", "password": PASSWORD, "full_name": ""},
    ):
        assert client.post("/api/v1/auth/register", json=body).status_code == 422


def test_login_logout_flow(client: TestClient, db_session: Session) -> None:
    register(client)
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401

    bad = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "nope"})
    unknown = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "x"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json()["detail"] == unknown.json()["detail"]  # no account enumeration

    ok = client.post("/api/v1/auth/login", json={"email": "A@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200
    actions = {e.action for e in db_session.scalars(select(AuditEvent))}
    assert {"user.register", "user.login", "user.login_failed"} <= actions


def test_account_locks_after_repeated_wrong_passwords(client: TestClient) -> None:
    register(client)
    client.post("/api/v1/auth/logout")
    for _ in range(5):
        r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "bad"})
        assert r.status_code == 401
    # even the right password is refused while locked
    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 429


def test_auth_rate_limited_per_ip(client: TestClient) -> None:
    codes = [
        client.post(
            "/api/v1/auth/login", json={"email": f"u{i}@example.com", "password": "x"}
        ).status_code
        for i in range(12)
    ]
    assert codes[-1] == 429


def test_disabled_account_cannot_log_in(client: TestClient, db_session: Session) -> None:
    register(client)
    user = db_session.scalar(select(User))
    assert user
    user.is_active = False
    db_session.commit()
    assert client.get("/api/v1/auth/me").status_code == 401  # existing session stops working
    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 403


def test_email_verification(client: TestClient, outbox: list) -> None:
    register(client)
    assert len(outbox) == 1 and outbox[0][0] == "a@example.com"
    token = token_from(outbox[0][2])
    assert client.post("/api/v1/auth/verify/confirm", json={"token": token}).status_code == 200
    assert client.get("/api/v1/auth/me").json()["email_verified"] is True
    # single use
    assert client.post("/api/v1/auth/verify/confirm", json={"token": token}).status_code == 400


def test_email_features_off_without_smtp(client: TestClient) -> None:
    assert client.get("/api/v1/auth/features").json() == {"email": False}
    register(client)
    assert client.post("/api/v1/auth/verify/request").status_code == 503


def test_password_reset_signs_out_other_sessions(
    client: TestClient, db_session: Session, outbox: list
) -> None:
    register(client)
    outbox.clear()
    r = client.post("/api/v1/auth/password/forgot", json={"email": "a@example.com"})
    same = client.post("/api/v1/auth/password/forgot", json={"email": "nobody@example.com"})
    assert r.status_code == same.status_code == 202
    assert r.json() == same.json()  # no account enumeration
    assert len(outbox) == 1
    token = token_from(outbox[0][2])

    new_password = "a much better passphrase"
    r = client.post("/api/v1/auth/password/reset", json={"token": token, "password": new_password})
    assert r.status_code == 200
    assert db_session.query(AuthSession).count() == 1  # only the fresh session remains
    client.post("/api/v1/auth/logout")
    ok = client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": new_password}
    )
    assert ok.status_code == 200


def test_password_change_requires_current_password(client: TestClient) -> None:
    register(client)
    wrong = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "wrong", "new_password": "another long password"},
    )
    assert wrong.status_code == 400
    ok = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": PASSWORD, "new_password": "another long password"},
    )
    assert ok.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200


def test_foreign_origin_blocked(client: TestClient) -> None:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": PASSWORD},
        headers={"origin": "https://evil.example"},
    )
    assert r.status_code == 403
