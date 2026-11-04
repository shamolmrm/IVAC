"""Test fixtures: SQLite in-memory DB and an in-memory Redis stand-in."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.cache import get_redis
from app.core.db import Base, get_db
from app.main import app


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def incr(self, name: str) -> int:
        self.data[name] = str(int(self.data.get(name, "0")) + 1)
        return int(self.data[name])

    async def expire(self, name: str, time: int) -> bool:
        return True

    async def get(self, name: str) -> str | None:
        return self.data.get(name)

    async def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self.data[name] = value
        return True

    async def ping(self) -> bool:
        return True


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as session:
        yield session


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def client(db_session: Session, fake_redis: FakeRedis) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
