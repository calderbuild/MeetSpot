"""SEO内容生成服务.

负责关键词提取、Meta标签、结构化数据以及城市内容片段生成。
该模块与Jinja2模板配合, 为SSR页面提供语义化上下文。
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

import jieba
import jieba.analyse


class SEOContentGenerator:
    """封装SEO内容生成逻辑."""

    def __init__(self) -> None:
        self.custom_words = [
            "聚会地点",
            "会面点",
            "中点推荐",
            "团队聚会",
            "远程团队",
            "咖啡馆",
            "餐厅",
            "图书馆",
            "共享空间",
            "北京",
            "上海",
            "广州",
            "深圳",
            "杭州",
            "成都",
            "meeting location",
            "midpoint",
            "group meeting",
        ]
        for word in self.custom_words:
            jieba.add_word(word)

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """基于TF-IDF提取关键词."""
        if not text:
            return []
        return jieba.analyse.extract_tags(
            text,
            topK=top_k,
            withWeight=False,
            allowPOS=("n", "nr", "ns", "nt", "nw", "nz", "v", "vn"),
        )

    def generate_meta_tags(self, page_type: str, data: Dict) -> Dict[str, str]:
        """根据页面类型生成Meta标签."""
        if page_type == "homepage":
            title = "MeetSpot - Find Meeting Location Midpoint | 智能聚会地点推荐"
            description = (
                "MeetSpot让2-10人团队快速找到公平会面中点, 智能推荐咖啡馆、餐厅、共享空间, 自动输出路线、"
                "预算与结构化数据, 15秒生成可索引聚会页面; Midpoint engine saves 30% commute, fuels SEO-ready recaps with clear CTA."
            )
            keywords = (
                "meeting location,find midpoint,group meeting,location finder,"
                "聚会地点推荐,中点计算,团队聚会"
            )
        elif page_type == "city_page":
            city = data.get("city", "")
            city_en = data.get("city_en", "")
            venue_types = data.get("venue_types", [])
            venue_snippet = "、".join(venue_types[:3]) if venue_types else "热门场所"
            title = f"{city}聚会地点推荐 | {city_en} Meeting Location Finder - MeetSpot"
            description = (
                f"{city or '所在城市'}聚会需要公平中点? MeetSpot根据2-10人轨迹计算平衡路线, 推荐{venue_snippet}等场所, "
                "输出中文/英文场地文案、预算与交通信息, 15秒生成可索引城市着陆页; Local insights boost trust, shareable cards unlock faster decisions."
            )
            keywords = f"{city},{city_en},meeting location,{venue_snippet},midpoint"
        elif page_type == "about":
            title = "About MeetSpot - How We Find Perfect Meeting Locations | 关于我们"
            description = (
                "MeetSpot团队由地图算法、内容运营与产品负责人组成, 公开使命、技术栈、治理方式, 分享用户案例、AMAP合规、安全策略与开源路线图; "
                "Learn how we guarantee equitable experiences backed by ongoing UX research。"
            )
            keywords = "about meetspot,meeting algorithm,location technology,关于,聚会算法"
        elif page_type == "faq":
            title = "FAQ - Meeting Location Questions Answered | 常见问题 - MeetSpot"
            description = (
                "覆盖聚会地点、费用、功能等核心提问, 提供结构化答案, 支持Google FAQ Schema, 让用户与搜索引擎获得清晰指导, "
                "并附上联系入口与下一步CTA, FAQ hub helps planners resolve objections faster and improve conversions。"
            )
            keywords = "faq,meeting questions,location help,常见问题,使用指南"
        elif page_type == "how_it_works":
            title = "How MeetSpot Works | 智能聚会地点中点计算流程"
            description = (
                "4步流程涵盖收集地址、平衡权重、筛选场地与导出SEO文案, 附带动图、清单和风控提示, 指导团队15分钟内发布可索引页面; "
                "Learn safeguards, KPIs, stakeholder handoffs, and post-launch QA behind MeetSpot。"
            )
            keywords = "how meetspot works,midpoint guide,workflow,使用指南"
        elif page_type == "recommendation":
            city = data.get("city", "未知城市")
            keyword = data.get("keyword", "聚会地点")
            count = data.get("locations_count", 2)
            title = f"{city}{keyword}推荐 - {count}人聚会最佳会面点 | MeetSpot"
            description = (
                f"{city}{count}人{keyword}推荐由MeetSpot中点引擎生成, 结合每位参与者的路程、预算与场地偏好, "
                "给出评分、热力图和可复制行程; Share SEO-ready cards、CTA, keep planning transparent, document-ready for clients, and measurable。"
            )
            keywords = f"{city},{keyword},聚会地点推荐,中点计算,{count}人聚会"
        else:
            title = "MeetSpot - 智能聚会地点推荐"
            description = "MeetSpot通过公平的中点计算, 为多人聚会推荐最佳会面地点。"
            keywords = "meetspot,meeting location,聚会地点"

        return {
            "title": title[:60],
            "description": description[:160],
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
                "logo": f"{base_url}/static/images/og-image.png",
                "foundingDate": "2023-08-01",
                "contactPoint": [
                    {
                        "@type": "ContactPoint",
                        "contactType": "customer support",
                        "email": "hello@meetspot.app",
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
                "aggregateRating": {
                    "@type": "AggregateRating",
                    "ratingValue": venue.get("rating", 4.5),
                    "reviewCount": venue.get("review_count", 100),
                },
                "priceRange": venue.get("price_range", "$$"),
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
                "supply": data.get("supplies", ["参与者地址", "交通方式偏好"]),
                "tool": data.get("tools", ["MeetSpot Dashboard"]),
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

    def generate_city_content(self, city_data: Dict) -> Dict[str, str]:
        """生成城市页面内容块, 使用丰富的城市数据."""
        city = city_data.get("name", "")
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
            use_cases_html = f'''
            <section class="use-cases">
                <h2>{city}真实使用场景</h2>
                <div class="use-cases-grid">{cases_items}</div>
            </section>'''

        # 生成场所类型
        venues_html = "、".join(popular_venues[:4]) if popular_venues else "咖啡馆、餐厅"

        content = {
            "intro": f'''
                <div class="city-hero">
                    <h1>{city}聚会地点推荐 - {city_en}</h1>
                    <p class="tagline">{tagline}</p>
                    <p class="lead">{description}</p>
                </div>''',

            "features": f'''
                <section class="city-features">
                    <h2>为什么在{city}使用MeetSpot？</h2>
                    <div class="features-grid">
                        <div class="feature-card">
                            <div class="feature-icon">🚇</div>
                            <h3>{metro_lines}条地铁线路</h3>
                            <p>{city}地铁网络发达，MeetSpot优先推荐地铁站周边的聚会场所</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">🎯</div>
                            <h3>智能中点计算</h3>
                            <p>球面几何算法确保每位参与者通勤距离公平均衡</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">📍</div>
                            <h3>本地精选场所</h3>
                            <p>覆盖{city}{venues_html}等热门类型，高评分场所优先推荐</p>
                        </div>
                    </div>
                </section>''',

            "landmarks": f'''
                <section class="city-landmarks">
                    <h2>{city}热门聚会区域</h2>
                    <div class="tags-section">
                        <div class="tags-group">
                            <h3>地标商圈</h3>
                            <div class="tags">{landmarks_html}</div>
                        </div>
                        <div class="tags-group">
                            <h3>商务中心</h3>
                            <div class="tags">{districts_html}</div>
                        </div>
                        <div class="tags-group">
                            <h3>高校聚集区</h3>
                            <div class="tags">{universities_html}</div>
                        </div>
                    </div>
                </section>''' if landmarks or business_districts or university_clusters else "",

            "use_cases": use_cases_html,

            "local_tips": f'''
                <section class="local-tips">
                    <h2>{city}聚会小贴士</h2>
                    <div class="tip-card">
                        <div class="tip-icon">💡</div>
                        <p>{local_tips}</p>
                    </div>
                </section>''' if local_tips else "",

            "how_it_works": f'''
                <section class="how-it-works">
                    <h2>如何在{city}找到最佳聚会地点？</h2>
                    <div class="steps">
                        <div class="step">
                            <span class="step-number">1</span>
                            <div class="step-content">
                                <h4>输入参与者位置</h4>
                                <p>支持输入{city}任意地址、地标或高校名称（如{university_clusters[0] if university_clusters else "当地高校"}）</p>
                            </div>
                        </div>
                        <div class="step">
                            <span class="step-number">2</span>
                            <div class="step-content">
                                <h4>选择场所类型</h4>
                                <p>根据聚会目的选择{venues_html}等场景</p>
                            </div>
                        </div>
                        <div class="step">
                            <span class="step-number">3</span>
                            <div class="step-content">
                                <h4>获取智能推荐</h4>
                                <p>系统自动计算地理中点，推荐{landmarks[0] if landmarks else "市中心"}等区域的高评分场所</p>
                            </div>
                        </div>
                    </div>
                </section>''',

            "cta": f'''
                <section class="cta-section">
                    <h2>开始规划{city}聚会</h2>
                    <p>无需注册，输入地址即可获取推荐</p>
                    <a href="/" class="cta-button">立即使用 MeetSpot</a>
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
