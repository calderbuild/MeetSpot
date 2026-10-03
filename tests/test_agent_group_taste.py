"""MeetSpotAgent 接入 Qloo：英文请求走 Google、带口味时 agent 被要求调用 group_taste_rank。"""

import asyncio
import json

import app.tool.qloo_client as qloo_client
from api.index import MeetSpotRequest, assess_request_complexity
from app.agent.meetspot_agent import MeetSpotAgent, create_meetspot_agent
from app.agent.tools import GroupTasteTool


def test_english_agent_uses_google_tools(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "g-key")
    agent = create_meetspot_agent("en")
    assert agent.map_provider == "google"
    geocode = agent.available_tools.tool_map["geocode"]
    assert geocode._get_recommender().map_provider == "google"
    assert "group_taste_rank" in agent.available_tools.tool_map


def test_chinese_agent_stays_on_amap(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "g-key")
    agent = create_meetspot_agent("zh")
    assert agent.available_tools.tool_map["geocode"]._get_recommender().map_provider == "amap"
    assert "group_taste_rank" not in agent.available_tools.tool_map
    assert "group_taste_rank" not in agent.system_prompt


def test_english_task_asks_for_taste_tool_only_when_tastes_given():
    task = MeetSpotAgent._english_task(
        ["Times Square", "Union Square"], "restaurant", "", ["Barbie, Taylor Swift", ""]
    )
    assert "group_taste_rank" in task
    assert "Person 1: at Times Square; likes: Barbie, Taylor Swift" in task
    assert "Person 2: at Union Square; likes: no preference given" in task

    plain = MeetSpotAgent._english_task(["A", "B"], "cafe", "", None)
    assert "group_taste_rank" not in plain


def test_tastes_force_rule_mode_even_for_complex_requests():
    request = MeetSpotRequest(
        locations=["a", "b", "c", "d"],
        keywords="cafe restaurant bar",
        user_requirements="quiet parking",
        tastes=["Barbie", "", "", ""],
    )
    assert assess_request_complexity(request)["use_agent"] is False


def test_group_taste_tool_reports_ranks_and_recognition(monkeypatch):
    async def fake_resolve(names, tastes):
        return [
            {"name": "Person 1", "items": [{"entity_id": "E1", "name": "Barbie", "kind": "movie"}], "unresolved": []},
            {"name": "Person 2", "items": [{"entity_id": "E2", "name": "Metallica", "kind": "artist"}], "unresolved": ["zzz"]},
        ]

    async def fake_rank(center, keywords, people):
        assert center == (-73.98, 40.75)
        return {
            "ranked": [
                {
                    "name": "Eataly",
                    "address": "200 5th Ave",
                    "location": "-73.99,40.74",
                    "biz_ext": {"rating": "4.4"},
                    "_taste": {
                        "pool": 30,
                        "fair_pct": 0.9,
                        "people": [
                            {"name": "Person 1", "pct": 1.0, "because": {"name": "Barbie"}},
                            {"name": "Person 2", "pct": 0.9, "because": None},
                        ],
                    },
                }
            ],
            "excluded": [{"name": "Hard Rock Cafe", "unhappy_person": "Person 2", "unhappy_rank": 17}],
            "common_ground": ["Blues"],
            "candidate_count": 30,
        }

    monkeypatch.setattr(qloo_client, "resolve_people", fake_resolve)
    monkeypatch.setattr(qloo_client, "rank_venues", fake_rank)
    result = asyncio.run(
        GroupTasteTool().execute(
            center={"lng": -73.98, "lat": 40.75},
            participants=[{"name": "Person 1", "tastes": "Barbie"}, {"name": "Person 2", "tastes": "Metallica, zzz"}],
        )
    )
    data = json.loads(result.output)
    venue = data["venues"][0]
    assert venue["worst_rank"] == 4  # fair_pct 0.9 of 30
    assert venue["per_person"]["Person 1"] == {"rank": 1, "because": "Barbie"}
    assert data["left_out"] == [{"name": "Hard Rock Cafe", "who": "Person 2", "their_rank": 17}]
    assert data["participants"]["Person 2"]["not_recognized"] == ["zzz"]


def test_group_taste_tool_fails_with_recognition_when_unavailable(monkeypatch):
    async def fake_resolve(names, tastes):
        return [{"name": "Person 1", "items": [], "unresolved": ["qqq"]}]

    async def fake_rank(center, keywords, people):
        return None

    monkeypatch.setattr(qloo_client, "resolve_people", fake_resolve)
    monkeypatch.setattr(qloo_client, "rank_venues", fake_rank)
    result = asyncio.run(
        GroupTasteTool().execute(
            center={"lng": 0, "lat": 0}, participants=[{"name": "Person 1", "tastes": "qqq"}]
        )
    )
    assert result.error and "qqq" in result.error


def test_english_agent_gets_english_system_prompt(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "g-key")
    assert "Answer in English" in create_meetspot_agent("en").system_prompt
    assert "English" in create_meetspot_agent("en").next_step_prompt
    assert "中文" in create_meetspot_agent("zh").system_prompt


def test_english_text_reply_ends_the_agent_loop(monkeypatch):
    """英文最终回答没有"推荐"二字，过去会一直跑到 max_steps。"""
    from types import SimpleNamespace

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "g-key")
    agent = create_meetspot_agent("en")

    async def fake_ask_tool(**kwargs):
        return SimpleNamespace(tool_calls=[], content="Go to The Press Lounge: nobody ranks it below #2.")

    monkeypatch.setattr(agent.llm, "ask_tool", fake_ask_tool)
    assert asyncio.run(agent.think()) is False


def test_taste_requests_skip_the_free_limit_during_judging(monkeypatch):
    import api.index as index
    from datetime import date

    taste = MeetSpotRequest(locations=["a", "b"], tastes=["Barbie", ""])
    plain = MeetSpotRequest(locations=["a", "b"])
    assert index._judging_exempt(taste) and not index._judging_exempt(plain)

    class After(date):
        @classmethod
        def today(cls):
            return date(2026, 11, 17)

    monkeypatch.setattr(index, "date", After)
    assert not index._judging_exempt(taste)


def test_agent_card_payload_cannot_close_its_script_tag():
    from app.tool.meetspot_recommender import CafeRecommender

    out = CafeRecommender._render_agent_html(["</script><b>x"], "restaurant", ["Barbie"])
    assert "</script><b>" not in out and "<\\/script><b>x" in out
    assert "/api/find_meetspot_agent" in out
