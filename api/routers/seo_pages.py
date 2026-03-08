"""SEO页面路由 - 负责SSR页面与爬虫友好输出."""
from __future__ import annotations

import json
import os
from datetime import datetime
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
    meta_tags = {
        "title": t.get("seo.home.title", "MeetSpot"),
        "description": t.get("seo.home.description", ""),
        "keywords": "聚会地点推荐,中点计算,meeting location,midpoint",
    }
    faq_schema = seo_generator.generate_schema_org(
        "faq",
        {"faqs": _get_faqs(lang)[:3]},
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
    return _render_homepage(request, "zh")


@router.get("/en/", response_class=HTMLResponse)
@router.get("/en", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def homepage_en(request: Request):
    return _render_homepage(request, "en")


# ---------------------------------------------------------------------------
# City page
# ---------------------------------------------------------------------------

def _render_city_page(request: Request, city_slug: str, lang: str):
    city = _get_city_by_slug(city_slug)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    t = get_translations(lang)
    prefix = _lang_prefix(lang)
    city_name = city.get("name_en", city.get("name")) if lang == "en" else city.get("name")
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
        "description": t.get("seo.home.description", ""),
        "keywords": "about MeetSpot,meeting algorithm",
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
                {"name": t.get("how.step1_title", ""), "text": t.get("how.step1_desc", "")},
                {"name": t.get("how.step2_title", ""), "text": t.get("how.step2_desc", "")},
                {"name": t.get("how.step3_title", ""), "text": t.get("how.step3_desc", "")},
                {"name": t.get("how.step4_title", ""), "text": t.get("how.step4_desc", "")},
                {"name": t.get("how.step5_title", ""), "text": t.get("how.step5_desc", "")},
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
        {"name": t.get("seo.breadcrumb.guide", "Guide"), "url": f"{prefix}/how-it-works"},
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
# Sitemap & Robots
# ---------------------------------------------------------------------------

@router.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap():
    today = datetime.now().strftime("%Y-%m-%d")
    pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "/about", "priority": "0.8", "changefreq": "monthly"},
        {"loc": "/faq", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "/how-it-works", "priority": "0.7", "changefreq": "monthly"},
    ]
    city_pages = [
        {"loc": f"/meetspot/{city['slug']}", "priority": "0.9", "changefreq": "weekly"}
        for city in load_cities()
    ]
    all_pages = pages + city_pages

    entries = []
    for item in all_pages:
        zh_url = f"{BASE_URL}{item['loc']}"
        en_loc = f"/en{item['loc']}" if item["loc"] != "/" else "/en/"
        en_url = f"{BASE_URL}{en_loc}"
        hreflang_zh = f'        <xhtml:link rel="alternate" hreflang="zh" href="{zh_url}"/>'
        hreflang_en = f'        <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>'
        hreflang_default = f'        <xhtml:link rel="alternate" hreflang="x-default" href="{zh_url}"/>'
        # Chinese URL entry
        entries.append(
            f"    <url>\n"
            f"        <loc>{zh_url}</loc>\n"
            f"        <lastmod>{today}</lastmod>\n"
            f"        <changefreq>{item['changefreq']}</changefreq>\n"
            f"        <priority>{item['priority']}</priority>\n"
            f"{hreflang_zh}\n{hreflang_en}\n{hreflang_default}\n"
            f"    </url>"
        )
        # English URL entry
        entries.append(
            f"    <url>\n"
            f"        <loc>{en_url}</loc>\n"
            f"        <lastmod>{today}</lastmod>\n"
            f"        <changefreq>{item['changefreq']}</changefreq>\n"
            f"        <priority>{item['priority']}</priority>\n"
            f"{hreflang_zh}\n{hreflang_en}\n{hreflang_default}\n"
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
            "X-Robots-Tag": "noindex",
        },
    )


@router.api_route("/robots.txt", methods=["GET", "HEAD"])
async def robots_txt():
    today = datetime.now().strftime("%Y-%m-%d")
    robots = f"""# MeetSpot Robots.txt\n# Generated: {today}\n\nUser-agent: *\nAllow: /\nCrawl-delay: 1\n\nDisallow: /admin/\nDisallow: /api/internal/\nDisallow: /*.json$\n\nSitemap: {BASE_URL}/sitemap.xml\n\nUser-agent: Googlebot\nAllow: /\n\nUser-agent: Baiduspider\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n\nUser-agent: CCBot\nDisallow: /\n"""
    return Response(
        content=robots,
        media_type="text/plain",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
        },
    )
