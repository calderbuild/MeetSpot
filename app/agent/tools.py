"""MeetSpot Agent 工具集 - 封装推荐系统的核心功能"""

from typing import Dict, List

from app.tool.base import BaseTool, ToolResult
from app.logger import logger


class GeocodeTool(BaseTool):
    """地理编码工具 - 将地址转换为经纬度坐标"""

    name: str = "geocode"
    description: str = """将地址或地点名称转换为经纬度坐标。
支持各种地址格式：
- 完整地址：'北京市海淀区中关村大街1号'
- 大学简称：'北大'、'清华'、'复旦'（自动扩展为完整地址）
- 知名地标：'天安门'、'外滩'、'广州塔'
- 商圈区域：'三里屯'、'王府井'

返回地址的经纬度坐标和格式化地址。"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "address": {
                "type": "string",
                "description": "地址或地点名称，如'北京大学'、'上海市浦东新区陆家嘴'"
            }
        },
        "required": ["address"]
    }

    class Config:
        arbitrary_types_allowed = True

    def _get_recommender(self):
        """延迟加载推荐器，并确保 API key 已设置"""
        if not hasattr(self, '_cached_recommender'):
            from app.tool.meetspot_recommender import CafeRecommender
            from app.config import config
            recommender = CafeRecommender()
            # 确保 API key 已设置
            if hasattr(config, 'amap') and config.amap and hasattr(config.amap, 'api_key'):
                recommender.api_key = config.amap.api_key
            object.__setattr__(self, '_cached_recommender', recommender)
        return self._cached_recommender

    async def execute(self, address: str) -> ToolResult:
        """执行地理编码"""
        try:
            recommender = self._get_recommender()
            result = await recommender._geocode(address)

            if result:
                location = result.get("location", "")
                lng, lat = location.split(",") if location else (None, None)

                return BaseTool.success_response({
                    "address": address,
                    "formatted_address": result.get("formatted_address", ""),
                    "location": location,
                    "lng": float(lng) if lng else None,
                    "lat": float(lat) if lat else None,
                    "city": result.get("city", ""),
                    "district": result.get("district", "")
                })

            return BaseTool.fail_response(f"无法解析地址: {address}")

        except Exception as e:
            logger.error(f"地理编码失败: {e}")
            return BaseTool.fail_response(f"地理编码错误: {str(e)}")


class CalculateCenterTool(BaseTool):
    """智能中心点工具 - 计算多个位置的最佳会面点

    使用智能算法，综合考虑：
    - POI 密度：周边是否有足够的目标场所
    - 交通便利性：是否靠近地铁站/公交站
    - 公平性：对所有参与者的距离是否均衡
    """

    name: str = "calculate_center"
    description: str = """智能计算最佳会面中心点。

不同于简单的几何中心，本工具会：
1. 在几何中心周围生成多个候选点
2. 评估每个候选点的 POI 密度、交通便利性和公平性
3. 返回综合得分最高的点作为最佳会面位置

这样可以避免中心点落在河流、荒地等不适合的位置。"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "coordinates": {
                "type": "array",
                "description": "坐标点列表，每个元素包含 lng（经度）、lat（纬度）和可选的 name（名称）",
                "items": {
                    "type": "object",
                    "properties": {
                        "lng": {"type": "number", "description": "经度"},
                        "lat": {"type": "number", "description": "纬度"},
                        "name": {"type": "string", "description": "位置名称（可选）"}
                    },
                    "required": ["lng", "lat"]
                }
            },
            "keywords": {
                "type": "string",
                "description": "搜索的场所类型，如'咖啡馆'、'餐厅'，用于评估 POI 密度",
                "default": "咖啡馆"
            },
            "use_smart_algorithm": {
                "type": "boolean",
                "description": "是否使用智能算法（考虑 POI 密度和交通），默认 true",
                "default": True
            }
        },
        "required": ["coordinates"]
    }

    class Config:
        arbitrary_types_allowed = True

    def _get_recommender(self):
        """延迟加载推荐器，并确保 API key 已设置"""
        if not hasattr(self, '_cached_recommender'):
            from app.tool.meetspot_recommender import CafeRecommender
            from app.config import config
            recommender = CafeRecommender()
            if hasattr(config, 'amap') and config.amap and hasattr(config.amap, 'api_key'):
                recommender.api_key = config.amap.api_key
            object.__setattr__(self, '_cached_recommender', recommender)
        return self._cached_recommender

    async def execute(
        self,
        coordinates: List[Dict],
        keywords: str = "咖啡馆",
        use_smart_algorithm: bool = True
    ) -> ToolResult:
        """计算最佳中心点"""
        try:
            if not coordinates or len(coordinates) < 2:
                return BaseTool.fail_response("至少需要2个坐标点来计算中心")

            recommender = self._get_recommender()

            # 转换为 (lng, lat) 元组列表
            coord_tuples = [(c["lng"], c["lat"]) for c in coordinates]

            if use_smart_algorithm:
                # 使用智能中心点算法
                center, evaluation_details = await recommender._calculate_smart_center(
                    coord_tuples, keywords
                )
                logger.info(f"智能中心点算法完成，最优中心: {center}")
            else:
                # 使用简单几何中心
                center = recommender._calculate_center_point(coord_tuples)
                evaluation_details = {"algorithm": "geometric_center"}

            # 计算每个点到中心的距离
            distances = []
            for c in coordinates:
                dist = recommender._calculate_distance(center, (c["lng"], c["lat"]))
                distances.append({
                    "name": c.get("name", f"({c['lng']:.4f}, {c['lat']:.4f})"),
                    "distance_to_center": round(dist, 0)
                })

            max_dist = max(d["distance_to_center"] for d in distances)
            min_dist = min(d["distance_to_center"] for d in distances)

            result = {
                "center": {
                    "lng": round(center[0], 6),
                    "lat": round(center[1], 6)
                },
                "algorithm": "smart" if use_smart_algorithm else "geometric",
                "input_count": len(coordinates),
                "distances": distances,
                "max_distance": max_dist,
                "fairness_score": round(100 - (max_dist - min_dist) / 100, 1)
            }

            # 添加智能算法的评估详情
            if use_smart_algorithm and evaluation_details:
                result["evaluation"] = {
                    "geo_center": evaluation_details.get("geo_center"),
                    "best_score": evaluation_details.get("best_score"),
                    "top_candidates": len(evaluation_details.get("all_candidates", []))
                }

            return BaseTool.success_response(result)

        except Exception as e:
            logger.error(f"计算中心点失败: {e}")
            return BaseTool.fail_response(f"计算中心点错误: {str(e)}")


class SearchPOITool(BaseTool):
    """搜索POI工具 - 在指定位置周围搜索场所"""

    name: str = "search_poi"
    description: str = """在指定中心点周围搜索各类场所（POI）。
支持搜索：咖啡馆、餐厅、图书馆、健身房、KTV、电影院、商场等。
返回场所的名称、地址、评分、距离等信息。"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "center_lng": {
                "type": "number",
                "description": "中心点经度"
            },
            "center_lat": {
                "type": "number",
                "description": "中心点纬度"
            },
            "keywords": {
                "type": "string",
                "description": "搜索关键词，如'咖啡馆'、'餐厅'、'图书馆'"
            },
            "radius": {
                "type": "integer",
                "description": "搜索半径（米），默认3000米",
                "default": 3000
            }
        },
        "required": ["center_lng", "center_lat", "keywords"]
    }

    class Config:
        arbitrary_types_allowed = True

    def _get_recommender(self):
        """延迟加载推荐器，并确保 API key 已设置"""
        if not hasattr(self, '_cached_recommender'):
            from app.tool.meetspot_recommender import CafeRecommender
            from app.config import config
            recommender = CafeRecommender()
            if hasattr(config, 'amap') and config.amap and hasattr(config.amap, 'api_key'):
                recommender.api_key = config.amap.api_key
            object.__setattr__(self, '_cached_recommender', recommender)
        return self._cached_recommender

    async def execute(
        self,
        center_lng: float,
        center_lat: float,
        keywords: str,
        radius: int = 3000
    ) -> ToolResult:
        """搜索POI"""
        try:
            recommender = self._get_recommender()
            center = f"{center_lng},{center_lat}"

            places = await recommender._search_pois(
                location=center,
                keywords=keywords,
                radius=radius,
                types="",
                offset=20
            )

            if not places:
                return BaseTool.fail_response(
                    f"在 ({center_lng:.4f}, {center_lat:.4f}) 附近 {radius}米范围内"
                    f"未找到与 '{keywords}' 相关的场所"
                )

            # 简化返回数据
            simplified = []
            for p in places[:10]:  # 最多返回10个，控制 LLM 上下文长度
                biz_ext = p.get("biz_ext", {}) or {}
                location = p.get("location", "")
                lng, lat = location.split(",") if location else (0, 0)

                # 计算到中心的距离
                distance = recommender._calculate_distance(
                    (center_lng, center_lat),
                    (float(lng), float(lat))
                ) if location else 0

                simplified.append({
                    "name": p.get("name", ""),
                    "address": p.get("address", ""),
                    "rating": biz_ext.get("rating", "N/A"),
                    "cost": biz_ext.get("cost", ""),
                    "location": location,
                    "lng": float(lng) if lng else None,
                    "lat": float(lat) if lat else None,
                    "distance": round(distance, 0),
                    "tel": p.get("tel", ""),
                    "tag": p.get("tag", ""),
                    "type": p.get("type", "")
                })

            # 按距离排序
            simplified.sort(key=lambda x: x.get("distance", 9999))

            return BaseTool.success_response({
                "places": simplified,
                "count": len(simplified),
                "keywords": keywords,
                "center": {"lng": center_lng, "lat": center_lat},
                "radius": radius
            })

        except Exception as e:
            logger.error(f"POI搜索失败: {e}")
            return BaseTool.fail_response(f"POI搜索错误: {str(e)}")


class GenerateRecommendationTool(BaseTool):
    """智能推荐工具 - 使用 LLM 生成个性化推荐结果

    结合规则评分和 LLM 智能评分，生成更精准的推荐：
    - 规则评分：基于距离、评分、热度等客观指标
    - LLM 评分：理解用户需求语义，评估场所匹配度
    """

    name: str = "generate_recommendation"
    description: str = """智能生成会面地点推荐。

本工具使用双层评分系统：
1. 规则评分（40%）：基于距离、评分、热度等客观指标
2. LLM 智能评分（60%）：理解用户需求，评估场所特色与需求的匹配度

最终生成个性化的推荐理由，帮助用户做出最佳选择。"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "places": {
                "type": "array",
                "description": "候选场所列表（来自search_poi的结果）",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "场所名称"},
                        "address": {"type": "string", "description": "地址"},
                        "rating": {"type": "string", "description": "评分"},
                        "distance": {"type": "number", "description": "距中心点距离"},
                        "location": {"type": "string", "description": "坐标"}
                    }
                }
            },
            "center": {
                "type": "object",
                "description": "中心点坐标",
                "properties": {
                    "lng": {"type": "number", "description": "经度"},
                    "lat": {"type": "number", "description": "纬度"}
                },
                "required": ["lng", "lat"]
            },
            "participant_locations": {
                "type": "array",
                "description": "参与者位置名称列表，用于 LLM 评估公平性",
                "items": {"type": "string"},
                "default": []
            },
            "keywords": {
                "type": "string",
                "description": "搜索的场所类型，如'咖啡馆'、'餐厅'",
                "default": "咖啡馆"
            },
            "user_requirements": {
                "type": "string",
                "description": "用户的特殊需求，如'停车方便'、'环境安静'",
                "default": ""
            },
            "recommendation_count": {
                "type": "integer",
                "description": "推荐数量，默认5个",
                "default": 5
            },
            "use_llm_ranking": {
                "type": "boolean",
                "description": "是否使用 LLM 智能排序，默认 true",
                "default": True
            }
        },
        "required": ["places", "center"]
    }

    class Config:
        arbitrary_types_allowed = True

    def _get_recommender(self):
        """延迟加载推荐器，并确保 API key 已设置"""
        if not hasattr(self, '_cached_recommender'):
            from app.tool.meetspot_recommender import CafeRecommender
            from app.config import config
            recommender = CafeRecommender()
            if hasattr(config, 'amap') and config.amap and hasattr(config.amap, 'api_key'):
                recommender.api_key = config.amap.api_key
            object.__setattr__(self, '_cached_recommender', recommender)
        return self._cached_recommender

    async def execute(
        self,
        places: List[Dict],
        center: Dict,
        participant_locations: List[str] = None,
        keywords: str = "咖啡馆",
        user_requirements: str = "",
        recommendation_count: int = 5,
        use_llm_ranking: bool = True
    ) -> ToolResult:
        """智能生成推荐"""
        try:
            if not places:
                return BaseTool.fail_response("没有候选场所可供推荐")

            recommender = self._get_recommender()
            center_point = (center["lng"], center["lat"])

            # 1. 先用规则评分进行初步排序
            ranked = recommender._rank_places(
                places=places,
                center_point=center_point,
                user_requirements=user_requirements,
                keywords=keywords
            )

            # 2. 如果启用 LLM 智能排序，进行重排序
            if use_llm_ranking and participant_locations:
                logger.info("启用 LLM 智能排序")
                ranked = await recommender._llm_smart_ranking(
                    places=ranked,
                    user_requirements=user_requirements,
                    participant_locations=participant_locations or [],
                    keywords=keywords,
                    top_n=recommendation_count + 3  # 多取几个以便筛选
                )

            # 取前N个推荐
            top_places = ranked[:recommendation_count]

            # 生成推荐结果
            recommendations = []
            for i, place in enumerate(top_places, 1):
                score = place.get("_final_score") or place.get("_score", 0)
                distance = place.get("_distance") or place.get("distance", 0)
                rating = place.get("_raw_rating") or place.get("rating", "N/A")

                # 优先使用 LLM 生成的理由
                llm_reason = place.get("_llm_reason", "")
                rule_reason = place.get("_recommendation_reason", "")

                if llm_reason:
                    reasons = [llm_reason]
                elif rule_reason:
                    reasons = [rule_reason]
                else:
                    # 兜底：构建基础推荐理由
                    reasons = []
                    if distance <= 500:
                        reasons.append("距离中心点很近")
                    elif distance <= 1000:
                        reasons.append("距离适中")

                    if rating != "N/A":
                        try:
                            r = float(rating)
                            if r >= 4.5:
                                reasons.append("口碑优秀")
                            elif r >= 4.0:
                                reasons.append("评价良好")
                        except (ValueError, TypeError):
                            pass

                    if not reasons:
                        reasons = ["综合评分较高"]

                recommendations.append({
                    "rank": i,
                    "name": place.get("name", ""),
                    "address": place.get("address", ""),
                    "rating": str(rating) if rating else "N/A",
                    "distance": round(distance, 0),
                    "score": round(score, 1),
                    "llm_score": place.get("_llm_score", 0),
                    "tel": place.get("tel", ""),
                    "reasons": reasons,
                    "location": place.get("location", ""),
                    "scoring_method": "llm+rule" if place.get("_llm_score") else "rule"
                })

            return BaseTool.success_response({
                "recommendations": recommendations,
                "total_candidates": len(places),
                "user_requirements": user_requirements,
                "center": center,
                "llm_ranking_used": use_llm_ranking and bool(participant_locations)
            })

        except Exception as e:
            logger.error(f"生成推荐失败: {e}")
            return BaseTool.fail_response(f"生成推荐错误: {str(e)}")


# 导出所有工具
__all__ = [
    "GeocodeTool",
    "CalculateCenterTool",
    "SearchPOITool",
    "GenerateRecommendationTool"
]
