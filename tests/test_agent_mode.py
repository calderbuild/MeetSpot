import asyncio
import time

import api.index
from api.index import MeetSpotRequest, assess_request_complexity
from app.tool.base import ToolResult


def _complex_request():
    return MeetSpotRequest(
        locations=["地点甲", "地点乙", "地点丙", "地点丁"],
        keywords="咖啡馆 餐厅 茶馆",
        user_requirements="安静 停车",
    )


def _fake_config():
    class _Amap:
        api_key = "test-key"

    class _GoogleMaps:
        api_key = ""

    class _Config:
        amap = _Amap()
        google_maps = _GoogleMaps()

    return _Config()


def test_agent_module_enabled():
    assert api.index.agent_available is True
    agent = api.index.create_meetspot_agent()
    assert agent.name == "MeetSpotAgent"


def test_complex_request_routes_to_agent():
    request = _complex_request()

    complexity = assess_request_complexity(request)

    assert complexity["use_agent"] is True
    assert complexity["complexity_score"] >= 40


def test_simple_request_routes_to_rule():
    request = MeetSpotRequest(
        locations=["地点甲", "地点乙"],
        keywords="咖啡馆",
    )

    complexity = assess_request_complexity(request)

    assert complexity["use_agent"] is False


def test_agent_success_path_returns_agent_mode(monkeypatch):
    class FakeAgent:
        async def recommend(self, locations, keywords, requirements):
            return {
                "success": True,
                "recommendation": "Agent 推荐结果",
                "geocode_results": [],
                "center_point": None,
                "search_results": [],
                "steps_executed": 4,
            }

    monkeypatch.setattr(api.index, "config", _fake_config())
    monkeypatch.setattr(api.index, "create_meetspot_agent", lambda: FakeAgent())

    result = asyncio.run(
        api.index._process_meetspot_request(_complex_request(), time.time(), "zh")
    )

    assert result["success"] is True
    assert result["mode"] == "agent"
    assert result["output"] == "Agent 推荐结果"


def test_agent_failure_falls_back_to_rule_mode(monkeypatch):
    class FakeAgent:
        async def recommend(self, locations, keywords, requirements):
            raise RuntimeError("LLM 不可用")

    async def fake_execute(self, **kwargs):
        return ToolResult(
            output="## 已为您找到2家适合会面的咖啡馆\nHTML页面: workspace/js_src/place_recommendation_test.html"
        )

    monkeypatch.setattr(api.index, "config", _fake_config())
    monkeypatch.setattr(api.index, "create_meetspot_agent", lambda: FakeAgent())
    monkeypatch.setattr(
        "app.tool.meetspot_recommender.CafeRecommender.execute", fake_execute
    )

    result = asyncio.run(
        api.index._process_meetspot_request(_complex_request(), time.time(), "zh")
    )

    assert result["success"] is True
    assert result["mode"] == "rule_llm"
    assert "已为您找到2家适合会面的咖啡馆" in result["output"]
