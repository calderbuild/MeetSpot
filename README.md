<div align="center">

# MeetSpot

<img src="docs/logo.jpg" alt="MeetSpot Logo" width="200"/>

### AI Agent for Multi-Person Meeting Point Recommendations

*Not just a search tool. An autonomous agent that decides the fairest meeting point for everyone.*

[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen?style=for-the-badge)](https://meetspot-irq2.onrender.com)
[![Video Demo](https://img.shields.io/badge/Bilibili-Demo-00A1D6?style=for-the-badge&logo=bilibili)](https://www.bilibili.com/video/BV1aUK7zNEvo/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Build Status](https://github.com/calderbuild/MeetSpot/actions/workflows/ci.yml/badge.svg)](https://github.com/calderbuild/MeetSpot/actions)
[![GitHub stars](https://img.shields.io/github/stars/calderbuild/MeetSpot?style=social)](https://github.com/calderbuild/MeetSpot)

**Qloo Agentic Hackathon 2026:** [group taste fairness](#group-taste-fairness-with-qloo) · [try the New York demo group](https://meetspot-irq2.onrender.com/public/meetspot_finder.html?lang=en)

**RevenueCat Shipaton 2026:** [demo video (1:48)](https://youtu.be/_y6peCnn-8w) · [Devpost](https://devpost.com/software/meetspot-for-macos) · [macOS app + RevenueCat](#macos-app--revenuecat)

[English](README.md) | [简体中文](README_ZH.md)

</div>

---

## Why MeetSpot?

Most location tools return results near *you*. MeetSpot calculates the **geographic center** of all participants and returns AI-ranked venues that minimize everyone's travel time.

| Traditional Tools | MeetSpot |
|-------------------|----------|
| Search near your location | Calculate fair center for all |
| Keyword-based ranking | AI-powered multi-factor scoring |
| Static results | Adaptive dual-mode routing |
| No reasoning | Explainable AI with chain-of-thought |

<div align="center">
<img src="docs/show1-en.png" alt="MeetSpot Interface" width="85%"/>
</div>

---

## What's New

| When | What | Context |
|------|------|---------|
| 2026-10 | **Group taste fairness**: each person lists what they like, Qloo scores the same venues once per person, and venues are ranked by the least-satisfied person ([details](#group-taste-fairness-with-qloo), PR #92) | Qloo Agentic Hackathon 2026 |
| 2026-10 | **macOS app + RevenueCat paywall**: Electron desktop build with a server-verified `meetspot_pro` entitlement, running against the RevenueCat Test Store ([details](#macos-app--revenuecat), PR #89, #90) | RevenueCat Shipaton 2026 (results on 2026-10-20) |
| 2026-09 | **Real commute-time fairness**: when users set a max commute per person, candidate centers are checked against real travel times from Google Routes and rejected if anyone goes over ([details](#real-commute-time-fairness), PR #84) | AI Builders Hackathon 2026 |

---

## Group Taste Fairness with Qloo

Picking a place for a group usually means somebody gets dragged somewhere they would never choose. MeetSpot already finds a fair *location* for everyone; since 2026-09-30 it also finds a fair *place*, using each person's own taste.

Each person lists a few things they love (artists, movies, shows, brands, books). MeetSpot resolves them to Qloo entities, has Qloo score the same set of nearby venues once **per person**, and ranks venues by the **least-satisfied person** (maximin over each person's percentile), not the group average. A venue that two people love and the third would hate is left out, and the page says who would have been unhappy and why.

```mermaid
flowchart LR
    A[Addresses + tastes per person] --> B[Qloo /search: resolve each taste]
    A --> C[Fair center + real commute check]
    B --> D[Qloo heatmap per person: min per cell]
    D --> C
    C --> E[Qloo insights: 30 candidate venues near the center]
    E --> F[Qloo insights per person on the same 30, with explainability]
    F --> G[Percentile per person, rank by the worst-off person]
    B --> H[Qloo analysis/compare: shared taste tags]
    G --> I[Results page + MeetSpot agent tool group_taste_rank]
    H --> I
```

**How Qloo is used**

| Qloo capability | What MeetSpot does with it |
|---|---|
| `/search` | Turns "Taylor Swift, Barbie" into entities and shows each person what their taste was recognized as |
| `/v2/insights` place + `filter.location` + venue tag | Candidate restaurants, cafes or bars around the fair center |
| `filter.results.entities` + `signal.interests.entities` | Scores the *same* candidates once per person, so people can be compared |
| `feature.explainability` | "Person 1 matches via Barbie": the reason comes from Qloo's data, not from an LLM |
| `filter.type=urn:heatmap` | One taste heatmap per person; the cell-wise minimum picks between commute-fair centers and shades the map |
| `/v2/analysis/compare` | "What you have in common" for the group |
| `filter.price_level.max` | Budget filter mapped from the existing price range field |

**What the agent does.** `MeetSpotAgent` (a ReAct agent over DeepSeek) gets a new tool, `group_taste_rank`. Given a group with tastes it geocodes everyone, computes the fair center, calls the tool, and explains its pick person by person using only what the tools returned. On the results page, **Ask the agent** runs it on the same group and shows each tool call it made.

**What changed for the hackathon** (all after 2026-09-30): the Qloo client (`app/tool/qloo_client.py`), per-person maximin ranking and taste heatmap in the recommender, the agent tool and English agent mode, per-person taste inputs with a New York demo group, the taste card / fit bars / left-out venues on the results page, and the Ask the agent card. Requests without tastes behave exactly as before.

**Try it:** open the [finder](https://meetspot-irq2.onrender.com/public/meetspot_finder.html?lang=en), click **Try a demo group in New York**, then **Find Fair Midpoint**. Taste searches are not counted against the free daily limit during judging.

---

## Real Commute-Time Fairness

A geometric midpoint can still be unfair: one person may have a direct train while another needs two transfers. On the international (Google Maps) path, each participant can set a **max commute** in minutes. MeetSpot then takes several candidate centers, asks Google Routes (`computeRouteMatrix`) for each person's real travel time to each one, and keeps the candidate that breaks no one's limit. If every candidate breaks some limit, it picks the one with the smallest total overage, and treats an unreachable leg as the worst case. The results page shows which candidates were accepted or rejected and why.

Requests without commute limits, and the Amap (China) path, behave exactly as before. Code: `app/tool/google_directions_client.py` and `_verify_commute_fairness` in `app/tool/meetspot_recommender.py`.

---

## Agent Architecture

MeetSpot is an **AI Agent** - it makes autonomous decisions based on request complexity, not just executes searches.

```
                              User Request
                                   │
                    ┌──────────────┴──────────────┐
                    │      Complexity Router      │
                    │    (Autonomous Decision)    │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    │                    ▼
    ┌─────────────────┐            │          ┌─────────────────┐
    │    Rule Mode    │            │          │   Agent Mode    │
    │  Rules + LLM    │            │          │   ReAct agent   │
    │  Deterministic  │            │          │  LLM-Enhanced   │
    └────────┬────────┘            │          └────────┬────────┘
             │                     │                   │
             └─────────────────────┼───────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │    5-Step Processing        │
                    │        Pipeline             │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────┬──────────┬────┴────┬──────────┬──────────┐
        │          │          │         │          │          │
        ▼          ▼          ▼         ▼          ▼          ▼
    Geocode    Center     POI      Ranking     HTML      Result
              Calc      Search               Gen
```

### Intelligent Mode Selection

The Agent autonomously decides which processing mode to use:

| Factor | Score |
|--------|-------|
| Locations | 3 locations +15, 4 or more +30 |
| Venue types in `keywords` | 2 types +12, 3 or more +25 |
| Special requirements | 2 matched +15, 3 or more +25, or +20 for a long free-text description (over 50 characters) |
| Filters | +5 each for `min_rating`, `max_distance` under 10 km, `price_range` |

- **Score < 40**: Rule Mode (deterministic rules, faster)
- **Score >= 40**: Agent Mode (LLM reasoning, semantic understanding). If the agent times out or errors, the request falls back to Rule Mode.

The scoring lives in `assess_request_complexity` in `api/index.py`.

### Agent Mode Scoring

```
Final Score = Rule Score × 0.4 + LLM Score × 0.6
```

The LLM analyzes semantic fit between venues and requirements, then blends with rule-based scoring. Results include **Explainable AI** visualization showing the agent's reasoning process.

### 5-Step Pipeline

| Step | Function | Details |
|------|----------|---------|
| **Geocode** | Address → Coordinates | 60+ smart mappings (universities, landmarks) |
| **Center Calc** | Fair point calculation | Spherical geometry for accuracy |
| **POI Search** | Venue discovery | Concurrent async search, auto-fallback |
| **Ranking** | Multi-factor scoring | Base(30) + Popularity(20) + Distance(25) + Scenario(15) + Requirements(10) |
| **HTML Gen** | Interactive map | Amap JS API (China) or Google Maps JS API (international) |

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/calderbuild/MeetSpot.git && cd MeetSpot
pip install -r requirements.txt

# Configure (get key from https://lbs.amap.com/)
cp config/config.toml.example config/config.toml
# Edit config.toml and add your AMAP_API_KEY

# Run
python web_server.py
```

Open http://127.0.0.1:8000

---

## macOS App + RevenueCat

MeetSpot has a macOS desktop build (Electron, in `desktop/`) built for RevenueCat Shipaton 2026. The free tier is one search a day; a **MeetSpot Pro** entitlement through RevenueCat removes that limit.

Status: the purchase flow works end to end against the **RevenueCat Test Store** only. The app is not on any store and does not take real payments yet; you run it from source.

<div align="center">
<img src="docs/shipaton/macos-app.jpg" alt="MeetSpot running as a macOS app" width="52%"/>
<img src="docs/shipaton/commute-check.png" alt="Real commute-time fairness check" width="16%"/>
<img src="docs/shipaton/paywall.jpg" alt="RevenueCat paywall in the macOS app" width="28%"/>
</div>

How the purchase flow works:

1. The app keeps an anonymous RevenueCat app user id in localStorage and sends it as `X-RC-App-User-Id` with every search.
2. When the free search is used up, the server answers `need_payment`. The app then loads [`@revenuecat/purchases-js`](https://www.npmjs.com/package/@revenuecat/purchases-js) and calls `presentPaywall()` for the current offering.
3. After the purchase, the app reruns the search. The server never trusts the client: it calls RevenueCat REST `GET /v1/subscribers/{id}` with the secret key and skips the quota only when the `meetspot_pro` entitlement is active (`app/payment/revenuecat.py`). If that lookup fails, the request falls back to the normal quota and is never granted.
4. On launch the app calls `getCustomerInfo()`. An active `meetspot_pro` shows a **MeetSpot Pro** badge; otherwise a **Go Pro** button opens the same paywall. The badge is display only, and the server still decides on every search.

```mermaid
sequenceDiagram
    participant App as macOS app (Electron)
    participant API as MeetSpot server (FastAPI)
    participant RC as RevenueCat
    App->>API: POST /api/find_meetspot + X-RC-App-User-Id
    API->>RC: GET /v1/subscribers/{id} (secret key)
    RC-->>API: entitlements
    alt meetspot_pro active
        API-->>App: results, no quota
    else not active or lookup failed
        API-->>App: need_payment once the free search is used
        App->>RC: presentPaywall(), Test Store purchase
        App->>API: rerun the search
    end
```

| File | What it does |
|------|--------------|
| `desktop/main.js`, `desktop/preload.js` | Electron shell; the preload sets `window.MEETSPOT_PLATFORM = "macos"` |
| `public/meetspot_finder.html` | App user id, Web SDK paywall, automatic retry, Pro badge |
| `app/payment/revenuecat.py` | Server-side entitlement check; any failure falls back to the free limit |
| `api/index.py` | Quota gate in `find_meetspot`, `/api/config/revenuecat` |
| `tests/test_revenuecat.py` | 12 tests against a mocked RevenueCat |

Run it locally:

```bash
# 1. Server (needs AMAP_API_KEY / GOOGLE_MAPS_API_KEY + LLM key as in Quick Start)
export REVENUECAT_PUBLIC_KEY=test_xxx      # Test Store public API key
export REVENUECAT_SECRET_KEY=sk_xxx        # v1 secret API key (server only)
uvicorn api.index:app

# 2. Desktop app (second terminal)
cd desktop && npm install && npm start

# Or build MeetSpot.app with its icon (ad-hoc signed, written to desktop/dist/)
cd desktop && npm run package
```

RevenueCat setup: create a project (it comes with a Test Store), an entitlement `meetspot_pro`, a Test Store product attached to it (a one-time purchase, since Test Store subscriptions expire after about 25 minutes), add it to the default offering, and configure a paywall on that offering.

To make a test purchase, run one search (free), then run a second one. The paywall appears. Pick the product and choose the successful-purchase option in the Test Store dialog. The search reruns and goes through, and the customer shows `meetspot_pro` active in the RevenueCat dashboard.

Known limitation: the app user id is anonymous and device-local. Anyone who learns that id could reuse its entitlement. The production fix is to tie the id to a MeetSpot account (`app/auth`). Without the header or the RevenueCat keys, MeetSpot behaves exactly as before, and the web build keeps its existing payment flow.

---

## Free Tier and Pricing

The live web app gives each visitor (tracked by IP) one free search a day. After that, searches use credits bought through the existing web payment flow (302.ai checkout, `api/routers/payment.py`). Self-hosted instances have no limit unless you configure one (`FREE_DAILY_LIMIT`).

---

## API Reference

### Main Endpoint

`POST /api/find_meetspot`

```json
{
  "locations": ["Peking University", "Tsinghua University", "Renmin University"],
  "keywords": "cafe restaurant",
  "user_requirements": "parking, quiet environment"
}
```

Optional `tastes` (one string per location, English path only) turns on Qloo group taste ranking:

```json
{
  "locations": ["Times Square, New York", "Union Square, New York", "Grand Central Terminal, New York"],
  "keywords": "restaurant",
  "tastes": ["Taylor Swift, Barbie", "Metallica, John Wick", "Bad Bunny, Trader Joe's"],
  "language": "en"
}
```

**Response:**
```json
{
  "success": true,
  "html_url": "/workspace/js_src/place_recommendation_20260929153459_1f2dace8.html",
  "locations_count": 2,
  "processing_time": 5.2,
  "mode": "rule_llm",
  "message": "Recommendation generated successfully"
}
```

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/find_meetspot_agent` | POST | Force Agent Mode (LLM reasoning); with `tastes` it calls Qloo through `group_taste_rank` and returns `taste_ranking` + `tool_trace` |
| `/api/ai_chat` | POST | AI customer service chat |
| `/health` | GET | System health check |
| `/docs` | GET | Interactive API documentation |

---

## Screenshots

<table>
<tr>
<td width="50%"><img src="docs/agent-thinking-en.png" alt="Agent Reasoning"/><p align="center"><b>Agent Chain-of-Thought</b></p></td>
<td width="50%"><img src="docs/result-map-en.png" alt="Interactive Map"/><p align="center"><b>Interactive Map View</b></p></td>
</tr>
<tr>
<td width="50%"><img src="docs/homepage-en.png" alt="Homepage"/><p align="center"><b>Homepage</b></p></td>
<td width="50%"><img src="docs/finder-input-en.png" alt="Input Interface"/><p align="center"><b>Meeting Point Finder</b></p></td>
</tr>
</table>

<details>
<summary><b>More Screenshots</b></summary>

<table>
<tr>
<td width="60%" align="center"><img src="docs/result-summary-en.png" alt="Full Results Page"/><p align="center"><b>Full Results Page (NYC example)</b></p></td>
<td width="40%" align="center"><img src="docs/ai-chat-en.png" alt="AI Chat"/><p align="center"><b>AI Assistant Chat</b></p></td>
</tr>
</table>

</details>

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | FastAPI, Pydantic, aiohttp, SQLAlchemy 2.0, asyncio |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript, Boxicons |
| **Maps** | Amap (Gaode) for China + Google Maps Platform for international (auto-routed by language) |
| **AI** | DeepSeek (default `deepseek-flash`) via OpenAI-compatible API |
| **Deploy** | Docker (the live demo runs on Render) |

### Docker Quick Start

1. Copy the environment template and fill in your keys: `cp .env.example .env`
2. Build and run: `docker build -t meetspot . && docker run --env-file .env -p 8000:8000 meetspot`
3. Open http://localhost:8000 and check http://localhost:8000/health

---

## Project Structure

```
MeetSpot/
├── api/
│   └── index.py                 # FastAPI application entry
├── app/
│   ├── tool/
│   │   └── meetspot_recommender.py  # Core recommendation engine
│   ├── config.py                # Configuration management
│   └── design_tokens.py         # WCAG-compliant color system
├── templates/                   # Jinja2 templates
├── public/                      # Static assets
└── workspace/js_src/            # Generated result pages
```

---

## Development

```bash
# Development server with hot reload
uvicorn api.index:app --reload

# Run tests
pytest tests/ -v

# Code quality (same checks as CI)
ruff check . && flake8 . --select=E9,F63,F7,F82
```

---

## Contributing

Contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Contact

<table>
<tr>
<td>

**Email:** johnrobertdestiny@gmail.com

**GitHub:** [Issues](https://github.com/calderbuild/MeetSpot/issues)

**Blog:** [calderbuild.github.io](https://calderbuild.github.io/)

</td>
<td align="center">

<img src="public/docs/vx_chat.png" alt="WeChat" width="150"/>

**Personal WeChat**

</td>
<td align="center">

<img src="public/docs/vx_group.png" alt="WeChat Group" width="150"/>

**WeChat Group**

</td>
</tr>
</table>

---

## Acknowledgements

Special thanks to [AIGC Link](https://xhslink.com/m/80ngts127cA) for the promotions on XiaoHongShu.

---

## Roadmap

- Tie the RevenueCat app user id to a MeetSpot account so a Pro entitlement cannot be reused from another device
- Enterprise meeting planning mode (team offsites, external meetings with special requirements)
- A benchmark suite for recommendation quality

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**If MeetSpot helps you, please give it a star!**

[![Star History Chart](https://api.star-history.com/svg?repos=calderbuild/MeetSpot&type=Date)](https://star-history.com/#calderbuild/MeetSpot&Date)

</div>
