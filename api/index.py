import sys
import os
import time
import asyncio
import re
import json
import gc
from typing import List, Optional

# 并发控制：防止OOM，保证每个请求都能完成
MAX_CONCURRENT_REQUESTS = 3  # 最大同时处理请求数
_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# WhiteNoise将通过StaticFiles中间件集成，不需要ASGI↔WSGI转换
from api.routers import auth, payment, seo_pages
from app.i18n import detect_language, t as _t

# 导入应用模块
try:
    from app.config import config
    from app.tool.meetspot_recommender import CafeRecommender
    from app.logger import logger
    from app.db.database import init_db

    print("✅ 成功导入所有必要模块")
    config_available = True
except ImportError as e:
    print(f"⚠️ 导入模块警告: {e}")
    config = None
    config_available = False
    # 创建 fallback logger（当 app.logger 导入失败时）
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("meetspot")

    # Fallback for init_db
    async def init_db():
        logger.warning("Database module not available, skipping init")


# 导入 Agent 模块（高内存消耗，暂时禁用以保证稳定性）
agent_available = False  # 禁用 Agent 模式，节省内存
# try:
#     from app.agent import MeetSpotAgent, create_meetspot_agent
#     agent_available = True
#     print("✅ 成功导入 Agent 模块")
# except ImportError as e:
#     print(f"⚠️ Agent 模块导入失败: {e}")
print("ℹ️ Agent 模块已禁用（节省内存）")


def create_meetspot_agent():
    """Stub function - Agent模式已禁用，此函数不应被调用"""
    raise RuntimeError("Agent模式已禁用，请使用规则模式")


# 导入 LLM 模块
llm_available = False
llm_instance = None
try:
    from app.llm import LLM
    from app.schema import Message

    llm_available = True
    print("✅ 成功导入 LLM 模块")
except ImportError as e:
    print(f"⚠️ LLM 模块导入失败: {e}")

    # 在Vercel环境下创建最小化配置类
    class MinimalConfig:
        class AMapSettings:
            def __init__(self, api_key):
                self.api_key = api_key

        class GoogleMapsSettings:
            def __init__(self, api_key):
                self.api_key = api_key

        def __init__(self):
            amap_key = os.getenv("AMAP_API_KEY", "")
            if amap_key:
                self.amap = self.AMapSettings(amap_key)
            else:
                self.amap = None
            google_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
            if google_key:
                self.google_maps = self.GoogleMapsSettings(google_key)
            else:
                self.google_maps = None

    if os.getenv("AMAP_API_KEY"):
        config = MinimalConfig()
        config_available = True
        print("✅ 创建最小化配置（仅高德地图）")
    else:
        print("❌ 未找到AMAP_API_KEY环境变量")

# 在Vercel环境下导入最小化推荐器
if not config_available and os.getenv("AMAP_API_KEY"):
    try:
        # 创建最小化推荐器
        import asyncio
        import httpx
        import json
        import hashlib
        import time
        from datetime import datetime

        class MinimalCafeRecommender:
            """最小化推荐器，专为Vercel环境设计"""

            def __init__(self):
                self.api_key = os.getenv("AMAP_API_KEY")
                self.base_url = "https://restapi.amap.com/v3"

            async def execute(
                self, locations, keywords="咖啡馆", place_type="", user_requirements=""
            ):
                """执行推荐"""
                try:
                    # 简化的推荐逻辑
                    result_html = await self._generate_recommendations(
                        locations, keywords, user_requirements
                    )

                    # 生成HTML文件
                    html_filename = f"place_recommendation_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}.html"
                    html_path = f"workspace/js_src/{html_filename}"

                    # 确保目录存在
                    os.makedirs("workspace/js_src", exist_ok=True)

                    # 写入HTML文件
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(result_html)

                    # 返回结果对象
                    class Result:
                        def __init__(self, output):
                            self.output = output

                    return Result(
                        f"生成的推荐页面：{html_path}\nHTML页面: {html_filename}"
                    )

                except Exception as e:
                    return Result(f"推荐失败: {str(e)}")

            async def _generate_recommendations(
                self, locations, keywords, user_requirements
            ):
                """生成推荐HTML"""
                # 简化的HTML模板
                html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MeetSpot 推荐结果</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
        .locations {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        .result {{ margin: 10px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 MeetSpot 推荐结果</h1>
        <p>为您推荐最佳会面地点</p>
    </div>

    <div class="locations">
        <h3>📍 您的位置信息</h3>
        <p><strong>位置:</strong> {", ".join(locations)}</p>
        <p><strong>需求:</strong> {keywords}</p>
        {f"<p><strong>特殊要求:</strong> {user_requirements}</p>" if user_requirements else ""}
    </div>

    <div class="result">
        <h3>💡 推荐建议</h3>
        <p>由于在Vercel环境下运行，推荐功能已简化。建议您:</p>
        <ul>
            <li>选择位置中心点附近的{keywords}</li>
            <li>考虑交通便利性和停车条件</li>
            <li>选择环境舒适、适合交流的场所</li>
        </ul>
    </div>

    <div class="result">
        <h3>⚠️ 注意事项</h3>
        <p>当前运行在简化模式下。如需完整功能，请在本地环境运行或配置完整的环境变量。</p>
    </div>
</body>
</html>
                """
                return html_content

        CafeRecommender = MinimalCafeRecommender
        print("✅ 创建最小化推荐器")

    except Exception as e:
        print(f"❌ 创建最小化推荐器失败: {e}")
        CafeRecommender = None


# 请求模型定义
class LocationRequest(BaseModel):
    locations: List[str]
    venue_types: Optional[List[str]] = ["咖啡馆"]
    user_requirements: Optional[str] = ""


class LocationCoord(BaseModel):
    """预解析的地址坐标信息（来自前端 Autocomplete 选择）"""

    name: str  # 用户选择的地点名称
    address: str  # 完整地址
    lng: float  # 经度
    lat: float  # 纬度
    city: Optional[str] = ""  # 城市名


class MeetSpotRequest(BaseModel):
    locations: List[str]
    keywords: Optional[str] = "咖啡馆"
    place_type: Optional[str] = ""
    user_requirements: Optional[str] = ""
    # 筛选条件
    min_rating: Optional[float] = 0.0  # 最低评分 (0-5)
    max_distance: Optional[int] = 100000  # 最大距离 (米)
    price_range: Optional[str] = ""  # 价格区间: economy/mid/high
    # 预解析坐标（可选，由前端 Autocomplete 提供）
    location_coords: Optional[List[LocationCoord]] = None
    language: Optional[str] = ""


class AIChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []
    lang: Optional[str] = ""


# MeetSpot AI客服系统提示词
MEETSPOT_SYSTEM_PROMPT = """你是MeetSpot（聚点）的AI Agent智能助手。MeetSpot是一款多人会面地点推荐的AI Agent，核心解决"在哪见面最公平"的问题。

## 核心定位
MeetSpot不是简单的搜索工具，而是一个完整的AI Agent：
- 高德地图搜"我附近"，MeetSpot搜"我们中间"
- 大众点评帮你找"好店"，MeetSpot帮你找"对所有人都公平的好店"

## 技术特点
1. **球面几何算法**：使用Haversine公式计算地球曲面真实中点，比平面算法精确15-20%
2. **GPT-4o智能评分**：AI对候选场所进行多维度评分（距离、评分、停车、环境、交通便利度）
3. **5步透明推理**：解析地址 -> 计算中点 -> 搜索周边 -> GPT-4o评分 -> 生成推荐
4. **可解释AI**：用户可以看到Agent每一步是怎么"思考"的，完全透明

## 产品能力
- **覆盖范围**：350+城市，基于高德地图数据
- **场景类型**：12种主题（咖啡馆、餐厅、图书馆、KTV、健身房、密室逃脱等）
- **智能识别**：60+高校简称预置，"北大"自动识别为"北京市海淀区北京大学"
- **参与人数**：支持2-10人，满足团队与家人聚会需求

## 响应时间
- 单场景推荐：5-8秒
- 双场景推荐：8-12秒
- Agent复杂模式：15-30秒
（包含完整流程：地理编码、POI搜索、GPT-4o智能评分、交通建议）

## 使用方法
1. 输入2个以上参与者地点（支持地址、地标、简称如"北大"）
2. 选择场景类型（可多选，如"咖啡馆 餐厅"）
3. 可选：设置特殊需求（停车方便、环境安静等）
4. 点击推荐，5-30秒后获取AI Agent推荐结果

## 常见问题
- **和高德有什么区别？** 高德搜"我附近"，MeetSpot搜"我们中间"，是高德/百度都没有的功能
- **支持哪些城市？** 350+城市，覆盖全国主要城市
- **推荐速度如何？** 单场景5-8秒，双场景8-12秒，复杂Agent模式15-30秒
- **是否收费？** 完全免费，无需注册，直接使用

## 回答规范
- 用友好、专业的语气回答问题
- 强调MeetSpot是AI Agent，不是简单搜索工具
- 突出"公平"、"透明可解释"、"GPT-4o智能评分"等核心价值
- 回答简洁明了，使用中文
- 如果用户问无关问题，礼貌引导了解产品功能"""

MEETSPOT_SYSTEM_PROMPT_EN = """You are the MeetSpot AI Assistant. MeetSpot is an AI Agent for multi-person meeting point recommendations, solving the problem of "where to meet that's fair for everyone."

## Core Positioning
MeetSpot is not a simple search tool — it's a complete AI Agent:
- Map apps search "near me"; MeetSpot searches "between us"
- Review apps find "good places"; MeetSpot finds "good places that are fair for everyone"

## Technical Highlights
1. **Spherical Geometry**: Uses Haversine formula for true surface midpoint calculation, 15-20% more accurate than planar algorithms
2. **GPT-4o Smart Scoring**: AI evaluates venues across multiple dimensions (distance, rating, parking, ambiance, transit)
3. **5-Step Transparent Reasoning**: Parse addresses → Calculate midpoint → Search nearby → GPT-4o scoring → Generate recommendations
4. **Explainable AI**: Users can see how the Agent "thinks" at every step — fully transparent

## Capabilities
- **Coverage**: 350+ cities across China, powered by Amap data
- **Venue Types**: 12 themes (cafes, restaurants, libraries, KTV, gyms, escape rooms, etc.)
- **Smart Recognition**: 60+ university abbreviations pre-loaded
- **Group Size**: 2-10 participants

## Response Times
- Single scenario: 5-8 seconds
- Dual scenario: 8-12 seconds
- Agent complex mode: 15-30 seconds

## How to Use
1. Enter 2+ participant locations (addresses, landmarks, or abbreviations)
2. Choose venue type(s) (multiple allowed)
3. Optional: Set special requirements (parking, quiet environment, etc.)
4. Click recommend — get AI Agent results in 5-30 seconds

## Response Guidelines
- Use friendly, professional tone
- Emphasize MeetSpot is an AI Agent, not a simple search tool
- Highlight "fairness," "transparent explainability," and "GPT-4o smart scoring"
- Keep answers concise and clear, respond in English
- If users ask unrelated questions, politely guide them to explore the product"""

# 预设问题列表
PRESET_QUESTIONS = [
    {"id": 1, "question": "MeetSpot是什么？", "category": "产品介绍"},
    {"id": 2, "question": "AI Agent怎么工作的？", "category": "技术"},
    {"id": 3, "question": "支持哪些场景？", "category": "功能"},
    {"id": 4, "question": "推荐需要多久？", "category": "性能"},
    {"id": 5, "question": "和高德地图有什么区别？", "category": "对比"},
    {"id": 6, "question": "是否收费？", "category": "其他"},
]

PRESET_QUESTIONS_EN = [
    {"id": 1, "question": "What is MeetSpot?", "category": "Product"},
    {"id": 2, "question": "How does the AI Agent work?", "category": "Technology"},
    {"id": 3, "question": "What venue types are supported?", "category": "Features"},
    {"id": 4, "question": "How fast are recommendations?", "category": "Performance"},
    {
        "id": 5,
        "question": "How is it different from map apps?",
        "category": "Comparison",
    },
    {"id": 6, "question": "Is it free to use?", "category": "Other"},
]

# 环境变量配置（用于 Vercel）
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
AMAP_JS_API_KEY = os.getenv("AMAP_JS_API_KEY", "")  # JS API key for frontend map
AMAP_SECURITY_JS_CODE = os.getenv("AMAP_SECURITY_JS_CODE", "")

# Google Maps 国际场景（/en/ 路径下使用）
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# 免费次数限制
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "1"))


def _parse_cors_origins(raw_value: str) -> List[str]:
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return origins or ["*"]


def _get_client_ip(request: Request) -> str:
    """获取客户端 IP，优先读取代理头。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _quota_exceeded_response(
    used_today: int, start_time: float, lang: str = "zh"
) -> dict:
    return {
        "success": False,
        "need_payment": True,
        "message": _t("api.error.quota_exceeded", lang),
        "free_used": used_today,
        "free_limit": FREE_DAILY_LIMIT,
        "processing_time": time.time() - start_time,
    }


# 创建 FastAPI 应用
app = FastAPI(
    title="MeetSpot", description="MeetSpot会面点推荐服务 - 完整功能版", version="1.0.0"
)


# ============================================================================
# 应用启动事件 - 生成设计token CSS文件
# ============================================================================
@app.on_event("startup")
async def startup_event():
    """应用启动时生成设计token CSS文件"""
    try:
        from app.design_tokens import generate_design_tokens_css

        generate_design_tokens_css()
        logger.info("✅ Design tokens CSS generated successfully")
    except Exception as e:
        logger.error(f"❌ Failed to generate design tokens CSS: {e}")
        # 不阻止应用启动,即使CSS生成失败


@app.on_event("startup")
async def startup_database():
    """确保MVP所需的数据库表已创建。"""
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        raise


# 配置CORS（生产环境禁止 "*" + credentials 组合）
cors_origins = _parse_cors_origins(os.getenv("CORS_ALLOW_ORIGINS", "*"))
cors_allow_all = "*" in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if cors_allow_all else cors_origins,
    allow_credentials=not cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 缓存中间件 - 为静态资源添加 Cache-Control 头
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    """Add Cache-Control headers for static assets to improve performance."""
    response = await call_next(request)
    path = request.url.path

    # 静态资源长期缓存 (1 year for immutable assets)
    if any(path.endswith(ext) for ext in [".css", ".js", ".woff2", ".woff", ".ttf"]):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    # 图片缓存 (30 days)
    elif any(
        path.endswith(ext)
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"]
    ):
        response.headers["Cache-Control"] = "public, max-age=2592000"
    # HTML 页面短期缓存 (10 minutes, revalidate)
    elif (
        path.endswith(".html")
        or path == "/"
        or path in ["/about", "/faq", "/how-it-works"]
    ):
        response.headers["Cache-Control"] = (
            "public, max-age=600, stale-while-revalidate=86400"
        )
    # sitemap/robots - long cache with stale-while-revalidate for Render cold starts
    # This ensures CDN can serve cached content when origin is cold (fixes GSC "Couldn't fetch")
    elif path in ["/sitemap.xml", "/robots.txt"]:
        response.headers["Cache-Control"] = (
            "public, max-age=86400, stale-while-revalidate=604800"
        )

    return response


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Global rate limit handler."""
    lang = detect_language(request)
    return JSONResponse(
        status_code=429,
        content={"detail": _t("api.error.rate_limit", lang)},
    )


app.state.limiter = seo_pages.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)


# HEAD 请求兼容中间件 - Googlebot 等爬虫使用 HEAD 检查页面状态
@app.middleware("http")
async def head_method_support(request: Request, call_next):
    """Convert HEAD requests to GET internally, then strip the body."""
    if request.method == "HEAD":
        request.scope["method"] = "GET"
        response = await call_next(request)
        # Return headers only, no body (per HTTP spec for HEAD)
        from starlette.responses import Response as StarletteResponse

        return StarletteResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
    return await call_next(request)


# 挂载静态文件（如果目录存在）
try:
    # Vercel环境下创建必要的目录结构
    workspace_dir = "workspace"
    js_src_dir = os.path.join(workspace_dir, "js_src")
    os.makedirs(js_src_dir, exist_ok=True)

    if os.path.exists(workspace_dir):
        app.mount("/workspace", StaticFiles(directory=workspace_dir), name="workspace")
        logger.info("mounted_static_workspace")

    if os.path.exists("public"):
        app.mount("/public", StaticFiles(directory="public"), name="public")
        logger.info("mounted_static_public")

    if os.path.exists("docs"):
        app.mount("/docs-static", StaticFiles(directory="docs"), name="docs-static")
        logger.info("mounted_static_docs")

    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")
        logger.info("mounted_static_assets")

    if os.path.exists("locales"):
        app.mount("/locales", StaticFiles(directory="locales"), name="locales")
        logger.info("mounted_static_locales")
except Exception as e:
    logger.warning(f"静态文件挂载失败: {e}")
    # 在Vercel环境下，静态文件挂载可能失败，这是正常的

app.include_router(auth.router)
app.include_router(payment.router)
app.include_router(seo_pages.router)


@app.get("/health")
async def health_check():
    """健康检查和配置状态"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "config": {
            "amap_configured": bool(
                AMAP_API_KEY or (config and hasattr(config, "amap") and config.amap)
            ),
            "full_features": config_available,
            "minimal_mode": not config_available and bool(AMAP_API_KEY),
        },
    }


@app.api_route("/google48ac1a797739b7b0.html", methods=["GET", "HEAD"])
async def google_verification():
    """返回Google Search Console验证文件（支持GET和HEAD请求）"""
    google_file = "public/google48ac1a797739b7b0.html"
    if os.path.exists(google_file):
        response = FileResponse(
            google_file,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
        return response
    # 如果文件不存在，返回404
    raise HTTPException(status_code=404, detail="Google verification file not found")


@app.api_route("/BingSiteAuth.xml", methods=["GET", "HEAD"])
async def bing_verification():
    """返回Bing站点验证文件（支持GET和HEAD请求）"""
    bing_file = "public/BingSiteAuth.xml"
    if os.path.exists(bing_file):
        response = FileResponse(
            bing_file,
            media_type="application/xml",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
        return response
    # 如果文件不存在，返回404
    raise HTTPException(status_code=404, detail="Bing verification file not found")


# sitemap.xml 和 robots.txt 由 seo_pages.router 动态生成（含城市页）


@app.api_route("/favicon.ico", methods=["GET", "HEAD"])
async def favicon_ico():
    """返回网站图标（支持GET和HEAD请求）"""
    # 优先返回SVG favicon（现代浏览器支持）
    svg_file = "public/favicon.svg"
    if os.path.exists(svg_file):
        return FileResponse(
            svg_file,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "Content-Type": "image/svg+xml",
            },
        )
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.api_route("/favicon.svg", methods=["GET", "HEAD"])
async def favicon_svg():
    """返回SVG网站图标（支持GET和HEAD请求）"""
    svg_file = "public/favicon.svg"
    if os.path.exists(svg_file):
        return FileResponse(
            svg_file,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "Content-Type": "image/svg+xml",
            },
        )
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/config")
async def get_config():
    """获取当前配置状态（不暴露敏感信息）"""
    amap_key = ""
    if config:
        amap_key = config.amap.api_key
    else:
        amap_key = AMAP_API_KEY

    return {
        "amap_api_key_configured": bool(amap_key),
        "amap_api_key_length": len(amap_key) if amap_key else 0,
        "config_loaded": bool(config),
        "full_features_available": bool(config),
    }


# ==================== AI 客服接口 ====================


@app.get("/api/ai_chat/preset_questions")
async def get_preset_questions(raw_request: Request):
    """Get preset question list, language-aware."""
    lang = detect_language(raw_request)
    questions = PRESET_QUESTIONS_EN if lang == "en" else PRESET_QUESTIONS
    return {"success": True, "questions": questions}


@app.post("/api/ai_chat")
async def ai_chat(request: AIChatRequest, raw_request: Request = None):
    """AI chat endpoint - bilingual."""
    start_time = time.time()
    lang = request.lang or (detect_language(raw_request) if raw_request else "zh")

    try:
        print(f"[AI Chat] message: {request.message[:50]}...")

        if not llm_available:
            print("LLM module unavailable, using fallback")
            return {
                "success": True,
                "response": _t("api.chat.fallback", lang),
                "processing_time": time.time() - start_time,
                "mode": "fallback",
            }

        # 获取LLM API配置
        llm_api_key = os.getenv("LLM_API_KEY", "")
        llm_api_base = os.getenv("LLM_API_BASE", "https://newapi.deepwisdom.ai/v1")
        llm_model = os.getenv("LLM_MODEL", "deepseek-chat")

        if not llm_api_key:
            print("LLM_API_KEY not configured")
            return {
                "success": True,
                "response": _t("api.chat.configuring", lang),
                "processing_time": time.time() - start_time,
                "mode": "fallback",
            }

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=llm_api_key, base_url=llm_api_base)

        system_prompt = (
            MEETSPOT_SYSTEM_PROMPT_EN if lang == "en" else MEETSPOT_SYSTEM_PROMPT
        )
        messages = [{"role": "system", "content": system_prompt}]

        if request.conversation_history:
            recent_history = request.conversation_history[-10:]
            messages.extend(recent_history)

        messages.append({"role": "user", "content": request.message})

        print(f"[AI Chat] calling LLM ({llm_model}), messages: {len(messages)}")

        response = await client.chat.completions.create(
            model=llm_model, messages=messages, max_tokens=500, temperature=0.7
        )

        ai_response = response.choices[0].message.content
        processing_time = time.time() - start_time

        print(f"[AI Chat] response generated, time: {processing_time:.2f}s")

        return {
            "success": True,
            "response": ai_response,
            "processing_time": processing_time,
            "mode": "llm",
        }

    except Exception as e:
        print(f"[AI Chat] error: {str(e)}")
        return {
            "success": False,
            "response": _t("api.chat.error", lang),
            "error": str(e),
            "processing_time": time.time() - start_time,
            "mode": "error",
        }


# ==================== 智能路由逻辑 ====================


def assess_request_complexity(request: MeetSpotRequest) -> dict:
    """评估请求复杂度，决定使用哪种模式

    Returns:
        dict: {
            "use_agent": bool,  # 是否使用Agent模式
            "complexity_score": int,  # 复杂度分数 (0-100)
            "reasons": list,  # 判断原因
            "mode_name": str  # 模式名称（用于日志）
        }
    """
    score = 0
    reasons = []

    # 1. 地点数量 (权重: 30分)
    location_count = len(request.locations)
    if location_count >= 4:
        score += 30
        reasons.append(f"{location_count}个地点，需要复杂的中心点计算")
    elif location_count >= 3:
        score += 15
        reasons.append(f"{location_count}个地点")

    # 2. 场所类型数量 (权重: 25分)
    keywords = request.keywords or ""
    keyword_count = len(keywords.split()) if keywords else 0
    if keyword_count >= 3:
        score += 25
        reasons.append(f"{keyword_count}种场所类型，需要智能平衡")
    elif keyword_count >= 2:
        score += 12
        reasons.append(f"{keyword_count}种场所类型")

    # 3. 特殊需求复杂度 (权重: 25分)
    requirements = request.user_requirements or ""
    if requirements:
        req_keywords = [
            "商务",
            "安静",
            "停车",
            "Wi-Fi",
            "包间",
            "儿童",
            "24小时",
            "久坐",
        ]
        matched_reqs = sum(1 for kw in req_keywords if kw in requirements)
        if matched_reqs >= 3:
            score += 25
            reasons.append(f"{matched_reqs}个特殊需求，需要综合权衡")
        elif matched_reqs >= 2:
            score += 15
            reasons.append(f"{matched_reqs}个特殊需求")
        elif len(requirements) > 50:
            score += 20
            reasons.append("详细的自定义需求描述")

    # 4. 筛选条件 (权重: 20分)
    has_filters = False
    if request.min_rating and request.min_rating > 0:
        has_filters = True
        score += 5
    if request.max_distance and request.max_distance < 10000:
        has_filters = True
        score += 5
    if request.price_range:
        has_filters = True
        score += 5
    if has_filters:
        reasons.append("有精确筛选条件")

    # 决定模式 (阈值: 40分)
    use_agent = score >= 40 and agent_available

    # 如果Agent不可用，降级到规则模式
    if score >= 40 and not agent_available:
        reasons.append("Agent模块不可用，使用增强规则模式")

    mode_name = "Agent智能模式" if use_agent else "快速规则模式"

    return {
        "use_agent": use_agent,
        "complexity_score": min(score, 100),
        "reasons": reasons,
        "mode_name": mode_name,
    }


# ==================== 会面点推荐接口 ====================


@app.post("/api/find_meetspot")
async def find_meetspot(request: MeetSpotRequest, raw_request: Request = None):
    """统一的会面地点推荐入口 - 智能路由

    根据请求复杂度自动选择最优模式：
    - 简单请求: 规则+LLM模式 (快速，0.3-0.8秒)
    - 复杂请求: Agent模式 (深度分析，3-8秒)
    """
    start_time = time.time()
    client_ip = _get_client_ip(raw_request) if raw_request else None
    lang = (
        request.language
        if request.language in ("zh", "en")
        else (detect_language(raw_request) if raw_request else "zh")
    )

    # 免费次数限制检查
    if client_ip and FREE_DAILY_LIMIT > 0:
        try:
            from app.db.database import AsyncSessionLocal
            from app.db import payment_crud

            async with AsyncSessionLocal() as db:
                used_today = await payment_crud.get_free_usage_today(db, client_ip)
                if used_today >= FREE_DAILY_LIMIT:
                    return _quota_exceeded_response(used_today, start_time, lang)
        except Exception as e:
            # 免费次数检查失败不阻塞主流程
            logger.warning(f"免费次数检查异常（不影响请求）: {e}")

    # 并发控制：排队处理，保证每个请求都能完成
    async with _request_semaphore:
        result = await _process_meetspot_request(request, start_time, lang)

    # 请求成功后记录免费使用
    if (
        client_ip
        and FREE_DAILY_LIMIT > 0
        and isinstance(result, dict)
        and result.get("success")
    ):
        try:
            from app.db.database import AsyncSessionLocal
            from app.db import payment_crud

            async with AsyncSessionLocal() as db:
                consumed, used_today = await payment_crud.try_consume_free_use(
                    db=db,
                    ip_address=client_ip,
                    daily_limit=FREE_DAILY_LIMIT,
                )
                if not consumed:
                    logger.info("free_quota_race_lost")
                    return _quota_exceeded_response(used_today, start_time, lang)
        except Exception as e:
            logger.warning(f"记录免费使用异常: {e}")

    return result


async def _process_meetspot_request(
    request: MeetSpotRequest,
    start_time: float,
    lang: str = "zh",
):
    """实际处理推荐请求的内部函数"""
    # 评估请求复杂度
    complexity = assess_request_complexity(request)
    logger.info(
        f"[智能路由] 复杂度评估: {complexity['complexity_score']}分, 模式: {complexity['mode_name']}"
    )
    if complexity["reasons"]:
        logger.info(f"[智能路由] 触发原因: {', '.join(complexity['reasons'])}")

    try:
        logger.debug(f"收到请求: {request.model_dump()}")

        # 检查配置
        if config and getattr(config, "amap", None):
            api_key = config.amap.api_key
            logger.info("using_amap_key_source=config")
        else:
            api_key = AMAP_API_KEY
            logger.info("using_amap_key_source=env")

        if not api_key:
            raise HTTPException(
                status_code=500, detail=_t("api.error.amap_not_configured", lang)
            )

        # ========== 智能路由：根据复杂度选择模式 ==========
        if complexity["use_agent"]:
            print(f"🤖 [Agent模式] 复杂请求，启用Agent智能分析...")
            try:
                agent = create_meetspot_agent()
                # 添加15秒超时，确保Agent模式不会无限等待
                AGENT_TIMEOUT = 15  # 秒
                agent_result = await asyncio.wait_for(
                    agent.recommend(
                        locations=request.locations,
                        keywords=request.keywords or "咖啡馆",
                        requirements=request.user_requirements or "",
                    ),
                    timeout=AGENT_TIMEOUT,
                )

                processing_time = time.time() - start_time
                print(f"⏱️  [Agent] 推荐完成，耗时: {processing_time:.2f}秒")

                # Agent模式返回格式
                return {
                    "success": agent_result.get("success", False),
                    "html_url": None,  # Agent模式暂不生成HTML
                    "locations_count": len(request.locations),
                    "processing_time": processing_time,
                    "message": "Agent智能推荐完成",
                    "output": agent_result.get("recommendation", ""),
                    "mode": "agent",
                    "complexity_score": complexity["complexity_score"],
                    "complexity_reasons": complexity["reasons"],
                    "agent_data": {
                        "geocode_results": agent_result.get("geocode_results", []),
                        "center_point": agent_result.get("center_point"),
                        "search_results": agent_result.get("search_results", []),
                        "steps_executed": agent_result.get("steps_executed", 0),
                    },
                }
            except asyncio.TimeoutError:
                print(f"⚠️ [Agent] 执行超时({AGENT_TIMEOUT}秒)，降级到规则模式")
            except Exception as agent_error:
                print(f"⚠️ [Agent] 执行失败，降级到规则模式: {agent_error}")
                # 降级到规则模式，继续执行下面的代码

        # ========== 规则+LLM模式（默认/降级） ==========
        if config:
            print("🔧 开始初始化推荐工具...")
            recommender = CafeRecommender()

            print("🚀 开始执行推荐...")
            # 转换 location_coords 为推荐器期望的格式
            pre_resolved_coords = None
            if request.location_coords:
                pre_resolved_coords = [
                    {
                        "name": coord.name,
                        "address": coord.address,
                        "lng": coord.lng,
                        "lat": coord.lat,
                        "city": coord.city or "",
                    }
                    for coord in request.location_coords
                ]
                print(f"📍 使用前端预解析坐标: {len(pre_resolved_coords)} 个")

            # 调用推荐工具
            result = await recommender.execute(
                locations=request.locations,
                keywords=request.keywords or "咖啡馆",
                place_type=request.place_type or "",
                user_requirements=request.user_requirements or "",
                min_rating=request.min_rating or 0.0,
                max_distance=request.max_distance or 100000,
                price_range=request.price_range or "",
                pre_resolved_coords=pre_resolved_coords,
                language=lang,
            )

            processing_time = time.time() - start_time
            print(f"⏱️  推荐完成，耗时: {processing_time:.2f}秒")

            # 解析工具输出，提取HTML文件路径
            output_text = result.output
            html_url = None

            print(f"📄 工具输出预览: {output_text[:200]}...")

            # 从输出中提取HTML文件路径 - 修复的正则表达式
            html_match = re.search(r"HTML页面:\s*([^\s\n]+\.html)", output_text)
            if html_match:
                html_filename = html_match.group(1)
                print(f"🔍 找到HTML文件名: {html_filename}")
                html_url = f"/workspace/js_src/{html_filename}"
                print(f"🌐 转换为URL: {html_url}")
            else:
                print("❌ 未找到'HTML页面:'模式，尝试其他模式...")
                # 尝试匹配生成的推荐页面格式
                html_match2 = re.search(
                    r"生成的推荐页面：\s*([^\s\n]+\.html)", output_text
                )
                if html_match2:
                    html_path = html_match2.group(1)
                    if html_path.startswith("workspace/"):
                        html_url = f"/{html_path}"
                    else:
                        html_url = f"/workspace/{html_path}"
                    print(f"🔍 备用匹配1找到: {html_url}")
                else:
                    # 尝试匹配任何place_recommendation格式的文件名
                    html_match3 = re.search(
                        r"(place_recommendation_\d{14}_[a-f0-9]+\.html)", output_text
                    )
                    if html_match3:
                        html_filename = html_match3.group(1)
                        html_url = f"/workspace/js_src/{html_filename}"
                        print(f"🔍 备用匹配2找到: {html_url}")
                    else:
                        print("❌ 所有匹配模式都失败了")
                        html_url = None

            # 返回前端期望的格式（包含模式信息）
            response_data = {
                "success": True,
                "html_url": html_url,
                "locations_count": len(request.locations),
                "processing_time": processing_time,
                "message": "Recommendation generated successfully"
                if lang == "en"
                else "推荐生成成功",
                "output": output_text,
                "mode": "rule_llm",  # 规则+LLM增强模式
                "complexity_score": complexity["complexity_score"],
                "complexity_reasons": complexity["reasons"],
            }

            print(
                f"📤 返回响应: success={response_data['success']}, html_url={response_data['html_url']}"
            )
            logger.info(
                "recommendation_completed",
                location_count=len(request.locations),
                venue_type=request.keywords or "咖啡馆",
                has_html=html_url is not None,
                processing_time_ms=int(processing_time * 1000),
                mode="rule_llm",
            )
            # 主动释放内存
            gc.collect()
            return response_data

        else:
            # Fallback：如果无法加载完整模块，返回错误
            print("❌ 配置未加载")
            raise HTTPException(
                status_code=500, detail=_t("api.error.config_error", lang)
            )

    except Exception as e:
        print(f"💥 异常发生: {str(e)}")
        print(f"异常类型: {type(e)}")
        import traceback

        traceback.print_exc()

        processing_time = time.time() - start_time

        # 主动释放内存
        gc.collect()

        # 返回错误响应，但保持前端期望的格式
        error_response = {
            "success": False,
            "error": str(e),
            "processing_time": processing_time,
            "message": f"Recommendation failed: {str(e)}"
            if lang == "en"
            else f"推荐失败: {str(e)}",
        }

        print(f"📤 返回错误响应: {error_response['message']}")
        return error_response


@app.post("/api/find_meetspot_agent")
async def find_meetspot_agent(request: MeetSpotRequest):
    """Agent 模式的会面地点推荐功能

    使用 AI Agent 进行智能推荐，支持：
    - 自主规划推荐流程
    - 智能分析场所特点
    - 生成个性化推荐理由
    """
    start_time = time.time()

    try:
        print(f"🤖 [Agent] 收到请求: {request.model_dump()}")

        # 检查 Agent 是否可用
        if not agent_available:
            print("⚠️ Agent 模块不可用，回退到规则模式")
            return await find_meetspot(request)

        # 检查配置
        if not config or not config.amap or not config.amap.api_key:
            print("❌ API 密钥未配置")
            raise HTTPException(status_code=500, detail="高德地图API密钥未配置")

        print("🔧 [Agent] 初始化 MeetSpotAgent...")
        agent = create_meetspot_agent()

        print("🚀 [Agent] 开始执行推荐任务...")
        result = await agent.recommend(
            locations=request.locations,
            keywords=request.keywords or "咖啡馆",
            requirements=request.user_requirements or "",
        )

        processing_time = time.time() - start_time
        print(f"⏱️  [Agent] 推荐完成，耗时: {processing_time:.2f}秒")

        # 构建响应
        response_data = {
            "success": result.get("success", False),
            "mode": "agent",
            "recommendation": result.get("recommendation", ""),
            "geocode_results": result.get("geocode_results", []),
            "center_point": result.get("center_point"),
            "search_results": result.get("search_results", []),
            "steps_executed": result.get("steps_executed", 0),
            "locations_count": len(request.locations),
            "processing_time": processing_time,
            "message": "Agent 推荐生成成功" if result.get("success") else "推荐失败",
        }

        print(f"📤 [Agent] 返回响应: success={response_data['success']}")
        return response_data

    except Exception as e:
        print(f"💥 [Agent] 异常发生: {str(e)}")
        import traceback

        traceback.print_exc()

        processing_time = time.time() - start_time

        # 尝试回退到规则模式
        print("⚠️ [Agent] 尝试回退到规则模式...")
        try:
            fallback_result = await find_meetspot(request)
            fallback_result["mode"] = "rule_fallback"
            fallback_result["agent_error"] = str(e)
            return fallback_result
        except Exception as fallback_error:
            return {
                "success": False,
                "mode": "agent",
                "error": str(e),
                "processing_time": processing_time,
                "message": f"Agent 推荐失败: {str(e)}",
            }


@app.post("/recommend")
async def get_recommendations(request: LocationRequest):
    """兼容性API端点 - 统一响应格式"""
    # 转换请求格式
    meetspot_request = MeetSpotRequest(
        locations=request.locations,
        keywords=request.venue_types[0] if request.venue_types else "咖啡馆",
        user_requirements=request.user_requirements,
    )

    # 直接调用主端点并返回相同格式
    return await find_meetspot(meetspot_request)


@app.get("/api/config/amap")
async def get_amap_config():
    """返回 AMap 配置（用于前端地图和 Autocomplete）

    Note: 前端需要 JS API key，与后端 geocoding 使用的 Web服务 key 不同
    """
    # 优先使用 JS API key（前端地图专用）
    js_api_key = AMAP_JS_API_KEY
    security_js_code = AMAP_SECURITY_JS_CODE

    # 从 config.toml 获取（如果存在）
    if config and hasattr(config, "amap") and config.amap:
        if not js_api_key:
            js_api_key = getattr(config.amap, "js_api_key", "") or getattr(
                config.amap, "api_key", ""
            )
        if not security_js_code:
            security_js_code = getattr(config.amap, "security_js_code", "")

    # 最后回退到 Web服务 key（不推荐，可能无法加载地图）
    if not js_api_key:
        js_api_key = AMAP_API_KEY

    return {"api_key": js_api_key, "security_js_code": security_js_code}


@app.get("/api/config/google_maps")
async def get_google_maps_config():
    """返回 Google Maps 配置（用于 /en/ 国际场景前端地图加载）

    与高德 key 不同的是，Google Maps JS API 的 key 限制由 referer / IP 在 GCP 控制台配置，
    这里直接返回；前端在没有 key 时应优雅降级（不渲染地图，仅显示列表）
    """
    api_key = GOOGLE_MAPS_API_KEY
    if not api_key and config and hasattr(config, "google_maps") and config.google_maps:
        api_key = getattr(config.google_maps, "api_key", "")
    return {"api_key": api_key}


@app.get("/api/config/analytics")
async def get_analytics_config():
    """返回分析追踪配置（百度统计 + GA4）"""
    return {
        "baidu_tongji_id": os.getenv("BAIDU_TONGJI_ID", ""),
        "ga4_measurement_id": os.getenv("GA4_MEASUREMENT_ID", ""),
    }


@app.get("/api/status")
async def api_status():
    """API状态检查"""
    return {
        "status": "healthy",
        "service": "MeetSpot",
        "version": "1.0.0",
        "platform": "Multi-platform",
        "features": "Complete" if config else "Limited",
        "timestamp": time.time(),
    }


# Vercel 处理函数
app_instance = app

# 如果直接运行此文件（本地测试）
if __name__ == "__main__":
    import uvicorn

    print("🚀 启动 MeetSpot 完整功能服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
