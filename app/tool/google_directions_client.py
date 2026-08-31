"""Google Routes API 客户端 -- 真实通勤时间查询（computeRouteMatrix）

设计原则：
- 与 app/tool/google_maps_client.py 同一套约定：module 级 TIMEOUT 常量、共享的
  _resolve_api_key（同一个 GOOGLE_MAPS_API_KEY），任何失败（网络/超时/非200）返回空列表
  而非抛异常，不打断上游调用者
- 响应解析拆成纯函数 _parse_route_matrix_response，不依赖网络，方便直接单测
- 内部坐标沿用仓库既有的 (lng, lat) 元组惯例（高德习惯），只在拼 Google 请求体时换成
  latLng 的 {latitude, longitude}
"""

from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from app.logger import logger
from app.tool.google_maps_client import _resolve_api_key

ROUTE_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
# 批量矩阵计算比单次 geocode/places 查询慢，给更宽松的超时
TIMEOUT = aiohttp.ClientTimeout(total=15.0)

# TRANSIT / TRAFFIC_AWARE_OPTIMAL 上限 100 elements，其余 travelMode 上限 625
# （官方文档 2026-08-25 核实：developers.google.com/maps/documentation/routes/compute_route_matrix）
_TRANSIT_MODES = {"TRANSIT", "TRAFFIC_AWARE_OPTIMAL"}
_MAX_ELEMENTS_TRANSIT = 100
_MAX_ELEMENTS_DEFAULT = 625


def _to_waypoint(coord: Tuple[float, float]) -> Dict[str, Any]:
    lng, lat = coord
    return {"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lng}}}}


def _parse_route_matrix_response(data: Any) -> List[Dict[str, Any]]:
    """把 computeRouteMatrix 的原始响应（元素数组）归一化为内部格式。

    纯函数，不做任何网络调用 -- 单测直接喂 fixture 即可，不需要 mock HTTP。
    """
    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []
    for elem in data:
        if not isinstance(elem, dict):
            continue

        condition = elem.get("condition", "")
        duration_raw = elem.get("duration", "")
        duration_seconds: Optional[int] = None
        if isinstance(duration_raw, str) and duration_raw.endswith("s"):
            try:
                duration_seconds = int(float(duration_raw[:-1]))
            except ValueError:
                duration_seconds = None

        results.append(
            {
                "origin_index": elem.get("originIndex", 0),
                "destination_index": elem.get("destinationIndex", 0),
                "duration_seconds": duration_seconds,
                "distance_meters": elem.get("distanceMeters"),
                "ok": condition == "ROUTE_EXISTS" and duration_seconds is not None,
            }
        )
    return results


async def google_route_matrix(
    origins: List[Tuple[float, float]],
    destinations: List[Tuple[float, float]],
    mode: str = "TRANSIT",
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """批量查询多个起点到多个终点的真实通勤时间（一次 HTTP 调用覆盖整个矩阵）。

    Args:
        origins/destinations: (lng, lat) 元组列表，与仓库其余坐标惯例一致
        mode: Routes API travelMode 枚举 -- "TRANSIT" | "DRIVE" | "WALK" | "BICYCLE" | "TWO_WHEELER"
        api_key: 显式传入优先，否则读 GOOGLE_MAPS_API_KEY 环境变量（同 google_maps_client.py）

    Returns:
        归一化列表，每个元素：
        {"origin_index", "destination_index", "duration_seconds", "distance_meters", "ok"}
        origin_index/destination_index 对应输入列表的下标，按 origins x destinations 展开，
        列表长度可能小于 len(origins)*len(destinations)（Google 对无法计算的 pair 可能跳过而非报错）。

        任何失败（key 未配置、网络异常、超时、非 200、matrix 太大）返回空列表，不抛异常 --
        调用方应把空列表当"这次查不到真实通勤时间"处理，不代表所有候选都不可行。
    """
    key = _resolve_api_key(api_key)
    if not key:
        logger.warning("Google Maps API key 未配置，跳过 route matrix 查询")
        return []
    if not origins or not destinations:
        return []

    element_count = len(origins) * len(destinations)
    element_cap = (
        _MAX_ELEMENTS_TRANSIT if mode in _TRANSIT_MODES else _MAX_ELEMENTS_DEFAULT
    )
    if element_count > element_cap:
        logger.warning(
            f"route matrix 请求 {element_count} 个 pair 超过 {mode} 上限 {element_cap}，跳过"
        )
        return []

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status,condition",
    }
    body: Dict[str, Any] = {
        "origins": [_to_waypoint(c) for c in origins],
        "destinations": [_to_waypoint(c) for c in destinations],
        "travelMode": mode,
    }
    # routingPreference 只对非 TRANSIT 模式有意义（TRANSIT 靠时刻表，没有"路况感知"这个概念）
    if mode == "DRIVE":
        body["routingPreference"] = "TRAFFIC_AWARE"

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(
                ROUTE_MATRIX_URL, headers=headers, json=body
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(
                        f"Google Route Matrix 请求失败: {resp.status}, 响应: {text[:200]}"
                    )
                    return []
                data = await resp.json()
    except Exception as e:
        logger.error(f"Google Route Matrix 异常: {e}")
        return []

    return _parse_route_matrix_response(data)
