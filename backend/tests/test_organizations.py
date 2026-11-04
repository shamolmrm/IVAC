import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import User

PASSWORD = "correct horse battery"


@pytest.fixture
def make_client(client: TestClient):
    """Extra independent browsers (own cookie jars) sharing the same app + DB."""
    clients: list[TestClient] = []

    def factory() -> TestClient:
        c = TestClient(app)
        clients.append(c)
        return c

    yield factory
    for c in clients:
        c.close()


def signup(c: TestClient, email: str, name: str = "Test User") -> dict:
    r = c.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "full_name": name}
    )
    assert r.status_code == 201, r.text
    return r.json()


def make_superadmin(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email))
    assert user
    user.is_superadmin = True
    db.commit()


def new_agency(c: TestClient, name: str = "Alpha Travels") -> dict:
    r = c.post("/api/v1/orgs", json={"name": name, "phone": "01711111111"})
    assert r.status_code == 201, r.text
    return r.json()


def approve(admin: TestClient, org_id: str) -> None:
    r = admin.post(f"/api/v1/admin/orgs/{org_id}/status", json={"status": "active"})
    assert r.status_code == 200, r.text


def invite(c: TestClient, org_id: str, email: str, role: str = "agent") -> str:
    r = c.post(f"/api/v1/orgs/{org_id}/invites", json={"email": email, "role": role})
    assert r.status_code == 201, r.text
    m = re.search(r"token=([\w-]+)", r.json()["link"])
    assert m
    return m.group(1)


@pytest.fixture
def setup(client: TestClient, make_client, db_session: Session):
    """owner (client) with an approved agency, and a superadmin browser."""
    signup(client, "owner@alpha.com", "Owner A")
    org = new_agency(client)
    admin = make_client()
    signup(admin, "admin@example.com", "Admin")
    make_superadmin(db_session, "admin@example.com")
    approve(admin, org["id"])
    return {"org": org, "admin": admin}


def test_new_agency_is_pending_and_creator_is_owner(client: TestClient) -> None:
    signup(client, "owner@alpha.com")
    org = new_agency(client)
    assert org["status"] == "pending" and org["my_role"] == "owner"
    mine = client.get("/api/v1/orgs/mine").json()
    assert [o["id"] for o in mine] == [org["id"]]
    # pending agencies cannot invite staff yet
    r = client.post(
        f"/api/v1/orgs/{org['id']}/invites", json={"email": "x@alpha.com", "role": "agent"}
    )
    assert r.status_code == 403


def test_only_superadmin_can_approve(client: TestClient) -> None:
    signup(client, "owner@alpha.com")
    org = new_agency(client)
    r = client.post(f"/api/v1/admin/orgs/{org['id']}/status", json={"status": "active"})
    assert r.status_code == 403
    assert client.get("/api/v1/admin/orgs").status_code == 403


def test_invite_and_accept(client: TestClient, make_client, setup) -> None:
    org_id = setup["org"]["id"]
    token = invite(client, org_id, "Agent@Alpha.com", "agent")

    agent = make_client()
    signup(agent, "agent@alpha.com", "Agent A")
    preview = agent.post("/api/v1/invites/preview", json={"token": token}).json()
    assert preview["organization"] == "Alpha Travels" and preview["role"] == "agent"
    r = agent.post("/api/v1/invites/accept", json={"token": token})
    assert r.status_code == 200 and r.json()["my_role"] == "agent"
    # single use
    assert agent.post("/api/v1/invites/accept", json={"token": token}).status_code == 400
    assert agent.get("/api/v1/auth/me").json()["email_verified"] is True

    members = client.get(f"/api/v1/orgs/{org_id}/members").json()
    assert {m["email"]: m["role"] for m in members} == {
        "owner@alpha.com": "owner", "agent@alpha.com": "agent",
    }


def test_invite_only_for_the_invited_email(client: TestClient, make_client, setup) -> None:
    token = invite(client, setup["org"]["id"], "agent@alpha.com")
    other = make_client()
    signup(other, "someone@else.com")
    assert other.post("/api/v1/invites/accept", json={"token": token}).status_code == 403


def test_revoked_invite_cannot_be_used(client: TestClient, make_client, setup) -> None:
    org_id = setup["org"]["id"]
    token = invite(client, org_id, "agent@alpha.com")
    inv_id = client.get(f"/api/v1/orgs/{org_id}/invites").json()[0]["id"]
    assert client.delete(f"/api/v1/orgs/{org_id}/invites/{inv_id}").status_code == 204
    agent = make_client()
    signup(agent, "agent@alpha.com")
    assert agent.post("/api/v1/invites/accept", json={"token": token}).status_code == 400


def test_role_permissions(client: TestClient, make_client, setup) -> None:
    org_id = setup["org"]["id"]
    mgr = make_client()
    signup(mgr, "mgr@alpha.com")
    mgr.post("/api/v1/invites/accept", json={"token": invite(client, org_id, "mgr@alpha.com",
                                                             "manager")})
    agent = make_client()
    signup(agent, "agent@alpha.com")
    agent.post("/api/v1/invites/accept", json={"token": invite(mgr, org_id, "agent@alpha.com")})

    # manager may invite agents only
    r = mgr.post(f"/api/v1/orgs/{org_id}/invites", json={"email": "m2@alpha.com",
                                                         "role": "manager"})
    assert r.status_code == 403
    # agents cannot see staff or invite
    assert agent.get(f"/api/v1/orgs/{org_id}/members").status_code == 403
    assert agent.get(f"/api/v1/orgs/{org_id}").status_code == 200
    # only owners edit agency details or members
    assert mgr.patch(f"/api/v1/orgs/{org_id}", json={"name": "Hacked"}).status_code == 403
    members = client.get(f"/api/v1/orgs/{org_id}/members").json()
    agent_member = next(m for m in members if m["email"] == "agent@alpha.com")
    r = mgr.patch(f"/api/v1/orgs/{org_id}/members/{agent_member['id']}", json={"is_active": False})
    assert r.status_code == 403
    # owner deactivates the agent -> agent loses access immediately
    r = client.patch(
        f"/api/v1/orgs/{org_id}/members/{agent_member['id']}", json={"is_active": False}
    )
    assert r.status_code == 200
    assert agent.get(f"/api/v1/orgs/{org_id}").status_code == 404


def test_last_owner_cannot_be_removed(client: TestClient, make_client, setup) -> None:
    org_id = setup["org"]["id"]
    co = make_client()
    signup(co, "co@alpha.com")
    co.post("/api/v1/invites/accept", json={"token": invite(client, org_id, "co@alpha.com",
                                                            "owner")})
    members = {m["email"]: m["id"] for m in client.get(f"/api/v1/orgs/{org_id}/members").json()}
    # owner cannot change themselves
    r = client.patch(f"/api/v1/orgs/{org_id}/members/{members['owner@alpha.com']}",
                     json={"role": "agent"})
    assert r.status_code == 400
    # co-owner demotes the first owner: allowed, one owner remains
    r = co.patch(f"/api/v1/orgs/{org_id}/members/{members['owner@alpha.com']}",
                 json={"role": "agent"})
    assert r.status_code == 200


def test_tenant_isolation(client: TestClient, make_client, setup, db_session: Session) -> None:
    """A member of agency B must not see or touch anything of agency A."""
    org_a = setup["org"]["id"]
    owner_b = make_client()
    signup(owner_b, "owner@beta.com")
    org_b = new_agency(owner_b, "Beta Tours")
    approve(setup["admin"], org_b["id"])

    for method, path, body in (
        ("get", f"/api/v1/orgs/{org_a}", None),
        ("get", f"/api/v1/orgs/{org_a}/members", None),
        ("get", f"/api/v1/orgs/{org_a}/invites", None),
        ("patch", f"/api/v1/orgs/{org_a}", {"name": "x"}),
        ("post", f"/api/v1/orgs/{org_a}/invites", {"email": "spy@beta.com", "role": "agent"}),
    ):
        kwargs = {"json": body} if body is not None else {}
        r = getattr(owner_b, method)(path, **kwargs)
        assert r.status_code == 404, (method, path, r.status_code)  # existence not revealed

    # B's membership id cannot be used against A
    b_member = owner_b.get(f"/api/v1/orgs/{org_b['id']}/members").json()[0]["id"]
    r = client.patch(f"/api/v1/orgs/{org_a}/members/{b_member}", json={"is_active": False})
    assert r.status_code == 404
    assert [o["name"] for o in owner_b.get("/api/v1/orgs/mine").json()] == ["Beta Tours"]
    # superadmin sees both
    names = {o["name"] for o in setup["admin"].get("/api/v1/admin/orgs").json()}
    assert names == {"Alpha Travels", "Beta Tours"}
    actions = {e.action for e in db_session.scalars(select(AuditEvent))}
    assert {"org.create", "org.status"} <= actions


def test_suspended_agency_blocks_invites(client: TestClient, setup) -> None:
    org_id = setup["org"]["id"]
    r = setup["admin"].post(f"/api/v1/admin/orgs/{org_id}/status", json={"status": "suspended"})
    assert r.status_code == 200
    r = client.post(f"/api/v1/orgs/{org_id}/invites", json={"email": "a@x.com", "role": "agent"})
    assert r.status_code == 403
