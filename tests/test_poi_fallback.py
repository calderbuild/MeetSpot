import asyncio
import math

from app.tool.meetspot_recommender import CafeRecommender


def _sample_places(names):
    places = []
    for i, name in enumerate(names):
        places.append(
            {
                "name": name,
                "location": f"116.31{i},39.99{i}",
                "address": f"{name}地址",
                "business_hours": "08:00-21:00",
                "tel": "010-12345678",
                "tag": ["咖啡馆"],
                "biz_ext": {"rating": "4.7"},
                "_matched_requirements": [],
                "_recommendation_reason": f"{name}推荐理由",
                "_score": 80,
                "_score_breakdown": {
                    "base": 20,
                    "distance": 20,
                    "popularity": 20,
                    "scenario": 10,
                    "requirement": 10,
                },
            }
        )
    return places


def _make_recommender(monkeypatch, search_results):
    recommender = CafeRecommender(api_key="test-key")

    async def _fake_geocode(address, **kwargs):
        return {
            "location": "116.3100,39.9920",
            "formatted_address": address,
            "city": "北京市",
        }

    async def _fake_search_pois(location, keywords, radius=2000, types="", offset=20):
        return search_results.get((keywords, radius), [])

    async def _fake_smart_city_inference(
        original_locations, geocode_results, city_hint=""
    ):
        return geocode_results

    async def _fake_generate_html_page(*args, **kwargs):
        return "workspace/js_src/place_recommendation_test.html"

    async def _fake_transport_tips(*args, **kwargs):
        return "<li><i class='bx bx-train'></i>测试交通建议</li>"

    monkeypatch.setattr(recommender, "_geocode", _fake_geocode)
    monkeypatch.setattr(recommender, "_search_pois", _fake_search_pois)
    monkeypatch.setattr(
        recommender, "_smart_city_inference", _fake_smart_city_inference
    )
    monkeypatch.setattr(recommender, "_generate_html_page", _fake_generate_html_page)
    monkeypatch.setattr(
        recommender, "_llm_generate_transport_tips", _fake_transport_tips
    )
    return recommender


def test_poi_fallback_uses_fallback_category(monkeypatch):
    recommender = _make_recommender(
        monkeypatch,
        {("餐厅", 5000): _sample_places(["回退餐厅"])},
    )

    result = asyncio.run(
        recommender.execute(
            locations=["地点甲", "地点乙"],
            keywords="茶馆",
        )
    )

    assert result.output
    assert "已为您推荐附近的「餐厅」" in result.output
    assert "回退餐厅" in result.output


def test_poi_fallback_radius_expansion(monkeypatch):
    recommender = _make_recommender(
        monkeypatch,
        {("餐厅", 50000): _sample_places(["远距离餐厅"])},
    )

    result = asyncio.run(
        recommender.execute(
            locations=["地点甲", "地点乙"],
            keywords="茶馆",
        )
    )

    assert result.output
    assert "餐厅（扩大范围）" in result.output
    assert "远距离餐厅" in result.output


def test_poi_all_searches_fail_returns_clear_error(monkeypatch):
    recommender = _make_recommender(monkeypatch, {})

    result = asyncio.run(
        recommender.execute(
            locations=["地点甲", "地点乙"],
            keywords="茶馆",
        )
    )

    assert "在该区域未能找到任何推荐场所" in result.output
    assert "高德 API 配额" in result.output


def test_multi_keyword_search_merges_results(monkeypatch):
    recommender = _make_recommender(
        monkeypatch,
        {
            ("咖啡馆", 5000): _sample_places(["咖啡店A"]),
            ("餐厅", 5000): _sample_places(["餐厅B"]),
        },
    )

    result = asyncio.run(
        recommender.execute(
            locations=["地点甲", "地点乙"],
            keywords="咖啡馆 餐厅",
        )
    )

    assert result.output
    assert "咖啡店A" in result.output
    assert "餐厅B" in result.output


def test_center_point_midpoint():
    recommender = CafeRecommender(api_key="test-key")

    center = recommender._calculate_center_point([(0.0, 0.0), (2.0, 0.0)])

    assert math.isclose(center[0], 1.0, abs_tol=1e-6)
    assert math.isclose(center[1], 0.0, abs_tol=1e-6)


def test_rank_places_filters_by_min_rating():
    recommender = CafeRecommender(api_key="test-key")
    places = [
        {
            "name": "低分店",
            "location": "116.3100,39.9920",
            "address": "低分地址",
            "rating": 4.0,
            "biz_ext": {"rating": "4.0"},
            "tag": [],
        },
        {
            "name": "高分店",
            "location": "116.3110,39.9930",
            "address": "高分地址",
            "rating": 4.6,
            "biz_ext": {"rating": "4.6"},
            "tag": [],
        },
    ]

    ranked = recommender._rank_places(
        places,
        (116.3105, 39.9925),
        "",
        "咖啡馆",
        min_rating=4.2,
        language="zh",
    )

    assert [p["name"] for p in ranked] == ["高分店"]


def test_rank_places_filters_by_price_range():
    recommender = CafeRecommender(api_key="test-key")
    places = [
        {
            "name": "经济店",
            "location": "116.3100,39.9920",
            "address": "经济地址",
            "rating": 4.5,
            "biz_ext": {"rating": "4.5", "cost": "¥30"},
            "tag": [],
        },
        {
            "name": "中档店",
            "location": "116.3110,39.9930",
            "address": "中档地址",
            "rating": 4.5,
            "biz_ext": {"rating": "4.5", "cost": "人均80元"},
            "tag": [],
        },
        {
            "name": "高档店",
            "location": "116.3120,39.9940",
            "address": "高档地址",
            "rating": 4.5,
            "biz_ext": {"rating": "4.5", "cost": "¥200"},
            "tag": [],
        },
        {
            "name": "无价格店",
            "location": "116.3130,39.9950",
            "address": "无价格地址",
            "rating": 4.5,
            "biz_ext": {"rating": "4.5"},
            "tag": [],
        },
    ]

    ranked = recommender._rank_places(
        places,
        (116.3115, 39.9935),
        "",
        "咖啡馆",
        price_range="economy",
        language="zh",
    )

    names = [p["name"] for p in ranked]
    assert "经济店" in names
    assert "无价格店" in names
    assert "中档店" not in names
    assert "高档店" not in names
