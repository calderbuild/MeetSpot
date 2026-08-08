import asyncio

from app.tool.meetspot_recommender import CafeRecommender


def _sample_locations():
    return [
        {
            "name": "地点甲",
            "formatted_address": "地址甲",
            "location": "116.3100,39.9920",
            "lng": 116.3100,
            "lat": 39.9920,
            "city": "北京市",
        },
        {
            "name": "地点丙",
            "formatted_address": "地址丙",
            "location": "116.3260,40.0030",
            "lng": 116.3260,
            "lat": 40.0030,
            "city": "北京市",
        },
    ]


def _sample_places():
    return [
        {
            "name": "测试咖啡馆",
            "location": "116.3180,39.9970",
            "address": "测试地址",
            "business_hours": "08:00-21:00",
            "tel": "010-12345678",
            "tag": ["咖啡馆", "安静"],
            "biz_ext": {"rating": "4.7"},
            "_matched_requirements": ["安静"],
            "_recommendation_reason": "安静，距离适中",
            "_score": 80,
            "_score_breakdown": {
                "base": 20,
                "distance": 20,
                "popularity": 20,
                "scenario": 10,
                "requirement": 10,
            },
        }
    ]


def _make_recommender(monkeypatch, geocode_map):
    recommender = CafeRecommender(api_key="test-key")

    async def _fake_geocode(address, **kwargs):
        return geocode_map.get(address)

    async def _fake_search_pois(*args, **kwargs):
        return _sample_places()

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


def test_partial_geocode_failure_continues_with_remaining_locations(monkeypatch):
    geocode_map = {
        "地点甲": {
            "location": "116.3100,39.9920",
            "formatted_address": "地址甲",
            "city": "北京市",
        },
        "地点乙": None,
        "地点丙": {
            "location": "116.3260,40.0030",
            "formatted_address": "地址丙",
            "city": "北京市",
        },
    }
    recommender = _make_recommender(monkeypatch, geocode_map)

    result = asyncio.run(
        recommender.execute(
            locations=["地点甲", "地点乙", "地点丙"],
            keywords="咖啡馆",
        )
    )

    assert result.output
    assert "地点乙" in result.output
    assert "已跳过" in result.output
    assert "已为您找到" in result.output


def test_all_geocode_failures_return_clear_error(monkeypatch):
    recommender = _make_recommender(monkeypatch, {"地点甲": None, "地点乙": None})

    result = asyncio.run(
        recommender.execute(
            locations=["地点甲", "地点乙"],
            keywords="咖啡馆",
        )
    )

    assert "未能解析任何有效的地点位置" in result.output
    assert "地点甲" in result.output
    assert "地点乙" in result.output
    assert "高德 API 配额" in result.output


def test_all_geocode_failures_include_alias_hint(monkeypatch):
    recommender = _make_recommender(monkeypatch, {"北大": None})

    result = asyncio.run(
        recommender.execute(
            locations=["北大"],
            keywords="咖啡馆",
        )
    )

    assert "识别为简称/别名" in result.output
    assert "北京市海淀区北京大学" in result.output


def test_enhance_address_aliases():
    recommender = CafeRecommender(api_key="test-key")

    assert recommender._enhance_address("北大") == "北京市海淀区北京大学"
    assert recommender._enhance_address("清华") == "北京市海淀区清华大学"
    assert recommender._enhance_address("复旦") == "上海市杨浦区复旦大学"


def test_select_best_poi_prefers_full_keyword_match():
    recommender = CafeRecommender(api_key="test-key")
    pois = [
        {
            "name": "陈村",
            "cityname": "肇庆市",
            "adname": "鼎湖区",
            "location": "112.708412,23.126382",
        },
        {
            "name": "陈村地铁站A口",
            "cityname": "佛山市",
            "adname": "顺德区",
            "location": "113.236925,22.967238",
        },
    ]

    best = recommender._select_best_poi(pois, "陈村地铁站", "")

    assert best is not None
    assert best["name"] == "陈村地铁站A口"
    assert best["cityname"] == "佛山市"


def test_format_result_text_includes_skipped_note():
    recommender = CafeRecommender(api_key="test-key")

    text = recommender._format_result_text(
        locations=_sample_locations(),
        places=_sample_places(),
        html_path="workspace/js_src/place_recommendation_test.html",
        keywords="咖啡馆",
        skipped_locations=["地点乙"],
        language="zh",
    )

    assert "1 个地址解析失败，已跳过：地点乙" in text


def test_format_result_text_english_includes_skipped_note():
    recommender = CafeRecommender(api_key="test-key")

    text = recommender._format_result_text(
        locations=_sample_locations(),
        places=_sample_places(),
        html_path="workspace/js_src/place_recommendation_test.html",
        keywords="咖啡馆",
        skipped_locations=["Bad Place"],
        language="en",
    )

    assert "1 address(es) could not be parsed and were skipped: Bad Place" in text


def test_generate_html_content_includes_skipped_notice(monkeypatch):
    recommender = _make_recommender(monkeypatch, {"地点甲": None})
    notice = (
        '<div class="fallback-notice"><i class="bx bx-info-circle"></i>'
        '<span class="fallback-notice-text">注意：1 个地址解析失败，已跳过：地点乙</span></div>'
    )

    html = asyncio.run(
        recommender._generate_html_content(
            locations=_sample_locations(),
            places=_sample_places(),
            center_point=(116.3180, 39.9975),
            user_requirements="安静",
            keywords="咖啡馆",
            skipped_notice=notice,
            language="zh",
        )
    )

    assert "注意：1 个地址解析失败，已跳过：地点乙" in html
