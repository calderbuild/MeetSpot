import asyncio

from app.tool.google_directions_client import (
    _parse_route_matrix_response,
    google_route_matrix,
)


def test_parse_route_matrix_response_marks_existing_routes_ok():
    raw = [
        {
            "originIndex": 0,
            "destinationIndex": 0,
            "status": {},
            "distanceMeters": 822,
            "duration": "160s",
            "condition": "ROUTE_EXISTS",
        },
        {
            "originIndex": 1,
            "destinationIndex": 0,
            "status": {},
            "condition": "ROUTE_NOT_FOUND",
        },
    ]

    parsed = _parse_route_matrix_response(raw)

    assert parsed[0] == {
        "origin_index": 0,
        "destination_index": 0,
        "duration_seconds": 160,
        "distance_meters": 822,
        "ok": True,
    }
    assert parsed[1]["ok"] is False
    assert parsed[1]["duration_seconds"] is None


def test_parse_route_matrix_response_ignores_malformed_input():
    assert _parse_route_matrix_response(None) == []
    assert _parse_route_matrix_response({"not": "a list"}) == []
    assert _parse_route_matrix_response([{"duration": "not-a-duration"}]) == [
        {
            "origin_index": 0,
            "destination_index": 0,
            "duration_seconds": None,
            "distance_meters": None,
            "ok": False,
        }
    ]


def test_google_route_matrix_returns_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    result = asyncio.run(
        google_route_matrix(origins=[(116.31, 39.99)], destinations=[(116.32, 39.98)])
    )

    assert result == []


def test_google_route_matrix_returns_empty_for_empty_inputs(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")

    result = asyncio.run(
        google_route_matrix(origins=[], destinations=[(116.32, 39.98)])
    )

    assert result == []


def test_google_route_matrix_rejects_oversized_transit_matrix(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    origins = [(116.3 + i * 0.001, 39.9) for i in range(11)]
    destinations = [
        (116.4 + i * 0.001, 40.0) for i in range(10)
    ]  # 110 > 100 的 TRANSIT 上限

    result = asyncio.run(
        google_route_matrix(origins=origins, destinations=destinations, mode="TRANSIT")
    )

    assert result == []
