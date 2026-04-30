# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MeetSpot is an **AI Agent** for multi-person meeting point recommendations. Users provide locations and requirements; the Agent calculates the geographic center and recommends optimal venues. Built with FastAPI and Python 3.11+, uses Amap (Gaode Map) for 国内场景 + Google Maps Platform for 国际场景, and OpenRouter (default `openai/gpt-4o-mini`) for semantic scoring + AI chat.

**Live Demo**: https://meetspot-irq2.onrender.com

## Quick Reference

```bash
# Environment
conda activate meetspot                  # Or: source venv/bin/activate

# Development
uvicorn api.index:app --reload           # Preferred for iteration
python web_server.py                     # Full stack with auto env detection

# Test the main endpoint
curl -X POST "http://127.0.0.1:8000/api/find_meetspot" \
  -H "Content-Type: application/json" \
  -d '{"locations": ["北京大学", "清华大学"], "keywords": "咖啡馆"}'

# Testing
pytest tests/ -v                         # Full suite
pytest tests/test_file.py::test_name -v  # Single test
pytest --cov=app tests/                  # Coverage (target: 80%)
python tests/test_seo.py http://localhost:8000  # SEO validation (standalone)

# NOTE: tests/ is gitignored -- tests exist locally but are not in the repo

# Quality gates (run before PRs)
black . && ruff check . && mypy app/

# Postmortem regression check (optional, runs in CI)
python tools/postmortem_check.py         # Check for known issue patterns
```

**Key URLs**: Main UI (`/`), API docs (`/docs`), Health (`/health`)

## Repo Rules

- Follow `AGENTS.md` for repo-local guidelines (style, structure, what not to commit). In particular: runtime-generated files under `workspace/js_src/` must not be committed.
- Active feature plans live in `docs/plans/` (Markdown with YAML frontmatter, date-prefixed). Check there before implementing new features to avoid conflicting with planned work.

## Environment Setup

**Conda**: `conda env create -f environment.yml && conda activate meetspot` (env name is `meetspot`, not `meetspot-dev`)
**Pip**: `python3.11 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

**Required Environment Variables**:
- `AMAP_API_KEY` - Gaode Map API key (required)
- `AMAP_SECURITY_JS_CODE` - JS security code for frontend map
- `LLM_API_KEY` - OpenRouter / OpenAI / 兼容服务的 API key（生产用 OpenRouter `sk-or-v1-...` 形式）
- `LLM_API_BASE` - API base URL (default: `https://openrouter.ai/api/v1`)
- `LLM_MODEL` - Model name (default: `openai/gpt-4o-mini`，OpenRouter slug 格式，可换 `google/gemini-2.5-flash` / `anthropic/claude-haiku-4-5` 等)
- `GOOGLE_MAPS_API_KEY` - Google Maps Platform key（国际场景必需，缺失时 /en/ 路径地图静默降级）

**Local Config**: Copy `config/config.toml.example` to `config/config.toml` and fill in API keys. Alternatively, create a `.env` file with the environment variables above.

## Architecture

### Request Flow

```
POST /api/find_meetspot
        ↓
Complexity Router (assess_request_complexity)
        ↓
Rule+LLM Mode (Agent mode disabled for memory savings on free tier)
        ↓
5-Step Pipeline: Geocode → Center Calc → POI Search → Ranking → HTML Gen
```

Complexity scoring: +10/location, +15 for complex keywords, +10 for special requirements. Currently all requests use Rule+LLM mode (see Concurrency & Memory Budget).

### Entry Points
- `web_server.py` - Main entry, auto-detects production vs development
- `api/index.py` - FastAPI app with all endpoints, middleware, rate limiting (slowapi), CORS, and request concurrency control (MAX_CONCURRENT_REQUESTS = 3)
- `npm run dev` / `npm start` - Proxy to the same Python entry point for platforms that expect Node scripts

### Three-Tier Configuration (Graceful Degradation)

| Mode | Trigger | What Works |
|------|---------|------------|
| Full | `config/config.toml` exists | All features, TOML-based config |
| Simplified | `RAILWAY_ENVIRONMENT` set | Uses `app/config_simple.py` |
| Minimal | Only `AMAP_API_KEY` env var | `MinimalConfig` class in `api/index.py`, basic recommendations only |

### Core Components

```
app/tool/meetspot_recommender.py    # Main recommendation engine (CafeRecommender class)
  |- _enhance_address()             # 10 hardcoded aliases with city prefix
  |- PLACE_TYPE_CONFIG dict         # 12 venue themes with colors, icons
  |- BRAND_FEATURES dict            # 50+ brand profiles with feature scores
  |- _rank_places()                 # 100-point scoring algorithm
  |- _generate_html_content()       # Standalone HTML with Amap JS API
  |- geocode_cache (max 30)         # LRU-style address cache (reduced for free tier)
  |- poi_cache (max 15)             # LRU-style POI cache (reduced for free tier)

data/address_aliases.json           # 48 university + 5 landmark abbreviation mappings
app/design_tokens.py                # WCAG AA color palette, CSS generation
api/routers/seo_pages.py            # SEO landing pages + /compare page
api/services/seo_content.py         # SEOContentGenerator: meta tags, JSON-LD schema, city page snippets
```

### Frontend Address Input

`public/meetspot_finder.html` uses AMap Autocomplete API for real-time address suggestions. When users select from dropdown, coordinates are pre-resolved client-side, bypassing backend geocoding. Falls back to backend geocoding when manual text is entered.

### AI Chat

`/api/ai_chat` (POST) — bilingual conversational interface. Accepts `message`, `language`, and `conversation_history`. Returns streaming or full response using the configured LLM backend (DeepSeek/OpenAI/OpenRouter). System prompts: `MEETSPOT_SYSTEM_PROMPT` (zh) and `MEETSPOT_SYSTEM_PROMPT_EN` (en) defined in `api/index.py`.

`/api/ai_chat/preset_questions` (GET) — returns language-specific suggested questions for the chat UI.

### LLM Scoring (Agent Mode)

When Agent Mode is enabled, final venue scores blend rule-based and LLM semantic analysis:
```
Final Score = Rule Score * 0.4 + LLM Score * 0.6
```

**Current status**: `agent_available = False` in `api/index.py` (line 59) — hardcoded off for memory reasons. `/api/find_meetspot_agent` endpoint exists but returns disabled error. Re-enabling requires bumping Render tier.

### Token Counting

`app/llm.py` uses UTF-8 byte length estimation (`len(text.encode("utf-8")) // 3`) instead of tiktoken. This avoids loading tiktoken's ~80MB model data. Precision is sufficient for internal token limit checks -- not used for billing or exact truncation.

### i18n System

Lightweight JSON-based translations in `app/i18n.py`. Supported languages: `en` (default), `zh`. Translation files: `locales/{lang}.json`.

Language detection priority in `detect_language()`: URL prefix (`/en/` or `/zh/`) > Cookie (`lang`) > `Accept-Language` header > default `en` (国际化优先)。

**`/` 路由特殊**：`api/routers/seo_pages.py` 的根路径硬默认英文（仅 cookie `lang=zh` 时才返回中文），不依赖 Accept-Language。中文用户走 `/zh/` 显式路径或点击导航中文按钮（设置 cookie）。

Both `locales/zh.json` and `locales/en.json` are complete and in sync. To add a new language: create `locales/{lang}.json` with all keys from `locales/en.json`, then add the lang code to `SUPPORTED_LANGS` in `app/i18n.py`.

### 地图 Provider 双轨架构

`app/tool/meetspot_recommender.py` 的 `CafeRecommender` 根据 `language` 参数自动切换地图 provider：

| 路径 | provider | 客户端 | 前端 |
|------|---------|--------|------|
| `/` (默认) / `/en/*` | google | `app/tool/google_maps_client.py` (Places API New v1) | Google Maps JS API + `places.Autocomplete` |
| `/zh/*` 或 cookie/Header zh | amap | 内联高德 REST 调用 | 高德 JS API + `AMap.AutoComplete` |

切换点：`execute()` 入口设置 `self.map_provider`；`_geocode` 和 `_search_pois` 内部按字段分发；`_generate_html_content` 中 `map_script_block` 变量在 `if self.map_provider == "google"` 分支构造对应 JS 模板。Google client 输出严格归一化为高德 POI 格式（`location="lng,lat"` 字符串、`biz_ext.rating` 字符串），让 `_rank_places` 逻辑无需感知 provider 差异。

**Key 配置**：`AMAP_API_KEY` + `GOOGLE_MAPS_API_KEY` 环境变量，仅有高德时只走国内路径（向后兼容）。前端通过 `/api/config/amap` 和 `/api/config/google_maps` 获取 key。

### Concurrency & Memory Budget

`MAX_CONCURRENT_REQUESTS = 3` semaphore in `api/index.py` prevents OOM on Render's 512MB free tier. Rate limiting via slowapi. Agent mode disabled (`agent_available = False`) for the same reason. If re-enabling Agent mode or raising concurrency, monitor memory on the hosting tier.

### Optional Components

Database layer (`app/db/`, `app/models/`) is optional -- core recommendation works without it. Used for auth/payment/social features. Supports PostgreSQL (Supabase via asyncpg, with pgbouncer transaction mode hardening) as primary, SQLite + aiosqlite as local fallback. Controlled by `DATABASE_URL` env var in `app/db/database.py`.

Payment integration: 302.ai checkout via `api/routers/payment.py`. Config: `PAY302_APP_ID`, `PAY302_SECRET`, `PAY302_API_URL` env vars. Free daily limit (`FREE_DAILY_LIMIT`, default 1) + credit purchase system (`CREDIT_PRICE_CENTS`, `CREDITS_PER_PURCHASE`). Signature verification in `app/payment/signature.py`.

API routers:
- `api/routers/auth.py` — SMS auth: `POST /api/auth/send_code`, `POST /api/auth/verify_code`, `GET /api/auth/me`
- `api/routers/payment.py` — 302.ai checkout: `/create`, `/webhook`, `/success`, `/status/{id}`, `/balance`, `/free-remaining`
- `api/routers/seo_pages.py` — SEO pages including `/compare` and `/en/compare`

## Key Patterns

### Ranking Algorithm
Edit `_rank_places()` in `meetspot_recommender.py`:
- Base: 30 points (rating x 6)
- Popularity: 20 points (log-scaled reviews)
- Distance: 25 points (500m = full score, decays)
- Scenario: 15 points (keyword match)
- Requirements: 10 points (parking/quiet/business)

### Distance Filtering
Two-stage distance handling in `meetspot_recommender.py`:
1. **POI Search**: Amap API `radius` parameter (hardcoded 5000m, fallback to 50000m) in `_search_places()` calls
2. **Post-filter**: `max_distance` parameter in `_rank_places()` (default 100km, in meters)

### Brand Knowledge Base
`BRAND_FEATURES` dict in `meetspot_recommender.py` contains 50+ brand profiles (Starbucks, Haidilao, etc.) with feature scores (0.0-1.0) for: quiet, WiFi, business, parking, child-friendly, 24h. Used in requirements matching - brands scoring >=0.7 satisfy the requirement. Place types prefixed with `_` (e.g., `_library`) provide defaults.

### Adding Address Mappings
**Preferred**: Edit `data/address_aliases.json` -- maps abbreviations to full names (e.g., "北大" -> "北京大学"). This file has `university_aliases` and `landmark_aliases` sections.

**For cross-city ambiguity**: Add to the `alias_to_fullname` dict inside `_enhance_address()` in `meetspot_recommender.py` with full city prefix (e.g., "华工" -> "广东省广州市华南理工大学"). These hardcoded aliases include city/district for geocoding precision.

### Adding Venue Themes
Add entry to `PLACE_TYPE_CONFIG` with: Chinese name, Boxicons icons, 6 color values.

### Sitemap lastmod
`seo_pages.py` sitemap 用静态 `CONTENT_DATES` 字典，不要用 `datetime.now()`。Google 会忽略不可靠的 lastmod 信号。内容实际更新时手动修改日期。

## Postmortem System

Automated regression prevention system that tracks historical fixes and warns when code changes might reintroduce past bugs.

### Structure
```
postmortem/
  PM-2025-001.yaml ... PM-2026-xxx.yaml  # Historical fix documentation
tools/
  postmortem_init.py     # Generate initial knowledge base from git history
  postmortem_check.py    # Check code changes against known patterns
  postmortem_generate.py # Generate postmortem for a single commit
```

### CI Integration
- `postmortem-check.yml`: Runs on PRs, warns if changes match known issue patterns
- `postmortem-update.yml`: Auto-generates postmortem when `fix:` commits merge to main

### Adding New Postmortems
When fixing a bug, the CI will auto-generate a postmortem. For manual creation:
```bash
python tools/postmortem_generate.py <commit-hash>
```

Each postmortem YAML contains triggers (file patterns, function names, regex, keywords) that enable multi-dimensional pattern matching.

## Debugging

| Issue | Solution |
|-------|----------|
| `未找到AMAP_API_KEY` | Set environment variable |
| Import errors in production | Check MinimalConfig fallback |
| Wrong city geocoding | Add to `_enhance_address()` alias dict with city prefix |
| SSR 页面 env var 读取为空 | 勿用 `templates.env.globals["key"] = os.getenv(...)`（模块导入时求值）；改用 `TemplateResponse` context 字典在每次请求时动态传入（见 `_common_context()` in `api/routers/seo_pages.py`） |
| Render OOM (512MB) | Heavy deps removed (jieba/tiktoken); caches reduced (30/15 limits); Agent mode disabled. If OOM recurs, check `pip list` for new heavy imports |
| asyncpg + pgbouncer errors | `app/db/database.py` disables prepared statement cache and uses dynamic statement names. If adding raw SQL, avoid named prepared statements |
| `meetspot_finder.html` 缺全局功能 | 独立静态页不继承 `base.html`，新增全局功能（GA4、schema、trackEvent）需单独在该文件处理 |
| flake8 E999 f-string 反斜杠 | Python 3.11 不允许 f-string 表达式含反斜杠（`\"`），需先提取为变量再插值 |
| `git push` 被 postmortem CI 自动 commit reject | push 前先 `git pull --rebase origin main` |

**Logging**: Uses loguru via `app/logger.py`. `/health` endpoint shows config status.

## Deployment

Hosted on Render free tier (512MB RAM, cold starts after 15min idle).
Service ID: `srv-d2di8295pdvs73eu3re0`. Render CLI installed (`brew install render`), workspace set.

**Redeploy**: Push to `main` branch triggers auto-deploy. For manual restart without code changes:
```bash
git commit --allow-empty -m "chore: trigger redeploy" && git push origin main
```

**Render CLI**: `render deploys list srv-d2di8295pdvs73eu3re0 --confirm -o json` to check deploy status. Environment variables managed via API (`PUT /v1/services/{id}/env-vars` -- WARNING: PUT is full replacement, always GET first and merge).

**Generated artifacts**: HTML files in `workspace/js_src/` are runtime-generated and should not be committed.

## CI/CD

9 GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR | Python 3.11 & 3.12 tests, flake8, Docker build |
| `ci-simple.yml` | Push/PR | Lightweight CI variant |
| `ci-clean.yml` | Push/PR | Clean CI variant |
| `postmortem-check.yml` | PRs | Warns if changes match known bug patterns |
| `postmortem-update.yml` | `fix:` commits to main | Auto-generates postmortem YAML |
| `keep-alive.yml` | Cron | Prevents Render free tier cold starts |
| `lighthouse-ci.yml` | On demand | Performance metrics |
| `update-badges.yml` | On demand | Update repo badges |
| `auto-merge-clean.yml` | Dependabot PRs | Auto-merge dependency updates |

## Gitignore Gotchas

The `.gitignore` has unusually broad patterns -- be aware:
- `tests/` directory and all test-like files (`*test*.py`, `test_*.py`) are gitignored. Tests exist locally only.
- `Dockerfile` and `docker-compose.yml` are gitignored.
- `workspace/js_src/` is gitignored (runtime-generated HTML).
