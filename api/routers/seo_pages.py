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

router = APIRouter()
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)


def _common_context() -> dict:
    """每次请求时动态读取的公共模板变量."""
    return {"baidu_tongji_id": os.getenv("BAIDU_TONGJI_ID", "")}


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


@router.get("/", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def homepage(request: Request):
    """首页 - 提供SEO友好内容."""

    meta_tags = seo_generator.generate_meta_tags("homepage", {})
    faq_schema = seo_generator.generate_schema_org(
        "faq",
        {
            "faqs": [
                {
                    "question": "MeetSpot如何计算最佳聚会地点？",
                    "answer": "我们使用球面几何算法计算所有参与者位置的地理中点, 再推荐附近高评分场所。",
                },
                {
                    "question": "MeetSpot支持多少人的聚会?",
                    "answer": "默认支持2-10人, 满足大多数团队与家人聚会需求。",
                },
                {
                    "question": "需要付费吗?",
                    "answer": "MeetSpot完全免费且开源, 无需注册即可使用。",
                },
            ]
        },
    )
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("webapp", {}),
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org(
            "breadcrumb", {"items": [{"name": "Home", "url": "/"}]}
        ),
        faq_schema,
    )

    return templates.TemplateResponse(
        "pages/home.html",
        {
            "request": request,
            "meta_title": meta_tags["title"],
            "meta_description": meta_tags["description"],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": "https://meetspot-irq2.onrender.com/",
            "schema_jsonld": schema_list,
            "breadcrumbs": [],
            "cities": load_cities(),
            **_common_context(),
        },
    )


@router.get("/meetspot/{city_slug}", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def city_page(request: Request, city_slug: str):
    city = _get_city_by_slug(city_slug)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    meta_tags = seo_generator.generate_meta_tags(
        "city_page",
        {
            "city": city.get("name"),
            "city_en": city.get("name_en"),
            "venue_types": city.get("popular_venues", []),
        },
    )
    breadcrumb = seo_generator.generate_schema_org(
        "breadcrumb",
        {
            "items": [
                {"name": "Home", "url": "/"},
                {"name": city.get("name"), "url": f"/meetspot/{city_slug}"},
            ]
        },
    )
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("webapp", {}),
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        breadcrumb,
    )
    city_content = seo_generator.generate_city_content(city)

    return templates.TemplateResponse(
        "pages/city.html",
        {
            "request": request,
            "meta_title": meta_tags["title"],
            "meta_description": meta_tags["description"],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": f"https://meetspot-irq2.onrender.com/meetspot/{city_slug}",
            "schema_jsonld": schema_list,
            "breadcrumbs": [
                {"name": "首页", "url": "/"},
                {"name": city.get("name"), "url": f"/meetspot/{city_slug}"},
            ],
            "city": city,
            "city_content": city_content,
            **_common_context(),
        },
    )


@router.get("/about", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def about_page(request: Request):
    meta_tags = seo_generator.generate_meta_tags("about", {})
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org(
            "breadcrumb",
            {
                "items": [
                    {"name": "Home", "url": "/"},
                    {"name": "About", "url": "/about"},
                ]
            },
        )
    )
    return templates.TemplateResponse(
        "pages/about.html",
        {
            "request": request,
            "meta_title": meta_tags["title"],
            "meta_description": meta_tags["description"],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": "https://meetspot-irq2.onrender.com/about",
            "schema_jsonld": schema_list,
            "breadcrumbs": [
                {"name": "首页", "url": "/"},
                {"name": "关于我们", "url": "/about"},
            ],
            **_common_context(),
        },
    )


@router.get("/how-it-works", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def how_it_works(request: Request):
    meta_tags = seo_generator.generate_meta_tags("how_it_works", {})
    how_to_schema = seo_generator.generate_schema_org(
        "how_to",
        {
            "name": "使用MeetSpot AI Agent规划公平会面",
            "description": "5步AI推理流程, 从输入地址到生成推荐, 5-30秒内完成。",
            "total_time": "PT1M",
            "steps": [
                {
                    "name": "解析地址",
                    "text": "AI智能识别地址/地标/简称，'北大'自动转换为'北京市海淀区北京大学'，校验经纬度。",
                },
                {
                    "name": "计算中心点",
                    "text": "使用球面几何（Haversine公式）计算地球曲面真实中点，数学上对每个人公平。",
                },
                {
                    "name": "搜索周边场所",
                    "text": "在中心点周边搜索匹配场景的POI，支持咖啡馆、餐厅、图书馆等12种场景主题。",
                },
                {
                    "name": "GPT-4o智能评分",
                    "text": "AI对候选场所进行多维度评分：距离、评分、停车、环境、交通便利度。",
                },
                {
                    "name": "生成推荐",
                    "text": "综合排序输出最优推荐，包含地图、评分、导航链接，可直接分享给朋友。",
                },
            ],
            "tools": ["MeetSpot AI Agent", "AMap API", "GPT-4o"],
            "supplies": ["参与者地址", "场景选择", "特殊需求（可选）"],
        },
    )
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org(
            "breadcrumb",
            {
                "items": [
                    {"name": "Home", "url": "/"},
                    {"name": "How it Works", "url": "/how-it-works"},
                ]
            },
        ),
        how_to_schema,
    )
    return templates.TemplateResponse(
        "pages/how_it_works.html",
        {
            "request": request,
            "meta_title": meta_tags["title"],
            "meta_description": meta_tags["description"],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": "https://meetspot-irq2.onrender.com/how-it-works",
            "schema_jsonld": schema_list,
            "breadcrumbs": [
                {"name": "首页", "url": "/"},
                {"name": "使用指南", "url": "/how-it-works"},
            ],
            **_common_context(),
        },
    )


@router.get("/faq", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def faq_page(request: Request):
    meta_tags = seo_generator.generate_meta_tags("faq", {})
    faqs = [
        {
            "question": "MeetSpot 是什么？",
            "answer": "MeetSpot（聚点）是一个智能会面地点推荐系统，帮助多人找到最公平的聚会地点。无论是商务会谈、朋友聚餐还是学习讨论，都能快速找到合适的场所。",
        },
        {
            "question": "支持多少人一起查找？",
            "answer": "支持 2-10 个参与者位置，系统会根据所有人的位置计算最佳中点。",
        },
        {
            "question": "支持哪些城市？",
            "answer": "目前覆盖北京、上海、广州、深圳、杭州等 350+ 城市，使用高德地图数据，持续扩展中。",
        },
        {
            "question": "可以搜索哪些类型的场所？",
            "answer": "支持咖啡馆、餐厅、图书馆、KTV、健身房、密室逃脱等多种场所类型，还可以同时搜索多种类型（如'咖啡馆+餐厅'）。",
        },
        {
            "question": "如何保证推荐公平？",
            "answer": "系统使用几何中心算法，确保每位参与者到聚会地点的距离都在合理范围内，没有人需要跑特别远。",
        },
        {
            "question": "推荐结果如何排序？",
            "answer": "基于评分、距离、用户需求的综合排序算法，优先推荐评分高、距离中心近、符合特殊需求的场所。",
        },
        {
            "question": "可以输入简称吗？",
            "answer": "支持！系统内置 60+ 大学简称映射，如'北大'会自动识别为'北京大学'。也支持输入地标名称如'国贸'、'东方明珠'等。",
        },
        {
            "question": "是否免费？需要注册吗？",
            "answer": "完全免费使用，无需注册，直接输入地址即可获得推荐结果。",
        },
        {
            "question": "推荐速度如何？",
            "answer": "AI Agent 会经历完整的5步推理流程：解析地址 → 计算中心点 → 搜索周边 → GPT-4o智能评分 → 生成推荐。单场景5-8秒，双场景8-12秒，复杂Agent模式15-30秒。",
        },
        {
            "question": "和高德地图有什么区别？",
            "answer": "高德搜索'我附近'，MeetSpot搜索'我们中间'。我们先用球面几何算出多人公平中点，再推荐那里的好店。这是高德/百度都没有的功能。",
        },
        {
            "question": "AI Agent是什么意思？",
            "answer": "MeetSpot不是简单的搜索工具，而是一个AI Agent。它有5步完整的推理链条，使用GPT-4o进行多维度评分（距离、评分、停车、环境），你可以看到AI每一步是怎么'思考'的，完全透明可解释。",
        },
        {
            "question": "如何反馈问题或建议？",
            "answer": "欢迎通过 GitHub Issues 反馈问题或建议，也可以发送邮件至 Johnrobertdestiny@gmail.com。",
        },
    ]
    schema_list = _build_schema_list(
        seo_generator.generate_schema_org("website", {}),
        seo_generator.generate_schema_org("organization", {}),
        seo_generator.generate_schema_org("faq", {"faqs": faqs}),
        seo_generator.generate_schema_org(
            "breadcrumb",
            {
                "items": [
                    {"name": "Home", "url": "/"},
                    {"name": "FAQ", "url": "/faq"},
                ]
            },
        ),
    )
    return templates.TemplateResponse(
        "pages/faq.html",
        {
            "request": request,
            "meta_title": meta_tags["title"],
            "meta_description": meta_tags["description"],
            "meta_keywords": meta_tags["keywords"],
            "canonical_url": "https://meetspot-irq2.onrender.com/faq",
            "schema_jsonld": schema_list,
            "breadcrumbs": [
                {"name": "首页", "url": "/"},
                {"name": "常见问题", "url": "/faq"},
            ],
            "faqs": faqs,
            **_common_context(),
        },
    )


@router.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap():
    base_url = "https://meetspot-irq2.onrender.com"
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [
        {"loc": "/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "/about", "priority": "0.8", "changefreq": "monthly"},
        {"loc": "/faq", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "/how-it-works", "priority": "0.7", "changefreq": "monthly"},
    ]
    city_urls = [
        {
            "loc": f"/meetspot/{city['slug']}",
            "priority": "0.9",
            "changefreq": "weekly",
        }
        for city in load_cities()
    ]
    entries = []
    for item in urls + city_urls:
        entries.append(
            f"    <url>\n        <loc>{base_url}{item['loc']}</loc>\n        <lastmod>{today}</lastmod>\n        <changefreq>{item['changefreq']}</changefreq>\n        <priority>{item['priority']}</priority>\n    </url>"
        )
    sitemap_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        + "\n".join(entries)
        + "\n</urlset>"
    )
    # Long cache with stale-while-revalidate to handle Render cold starts
    # CDN can serve stale content while revalidating in background
    return Response(
        content=sitemap_xml,
        media_type="application/xml",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "X-Robots-Tag": "noindex",  # Sitemap itself shouldn't be indexed
        },
    )


@router.api_route("/robots.txt", methods=["GET", "HEAD"])
async def robots_txt():
    today = datetime.now().strftime("%Y-%m-%d")
    robots = f"""# MeetSpot Robots.txt\n# Generated: {today}\n\nUser-agent: *\nAllow: /\nCrawl-delay: 1\n\nDisallow: /admin/\nDisallow: /api/internal/\nDisallow: /*.json$\n\nSitemap: https://meetspot-irq2.onrender.com/sitemap.xml\n\nUser-agent: Googlebot\nAllow: /\n\nUser-agent: Baiduspider\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n\nUser-agent: CCBot\nDisallow: /\n"""
    # Long cache with stale-while-revalidate to handle Render cold starts
    return Response(
        content=robots,
        media_type="text/plain",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
        },
    )
