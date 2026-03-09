"""SEO内容生成服务.

负责关键词提取、Meta标签、结构化数据以及城市内容片段生成。
该模块与Jinja2模板配合, 为SSR页面提供语义化上下文。
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List


class SEOContentGenerator:
    """封装SEO内容生成逻辑."""

    def generate_meta_tags(self, page_type: str, data: Dict) -> Dict[str, str]:
        """根据页面类型生成Meta标签."""
        if page_type == "homepage":
            title = "MeetSpot 聚点 - 多人聚会地点智能推荐"
            description = (
                "MeetSpot 帮助 2-10 人快速找到公平的聚会中点，"
                "智能推荐咖啡馆、餐厅、图书馆等场所，"
                "球面几何算法计算公平中心，覆盖 350+ 城市，免费使用无需注册。"
            )
            keywords = "聚会地点推荐,中点计算,团队聚会,meeting location,midpoint"
        elif page_type == "city_page":
            city = data.get("city", "")
            city_en = data.get("city_en", "")
            venue_types = data.get("venue_types", [])
            venue_snippet = "、".join(venue_types[:3]) if venue_types else "热门场所"
            title = f"{city}聚会地点推荐 - MeetSpot 聚点"
            description = (
                f"在{city or '所在城市'}找多人聚会的公平中点？"
                f"MeetSpot 根据 2-10 人位置计算最佳会面点，推荐{venue_snippet}等高评分场所，"
                f"覆盖{city}主要商圈和高校周边。"
            )
            keywords = f"{city}聚会地点,{city}聚餐推荐,{venue_snippet},{city_en}"
        elif page_type == "about":
            title = "关于 MeetSpot 聚点 - 智能聚会地点推荐"
            description = (
                "MeetSpot 是一款开源的多人聚会地点推荐工具，"
                "使用球面几何算法计算公平中点，结合智能评分推荐最佳场所，"
                "覆盖 350+ 城市，12 种场景主题。"
            )
            keywords = "关于 MeetSpot,聚会算法,地点推荐技术"
        elif page_type == "faq":
            title = "常见问题 - MeetSpot 聚点"
            description = (
                "MeetSpot 常见问题解答：如何计算聚会中点、支持多少人、"
                "覆盖哪些城市、是否免费、推荐速度等核心问题一站式解答。"
            )
            keywords = "MeetSpot 常见问题,聚会地点帮助,使用指南"
        elif page_type == "how_it_works":
            title = "使用指南 - MeetSpot 聚点"
            description = (
                "MeetSpot 使用指南：输入参与者地址、选择场所类型、"
                "设置特殊需求，5 步智能推理流程为你找到对所有人都公平的聚会地点。"
            )
            keywords = "MeetSpot 使用指南,聚会地点怎么选,中点计算教程"
        elif page_type == "recommendation":
            city = data.get("city", "未知城市")
            keyword = data.get("keyword", "聚会地点")
            count = data.get("locations_count", 2)
            title = f"{city}{keyword}推荐 - {count}人聚会 | MeetSpot"
            description = (
                f"{city} {count} 人{keyword}推荐，"
                f"MeetSpot 根据所有参与者位置计算公平中点，"
                f"智能推荐评分最高的{keyword}。"
            )
            keywords = f"{city},{keyword},聚会地点推荐,中点计算"
        else:
            title = "MeetSpot 聚点 - 智能聚会地点推荐"
            description = "MeetSpot 通过公平的中点计算，为多人聚会推荐最佳会面地点。"
            keywords = "MeetSpot,聚会地点推荐,中点计算"

        return {
            "title": title[:60],
            "description": description[:155],
            "keywords": keywords,
        }

    def generate_schema_org(self, page_type: str, data: Dict) -> Dict:
        """生成Schema.org结构化数据."""
        base_url = "https://meetspot-irq2.onrender.com"
        if page_type == "webapp":
            return {
                "@context": "https://schema.org",
                "@type": "WebApplication",
                "name": "MeetSpot",
                "url": base_url + "/",
                "description": "Find the perfect meeting location midpoint for groups",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web",
                "offers": {
                    "@type": "Offer",
                    "price": "0",
                    "priceCurrency": "USD",
                },
                "isAccessibleForFree": True,
                "applicationSubCategory": "Meeting & Location Planning",
                "author": {
                    "@type": "Organization",
                    "name": "MeetSpot Team",
                },
            }
        if page_type == "website":
            return {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "MeetSpot",
                "url": base_url + "/",
                "inLanguage": "zh-CN",
            }
        if page_type == "organization":
            return {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "MeetSpot",
                "url": base_url,
                "logo": base_url + "/public/favicon.svg",
                "contactPoint": [
                    {
                        "@type": "ContactPoint",
                        "contactType": "customer support",
                        "email": "Johnrobertdestiny@gmail.com",
                        "availableLanguage": ["zh-CN", "en"],
                    }
                ],
                "sameAs": [
                    "https://github.com/calderbuild/MeetSpot",
                    "https://jasonrobert.me/",
                ],
            }
        if page_type == "local_business":
            venue = data
            return {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": venue.get("name"),
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": venue.get("address"),
                    "addressLocality": venue.get("city"),
                    "addressCountry": "CN",
                },
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": venue.get("lat"),
                    "longitude": venue.get("lng"),
                },
            }
        if page_type == "faq":
            faqs = data.get("faqs", [])
            return {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": faq["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": faq["answer"],
                        },
                    }
                    for faq in faqs
                ],
            }
        if page_type == "how_to":
            steps = data.get("steps", [])
            if not steps:
                return {}
            return {
                "@context": "https://schema.org",
                "@type": "HowTo",
                "name": data.get("name", "如何使用MeetSpot"),
                "description": data.get(
                    "description",
                    "Step-by-step guide to plan a fair meetup with MeetSpot.",
                ),
                "totalTime": data.get("total_time", "PT15M"),
                "inLanguage": "zh-CN",
                "step": [
                    {
                        "@type": "HowToStep",
                        "name": step["name"],
                        "text": step["text"],
                    }
                    for step in steps
                ],
                "supply": [
                    {"@type": "HowToSupply", "name": s}
                    for s in data.get("supplies", ["参与者地址", "交通方式偏好"])
                ],
                "tool": [
                    {"@type": "HowToTool", "name": t}
                    for t in data.get("tools", ["MeetSpot Dashboard"])
                ],
            }
        if page_type == "breadcrumb":
            items = data.get("items", [])
            return {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": idx + 1,
                        "name": item["name"],
                        "item": f"{base_url}{item['url']}",
                    }
                    for idx, item in enumerate(items)
                ],
            }
        return {}

    def generate_city_content(self, city_data: Dict, lang: str = "zh") -> Dict[str, str]:
        """生成城市页面内容块, 使用丰富的城市数据."""
        from app.i18n import get_translations
        t = get_translations(lang)

        city = city_data.get("name", "")
        city_display = city_data.get("name_en", city) if lang == "en" else city
        city_en = city_data.get("name_en", "")
        tagline = city_data.get("tagline", "")
        description = city_data.get("description", "")
        landmarks = city_data.get("landmarks", [])
        university_clusters = city_data.get("university_clusters", [])
        business_districts = city_data.get("business_districts", [])
        metro_lines = city_data.get("metro_lines", 0)
        use_cases = city_data.get("use_cases", [])
        local_tips = city_data.get("local_tips", "")
        popular_venues = city_data.get("popular_venues", [])

        # 生成地标标签
        landmarks_html = "".join(
            f'<span class="tag tag-landmark">{lm}</span>' for lm in landmarks[:5]
        ) if landmarks else ""

        # 生成商圈标签
        districts_html = "".join(
            f'<span class="tag tag-district">{d}</span>' for d in business_districts[:4]
        ) if business_districts else ""

        # 生成高校标签
        universities_html = "".join(
            f'<span class="tag tag-university">{u}</span>' for u in university_clusters[:4]
        ) if university_clusters else ""

        # 生成使用场景卡片
        use_cases_html = ""
        if use_cases:
            cases_items = ""
            for uc in use_cases[:3]:
                scenario = uc.get("scenario", "")
                example = uc.get("example", "")
                cases_items += f'''
                <div class="use-case-card">
                    <h4>{scenario}</h4>
                    <p>{example}</p>
                </div>'''
            section_title = t.get("city.use_cases_title", "").replace("{city}", city_display)
            use_cases_html = f'''
            <section class="use-cases">
                <h2>{section_title}</h2>
                <div class="use-cases-grid">{cases_items}</div>
            </section>'''

        # 生成场所类型
        joiner = ", " if lang == "en" else "、"
        venues_html = joiner.join(popular_venues[:4]) if popular_venues else ("cafes, restaurants" if lang == "en" else "咖啡馆、餐厅")

        # Helper to resolve template strings
        def _t(key: str) -> str:
            return t.get(key, key).replace("{city}", city_display).replace("{count}", str(metro_lines)).replace("{venues}", venues_html)

        intro_title = f"{city_display} Meeting Point Finder - {city_en}" if lang == "en" else f"{city}聚会地点推荐 - {city_en}"

        content = {
            "intro": f'''
                <div class="city-hero">
                    <h1>{intro_title}</h1>
                    <p class="tagline">{tagline}</p>
                    <p class="lead">{description}</p>
                </div>''',

            "features": f'''
                <section class="city-features">
                    <h2>{_t("city.features_title")}</h2>
                    <div class="features-grid">
                        <div class="feature-card">
                            <div class="feature-icon">🚇</div>
                            <h3>{_t("city.metro_title")}</h3>
                            <p>{_t("city.metro_desc")}</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">🎯</div>
                            <h3>{_t("city.midpoint_title")}</h3>
                            <p>{_t("city.midpoint_desc")}</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">📍</div>
                            <h3>{_t("city.local_title")}</h3>
                            <p>{_t("city.local_desc")}</p>
                        </div>
                    </div>
                </section>''',

            "landmarks": f'''
                <section class="city-landmarks">
                    <h2>{_t("city.landmarks_title")}</h2>
                    <div class="tags-section">
                        <div class="tags-group">
                            <h3>{_t("city.landmarks_group")}</h3>
                            <div class="tags">{landmarks_html}</div>
                        </div>
                        <div class="tags-group">
                            <h3>{_t("city.districts_group")}</h3>
                            <div class="tags">{districts_html}</div>
                        </div>
                        <div class="tags-group">
                            <h3>{_t("city.universities_group")}</h3>
                            <div class="tags">{universities_html}</div>
                        </div>
                    </div>
                </section>''' if landmarks or business_districts or university_clusters else "",

            "use_cases": use_cases_html,

            "local_tips": f'''
                <section class="local-tips">
                    <h2>{_t("city.tips_title")}</h2>
                    <div class="tip-card">
                        <div class="tip-icon">💡</div>
                        <p>{local_tips}</p>
                    </div>
                </section>''' if local_tips else "",

            "how_it_works": f'''
                <section class="how-it-works">
                    <h2>{_t("city.how_title")}</h2>
                    <div class="steps">
                        <div class="step">
                            <span class="step-number">1</span>
                            <div class="step-content">
                                <h4>{_t("city.how_step1_title")}</h4>
                                <p>{_t("city.how_step1_desc")}</p>
                            </div>
                        </div>
                        <div class="step">
                            <span class="step-number">2</span>
                            <div class="step-content">
                                <h4>{_t("city.how_step2_title")}</h4>
                                <p>{_t("city.how_step2_desc")}</p>
                            </div>
                        </div>
                        <div class="step">
                            <span class="step-number">3</span>
                            <div class="step-content">
                                <h4>{_t("city.how_step3_title")}</h4>
                                <p>{_t("city.how_step3_desc")}</p>
                            </div>
                        </div>
                    </div>
                </section>''',

            "cta": f'''
                <section class="cta-section">
                    <h2>{_t("city.cta_title")}</h2>
                    <p>{_t("city.cta_desc")}</p>
                    <a href="/public/meetspot_finder.html" class="cta-button" data-track="cta_click" data-track-label="city_page">{_t("city.cta_btn")}</a>
                </section>''',
        }

        # 计算字数
        total_text = "".join(str(v) for v in content.values())
        text_only = "".join(ch for ch in total_text if ch.isalnum())
        content["word_count"] = len(text_only)
        return content

    def generate_city_content_simple(self, city: str) -> Dict[str, str]:
        """兼容旧API: 仅传入城市名时生成基础内容."""
        return self.generate_city_content({"name": city, "name_en": city})


seo_content_generator = SEOContentGenerator()
"""单例生成器, 供路由直接复用。"""
