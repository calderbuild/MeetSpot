"""Qloo Taste AI 客户端 -- 多人口味公平（Group Taste Fairness）

设计原则（与 google_maps_client.py 同一套约定）：
- API key 从 QLOO_API_KEY 环境变量读取；hackathon key 只能配 hackathon.api.qloo.com
- 网络失败 / 非 200 返回 None 或空结果，不抛异常，上游据此回退到不带口味的原有推荐
- 排序、分位数、geohash 等逻辑全部拆成纯函数，单测直接喂 fixture，不 mock HTTP

为什么每个人单独打分而不是把所有人的口味一次传给 Qloo：合成一个人会把分歧抹平。
固定同一批候选（filter.results.entities），逐人查 affinity，再按"最不满意的人"排序。
"""

import asyncio
import os
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from app.logger import logger

QLOO_BASE = os.getenv("QLOO_API_BASE", "https://hackathon.api.qloo.com")
TIMEOUT = aiohttp.ClientTimeout(total=15.0)
MAX_TAKE = 50  # insights 的 take 超过 50 会返回 400（2026-10-03 实测）

# 场馆 tag（2026-10-03 纽约实测有结果；urn:tag:category:place:coffee 返回 0 条，别用）
VENUE_TAGS = {
    "restaurant": "urn:tag:category:place:restaurant",
    "cafe": "urn:tag:category:place:cafe",
    "bar": "urn:tag:category:place:bar",
}
_CAFE_WORDS = ("cafe", "café", "coffee", "tea", "咖啡", "茶")
_BAR_WORDS = ("bar", "pub", "cocktail", "wine", "beer", "酒吧", "酒")

# 口味解析只搜文化类实体；不限类型时 "sushi" 会搜成专辑、"Taylor Swift" 先命中 person
TASTE_TYPES = ",".join(
    f"urn:entity:{t}"
    for t in ("artist", "movie", "tv_show", "brand", "book", "podcast", "videogame")
)
_GEO_SKIP_SUBTYPES = ("urn:tag:place", "urn:tag:location", "urn:tag:country")

_GEOHASH_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"


def _resolve_api_key(api_key: Optional[str] = None) -> str:
    return api_key or os.getenv("QLOO_API_KEY", "")


# ========== 纯函数 ==========


def venue_tag_for(keywords: str) -> str:
    """把 MeetSpot 的场馆关键词映射成 Qloo 场馆 tag，默认餐厅。"""
    text = (keywords or "").lower()
    if any(w in text for w in _CAFE_WORDS):
        return VENUE_TAGS["cafe"]
    if any(w in text for w in _BAR_WORDS):
        return VENUE_TAGS["bar"]
    return VENUE_TAGS["restaurant"]


def split_tastes(text: str) -> List[str]:
    """ "Taylor Swift, Barbie; sushi" -> ["Taylor Swift", "Barbie", "sushi"]"""
    parts = (text or "").replace(";", ",").replace("，", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


def percentiles(affinity: Dict[str, float]) -> Dict[str, float]:
    """每个人在候选集里的分位数（0 = 最不喜欢，1 = 最喜欢）。

    Qloo 的 affinity 原始值挤在 0.6-0.9 且带热度偏置，跨人直接比没有意义；
    换成"这家店在你自己的排序里排第几"，再取所有人的最小值才公平。
    """
    ordered = sorted(affinity, key=lambda cid: affinity[cid])
    if len(ordered) == 1:
        return {ordered[0]: 1.0}
    last = len(ordered) - 1
    return {cid: i / last for i, cid in enumerate(ordered)}


def maximin_order(pct_by_person: Dict[str, Dict[str, float]]) -> List[str]:
    """按"最不满意的人的分位数"降序排，平均分位数做平局裁决。

    只排所有人都有分数的候选（某人的打分接口漏掉一家店时，那家店不参与排序）。
    """
    people = list(pct_by_person)
    common = set.intersection(*(set(pct_by_person[p]) for p in people))

    def key(cid: str) -> Tuple[float, float]:
        vals = [pct_by_person[p][cid] for p in people]
        return (-min(vals), -sum(vals) / len(vals))

    return sorted(common, key=key)


def mean_order(pct_by_person: Dict[str, Dict[str, float]]) -> List[str]:
    people = list(pct_by_person)
    common = set.intersection(*(set(pct_by_person[p]) for p in people))
    return sorted(common, key=lambda c: -sum(pct_by_person[p][c] for p in people))


def excluded_by_fairness(
    pct_by_person: Dict[str, Dict[str, float]], top_n: int
) -> List[Dict[str, Any]]:
    """平均分能进前 N、但因为有人很不喜欢而被 maximin 挤出前 N 的店。

    这是"按平均分推荐会坑掉某个人"的直接证据，结果页单独展示。
    """
    fair_top = set(maximin_order(pct_by_person)[:top_n])
    out = []
    for cid in mean_order(pct_by_person)[:top_n]:
        if cid in fair_top:
            continue
        unhappy = min(pct_by_person, key=lambda p: pct_by_person[p][cid])
        out.append(
            {
                "entity_id": cid,
                "unhappy_person": unhappy,
                "unhappy_pct": pct_by_person[unhappy][cid],
            }
        )
    return out


def geohash_encode(lat: float, lng: float, precision: int = 7) -> str:
    """标准 geohash 编码（Qloo heatmap 返回 7 位 geohash 格子）。"""
    lat_lo, lat_hi, lng_lo, lng_hi = -90.0, 90.0, -180.0, 180.0
    bits, bit_count, even, out = 0, 0, True, []
    while len(out) < precision:
        if even:
            mid = (lng_lo + lng_hi) / 2
            bit = lng > mid
            lng_lo, lng_hi = (mid, lng_hi) if bit else (lng_lo, mid)
        else:
            mid = (lat_lo + lat_hi) / 2
            bit = lat > mid
            lat_lo, lat_hi = (mid, lat_hi) if bit else (lat_lo, mid)
        bits = (bits << 1) | int(bit)
        even = not even
        bit_count += 1
        if bit_count == 5:
            out.append(_GEOHASH_ALPHABET[bits])
            bits, bit_count = 0, 0
    return "".join(out)


def min_heat(heat_by_person: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Dict]:
    """每个 geohash 格子取所有人里最低的 affinity_rank = "口味公平热度"。

    只保留所有人都有数据的格子；返回 {geohash: {"heat", "lat", "lng"}}。
    """
    people = list(heat_by_person)
    common = set.intersection(*(set(heat_by_person[p]) for p in people))
    out = {}
    for gh in common:
        cell = heat_by_person[people[0]][gh]
        out[gh] = {
            "heat": min(heat_by_person[p][gh]["heat"] for p in people),
            "lat": cell["lat"],
            "lng": cell["lng"],
        }
    return out


def heat_at(fair_heat: Dict[str, Dict], lng: float, lat: float) -> Optional[float]:
    cell = fair_heat.get(geohash_encode(lat, lng, 7))
    return cell["heat"] if cell else None


def top_reason(explain: List[Dict], names: Dict[str, str]) -> Optional[Dict]:
    """explainability 里贡献最大的那一项口味 -> {"name", "share"}。"""
    if not explain:
        return None
    best = max(explain, key=lambda e: e.get("score", 0))
    name = names.get(best.get("entity_id", ""))
    return {"name": name, "share": best.get("score", 0)} if name else None


def to_poi(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Qloo place 实体 -> 高德 POI 格式（与 google_maps_client 的归一化一致）。

    让 _rank_places / _generate_html_content 不需要感知 provider 差异。
    """
    props = entity.get("properties") or {}
    loc = entity.get("location") or {}
    rating = props.get("business_rating")
    tags = [t.get("name") for t in entity.get("tags", []) if t.get("name")]
    price_level = props.get("price_level")
    return {
        "id": entity.get("entity_id", ""),
        "name": entity.get("name", ""),
        "location": f"{loc.get('lon')},{loc.get('lat')}",
        "address": props.get("address", ""),
        "tel": props.get("phone", "") or "",
        "type": ";".join(tags[:3]),
        "tag": ",".join(tags[:6]),
        "biz_ext": {
            "rating": f"{float(rating):.1f}" if rating is not None else "",
            "cost": "$" * int(price_level) if price_level else "",
        },
        "photos": [],
        "_qloo_entity_id": entity.get("entity_id", ""),
        "_qloo_popularity": entity.get("popularity", 0),
    }


# ========== 网络层 ==========


_RETRY_DELAYS = (1.0, 2.0, 4.0)  # hackathon key 并发稍多就回 429（2026-10-03 实测）


async def _get(
    session: aiohttp.ClientSession, path: str, params: Dict[str, Any], api_key: str
) -> Optional[Dict]:
    """GET 一次 Qloo 接口；429 按退避重试，其余失败返回 None。

    429 不重试的话，被限流的口味会被当成"搜不到"展示给用户，结果是错的而不只是慢。
    """
    for delay in (*_RETRY_DELAYS, None):
        try:
            async with session.get(
                QLOO_BASE + path, params=params, headers={"X-Api-Key": api_key}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                body = (await resp.text())[:200]
        except Exception as e:
            logger.warning(f"Qloo {path} 请求异常: {e}")
            return None
        if resp.status != 429 or delay is None:
            logger.warning(f"Qloo {path} 返回 {resp.status}: {body}")
            return None
        await asyncio.sleep(delay)
    return None


async def _search_one(session, query: str, api_key: str) -> Dict[str, Any]:
    data = await _get(
        session, "/search", {"query": query, "types": TASTE_TYPES, "take": 1}, api_key
    )
    hit = ((data or {}).get("results") or [None])[0]
    if not hit:
        return {"query": query, "entity_id": None, "name": None, "kind": None}
    kind = (hit.get("types") or [hit.get("subtype") or ""])[0].split(":")[-1]
    return {
        "query": query,
        "entity_id": hit.get("entity_id"),
        "name": hit.get("name"),
        "kind": kind.replace("_", " "),
    }


async def resolve_people(
    names: List[str], tastes: List[str], api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """每个人的口味文本 -> 解析后的 Qloo 实体。没填口味的人 items 为空（"无偏好"）。"""
    key = _resolve_api_key(api_key)
    queries = [split_tastes(t) for t in tastes]
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        flat = await asyncio.gather(
            *(_search_one(session, q, key) for qs in queries for q in qs)
        )
    people, i = [], 0
    for name, qs in zip(names, queries):
        hits = list(flat[i : i + len(qs)])
        i += len(qs)
        people.append(
            {
                "name": name,
                "items": [h for h in hits if h["entity_id"]],
                "unresolved": [h["query"] for h in hits if not h["entity_id"]],
            }
        )
    return people


def _point(lng: float, lat: float) -> str:
    return f"POINT({lng} {lat})"


async def _heat_for(session, center, ids: List[str], radius: int, api_key: str):
    data = await _get(
        session,
        "/v2/insights",
        {
            "filter.type": "urn:heatmap",
            "filter.location": _point(*center),
            "filter.location.radius": radius,
            "signal.interests.entities": ",".join(ids),
        },
        api_key,
    )
    cells = ((data or {}).get("results") or {}).get("heatmap") or []
    return {
        c["location"]["geohash"]: {
            "heat": c["query"]["affinity_rank"],
            "lat": c["location"]["latitude"],
            "lng": c["location"]["longitude"],
        }
        for c in cells
    }


async def group_heat(
    center: Tuple[float, float],
    people: List[Dict[str, Any]],
    radius: int = 6000,
    api_key: Optional[str] = None,
) -> Dict[str, Dict]:
    """每人一张 Qloo 口味热力图，按格子取最小值。没有有效口味的人不参与。"""
    key = _resolve_api_key(api_key)
    tasted = [p for p in people if p["items"]]
    if not tasted:
        return {}
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        heats = await asyncio.gather(
            *(
                _heat_for(
                    session, center, [i["entity_id"] for i in p["items"]], radius, key
                )
                for p in tasted
            )
        )
    if not all(heats):
        return {}
    return min_heat({p["name"]: h for p, h in zip(tasted, heats)})


async def _score_person(session, cand_ids: List[str], ids: List[str], api_key: str):
    data = await _get(
        session,
        "/v2/insights",
        {
            "filter.type": "urn:entity:place",
            "filter.results.entities": ",".join(cand_ids),
            "signal.interests.entities": ",".join(ids),
            "feature.explainability": "true",
            "take": min(len(cand_ids), MAX_TAKE),
        },
        api_key,
    )
    ents = ((data or {}).get("results") or {}).get("entities") or []
    return {
        e["entity_id"]: {
            "affinity": (e.get("query") or {}).get("affinity", 0.0),
            "explain": ((e.get("query") or {}).get("explainability") or {}).get(
                "signal.interests.entities", []
            ),
        }
        for e in ents
    }


async def _common_ground(session, a: Dict, b: Dict, api_key: str) -> List[str]:
    data = await _get(
        session,
        "/v2/analysis/compare",
        {
            "a.signal.interests.entities": ",".join(i["entity_id"] for i in a["items"]),
            "b.signal.interests.entities": ",".join(i["entity_id"] for i in b["items"]),
            "take": 15,
        },
        api_key,
    )
    tags = ((data or {}).get("results") or {}).get("tags") or []
    keep = [
        t for t in tags if not (t.get("subtype") or "").startswith(_GEO_SKIP_SUBTYPES)
    ]
    keep.sort(key=lambda t: -(t.get("query") or {}).get("score", 0))
    return [t["name"] for t in keep[:4] if t.get("name")]


async def rank_venues(
    center: Tuple[float, float],
    keywords: str,
    people: List[Dict[str, Any]],
    radius: int = 2000,
    top_n: int = 6,
    price_level_max: Optional[int] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """公平中心点附近取候选 -> 逐人打分 -> maximin 排序 -> 解释、被排除的店、共同点。

    Returns None 表示口味排序不可用（无 key / 没有人有有效口味 / 候选为空 / 打分失败），
    上游回退到原有推荐。
    """
    key = _resolve_api_key(api_key)
    tasted = [p for p in people if p["items"]]
    if not key or not tasted:
        return None

    params = {
        "filter.type": "urn:entity:place",
        "filter.tags": venue_tag_for(keywords),
        "filter.location": _point(*center),
        "filter.location.radius": radius,
        "take": 30,
    }
    if price_level_max:
        params["filter.price_level.max"] = price_level_max

    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        data = await _get(session, "/v2/insights", params, key)
        candidates = ((data or {}).get("results") or {}).get("entities") or []
        if not candidates:
            logger.info("Qloo 候选为空，回退到原有推荐")
            return None
        cand_ids = [c["entity_id"] for c in candidates]
        scores, common = await asyncio.gather(
            asyncio.gather(
                *(
                    _score_person(
                        session, cand_ids, [i["entity_id"] for i in p["items"]], key
                    )
                    for p in tasted
                )
            ),
            asyncio.gather(
                *(
                    _common_ground(session, a, b, key)
                    for a, b in combinations(tasted, 2)
                )
            ),
        )

    if not all(scores):
        logger.warning("Qloo 有人打分为空，回退到原有推荐")
        return None

    pct = {
        p["name"]: percentiles({cid: s["affinity"] for cid, s in sc.items()})
        for p, sc in zip(tasted, scores)
    }
    order = maximin_order(pct)
    by_id = {c["entity_id"]: c for c in candidates}
    item_names = {i["entity_id"]: i["name"] for p in tasted for i in p["items"]}

    ranked = []
    for rank, cid in enumerate(order[:top_n]):
        poi = to_poi(by_id[cid])
        poi["_taste"] = {
            "rank": rank,
            "fair_pct": min(pct[n][cid] for n in pct),
            "people": [
                {
                    "name": p["name"],
                    "pct": pct[p["name"]][cid],
                    "because": top_reason(sc[cid]["explain"], item_names),
                }
                for p, sc in zip(tasted, scores)
            ],
        }
        ranked.append(poi)

    excluded = [
        {**x, "name": by_id[x["entity_id"]].get("name", "")}
        for x in excluded_by_fairness(pct, top_n)
    ]
    shared = []
    for tags in common:
        shared.extend(t for t in tags if t not in shared)

    return {
        "ranked": ranked,
        "excluded": excluded,
        "common_ground": shared[:5],
        "candidate_count": len(candidates),
    }
