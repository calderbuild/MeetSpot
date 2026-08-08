import asyncio

from app.tool.meetspot_recommender import CafeRecommender


def _result(location, city):
    return {
        "original_location": location,
        "result": {
            "location": "116.4,39.9" if "北京" in city else "113.1,23.0",
            "city": city,
        },
    }


def test_cross_city_1_to_1_is_not_forced_to_same_city():
    recommender = CafeRecommender(api_key="test-key")
    results = [
        _result("北京地点", "北京市"),
        _result("佛山地点", "佛山市"),
    ]

    out = asyncio.run(recommender._smart_city_inference(["北京地点", "佛山地点"], results, ""))

    assert out == results


def test_outlier_regeocoded_to_main_city(monkeypatch):
    recommender = CafeRecommender(api_key="test-key")

    async def _fake_geocode(address, **kwargs):
        if "北京" in address:
            return {
                "location": "116.4,39.9",
                "formatted_address": "北京市正确位置",
                "city": "北京市",
            }
        return None

    monkeypatch.setattr(recommender, "_geocode", _fake_geocode)

    results = [
        {
            "original_location": "甲",
            "result": {"location": "116.4,39.9", "city": "北京市"},
        },
        {
            "original_location": "乙",
            "result": {"location": "116.5,39.95", "city": "北京市"},
        },
        {
            "original_location": "丙",
            "result": {"location": "121.5,31.2", "city": "上海市"},
        },
    ]

    out = asyncio.run(recommender._smart_city_inference(["甲", "乙", "丙"], results, ""))

    assert out[2]["result"]["city"] == "北京市"
    assert out[2]["result"]["location"] == "116.4,39.9"
    assert out[0]["result"] == results[0]["result"]


def test_city_hint_with_cross_city_skips_correction():
    recommender = CafeRecommender(api_key="test-key")
    results = [
        _result("北京地点", "北京市"),
        _result("广州地点", "广州市"),
    ]

    out = asyncio.run(
        recommender._smart_city_inference(["北京地点", "广州地点"], results, "北京")
    )

    assert out == results
