"""Agent tool outputs that the LLM reads back to the user."""

import asyncio
import json

from app.agent.tools import CalculateCenterTool


def _center(coordinates):
    result = asyncio.run(
        CalculateCenterTool().execute(
            coordinates=coordinates, use_smart_algorithm=False
        )
    )
    assert result.error is None
    return json.loads(result.output)


def test_fairness_score_is_not_negative_for_a_spread_out_group():
    """Two people in central Beijing and one about 60 km south: the distances to
    the center differ by far more than 10 km, which used to give a score below 0."""
    data = _center(
        [
            {"lng": 116.30, "lat": 39.98, "name": "A"},
            {"lng": 116.31, "lat": 39.98, "name": "B"},
            {"lng": 116.40, "lat": 39.45, "name": "C"},
        ]
    )
    spread = data["max_distance"] - min(
        d["distance_to_center"] for d in data["distances"]
    )
    assert spread > 10_000
    assert data["fairness_score"] == 0.0


def test_fairness_score_is_100_for_two_people():
    """With two people the center is the midpoint, so both travel the same distance."""
    data = _center(
        [
            {"lng": 116.30, "lat": 39.98, "name": "A"},
            {"lng": 116.48, "lat": 39.90, "name": "B"},
        ]
    )
    assert data["fairness_score"] == 100.0
