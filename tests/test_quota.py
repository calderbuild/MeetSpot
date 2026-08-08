import asyncio

import api.index
from api.index import MeetSpotRequest


def test_quota_disabled_when_limit_zero(monkeypatch):
    monkeypatch.setattr(api.index, "FREE_DAILY_LIMIT", 0)

    async def fake_process(request, start_time, lang):
        return {"success": True, "mode": "rule"}

    monkeypatch.setattr(api.index, "_process_meetspot_request", fake_process)

    result = asyncio.run(
        api.index.find_meetspot(
            MeetSpotRequest(locations=["地点甲", "地点乙"]),
            raw_request=None,
        )
    )

    assert result["success"] is True
    assert "need_payment" not in result


def test_quota_exceeded_blocks_request(monkeypatch):
    monkeypatch.setattr(api.index, "FREE_DAILY_LIMIT", 1)
    monkeypatch.setattr(api.index, "_get_client_ip", lambda raw_request: "1.2.3.4")

    class _URL:
        path = "/"

    class FakeRawRequest:
        url = _URL()
        cookies = {}
        headers = {}

    class FakeAsyncSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    async def fake_get_free_usage_today(db, ip_address):
        return 1

    async def fake_process(request, start_time, lang):
        return {"success": True, "mode": "rule"}

    monkeypatch.setattr(
        "app.db.database.AsyncSessionLocal", FakeAsyncSession
    )
    monkeypatch.setattr(
        "app.db.payment_crud.get_free_usage_today", fake_get_free_usage_today
    )
    monkeypatch.setattr(api.index, "_process_meetspot_request", fake_process)

    result = asyncio.run(
        api.index.find_meetspot(
            MeetSpotRequest(locations=["地点甲", "地点乙"]),
            raw_request=FakeRawRequest(),
        )
    )

    assert result["success"] is False
    assert result["need_payment"] is True
    assert result["free_used"] == 1
