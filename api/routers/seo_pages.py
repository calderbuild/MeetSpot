"""SEO页面路由 - 负责SSR页面与爬虫友好输出."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.services.seo_content import seo_content_generator as seo_generator
from app.i18n import get_translations, detect_language, DEFAULT_LANG

router = APIRouter()
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)

BASE_URL = "https://meetspot-irq2.onrender.com"


def _common_context(request: Request, lang: str = "zh") -> dict:
    """每次请求时动态读取的公共模板变量 + i18n."""
    t = get_translations(lang)
    return {
        "request": request,
        "baidu_tongji_id": os.getenv("BAIDU_TONGJI_ID", ""),
        "ga4_measurement_id": os.getenv("GA4_MEASUREMENT_ID", ""),
        "t": t,
        "lang": lang,
    }


@lru_cache(maxsize=128)
def load_cities() -> List[Dict]:
    """加载城市数据, 如不存在则创建默认值."""
    cities_file = "data/cities.json"
    if not os.path.exists(cities_file):
        os.makedirs("data", exist_ok=True)
        default_payload = {"cities": []}
        with open(cities_file, "w", encoding="utf-8") as fh:
            json.dump(default_payload, fh, ensure_ascii=False, indent=2)
        return []

    with open(cities_file, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload.get("cities", [])


def _get_city_by_slug(city_slug: str) -> Optional[Dict]:
    for city in load_cities():
        if city.get("slug") == city_slug:
            return city
    return None


def _build_schema_list(*schemas: Dict) -> List[Dict]:
    return [schema for schema in schemas if schema]


def _get_faqs(lang: str) -> List[Dict[str, str]]:
    """从翻译文件构建 FAQ 列表."""
    t = get_translations(lang)
    faqs = []
    for i in range(1, 13):
        q_key = f"faq.q{i}"
        a_key = f"faq.a{i}"
        if q_key in t and a_key in t:
            faqs.append({"question": t[q_key], "answer": t[a_key]})
    return faqs


def _lang_prefix(lang: str) -> str:
    return "/en" if lang == "en" else ""


def _hreflang_links(path: str) -> List[Dict[str, str]]:
    """生成 hreflang 链接对."""
    zh_path = path
    en_path = f"/en{path}" if path != "/" else "/en/"
    return [
        {"lang": "zh", "href": f"{BASE_URL}{zh_path}"},
        {"lang": "en", "href": f"{BASE_URL}{en_path}"},
        {"lang": "x-default", "href": f"{BASE_URL}{zh_path}"},
    ]


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------


def _render_homepage(request: Request, lang: str):
    t = get_translations(lang)
    prefix = _lang_prefix(lang)
    if lang == "en":
        keywords = "meeting point finder,midpoint calculator,group meetup,fair meeting location,AI venue recommendation"
    else:
        keywords = "聚会地点推荐,中点计算,多人聚会,公平会面点,AI 场所推荐"
    meta_tags = {
        "title": t.get("seo.home.title", "MeetSpot"),
        "description": t.get("seo.home.description", ""),
        "keywords": keywords,
    }
    faq_schema = seo_generator.generate_schema_org(
        "faq",
        {"faqs": _get_faqs(lang)[:6]},
    )
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("webapp", {}),
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org(
            "breadcrumb", {"items": [{"name": "Home", "url": f"{prefix}/"}]}
        ),
        faq_schema,
    )
    canonical = f"{BASE_URL}{prefix}/" if lang == "en" else f"{BASE_URL}/"
    return templates.TemplateResponse(
        "pages/home.html",
        {
            **_common_context(request, lang),
            "meta_title": meta_tags["title"][:60],
            "meta_description": meta_tags["description"][:155],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": canonical,
            "schema_jsonld": schema_list,
            "breadcrumbs": [],
            "cities": load_cities(),
            "hreflang": _hreflang_links("/"),
        },
    )


@router.get("/", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def homepage(request: Request):
    # 默认英文（国际化优先）。中文用户点击导航 中文 切到 /zh/，不依赖 Accept-Language
    # 仅 cookie lang=zh 时尊重用户上次选择，让回访的中文用户保持中文体验
    if request.cookies.get("lang") == "zh":
        return _render_homepage(request, "zh")
    return _render_homepage(request, "en")


@router.get("/en/", response_class=HTMLResponse)
@router.get("/en", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def homepage_en(request: Request):
    return _render_homepage(request, "en")


@router.get("/zh/", response_class=HTMLResponse)
@router.get("/zh", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def homepage_zh(request: Request):
    return _render_homepage(request, "zh")


# ---------------------------------------------------------------------------
# City page
# ---------------------------------------------------------------------------


def _render_city_page(request: Request, city_slug: str, lang: str):
    city = _get_city_by_slug(city_slug)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    t = get_translations(lang)
    prefix = _lang_prefix(lang)
    city_name = (
        city.get("name_en", city.get("name")) if lang == "en" else city.get("name")
    )
    meta_tags = seo_generator.generate_meta_tags(
        "city_page",
        {
            "city": city.get("name"),
            "city_en": city.get("name_en"),
            "venue_types": city.get("popular_venues", []),
        },
    )
    breadcrumb_items = [
        {"name": t.get("seo.breadcrumb.home", "Home"), "url": f"{prefix}/"},
        {"name": city_name, "url": f"{prefix}/meetspot/{city_slug}"},
    ]
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("webapp", {}),
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org("breadcrumb", {"items": breadcrumb_items}),
        seo_generator.generate_schema_org("city", city),
    )
    city_content = seo_generator.generate_city_content(city, lang=lang)
    path = f"/meetspot/{city_slug}"
    return templates.TemplateResponse(
        "pages/city.html",
        {
            **_common_context(request, lang),
            "meta_title": meta_tags["title"][:60],
            "meta_description": meta_tags["description"][:155],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": f"{BASE_URL}{prefix}{path}",
            "schema_jsonld": schema_list,
            "breadcrumbs": breadcrumb_items,
            "city": city,
            "city_content": city_content,
            "hreflang": _hreflang_links(path),
        },
    )


@router.get("/meetspot/{city_slug}", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def city_page(request: Request, city_slug: str):
    return _render_city_page(request, city_slug, "zh")


@router.get("/en/meetspot/{city_slug}", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def city_page_en(request: Request, city_slug: str):
    return _render_city_page(request, city_slug, "en")


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------


def _render_about(request: Request, lang: str):
    t = get_translations(lang)
    prefix = _lang_prefix(lang)
    meta_tags = {
        "title": t.get("seo.about.title", "About MeetSpot"),
        "description": t.get("seo.about.description", ""),
        "keywords": t.get("seo.about.keywords", "about MeetSpot,meeting algorithm"),
    }
    breadcrumb_items = [
        {"name": t.get("seo.breadcrumb.home", "Home"), "url": f"{prefix}/"},
        {"name": t.get("seo.breadcrumb.about", "About"), "url": f"{prefix}/about"},
    ]
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org("breadcrumb", {"items": breadcrumb_items}),
    )
    path = "/about"
    return templates.TemplateResponse(
        "pages/about.html",
        {
            **_common_context(request, lang),
            "meta_title": meta_tags["title"][:60],
            "meta_description": meta_tags["description"][:155],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": f"{BASE_URL}{prefix}{path}",
            "schema_jsonld": schema_list,
            "breadcrumbs": breadcrumb_items,
            "hreflang": _hreflang_links(path),
        },
    )


@router.get("/about", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def about_page(request: Request):
    return _render_about(request, "zh")


@router.get("/en/about", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def about_page_en(request: Request):
    return _render_about(request, "en")


# ---------------------------------------------------------------------------
# How it works
# ---------------------------------------------------------------------------


def _render_how_it_works(request: Request, lang: str):
    t = get_translations(lang)
    prefix = _lang_prefix(lang)
    meta_tags = {
        "title": t.get("seo.how.title", "How It Works - MeetSpot"),
        "description": t.get("how.hero_desc", ""),
        "keywords": "MeetSpot guide,how to use,meeting point tutorial",
    }
    how_to_schema = seo_generator.generate_schema_org(
        "how_to",
        {
            "name": t.get("how.hero_title", "How It Works"),
            "description": t.get("how.hero_desc", ""),
            "total_time": "PT1M",
            "steps": [
                {
                    "name": t.get("how.step1_title", ""),
                    "text": t.get("how.step1_desc", ""),
                },
                {
                    "name": t.get("how.step2_title", ""),
                    "text": t.get("how.step2_desc", ""),
                },
                {
                    "name": t.get("how.step3_title", ""),
                    "text": t.get("how.step3_desc", ""),
                },
                {
                    "name": t.get("how.step4_title", ""),
                    "text": t.get("how.step4_desc", ""),
                },
                {
                    "name": t.get("how.step5_title", ""),
                    "text": t.get("how.step5_desc", ""),
                },
            ],
            "tools": ["MeetSpot AI Agent", "AMap API", "GPT-4o"],
            "supplies": [
                t.get("how.step1_title", "Participant addresses"),
                t.get("how.step2_title", "Venue type"),
                t.get("how.step3_title", "Special requirements"),
            ],
        },
    )
    breadcrumb_items = [
        {"name": t.get("seo.breadcrumb.home", "Home"), "url": f"{prefix}/"},
        {
            "name": t.get("seo.breadcrumb.guide", "Guide"),
            "url": f"{prefix}/how-it-works",
        },
    ]
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org("breadcrumb", {"items": breadcrumb_items}),
        how_to_schema,
    )
    path = "/how-it-works"
    return templates.TemplateResponse(
        "pages/how_it_works.html",
        {
            **_common_context(request, lang),
            "meta_title": meta_tags["title"][:60],
            "meta_description": meta_tags["description"][:155],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": f"{BASE_URL}{prefix}{path}",
            "schema_jsonld": schema_list,
            "breadcrumbs": breadcrumb_items,
            "hreflang": _hreflang_links(path),
        },
    )


@router.get("/how-it-works", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def how_it_works(request: Request):
    return _render_how_it_works(request, "zh")


@router.get("/en/how-it-works", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def how_it_works_en(request: Request):
    return _render_how_it_works(request, "en")


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------


def _render_faq(request: Request, lang: str):
    t = get_translations(lang)
    prefix = _lang_prefix(lang)
    faqs = _get_faqs(lang)
    meta_tags = {
        "title": t.get("seo.faq.title", "FAQ - MeetSpot"),
        "description": t.get("faq.hero_desc", ""),
        "keywords": "MeetSpot FAQ,meeting point help",
    }
    breadcrumb_items = [
        {"name": t.get("seo.breadcrumb.home", "Home"), "url": f"{prefix}/"},
        {"name": t.get("seo.breadcrumb.faq", "FAQ"), "url": f"{prefix}/faq"},
    ]
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org("faq", {"faqs": faqs}),
        seo_generator.generate_schema_org("breadcrumb", {"items": breadcrumb_items}),
    )
    path = "/faq"
    return templates.TemplateResponse(
        "pages/faq.html",
        {
            **_common_context(request, lang),
            "meta_title": meta_tags["title"][:60],
            "meta_description": meta_tags["description"][:155],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": f"{BASE_URL}{prefix}{path}",
            "schema_jsonld": schema_list,
            "breadcrumbs": breadcrumb_items,
            "faqs": faqs,
            "hreflang": _hreflang_links(path),
        },
    )


@router.get("/faq", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def faq_page(request: Request):
    return _render_faq(request, "zh")


@router.get("/en/faq", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def faq_page_en(request: Request):
    return _render_faq(request, "en")


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------


def _render_compare(request: Request, lang: str):
    t = get_translations(lang)
    prefix = _lang_prefix(lang)
    if lang == "en":
        compare_keywords = "MeetSpot comparison,meeting point methods,midpoint vs group chat,fair meeting location"
    else:
        compare_keywords = "聚会地点对比,MeetSpot 对比,选聚会地点方法,公平中点计算"
    meta_tags = {
        "title": t.get("seo.compare.title", "Compare - MeetSpot"),
        "description": t.get("compare.seo_desc", ""),
        "keywords": compare_keywords,
    }
    breadcrumb_items = [
        {"name": t.get("seo.breadcrumb.home", "Home"), "url": f"{prefix}/"},
        {
            "name": t.get("seo.breadcrumb.compare", "Compare"),
            "url": f"{prefix}/compare",
        },
    ]
    if lang == "en":
        compare_data = {
            "name": "Meeting Point Selection Methods Comparison",
            "description": "Compare three ways to choose a group meeting location: group chat, one person decides, or MeetSpot AI algorithm",
            "item1": "Group Chat Discussion",
            "item1_desc": "Manual group negotiation via messaging -- time-consuming and often biased toward the loudest voice",
            "item2": "One Person Decides",
            "item2_desc": "Fast but unfair -- the decision maker typically picks a spot convenient for themselves",
            "item3_desc": "AI-powered Haversine midpoint calculation ensuring mathematically fair distance for all 2-10 participants",
        }
    else:
        compare_data = {
            "name": "聚会地点选择方式对比",
            "description": "对比三种选聚会地点的方式：群里商量、一个人拍板、MeetSpot AI 算法",
            "item1": "群里商量",
            "item1_desc": "微信群讨论，耗时长，容易被声音大的人主导，结果未必公平",
            "item2": "一个人拍板",
            "item2_desc": "快但不公平，决策者往往选自己方便的地方",
            "item3_desc": "基于球面几何 Haversine 公式计算 2-10 人数学公平中点，AI 评分推荐最优场所",
        }
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org("breadcrumb", {"items": breadcrumb_items}),
        seo_generator.generate_schema_org("compare", compare_data),
    )
    path = "/compare"
    return templates.TemplateResponse(
        "pages/compare.html",
        {
            **_common_context(request, lang),
            "meta_title": meta_tags["title"][:60],
            "meta_description": meta_tags["description"][:155],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": f"{BASE_URL}{prefix}{path}",
            "schema_jsonld": schema_list,
            "breadcrumbs": breadcrumb_items,
            "hreflang": _hreflang_links(path),
        },
    )


@router.get("/compare", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def compare_page(request: Request):
    return _render_compare(request, "zh")


@router.get("/en/compare", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def compare_page_en(request: Request):
    return _render_compare(request, "en")


# ---------------------------------------------------------------------------
# Sitemap & Robots
# ---------------------------------------------------------------------------


@router.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap():
    # Static content dates -- update when page content actually changes
    CONTENT_DATES = {
        "/": "2026-04-04",
        "/about": "2026-03-28",
        "/faq": "2026-03-28",
        "/how-it-works": "2026-03-28",
        "/compare": "2026-04-02",
        "/public/meetspot_finder.html": "2026-04-02",
    }
    city_date = "2026-03-28"

    # Pages with standard /en/ prefix routing
    pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "/about", "priority": "0.8", "changefreq": "monthly"},
        {"loc": "/faq", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "/how-it-works", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/compare", "priority": "0.8", "changefreq": "monthly"},
    ]
    city_pages = [
        {"loc": f"/meetspot/{city['slug']}", "priority": "0.9", "changefreq": "weekly"}
        for city in load_cities()
    ]
    all_pages = pages + city_pages

    entries = []
    for item in all_pages:
        lastmod = CONTENT_DATES.get(item["loc"], city_date)
        zh_url = f"{BASE_URL}{item['loc']}"
        en_loc = f"/en{item['loc']}" if item["loc"] != "/" else "/en/"
        en_url = f"{BASE_URL}{en_loc}"
        hreflang_zh = (
            f'        <xhtml:link rel="alternate" hreflang="zh" href="{zh_url}"/>'
        )
        hreflang_en = (
            f'        <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>'
        )
        hreflang_default = f'        <xhtml:link rel="alternate" hreflang="x-default" href="{zh_url}"/>'
        # Chinese URL entry
        entries.append(
            f"    <url>\n"
            f"        <loc>{zh_url}</loc>\n"
            f"        <lastmod>{lastmod}</lastmod>\n"
            f"        <changefreq>{item['changefreq']}</changefreq>\n"
            f"        <priority>{item['priority']}</priority>\n"
            f"{hreflang_zh}\n{hreflang_en}\n{hreflang_default}\n"
            f"    </url>"
        )
        # English URL entry
        entries.append(
            f"    <url>\n"
            f"        <loc>{en_url}</loc>\n"
            f"        <lastmod>{lastmod}</lastmod>\n"
            f"        <changefreq>{item['changefreq']}</changefreq>\n"
            f"        <priority>{item['priority']}</priority>\n"
            f"{hreflang_zh}\n{hreflang_en}\n{hreflang_default}\n"
            f"    </url>"
        )

    # meetspot_finder.html: static file uses ?lang= param, not /en/ prefix
    finder_date = CONTENT_DATES["/public/meetspot_finder.html"]
    finder_zh = f"{BASE_URL}/public/meetspot_finder.html"
    finder_en = f"{BASE_URL}/public/meetspot_finder.html?lang=en"
    for loc, hreflang_self in [(finder_zh, "zh"), (finder_en, "en")]:
        entries.append(
            f"    <url>\n"
            f"        <loc>{loc}</loc>\n"
            f"        <lastmod>{finder_date}</lastmod>\n"
            f"        <changefreq>weekly</changefreq>\n"
            f"        <priority>0.9</priority>\n"
            f'        <xhtml:link rel="alternate" hreflang="zh" href="{finder_zh}"/>\n'
            f'        <xhtml:link rel="alternate" hreflang="en" href="{finder_en}"/>\n'
            f'        <xhtml:link rel="alternate" hreflang="x-default" href="{finder_zh}"/>\n'
            f"    </url>"
        )

    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>"
    )
    return Response(
        content=sitemap_xml,
        media_type="application/xml",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
        },
    )


@router.api_route("/robots.txt", methods=["GET", "HEAD"])
async def robots_txt():
    robots = f"""# MeetSpot Robots.txt

User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

Sitemap: {BASE_URL}/sitemap.xml

# Search engines
User-agent: Googlebot
Allow: /

User-agent: Baiduspider
Allow: /

# AI search bots -- allow citation
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Google-Extended
Allow: /

# Training-only crawlers -- block
User-agent: CCBot
Disallow: /
"""
    return Response(
        content=robots,
        media_type="text/plain",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
        },
    )


@router.api_route("/llms.txt", methods=["GET", "HEAD"])
async def llms_txt():
    """LLMs.txt -- emerging standard for AI discoverability."""
    content = f"""# MeetSpot

> MeetSpot is a free AI-powered meeting point finder that uses spherical geometry (Haversine formula) to calculate the mathematically fairest midpoint for 2-10 people, then ranks nearby venues using a 100-point scoring algorithm across 350+ cities in China.

## Key Pages

- [{BASE_URL}/](Homepage): Product overview, features, city directory
- [{BASE_URL}/public/meetspot_finder.html](App): The main tool -- enter addresses, get fair midpoint recommendations
- [{BASE_URL}/faq](FAQ): 12 common questions about how MeetSpot works
- [{BASE_URL}/how-it-works](Guide): 5-step AI reasoning process explained
- [{BASE_URL}/compare](Compare): MeetSpot vs group chat vs one-person decisions
- [{BASE_URL}/about](About): Project background, technical architecture, team

## How It Works

1. Users input 2-10 participant addresses
2. Haversine formula calculates the spherical geometry midpoint (15-20% more accurate than lat/lng averaging)
3. Amap POI API searches nearby venues within 5km radius
4. 100-point scoring: rating (30) + popularity (20) + distance (25) + scenario (15) + requirements (10)
5. Results rendered as interactive map with venue cards

## Technical Details

- Algorithm: Haversine (spherical trigonometry) for midpoint, not simple coordinate averaging
- Scoring: GPT-4o multi-dimensional venue evaluation when Agent mode is enabled
- Data: Amap (Gaode Map) POI database, 30M+ points of interest
- Coverage: 350+ cities in China, 12 venue theme categories
- Brand knowledge: 50+ brand profiles (Starbucks, Haidilao, etc.) with feature scores
- University aliases: 60+ Chinese university abbreviation mappings

## API

POST {BASE_URL}/api/find_meetspot
Content-Type: application/json
{{"locations": ["address1", "address2"], "keywords": "cafe"}}

## Contact

- GitHub: https://github.com/calderbuild/MeetSpot
- Author: Jason Robert (https://jasonrobert.me/)
- Email: Johnrobertdestiny@gmail.com
"""
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
        },
    )
