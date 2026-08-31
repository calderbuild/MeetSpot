import asyncio

import app.tool.google_directions_client as google_directions_client
from app.tool.meetspot_recommender import CafeRecommender


def _make_amap_recommender_with_stubs(monkeypatch):
    """Mirrors tests/test_geocode_failure.py's _make_recommender helper, minus the
    dependency on that module (keeps this file self-contained)."""
    recommender = CafeRecommender(api_key="test-key")
    assert recommender.map_provider == "amap"

    geocode_map = {
        "地点甲": {
            "location": "116.3100,39.9920",
            "formatted_address": "地址甲",
            "city": "北京市",
        },
        "地点乙": {
            "location": "116.3260,40.0030",
            "formatted_address": "地址乙",
            "city": "北京市",
        },
    }

    async def _fake_geocode(address, **kwargs):
        return geocode_map.get(address)

    async def _fake_search_pois(*args, **kwargs):
        return [
            {
                "name": "测试咖啡馆",
                "location": "116.3180,39.9970",
                "address": "测试地址",
                "business_hours": "08:00-21:00",
                "tel": "010-12345678",
                "tag": ["咖啡馆"],
                "biz_ext": {"rating": "4.7"},
                "_matched_requirements": [],
                "_recommendation_reason": "距离适中",
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

    async def _fake_smart_city_inference(
        original_locations, geocode_results, city_hint=""
    ):
        return geocode_results

    async def _fake_generate_html_page(*args, **kwargs):
        return "workspace/js_src/place_recommendation_test.html"

    async def _fake_transport_tips(*args, **kwargs):
        return "<li>测试交通建议</li>"

    async def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "_calculate_smart_center should not run for the amap provider, "
            "even when commute_budgets is supplied -- it costs an extra "
            "round of POI searches for no benefit since _verify_commute_fairness "
            "only supports the google provider"
        )

    monkeypatch.setattr(recommender, "_geocode", _fake_geocode)
    monkeypatch.setattr(recommender, "_search_pois", _fake_search_pois)
    monkeypatch.setattr(
        recommender, "_smart_city_inference", _fake_smart_city_inference
    )
    monkeypatch.setattr(recommender, "_generate_html_page", _fake_generate_html_page)
    monkeypatch.setattr(
        recommender, "_llm_generate_transport_tips", _fake_transport_tips
    )
    monkeypatch.setattr(recommender, "_calculate_smart_center", _fail_if_called)
    return recommender


def test_execute_skips_smart_center_for_amap_even_with_commute_budgets(monkeypatch):
    recommender = _make_amap_recommender_with_stubs(monkeypatch)

    result = asyncio.run(
        recommender.execute(
            locations=["地点甲", "地点乙"],
            keywords="咖啡馆",
            commute_budgets=[15, 15],
            transport_mode="TRANSIT",
        )
    )

    assert result.output


def _matrix_result(origin_index, destination_index, minutes, ok=True):
    return {
        "origin_index": origin_index,
        "destination_index": destination_index,
        "duration_seconds": minutes * 60,
        "distance_meters": minutes * 200,
        "ok": ok,
    }


def test_verify_commute_fairness_skips_when_not_google_provider(monkeypatch):
    recommender = CafeRecommender(api_key="test-key")
    assert recommender.map_provider == "amap"

    async def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "google_route_matrix should not be called for amap provider"
        )

    monkeypatch.setattr(
        google_directions_client, "google_route_matrix", _fail_if_called
    )

    result = asyncio.run(
        recommender._verify_commute_fairness(
            top_candidates=[(116.30, 39.90), (116.31, 39.91)],
            participant_coords=[(116.29, 39.89), (116.32, 39.92)],
            commute_budgets=[20, 20],
            transport_mode="TRANSIT",
            participant_names=["Alice", "Bob"],
        )
    )

    assert result is None


def test_verify_commute_fairness_picks_first_candidate_satisfying_all_budgets(
    monkeypatch,
):
    recommender = CafeRecommender(api_key="test-key")
    recommender.map_provider = "google"

    # Candidate 0 fails Bob's budget (42 > 25); candidate 1 satisfies everyone.
    async def _fake_route_matrix(origins, destinations, mode="TRANSIT", api_key=None):
        return [
            _matrix_result(0, 0, 12),  # Alice -> candidate 0: 12 min
            _matrix_result(1, 0, 42),  # Bob -> candidate 0: 42 min (over budget)
            _matrix_result(0, 1, 15),  # Alice -> candidate 1: 15 min
            _matrix_result(1, 1, 18),  # Bob -> candidate 1: 18 min
        ]

    monkeypatch.setattr(
        google_directions_client, "google_route_matrix", _fake_route_matrix
    )

    candidate0 = (116.30, 39.90)
    candidate1 = (116.31, 39.91)
    result = asyncio.run(
        recommender._verify_commute_fairness(
            top_candidates=[candidate0, candidate1],
            participant_coords=[(116.29, 39.89), (116.32, 39.92)],
            commute_budgets=[25, 25],
            transport_mode="TRANSIT",
            participant_names=["Alice", "Bob"],
        )
    )

    assert result["winner_point"] == candidate1
    assert result["winner_index"] == 1
    assert result["attempts"][0]["accepted"] is False
    assert result["attempts"][0]["violations"][0]["participant"] == "Bob"
    assert result["attempts"][1]["accepted"] is True


def test_verify_commute_fairness_falls_back_to_least_violations(monkeypatch):
    recommender = CafeRecommender(api_key="test-key")
    recommender.map_provider = "google"

    # Neither candidate satisfies everyone; candidate 1 violates fewer budgets.
    async def _fake_route_matrix(origins, destinations, mode="TRANSIT", api_key=None):
        return [
            _matrix_result(0, 0, 40),  # Alice -> candidate 0: over her 20min budget
            _matrix_result(1, 0, 40),  # Bob -> candidate 0: over his 25min budget
            _matrix_result(0, 1, 10),  # Alice -> candidate 1: within budget
            _matrix_result(1, 1, 40),  # Bob -> candidate 1: over his budget
        ]

    monkeypatch.setattr(
        google_directions_client, "google_route_matrix", _fake_route_matrix
    )

    candidate0 = (116.30, 39.90)
    candidate1 = (116.31, 39.91)
    result = asyncio.run(
        recommender._verify_commute_fairness(
            top_candidates=[candidate0, candidate1],
            participant_coords=[(116.29, 39.89), (116.32, 39.92)],
            commute_budgets=[20, 25],
            transport_mode="TRANSIT",
            participant_names=["Alice", "Bob"],
        )
    )

    assert result["winner_point"] == candidate1
    assert all(not a["accepted"] for a in result["attempts"])
    assert len(result["attempts"][1]["violations"]) == 1


def test_verify_commute_fairness_breaks_violation_tie_by_total_overage(monkeypatch):
    # Regression test for a real bug found during live verification against Google's
    # Routes API (3 spread-out NYC boroughs): when every candidate violates the same
    # NUMBER of participants' budgets, the old code always fell back to whichever
    # candidate happened to be listed first (the geometric center) -- even when another
    # candidate was objectively less bad for everyone. All three candidates below
    # violate both participants (2 violations each), but candidate 1 is a much smaller
    # overage than candidate 0 or candidate 2.
    recommender = CafeRecommender(api_key="test-key")
    recommender.map_provider = "google"

    async def _fake_route_matrix(origins, destinations, mode="TRANSIT", api_key=None):
        return [
            _matrix_result(0, 0, 45),  # Alice -> candidate 0: way over her 20min budget
            _matrix_result(1, 0, 80),  # Bob -> candidate 0: way over his 25min budget
            _matrix_result(0, 1, 21),  # Alice -> candidate 1: barely over
            _matrix_result(1, 1, 26),  # Bob -> candidate 1: barely over
            _matrix_result(0, 2, 45),  # Alice -> candidate 2: way over
            _matrix_result(1, 2, 69),  # Bob -> candidate 2: way over
        ]

    monkeypatch.setattr(
        google_directions_client, "google_route_matrix", _fake_route_matrix
    )

    candidate0 = (116.30, 39.90)
    candidate1 = (116.31, 39.91)
    candidate2 = (116.32, 39.92)
    result = asyncio.run(
        recommender._verify_commute_fairness(
            top_candidates=[candidate0, candidate1, candidate2],
            participant_coords=[(116.29, 39.89), (116.32, 39.92)],
            commute_budgets=[20, 25],
            transport_mode="TRANSIT",
            participant_names=["Alice", "Bob"],
        )
    )

    assert all(not a["accepted"] for a in result["attempts"])
    assert all(len(a["violations"]) == 2 for a in result["attempts"])  # tied on count
    assert result["winner_point"] == candidate1
    assert result["winner_index"] == 1


def test_verify_commute_fairness_treats_unreachable_as_worse_than_slow(monkeypatch):
    # Regression test for a real bug an independent review pass caught: when Google
    # Routes can't find a route at all (ok=False -> duration_minutes=None), the total-
    # overage tie-break computed `(None or 0) - budget`, a NEGATIVE number, making a
    # candidate nobody can actually reach via the requested mode look BETTER than a
    # candidate that's merely slow. An unreachable candidate must never win over a
    # reachable-but-over-budget one.
    recommender = CafeRecommender(api_key="test-key")
    recommender.map_provider = "google"

    async def _fake_route_matrix(origins, destinations, mode="TRANSIT", api_key=None):
        return [
            # Candidate 0: no transit route exists to Alice at all (e.g. across water).
            _matrix_result(0, 0, 0, ok=False),
            _matrix_result(1, 0, 15),  # Bob -> candidate 0: within budget
            # Candidate 1: everyone reachable, Alice just slightly over budget.
            _matrix_result(
                0, 1, 25
            ),  # Alice -> candidate 1: 5 min over her 20min budget
            _matrix_result(1, 1, 15),  # Bob -> candidate 1: within budget
        ]

    monkeypatch.setattr(
        google_directions_client, "google_route_matrix", _fake_route_matrix
    )

    candidate0 = (116.30, 39.90)
    candidate1 = (116.31, 39.91)
    result = asyncio.run(
        recommender._verify_commute_fairness(
            top_candidates=[candidate0, candidate1],
            participant_coords=[(116.29, 39.89), (116.32, 39.92)],
            commute_budgets=[20, 25],
            transport_mode="TRANSIT",
            participant_names=["Alice", "Bob"],
        )
    )

    # Both candidates tie on violation COUNT (1 each), so this only passes with the fix.
    assert len(result["attempts"][0]["violations"]) == 1
    assert len(result["attempts"][1]["violations"]) == 1
    assert result["winner_point"] == candidate1
    assert result["winner_index"] == 1


def _make_recommender_for_smart_center(monkeypatch, scores_by_index):
    recommender = CafeRecommender(api_key="test-key")
    recommender.map_provider = "google"

    call_count = {"n": 0}

    async def _fake_evaluate(candidate, participant_coords, keywords):
        idx = call_count["n"]
        call_count["n"] += 1
        score = scores_by_index[idx % len(scores_by_index)]
        return score, {"scores": {"poi_density": score}}

    monkeypatch.setattr(recommender, "_evaluate_center_candidate", _fake_evaluate)
    return recommender


def test_calculate_smart_center_skips_commute_check_without_budgets(monkeypatch):
    recommender = _make_recommender_for_smart_center(
        monkeypatch, scores_by_index=[50, 40, 30, 20, 10, 60, 25, 15, 5, 45]
    )

    async def _fail_if_called(*args, **kwargs):
        raise AssertionError("_verify_commute_fairness should not run without budgets")

    monkeypatch.setattr(recommender, "_verify_commute_fairness", _fail_if_called)

    coords = [(116.30, 39.90), (116.32, 39.92)]
    _, details = asyncio.run(recommender._calculate_smart_center(coords))

    assert "commute_check" not in details


def test_calculate_smart_center_uses_commute_check_winner(monkeypatch):
    recommender = _make_recommender_for_smart_center(
        monkeypatch, scores_by_index=[50, 40, 30, 20, 10, 60, 25, 15, 5, 45]
    )

    fake_winner_point = (999.0, 88.0)

    async def _fake_verify(
        top_candidates,
        participant_coords,
        commute_budgets,
        transport_mode,
        participant_names,
    ):
        assert len(top_candidates) == 3  # only the top-3 by cheap score get checked
        return {
            "transport_mode": transport_mode,
            "attempts": [
                {
                    "label": "Candidate 1",
                    "accepted": True,
                    "durations": [],
                    "violations": [],
                }
            ],
            "winner_point": fake_winner_point,
            "winner_index": 0,
        }

    monkeypatch.setattr(recommender, "_verify_commute_fairness", _fake_verify)

    coords = [(116.30, 39.90), (116.32, 39.92)]
    center, details = asyncio.run(
        recommender._calculate_smart_center(coords, commute_budgets=[20, 20])
    )

    assert center == fake_winner_point
    assert details["commute_check"]["winner_point"] == fake_winner_point


def test_render_commute_check_html_empty_without_data():
    recommender = CafeRecommender(api_key="test-key")
    assert recommender._render_commute_check_html(None, "en") == ""
    assert recommender._render_commute_check_html({"attempts": []}, "en") == ""


def test_render_commute_check_html_shows_rejection_reason():
    recommender = CafeRecommender(api_key="test-key")
    commute_check = {
        "transport_mode": "TRANSIT",
        "attempts": [
            {
                "label": "Candidate 1 (geometric center)",
                "accepted": False,
                "durations": [
                    {"participant": "Alice", "duration_minutes": 12.0},
                    {"participant": "Bob", "duration_minutes": 42.0},
                ],
                "violations": [
                    {
                        "participant": "Bob",
                        "duration_minutes": 42.0,
                        "budget_minutes": 25,
                    }
                ],
            }
        ],
    }

    html = recommender._render_commute_check_html(commute_check, "en")

    assert "Bob" in html
    assert "42min" in html
    assert "rejected" in html.lower()
