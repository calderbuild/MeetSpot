"""CafeRecommender 接入 Qloo 口味公平后的行为：什么时候启用、排序以谁为准、页面写了什么。

Qloo 网络调用在 meetspot_recommender 模块命名空间里替换（HTTP 边界），
排序、中心点选择和渲染走真实代码。
"""

import asyncio

import app.tool.meetspot_recommender as rec_module
from app.tool.meetspot_recommender import CafeRecommender
from app.tool.qloo_client import geohash_encode

GEOCODE = {
    "Times Square": {
        "location": "-73.9855,40.7580",
        "formatted_address": "Times Square",
        "city": "New York",
    },
    "Union Square": {
        "location": "-73.9903,40.7359",
        "formatted_address": "Union Square",
        "city": "New York",
    },
}


def _taste_place(name, rank, fair_pct):
    return {
        "name": name,
        "location": "-73.988,40.748",
        "address": f"{name} address",
        "tel": "",
        "tag": "Restaurant",
        "biz_ext": {"rating": str(3.0 + rank * 1.8), "cost": "$$"},  # 口味排第一的评分最低
        "photos": [],
        "_taste": {
            "rank": rank,
            "pool": 30,
            "fair_pct": fair_pct,
            "people": [
                {
                    "name": "Person 1",
                    "pct": 0.9,
                    "because": {"name": "Barbie", "share": 0.6},
                },
                {
                    "name": "Person 2",
                    "pct": fair_pct,
                    "because": {"name": "Metallica", "share": 1.0},
                },
            ],
        },
    }


def _make_recommender(monkeypatch, calls):
    monkeypatch.setenv("QLOO_API_KEY", "test-qloo")
    recommender = CafeRecommender(api_key="amap-key", google_api_key="google-key")

    async def fake_geocode(address, **kwargs):
        return GEOCODE.get(address)

    async def fake_city_inference(locations, results, city_hint=""):
        return results

    async def fake_search_pois(*args, **kwargs):
        calls.append("google_search")
        place = _taste_place("Google Place", 0, 0.5)
        del place["_taste"]
        return [place]

    async def fake_html_page(*args, **kwargs):
        calls.append(("html", kwargs))
        return "workspace/js_src/place_recommendation_test.html"

    async def fake_resolve(names, tastes):
        calls.append(("resolve", tastes))
        return [
            {
                "name": n,
                "items": [{"entity_id": f"E{i}", "name": t, "kind": "movie"}]
                if t
                else [],
                "unresolved": [],
            }
            for i, (n, t) in enumerate(zip(names, tastes))
        ]

    async def fake_heat(center, people):
        calls.append("heat")
        return {}

    async def fake_rank(center, keywords, people, price_level_max=None):
        calls.append(("rank", price_level_max))
        # 故意让评分更高的店排在口味公平顺序后面，验证最终顺序以 _taste.rank 为准
        return {
            "ranked": [
                _taste_place("Low Rated Fair Pick", 0, 0.8),
                _taste_place("High Rated", 1, 0.5),
            ],
            "excluded": [],
            "common_ground": ["Blues"],
            "candidate_count": 30,
        }

    monkeypatch.setattr(recommender, "_geocode", fake_geocode)
    monkeypatch.setattr(recommender, "_smart_city_inference", fake_city_inference)
    monkeypatch.setattr(recommender, "_search_pois", fake_search_pois)
    monkeypatch.setattr(recommender, "_generate_html_page", fake_html_page)
    monkeypatch.setattr(rec_module, "resolve_people", fake_resolve)
    monkeypatch.setattr(rec_module, "qloo_group_heat", fake_heat)
    monkeypatch.setattr(rec_module, "qloo_rank_venues", fake_rank)
    return recommender


def _run(recommender, **kwargs):
    return asyncio.run(
        recommender.execute(
            locations=["Times Square", "Union Square"], keywords="restaurant", **kwargs
        )
    )


def test_tastes_on_google_path_use_qloo_order(monkeypatch):
    calls = []
    recommender = _make_recommender(monkeypatch, calls)
    _run(recommender, language="en", tastes=["Barbie", "Metallica"], price_range="mid")

    assert "google_search" not in calls
    assert ("rank", 2) in calls  # mid -> Qloo price_level <= 2
    html_kwargs = next(c[1] for c in calls if isinstance(c, tuple) and c[0] == "html")
    taste_html = html_kwargs["taste_html"]
    assert "Group taste" in taste_html and "Blues" in taste_html


def test_ranked_places_follow_taste_rank_not_rule_score(monkeypatch):
    calls = []
    recommender = _make_recommender(monkeypatch, calls)
    captured = {}

    async def capture_html(locations, places, *args, **kwargs):
        captured["places"] = places
        return "workspace/js_src/place_recommendation_test.html"

    monkeypatch.setattr(recommender, "_generate_html_page", capture_html)
    _run(recommender, language="en", tastes=["Barbie", "Metallica"])

    names = [p["name"] for p in captured["places"]]
    assert names == ["Low Rated Fair Pick", "High Rated"]
    reason = captured["places"][0]["_recommendation_reason"]
    assert "Person 1 via Barbie" in reason
    assert "nobody ranks it below #7 of 30" in reason  # fair_pct 0.8 -> 第 7 名
    fit = CafeRecommender._render_taste_fit(captured["places"][0])
    assert "#4/30" in fit  # Person 1 pct 0.9 -> 第 4 名，和推荐理由用同一套名次


def test_qloo_unavailable_falls_back_to_google_search(monkeypatch):
    calls = []
    recommender = _make_recommender(monkeypatch, calls)

    async def no_rank(*args, **kwargs):
        calls.append("rank_none")
        return None

    monkeypatch.setattr(rec_module, "qloo_rank_venues", no_rank)
    _run(recommender, language="en", tastes=["Barbie", "Metallica"])
    assert "rank_none" in calls and "google_search" in calls


def test_no_tastes_keeps_original_flow(monkeypatch):
    calls = []
    recommender = _make_recommender(monkeypatch, calls)
    _run(recommender, language="en", tastes=["", "  "])
    assert "google_search" in calls
    assert not any(isinstance(c, tuple) and c[0] in ("resolve", "rank") for c in calls)
    html_kwargs = next(c[1] for c in calls if isinstance(c, tuple) and c[0] == "html")
    assert html_kwargs["taste_html"] == ""


def test_amap_path_ignores_tastes(monkeypatch):
    calls = []
    recommender = _make_recommender(monkeypatch, calls)
    _run(recommender, language="zh", tastes=["Barbie", "Metallica"])
    assert not any(isinstance(c, tuple) and c[0] == "resolve" for c in calls)


def test_missing_qloo_key_ignores_tastes(monkeypatch):
    calls = []
    recommender = _make_recommender(monkeypatch, calls)
    monkeypatch.delenv("QLOO_API_KEY")
    _run(recommender, language="en", tastes=["Barbie", "Metallica"])
    assert not any(isinstance(c, tuple) and c[0] == "resolve" for c in calls)


def test_prefer_taste_heat_only_among_accepted_candidates():
    a, b, c = (-73.98, 40.75), (-73.99, 40.74), (-73.97, 40.76)
    heat = {
        geohash_encode(a[1], a[0]): {"heat": 0.5, "lat": 0, "lng": 0},
        geohash_encode(b[1], b[0]): {"heat": 0.9, "lat": 0, "lng": 0},
        geohash_encode(c[1], c[0]): {"heat": 0.99, "lat": 0, "lng": 0},
    }
    check = {
        "attempts": [
            {"point": a, "accepted": True},
            {"point": b, "accepted": True},
            {"point": c, "accepted": False},  # 热度最高但通勤不达标，不能选
        ],
        "winner_point": a,
        "winner_index": 0,
    }
    assert CafeRecommender._prefer_taste_heat(check, heat, a) == b
    assert check["winner_index"] == 1
    assert check["attempts"][2]["taste_heat"] == 0.99


def test_prefer_taste_heat_keeps_center_with_single_accepted():
    a, b = (-73.98, 40.75), (-73.99, 40.74)
    heat = {geohash_encode(b[1], b[0]): {"heat": 0.9, "lat": 0, "lng": 0}}
    check = {
        "attempts": [{"point": a, "accepted": True}, {"point": b, "accepted": False}]
    }
    assert CafeRecommender._prefer_taste_heat(check, heat, a) == a
    assert CafeRecommender._prefer_taste_heat(None, heat, a) == a


def test_render_taste_html_escapes_input_and_explains_exclusion():
    people = [
        {
            "name": "Person 1",
            "items": [{"name": "<b>Barbie</b>", "kind": "movie"}],
            "unresolved": ["<script>"],
        },
        {"name": "Person 2", "items": [], "unresolved": []},
    ]
    taste = {
        "candidate_count": 30,
        "common_ground": [],
        "excluded": [
            {
                "name": "Hard Rock Cafe",
                "unhappy_person": "Person 2",
                "unhappy_rank": 21,
                "unhappy_pct": 0.31,
            }
        ],
    }
    out = CafeRecommender._render_taste_html(people, taste, {})
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert "&lt;b&gt;Barbie" in out
    assert "no preference" in out
    assert "Hard Rock Cafe" in out and "ranks it only #21 of 30" in out
    assert CafeRecommender._render_taste_html([], None, {}) == ""
