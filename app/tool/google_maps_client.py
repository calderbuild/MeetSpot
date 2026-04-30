"""Google Maps API 客户端 -- 国际场景 POI 搜索与地理编码

设计原则：
- 输出格式严格对齐 MeetSpot 高德 POI 数据结构（location="lng,lat" 字符串、biz_ext.rating 字符串等），
  让 _rank_places / _generate_html_content 等下游逻辑无需感知 provider 差异
- API key 通过参数传入或从 GOOGLE_MAPS_API_KEY 环境变量读取，与 MeetSpot 三级配置兼容
- 所有错误转为返回空结果而非抛异常，与现有 _search_pois / _geocode 的错误处理一致
"""

import os
from typing import Any, Dict, List, Optional

import aiohttp

from app.logger import logger

PLACES_NEARBY = "https://places.googleapis.com/v1/places:searchNearby"
PLACES_TEXT = "https://places.googleapis.com/v1/places:searchText"
GEOCODE_BASE = "https://maps.googleapis.com/maps/api/geocode/json"
TIMEOUT = aiohttp.ClientTimeout(total=10.0)


def _resolve_api_key(api_key: Optional[str] = None) -> str:
    """优先使用传入参数，否则从环境变量读取"""
    if api_key:
        return api_key
    return os.getenv("GOOGLE_MAPS_API_KEY", "")


async def google_geocode(
    address: str, api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """通过 Google Geocoding API 解析地址。

    Returns:
        Dict with keys: location ("lng,lat"), formatted_address, city -- 或 None
        字段命名对齐高德 geocode 返回的核心字段，让上游缓存与城市推断逻辑可复用
    """
    key = _resolve_api_key(api_key)
    if not key:
        logger.warning("Google Maps API key 未配置，跳过 Google geocode")
        return None

    params = {"address": address, "key": key}
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(GEOCODE_BASE, params=params) as resp:
                if resp.status != 200:
                    logger.error(
                        f"Google Geocoding 请求失败: {resp.status}, 地址: {address}"
                    )
                    return None
                data = await resp.json()
    except Exception as e:
        logger.error(f"Google Geocoding 异常: {e}, 地址: {address}")
        return None

    if data.get("status") != "OK":
        logger.warning(
            f"Google Geocoding 状态异常: {data.get('status')}, 地址: {address}"
        )
        return None

    results = data.get("results", [])
    if not results:
        return None

    result = results[0]
    loc = result.get("geometry", {}).get("location", {})
    lat = loc.get("lat")
    lng = loc.get("lng")
    if lat is None or lng is None:
        return None

    city_name = ""
    for comp in result.get("address_components", []):
        types = comp.get("types", [])
        if "locality" in types or "administrative_area_level_1" in types:
            city_name = comp.get("long_name", "")
            if "locality" in types:
                break

    return {
        "location": f"{lng},{lat}",
        "formatted_address": result.get("formatted_address", ""),
        "city": city_name,
        "_source": "google",
    }


async def google_search_pois(
    location: str,
    keywords: str,
    radius: int = 5000,
    types: str = "",
    offset: int = 20,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """通过 Google Places API 搜索 POI，签名对齐 _search_pois。

    Args:
        location: "lng,lat" 字符串（高德格式，内部转 lat/lng 给 Google）
        keywords: 搜索关键词
        radius: 搜索半径（米），Google 上限 50000
        types: 场所类型（与高德 types 编码不通用，此处主要用 keywords）
        offset: 单次返回数量，对应 Google 的 maxResultCount

    Returns:
        归一化为高德 POI 格式的列表（name, address, location, biz_ext, photos, tag, ...）
    """
    key = _resolve_api_key(api_key)
    if not key:
        logger.warning("Google Maps API key 未配置，跳过 Google POI 搜索")
        return []

    if "," not in location:
        logger.error(f"Google search_pois: location 格式错误 {location}")
        return []
    try:
        lng_str, lat_str = location.split(",", 1)
        lng = float(lng_str)
        lat = float(lat_str)
    except (ValueError, TypeError):
        logger.error(f"Google search_pois: 坐标解析失败 {location}")
        return []

    capped_radius = min(max(radius, 100), 50000)
    capped_offset = min(max(offset, 1), 20)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.location,"
            "places.rating,places.priceLevel,places.googleMapsUri,"
            "places.userRatingCount,places.types,places.primaryType,"
            "places.photos"
        ),
    }

    if keywords:
        url = PLACES_TEXT
        body: Dict[str, Any] = {
            "textQuery": keywords,
            "maxResultCount": capped_offset,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": capped_radius,
                }
            },
        }
    else:
        url = PLACES_NEARBY
        body = {
            "maxResultCount": capped_offset,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": capped_radius,
                }
            },
        }
        if types:
            body["includedTypes"] = [t.strip() for t in types.split(",") if t.strip()]

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(url, headers=headers, json=body) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(
                        f"Google Places 请求失败: {resp.status}, 响应: {text[:200]}"
                    )
                    return []
                data = await resp.json()
    except Exception as e:
        logger.error(f"Google Places 异常: {e}")
        return []

    pois: List[Dict[str, Any]] = []
    for place in data.get("places", []):
        loc = place.get("location", {}) or {}
        plat = loc.get("latitude")
        plng = loc.get("longitude")
        if plat is None or plng is None:
            continue

        display_name = place.get("displayName", {}) or {}
        name = (
            display_name.get("text", "")
            if isinstance(display_name, dict)
            else str(display_name)
        )

        rating = place.get("rating", 0) or 0
        review_count = place.get("userRatingCount", 0) or 0

        photos_raw = place.get("photos", []) or []
        photos: List[Dict[str, str]] = []
        for ph in photos_raw[:5]:
            ref = ph.get("name", "")
            if ref:
                photos.append(
                    {
                        "title": "",
                        "url": (
                            f"https://places.googleapis.com/v1/{ref}/media"
                            f"?maxWidthPx=400&key={key}"
                        ),
                    }
                )

        types_list = place.get("types", []) or []
        primary_type = place.get("primaryType", "")
        tag = ";".join([t for t in [primary_type, *types_list] if t][:5])

        pois.append(
            {
                "name": name,
                "address": place.get("formattedAddress", ""),
                "location": f"{plng},{plat}",
                "type": primary_type,
                "tag": tag,
                "biz_ext": {
                    "rating": str(rating) if rating else "",
                    "review_count": str(review_count) if review_count else "",
                    "cost": "",
                },
                "photos": photos,
                "google_maps_uri": place.get("googleMapsUri", ""),
                "_source": "google",
            }
        )
    return pois
