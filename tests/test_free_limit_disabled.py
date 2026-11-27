"""FREE_DAILY_LIMIT=0 turns the free-search limit off (see .env.example)."""

import pytest
from fastapi.testclient import TestClient

from api.index import app
from api.routers import payment
from app.db.database import get_db

client = TestClient(app)


@pytest.fixture
def no_database(monkeypatch):
    """The endpoint only needs today's usage count; answer it without a database."""
    used = {"count": 0}

    async def fake_get_db():
        yield None

    async def fake_usage(db, ip_address):
        return used["count"]

    app.dependency_overrides[get_db] = fake_get_db
    monkeypatch.setattr(payment.payment_crud, "get_free_usage_today", fake_usage)
    yield used
    app.dependency_overrides.pop(get_db, None)


def test_free_remaining_reports_unlimited_when_the_limit_is_off(
    monkeypatch, no_database
):
    """The finder turns "0 of 0 left" into a Buy credits button, so the API has to
    say that searches are not being counted."""
    monkeypatch.setattr(payment, "FREE_DAILY_LIMIT", 0)

    body = client.get("/api/payment/free-remaining").json()

    assert body["unlimited"] is True
    assert body["daily_limit"] == 0


def test_free_remaining_counts_down_when_the_limit_is_on(monkeypatch, no_database):
    monkeypatch.setattr(payment, "FREE_DAILY_LIMIT", 2)

    no_database["count"] = 1
    assert client.get("/api/payment/free-remaining").json() == {
        "remaining": 1,
        "daily_limit": 2,
        "used_today": 1,
        "unlimited": False,
    }

    no_database["count"] = 5
    body = client.get("/api/payment/free-remaining").json()
    assert body["remaining"] == 0 and body["unlimited"] is False
