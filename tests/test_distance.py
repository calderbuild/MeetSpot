import math

import pytest

from app.tool.meetspot_recommender import CafeRecommender

ONE_DEGREE_M = 111_195  # 地球平均半径下，大圆上 1 度的弧长


def _distance(point1, point2):
    return CafeRecommender(api_key="test-key")._calculate_distance(point1, point2)


@pytest.mark.parametrize("lat", [0.0, 23.13, 39.9, 51.5, 59.33, -33.87])
def test_one_degree_of_longitude_shrinks_with_latitude(lat):
    expected = ONE_DEGREE_M * math.cos(math.radians(lat))
    assert _distance((10.0, lat), (11.0, lat)) == pytest.approx(expected, rel=1e-3)


def test_one_degree_of_latitude_is_constant():
    assert _distance((116.4, 39.0), (116.4, 40.0)) == pytest.approx(ONE_DEGREE_M, rel=1e-3)
    assert _distance((103.8, 1.0), (103.8, 2.0)) == pytest.approx(ONE_DEGREE_M, rel=1e-3)


def test_known_city_pair():
    beijing = (116.4074, 39.9042)
    shanghai = (121.4737, 31.2304)
    assert _distance(beijing, shanghai) == pytest.approx(1_068_000, rel=5e-3)


def test_distance_is_symmetric_and_zero_for_same_point():
    a, b = (-74.0060, 40.7128), (-73.9857, 40.7484)
    assert _distance(a, b) == pytest.approx(_distance(b, a))
    assert _distance(a, a) == 0


def test_distance_across_the_antimeridian_is_short():
    assert _distance((179.9, 0.0), (-179.9, 0.0)) == pytest.approx(0.2 * ONE_DEGREE_M, rel=1e-3)


def test_max_distance_filter_uses_real_distance_near_the_equator():
    recommender = CafeRecommender(api_key="test-key")
    center = (103.8500, 1.3000)
    places = [
        {
            "name": "Near",
            "location": "103.8560,1.3000",  # 约 667 米
            "address": "near",
            "biz_ext": {"rating": "4.5"},
            "tag": [],
        },
        {
            "name": "Far",
            "location": "103.8600,1.3000",  # 约 1112 米，旧算法算成 850 米
            "address": "far",
            "biz_ext": {"rating": "4.5"},
            "tag": [],
        },
    ]

    ranked = recommender._rank_places(
        places, center, "", "cafe", max_distance=1000, language="en"
    )

    assert [p["name"] for p in ranked] == ["Near"]
    assert ranked[0]["_distance"] == pytest.approx(667, abs=2)
