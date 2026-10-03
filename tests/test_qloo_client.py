"""qloo_client 纯函数 + rank_venues 端到端排序测试。

AFFINITY 是 2026-10-03 用 hackathon key 实测的真实数据：纽约 Midtown 2km 内 30 家餐厅，
三个人分别是 Taylor Swift + Barbie（Ava）、Metallica + John Wick（Ben）、
Bad Bunny + Trader Joe's（Cleo）。
"""

import asyncio

import pytest

from app.tool import qloo_client
from app.tool.qloo_client import (
    VENUE_TAGS,
    excluded_by_fairness,
    geohash_encode,
    heat_at,
    maximin_order,
    mean_order,
    min_heat,
    percentiles,
    rank_venues,
    split_tastes,
    to_poi,
    top_reason,
    venue_tag_for,
)

AFFINITY = {
    'Ava': {
        'the Press Lounge': 0.8536,
        'Hard Rock Cafe': 0.8408,
        'Sony Hall': 0.8406,
        'Magic Hour Rooftop Bar & Lounge': 0.8397,
        'TAO Uptown': 0.8241,
        "IPPUDO Hell's Kitchen": 0.8227,
        'Nobu Fifty Seven': 0.8211,
        'Eataly - Flatiron': 0.821,
        'Catch': 0.8208,
        'Lips': 0.8205,
        'Buddakan': 0.8205,
        'The Cutting Room': 0.8182,
        'Birdland Jazz Club': 0.8179,
        'Slate': 0.813,
        'miss KOREA BBQ': 0.8118,
        'Eleven Madison Park': 0.8101,
        'IPPUDO NY': 0.8054,
        'Kimpton Hotel Eventi': 0.8037,
        'COTE Flatiron': 0.7987,
        'The Modern': 0.7984,
        'abc kitchen': 0.7983,
        "Ellen's Stardust Diner": 0.7926,
        'Cosme': 0.7924,
        "John's Pizzeria of Times Square": 0.7517,
        'YOTEL New York Times Square': 0.7293,
        'Shake Shack Theater District': 0.7231,
        '5 Napkin Burger': 0.7199,
        "Carmine's - 44th Street - NYC": 0.7076,
        'Havana Central Times Square': 0.7009,
        'ROW NYC': 0.6967,
    },
    'Ben': {
        'Hard Rock Cafe': 0.8134,
        'the Press Lounge': 0.7704,
        "Ellen's Stardust Diner": 0.7582,
        'Eataly - Flatiron': 0.7486,
        'The Cutting Room': 0.7479,
        'Magic Hour Rooftop Bar & Lounge': 0.7423,
        'Birdland Jazz Club': 0.7408,
        'Sony Hall': 0.7389,
        'Eleven Madison Park': 0.7357,
        'Lips': 0.7351,
        'Nobu Fifty Seven': 0.7323,
        'Cosme': 0.7294,
        'miss KOREA BBQ': 0.7285,
        'The Modern': 0.7261,
        'Slate': 0.7257,
        'TAO Uptown': 0.7253,
        "IPPUDO Hell's Kitchen": 0.7252,
        'IPPUDO NY': 0.7219,
        'abc kitchen': 0.7209,
        'Kimpton Hotel Eventi': 0.7195,
        'Catch': 0.7187,
        "John's Pizzeria of Times Square": 0.7164,
        'COTE Flatiron': 0.7155,
        'Buddakan': 0.7119,
        'YOTEL New York Times Square': 0.6953,
        'Shake Shack Theater District': 0.6819,
        '5 Napkin Burger': 0.662,
        "Carmine's - 44th Street - NYC": 0.6582,
        'ROW NYC': 0.6326,
        'Havana Central Times Square': 0.6113,
    },
    'Cleo': {
        'the Press Lounge': 0.9105,
        'TAO Uptown': 0.8996,
        'Magic Hour Rooftop Bar & Lounge': 0.898,
        'Eataly - Flatiron': 0.8979,
        'The Cutting Room': 0.8936,
        'Lips': 0.8918,
        'miss KOREA BBQ': 0.8896,
        'IPPUDO NY': 0.8874,
        'Birdland Jazz Club': 0.8868,
        'abc kitchen': 0.8784,
        'Kimpton Hotel Eventi': 0.8729,
        'Havana Central Times Square': 0.8486,
        '5 Napkin Burger': 0.8484,
        "Carmine's - 44th Street - NYC": 0.8457,
        'YOTEL New York Times Square': 0.8447,
        'ROW NYC': 0.8227,
        'Hard Rock Cafe': 0.8043,
        "IPPUDO Hell's Kitchen": 0.7993,
        'Catch': 0.7957,
        'Buddakan': 0.7919,
        'Nobu Fifty Seven': 0.7895,
        'Slate': 0.7866,
        'Eleven Madison Park': 0.7814,
        "Ellen's Stardust Diner": 0.7783,
        'Cosme': 0.7777,
        'COTE Flatiron': 0.7749,
        'The Modern': 0.7721,
        "John's Pizzeria of Times Square": 0.7687,
        'Shake Shack Theater District': 0.7486,
        'Sony Hall': 0.7267,
    },
}


def _pct():
    return {p: percentiles(v) for p, v in AFFINITY.items()}


def test_percentiles_span_zero_to_one():
    pct = percentiles(AFFINITY["Ava"])
    assert min(pct.values()) == 0.0
    assert max(pct.values()) == 1.0
    assert pct["the Press Lounge"] == 1.0


def test_maximin_drops_venue_one_person_dislikes():
    pct = _pct()
    # 按平均分 Hard Rock Cafe 排第 4，但 Cleo 只把它排在 45% 分位
    assert "Hard Rock Cafe" in mean_order(pct)[:6]
    assert "Hard Rock Cafe" not in maximin_order(pct)[:6]
    assert maximin_order(pct)[:4] == [
        "the Press Lounge",
        "Magic Hour Rooftop Bar & Lounge",
        "Eataly - Flatiron",
        "Lips",
    ]


def test_excluded_names_who_would_be_unhappy():
    excluded = {x["entity_id"]: x for x in excluded_by_fairness(_pct(), 6)}
    assert set(excluded) == {"Hard Rock Cafe", "TAO Uptown"}
    assert excluded["Hard Rock Cafe"]["unhappy_person"] == "Cleo"
    assert excluded["TAO Uptown"]["unhappy_person"] == "Ben"


def test_maximin_skips_candidates_missing_for_someone():
    pct = {"a": {"x": 1.0, "y": 0.0}, "b": {"x": 0.5}}
    assert maximin_order(pct) == ["x"]


def test_geohash_matches_reference_value():
    # Wikipedia 的 geohash 示例：57.64911, 10.40744 -> u4pruydqqvj
    assert geohash_encode(57.64911, 10.40744, 11) == "u4pruydqqvj"
    assert geohash_encode(57.64911, 10.40744) == "u4pruyd"


def test_min_heat_keeps_shared_cells_with_lowest_value():
    heat = {
        "a": {"g1": {"heat": 0.9, "lat": 1, "lng": 2}, "g2": {"heat": 0.8, "lat": 3, "lng": 4}},
        "b": {"g1": {"heat": 0.4, "lat": 1, "lng": 2}},
    }
    assert min_heat(heat) == {"g1": {"heat": 0.4, "lat": 1, "lng": 2}}


def test_heat_at_looks_up_cell_by_coordinate():
    gh = geohash_encode(40.7484, -73.9857)
    assert heat_at({gh: {"heat": 0.7, "lat": 0, "lng": 0}}, -73.9857, 40.7484) == 0.7
    assert heat_at({}, -73.9857, 40.7484) is None


@pytest.mark.parametrize(
    "keywords,tag",
    [
        ("coffee shop", VENUE_TAGS["cafe"]),
        ("咖啡馆", VENUE_TAGS["cafe"]),
        ("cocktail bar", VENUE_TAGS["bar"]),
        ("restaurant", VENUE_TAGS["restaurant"]),
        ("", VENUE_TAGS["restaurant"]),
    ],
)
def test_venue_tag_for(keywords, tag):
    assert venue_tag_for(keywords) == tag


def test_split_tastes():
    assert split_tastes("Taylor Swift, Barbie；x ,, ") == ["Taylor Swift", "Barbie；x"]
    assert split_tastes("a; b，c") == ["a", "b", "c"]
    assert split_tastes("") == []


def test_top_reason_picks_biggest_contributor():
    explain = [{"entity_id": "s", "score": 0.47}, {"entity_id": "b", "score": 0.53}]
    assert top_reason(explain, {"s": "Taylor Swift", "b": "Barbie"}) == {
        "name": "Barbie",
        "share": 0.53,
    }
    assert top_reason([], {}) is None


def test_to_poi_matches_amap_shape():
    poi = to_poi(
        {
            "entity_id": "E1",
            "name": "Eataly",
            "location": {"lat": 40.742, "lon": -73.99},
            "properties": {"address": "200 5th Ave", "business_rating": 4.5, "price_level": 2},
            "tags": [{"name": "Italian"}],
        }
    )
    assert poi["location"] == "-73.99,40.742"
    assert poi["biz_ext"] == {"rating": "4.5", "cost": "$$"}
    assert poi["_qloo_entity_id"] == "E1"


def _fake_get_factory():
    """按请求参数返回实测数据，只替换 HTTP 边界，排序逻辑走真实代码。"""
    names = list(AFFINITY["Ava"])
    who = {"A1": "Ava", "B1": "Ben", "C1": "Cleo"}

    async def fake_get(session, path, params, api_key):
        if path == "/v2/analysis/compare":
            return {"results": {"tags": [
                {"name": "Ireland", "subtype": "urn:tag:place:country", "query": {"score": 0.99}},
                {"name": "Blues", "subtype": "urn:tag:genre:music", "query": {"score": 0.9}},
            ]}}
        if "filter.results.entities" in params:
            person = who[params["signal.interests.entities"]]
            return {"results": {"entities": [
                {"entity_id": n, "query": {
                    "affinity": AFFINITY[person][n],
                    "explainability": {"signal.interests.entities": [
                        {"entity_id": params["signal.interests.entities"], "score": 1.0}
                    ]},
                }}
                for n in names
            ]}}
        return {"results": {"entities": [
            {"entity_id": n, "name": n, "location": {"lat": 40.75, "lon": -73.98}}
            for n in names
        ]}}

    return fake_get


def test_rank_venues_end_to_end(monkeypatch):
    monkeypatch.setattr(qloo_client, "_get", _fake_get_factory())
    people = [
        {"name": "Ava", "items": [{"entity_id": "A1", "name": "Barbie"}], "unresolved": []},
        {"name": "Ben", "items": [{"entity_id": "B1", "name": "Metallica"}], "unresolved": []},
        {"name": "Cleo", "items": [{"entity_id": "C1", "name": "Bad Bunny"}], "unresolved": []},
        {"name": "Dan", "items": [], "unresolved": ["zzz"]},  # 无偏好，不参与排序
    ]
    result = asyncio.run(
        rank_venues((-73.9857, 40.7484), "restaurant", people, api_key="k")
    )
    names = [p["name"] for p in result["ranked"]]
    assert names[0] == "the Press Lounge"
    assert "Hard Rock Cafe" not in names
    assert {x["name"] for x in result["excluded"]} == {"Hard Rock Cafe", "TAO Uptown"}
    assert [p["name"] for p in result["ranked"][0]["_taste"]["people"]] == ["Ava", "Ben", "Cleo"]
    assert result["ranked"][0]["_taste"]["people"][0]["because"]["name"] == "Barbie"
    assert result["common_ground"] == ["Blues"]  # 地名类 tag 被过滤


def test_rank_venues_returns_none_without_tastes():
    people = [{"name": "Dan", "items": [], "unresolved": []}]
    assert asyncio.run(rank_venues((0, 0), "", people, api_key="k")) is None


class _FakeResp:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        return {"ok": True}

    async def text(self):
        return "rate limited"


class _FakeSession:
    def __init__(self, statuses):
        self.statuses = list(statuses)

    def get(self, *args, **kwargs):
        return _FakeResp(self.statuses.pop(0))


def test_get_retries_on_429(monkeypatch):
    monkeypatch.setattr(qloo_client, "_RETRY_DELAYS", (0, 0, 0))
    session = _FakeSession([429, 429, 200])
    assert asyncio.run(qloo_client._get(session, "/search", {}, "k")) == {"ok": True}


def test_get_gives_up_after_retries_and_on_other_errors(monkeypatch):
    monkeypatch.setattr(qloo_client, "_RETRY_DELAYS", (0, 0, 0))
    assert asyncio.run(qloo_client._get(_FakeSession([429] * 4), "/s", {}, "k")) is None
    assert asyncio.run(qloo_client._get(_FakeSession([400, 200]), "/s", {}, "k")) is None
