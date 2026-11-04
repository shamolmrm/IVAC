import re
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.modules.applicants.models import Applicant
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import User

PASSWORD = "correct horse battery"
FUTURE = (date.today() + timedelta(days=5 * 365)).isoformat()


def person(passport: str = "BX0123456", **over) -> dict:
    body = {
        "surname": "Uddin",
        "given_name": "Rahim",
        "gender": "male",
        "date_of_birth": "1990-05-17",
        "passport_number": passport,
        "passport_issue_date": "2022-01-10",
        "passport_expiry_date": FUTURE,
        "visa_type": "tourist",
        "phone": "01712345678",
    }
    body.update(over)
    return body


@pytest.fixture
def browser(client: TestClient):
    extra: list[TestClient] = []

    def make(email: str) -> TestClient:
        c = TestClient(app)
        extra.append(c)
        r = c.post(
            "/api/v1/auth/register",
            json={"email": email, "password": PASSWORD, "full_name": "Test"},
        )
        assert r.status_code == 201, r.text
        return c

    yield make
    for c in extra:
        c.close()


def superadmin(db: Session, browser) -> TestClient:  # noqa: ANN001
    admin = browser("admin@example.com")
    user = db.scalar(select(User).where(User.email == "admin@example.com"))
    assert user
    user.is_superadmin = True
    db.commit()
    return admin


def agency(owner: TestClient, admin: TestClient, name: str) -> str:
    org_id = owner.post("/api/v1/orgs", json={"name": name}).json()["id"]
    assert admin.post(f"/api/v1/admin/orgs/{org_id}/status", json={"status": "active"}).is_success
    return org_id


def join(owner: TestClient, org_id: str, member: TestClient, email: str, role: str) -> None:
    r = owner.post(f"/api/v1/orgs/{org_id}/invites", json={"email": email, "role": role})
    token = re.search(r"token=([\w-]+)", r.json()["link"]).group(1)  # type: ignore[union-attr]
    assert member.post("/api/v1/invites/accept", json={"token": token}).is_success


# ── Individuals ──


def test_individual_creates_and_reads_own_applicant(browser, db_session: Session) -> None:
    me = browser("me@example.com")
    r = me.post("/api/v1/applicants", json=person(passport="bx 012-3456"))
    assert r.status_code == 201, r.text
    a = r.json()["applicant"]
    assert a["passport_number"] == "BX0123456"  # normalised
    assert a["surname"] == "UDDIN" and a["phone"] == "+8801712345678"
    assert r.json()["warnings"] == []

    listed = me.get("/api/v1/applicants").json()
    assert listed[0]["passport_masked"] == "******456"
    assert "passport_number" not in listed[0]

    stored = db_session.scalar(select(Applicant))
    assert stored is not None
    assert "BX0123456" not in stored.passport_enc  # encrypted at rest
    assert stored.passport_enc.startswith("v1:")

    assert me.get(f"/api/v1/applicants/{a['id']}").json()["passport_number"] == "BX0123456"
    actions = [e.action for e in db_session.scalars(select(AuditEvent))]
    assert "applicant.view" in actions  # reads of passport data are logged


def test_individuals_cannot_see_each_other(browser) -> None:
    a = browser("a@example.com")
    b = browser("b@example.com")
    aid = a.post("/api/v1/applicants", json=person()).json()["applicant"]["id"]
    assert b.get(f"/api/v1/applicants/{aid}").status_code == 404
    assert b.patch(f"/api/v1/applicants/{aid}", json={"notes": "x"}).status_code == 404
    assert b.delete(f"/api/v1/applicants/{aid}").status_code == 404
    assert b.get("/api/v1/applicants").json() == []
    # the same passport under another individual is allowed and not revealed
    r = b.post("/api/v1/applicants", json=person())
    assert r.status_code == 201 and r.json()["warnings"] == []


def test_duplicate_passport_rejected_in_same_scope(browser) -> None:
    me = browser("me@example.com")
    assert me.post("/api/v1/applicants", json=person()).status_code == 201
    r = me.post("/api/v1/applicants", json=person(given_name="Other"))
    assert r.status_code == 409
    # after archiving, the passport can be added again
    aid = me.get("/api/v1/applicants").json()[0]["id"]
    assert me.delete(f"/api/v1/applicants/{aid}").status_code == 204
    assert me.post("/api/v1/applicants", json=person()).status_code == 201


def test_same_name_and_birthday_warns(browser) -> None:
    me = browser("me@example.com")
    me.post("/api/v1/applicants", json=person("BX0123456"))
    r = me.post("/api/v1/applicants", json=person("BX9999999"))
    assert r.status_code == 201
    assert len(r.json()["warnings"]) == 1


def test_date_and_format_validation(browser) -> None:
    me = browser("me@example.com")
    expired = (date.today() - timedelta(days=1)).isoformat()
    soon = (date.today() + timedelta(days=60)).isoformat()
    def add(**over: str) -> int:
        return me.post("/api/v1/applicants", json=person(**over)).status_code

    assert add(passport_expiry_date=expired) == 422
    assert add(date_of_birth="2999-01-01") == 422
    assert add(passport="AB#12") == 422
    assert add(nid_number="123") == 422
    assert add(phone="12345") == 422
    r = me.post("/api/v1/applicants", json=person(passport_expiry_date=soon))
    assert r.status_code == 201 and "৬ মাসের কম" in r.json()["warnings"][0]
    # nothing half-saved from the failed attempts
    assert len(me.get("/api/v1/applicants").json()) == 1


def test_update_and_search(browser) -> None:
    me = browser("me@example.com")
    aid = me.post("/api/v1/applicants", json=person()).json()["applicant"]["id"]
    r = me.patch(f"/api/v1/applicants/{aid}", json={"nid_number": "1234567890", "notes": "VIP"})
    assert r.status_code == 200
    assert r.json()["applicant"]["nid_number"] == "1234567890"
    assert me.patch(f"/api/v1/applicants/{aid}", json={"gender": None}).status_code == 422
    assert len(me.get("/api/v1/applicants?q=rahim").json()) == 1
    assert len(me.get("/api/v1/applicants?q=BX0123456").json()) == 1  # blind-index lookup
    assert me.get("/api/v1/applicants?q=nobody").json() == []


# ── Agencies ──


def test_agency_roles_and_isolation(browser, db_session: Session) -> None:
    admin = superadmin(db_session, browser)
    owner = browser("owner@alpha.com")
    org = agency(owner, admin, "Alpha")
    agent1 = browser("agent1@alpha.com")
    agent2 = browser("agent2@alpha.com")
    join(owner, org, agent1, "agent1@alpha.com", "agent")
    join(owner, org, agent2, "agent2@alpha.com", "agent")

    # agent creates -> assigned to themselves; owner sees everything, other agent sees nothing
    r = agent1.post(f"/api/v1/orgs/{org}/applicants", json=person())
    assert r.status_code == 201, r.text
    aid = r.json()["applicant"]["id"]
    owner_list = owner.get(f"/api/v1/orgs/{org}/applicants").json()
    assert [x["id"] for x in owner_list] == [aid]
    assert agent2.get(f"/api/v1/orgs/{org}/applicants").json() == []
    assert agent2.get(f"/api/v1/applicants/{aid}").status_code == 404
    assert agent1.delete(f"/api/v1/applicants/{aid}").status_code == 403  # managers+ only

    # owner reassigns to agent2
    agent2_id = db_session.scalar(select(User.id).where(User.email == "agent2@alpha.com"))
    r = owner.post(f"/api/v1/applicants/{aid}/assign", json={"user_id": str(agent2_id)})
    assert r.status_code == 200
    assert agent2.get(f"/api/v1/applicants/{aid}").status_code == 200
    unassign = agent1.post(f"/api/v1/applicants/{aid}/assign", json={"user_id": None})
    assert unassign.status_code in (403, 404)

    # another agency cannot see or touch it, and may hold the same passport
    owner_b = browser("owner@beta.com")
    org_b = agency(owner_b, admin, "Beta")
    assert owner_b.get(f"/api/v1/applicants/{aid}").status_code == 404
    assert owner_b.get(f"/api/v1/orgs/{org}/applicants").status_code == 404
    r = owner_b.post(f"/api/v1/orgs/{org_b}/applicants", json=person())
    assert r.status_code == 201 and r.json()["warnings"] == []
    # ...but superadmin gets a duplicate-elsewhere audit event
    actions = [e.action for e in db_session.scalars(select(AuditEvent))]
    assert "applicant.duplicate_elsewhere" in actions

    # cannot assign to someone outside the agency
    outsider = db_session.scalar(select(User.id).where(User.email == "owner@beta.com"))
    r = owner.post(f"/api/v1/applicants/{aid}/assign", json={"user_id": str(outsider)})
    assert r.status_code == 422


def test_pending_agency_cannot_add_applicants(browser) -> None:
    owner = browser("owner@alpha.com")
    org = owner.post("/api/v1/orgs", json={"name": "Alpha"}).json()["id"]
    assert owner.post(f"/api/v1/orgs/{org}/applicants", json=person()).status_code == 403


def test_requires_login(client: TestClient) -> None:
    assert client.get("/api/v1/applicants").status_code == 401
    assert client.post("/api/v1/applicants", json=person()).status_code == 401
