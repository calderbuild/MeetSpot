# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MeetSpot is an **AI Agent** for multi-person meeting point recommendations. Users provide locations and requirements; the Agent calculates the geographic center and recommends optimal venues. Built with FastAPI and Python 3.11+, uses Amap (Gaode Map) API for geocoding/POI search, and DeepSeek/GPT-4o-mini for semantic scoring.

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
- There are no Cursor/Copilot rule files in this repo (no `.cursorrules`, no `.cursor/rules/`, no `.github/copilot-instructions.md`).

## Environment Setup

**Conda**: `conda env create -f environment.yml && conda activate meetspot` (env name is `meetspot`, not `meetspot-dev`)
**Pip**: `python3.11 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

**Required Environment Variables**:
- `AMAP_API_KEY` - Gaode Map API key (required)
- `AMAP_SECURITY_JS_CODE` - JS security code for frontend map
- `LLM_API_KEY` - DeepSeek/OpenAI API key (for AI chat and LLM scoring)
- `LLM_API_BASE` - API base URL (default: `https://newapi.deepwisdom.ai/v1`)
- `LLM_MODEL` - Model name (default: `deepseek-chat`)

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

Complexity scoring: +10/location, +15 for complex keywords, +10 for special requirements. Currently all requests use Rule+LLM mode since Agent mode is disabled (`agent_available = False` in `api/index.py`).

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
api/routers/seo_pages.py            # SEO landing pages
```

### Frontend Address Input

`public/meetspot_finder.html` uses AMap Autocomplete API for real-time address suggestions. When users select from dropdown, coordinates are pre-resolved client-side, bypassing backend geocoding. Falls back to backend geocoding when manual text is entered.

### LLM Scoring (Agent Mode)

When Agent Mode is enabled, final venue scores blend rule-based and LLM semantic analysis:
```
Final Score = Rule Score * 0.4 + LLM Score * 0.6
```
Agent Mode is currently disabled (`agent_available = False`) to conserve memory on free hosting tiers.

### Optional Components

Database layer (`app/db/`, `app/models/`) is optional - core recommendation works without it. Used for auth/social features with SQLite + aiosqlite.

Experimental agent endpoint (`/api/find_meetspot_agent`) requires OpenManus framework - **not production-ready**.

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
| Empty POI results | Fallback mechanism handles this automatically |
| Render OOM (512MB) | Caches are reduced (30/15 limits); Agent mode disabled |
| Render service down | Trigger redeploy: `git commit --allow-empty -m "trigger redeploy" && git push` |

**Logging**: Uses loguru via `app/logger.py`. `/health` endpoint shows config status.

## Deployment

Hosted on Render free tier (512MB RAM, cold starts after 15min idle).

**Redeploy**: Push to `main` branch triggers auto-deploy. For manual restart without code changes:
```bash
git commit --allow-empty -m "chore: trigger redeploy" && git push origin main
```

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

## Code Style

- Python: 4-space indent, type hints, `snake_case` functions, `PascalCase` classes, `SCREAMING_SNAKE_CASE` constants. Keep functions under ~50 lines; prefer dataclasses for structured payloads.
- Logging: Use structured messages via `app/logger.py` (loguru): `logger.info("geo_center_calculated", extra={...})`
- CSS: BEM-like (`meetspot-header__title`), colors from `design_tokens.py`
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`) with small scopes (e.g., `feat(tokens): add WCAG palette`)

## Gitignore Gotchas

The `.gitignore` has unusually broad patterns -- be aware:
- `tests/` directory and all test-like files (`*test*.py`, `test_*.py`) are gitignored. Tests exist locally only.
- `Dockerfile` and `docker-compose.yml` are gitignored.
- `workspace/js_src/` is gitignored (runtime-generated HTML).
