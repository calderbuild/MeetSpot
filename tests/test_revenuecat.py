import asyncio

import httpx
import pytest

import api.index
from api.index import MeetSpotRequest
from app.payment import revenuecat

_REAL_CLIENT = httpx.AsyncClient


def _mock_rc(monkeypatch, handler):
    """Route every httpx call made by revenuecat.has_pro through `handler`."""
    calls = []

    def recording(request):
        calls.append(request)
        return handler(request)

    monkeypatch.setattr(
        revenuecat.httpx,
        "AsyncClient",
        lambda **kw: _REAL_CLIENT(transport=httpx.MockTransport(recording), **kw),
    )
    return calls


def _subscriber(entitlements):
    return lambda request: httpx.Response(
        200, json={"subscriber": {"entitlements": entitlements}}
    )


@pytest.fixture(autouse=True)
def _rc_env(monkeypatch):
    monkeypatch.setenv("REVENUECAT_SECRET_KEY", "sk_test_dummy")
    revenuecat._cache.clear()


def test_active_lifetime_entitlement(monkeypatch):
    calls = _mock_rc(monkeypatch, _subscriber({"meetspot_pro": {"expires_date": None}}))
    assert asyncio.run(revenuecat.has_pro("user-1")) is True
    assert calls[0].headers["authorization"] == "Bearer sk_test_dummy"
    assert calls[0].url.path == "/v1/subscribers/user-1"


def test_active_until_future(monkeypatch):
    _mock_rc(
        monkeypatch, _subscriber({"meetspot_pro": {"expires_date": "2999-01-01T00:00:00Z"}})
    )
    assert asyncio.run(revenuecat.has_pro("user-1")) is True


def test_expired_entitlement(monkeypatch):
    _mock_rc(
        monkeypatch, _subscriber({"meetspot_pro": {"expires_date": "2020-01-01T00:00:00Z"}})
    )
    assert asyncio.run(revenuecat.has_pro("user-1")) is False


def test_grace_period_keeps_access(monkeypatch):
    _mock_rc(
        monkeypatch,
        _subscriber(
            {
                "meetspot_pro": {
                    "expires_date": "2020-01-01T00:00:00Z",
                    "grace_period_expires_date": "2999-01-01T00:00:00Z",
                }
            }
        ),
    )
    assert asyncio.run(revenuecat.has_pro("user-1")) is True


def test_missing_entitlement(monkeypatch):
    _mock_rc(monkeypatch, _subscriber({"other": {"expires_date": None}}))
    assert asyncio.run(revenuecat.has_pro("user-1")) is False


def test_http_error_never_grants(monkeypatch):
    _mock_rc(monkeypatch, lambda request: httpx.Response(500))
    assert asyncio.run(revenuecat.has_pro("user-1")) is False


def test_timeout_never_grants(monkeypatch):
    def boom(request):
        raise httpx.ReadTimeout("slow", request=request)

    _mock_rc(monkeypatch, boom)
    assert asyncio.run(revenuecat.has_pro("user-1")) is False


def test_no_secret_key_skips_lookup(monkeypatch):
    monkeypatch.delenv("REVENUECAT_SECRET_KEY")
    calls = _mock_rc(monkeypatch, _subscriber({"meetspot_pro": {"expires_date": None}}))
    assert asyncio.run(revenuecat.has_pro("user-1")) is False
    assert calls == []


def test_positive_result_cached_negative_not(monkeypatch):
    calls = _mock_rc(monkeypatch, _subscriber({}))
    asyncio.run(revenuecat.has_pro("user-1"))
    asyncio.run(revenuecat.has_pro("user-1"))
    assert (
        len(calls) == 2
    )  # "no" must not stick, the post-purchase retry needs a fresh lookup

    calls = _mock_rc(monkeypatch, _subscriber({"meetspot_pro": {"expires_date": None}}))
    asyncio.run(revenuecat.has_pro("user-1"))
    asyncio.run(revenuecat.has_pro("user-1"))
    assert len(calls) == 1


# --- quota bypass in find_meetspot -------------------------------------------


class _URL:
    path = "/"


def _raw_request(headers):
    class FakeRawRequest:
        url = _URL()
        cookies = {}

    FakeRawRequest.headers = headers
    return FakeRawRequest()


class _FakeSession:
    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _setup_quota_exhausted(monkeypatch, pro):
    monkeypatch.setattr(api.index, "FREE_DAILY_LIMIT", 1)
    monkeypatch.setattr(api.index, "_get_client_ip", lambda raw_request: "1.2.3.4")
    consumed = []

    async def used_today(db, ip_address):
        return 1

    async def consume(db, ip_address, daily_limit):
        consumed.append(ip_address)
        return True, 1

    async def process(request, start_time, lang):
        return {"success": True, "mode": "rule"}

    async def fake_has_pro(app_user_id):
        return pro

    monkeypatch.setattr("app.db.database.AsyncSessionLocal", _FakeSession)
    monkeypatch.setattr("app.db.payment_crud.get_free_usage_today", used_today)
    monkeypatch.setattr("app.db.payment_crud.try_consume_free_use", consume)
    monkeypatch.setattr(api.index, "_process_meetspot_request", process)
    monkeypatch.setattr(revenuecat, "has_pro", fake_has_pro)
    return consumed


def _search(headers):
    return asyncio.run(
        api.index.find_meetspot(
            MeetSpotRequest(locations=["地点甲", "地点乙"]),
            raw_request=_raw_request(headers),
        )
    )


def test_pro_user_bypasses_quota(monkeypatch):
    consumed = _setup_quota_exhausted(monkeypatch, pro=True)
    result = _search({"x-rc-app-user-id": "user-1"})
    assert result["success"] is True
    assert consumed == []  # pro searches don't eat the free quota


def test_non_pro_user_still_blocked(monkeypatch):
    _setup_quota_exhausted(monkeypatch, pro=False)
    result = _search({"x-rc-app-user-id": "user-1"})
    assert result["need_payment"] is True


def test_no_header_keeps_quota(monkeypatch):
    _setup_quota_exhausted(monkeypatch, pro=True)
    result = _search({})
    assert result["need_payment"] is True
