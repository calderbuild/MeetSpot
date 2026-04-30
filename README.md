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
<img src="docs/show1.jpg" alt="MeetSpot Interface" width="85%"/>
</div>

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
    │   (2-4 sec)     │            │          │   (8-15 sec)    │
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

| Factor | Score | Example |
|--------|-------|---------|
| Location count | +10/location | 4 locations = 40 pts |
| Complex keywords | +15 | "quiet business cafe with private rooms" |
| Special requirements | +10 | "parking, wheelchair accessible, WiFi" |

- **Score < 40**: Rule Mode (fast, deterministic, pattern-matched)
- **Score >= 40**: Agent Mode (LLM reasoning, semantic understanding)

### Agent Mode Scoring

```
Final Score = Rule Score × 0.4 + LLM Score × 0.6
```

The LLM analyzes semantic fit between venues and requirements, then blends with rule-based scoring. Results include **Explainable AI** visualization showing the agent's reasoning process.

### 5-Step Pipeline

| Step | Function | Details |
|------|----------|---------|
| **Geocode** | Address → Coordinates | 90+ smart mappings (universities, landmarks) |
| **Center Calc** | Fair point calculation | Spherical geometry for accuracy |
| **POI Search** | Venue discovery | Concurrent async search, auto-fallback |
| **Ranking** | Multi-factor scoring | Base(30) + Popularity(20) + Distance(25) + Scenario(15) + Requirements(10) |
| **HTML Gen** | Interactive map | Amap JS API integration |

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

**Response:**
```json
{
  "success": true,
  "html_url": "/workspace/js_src/recommendation_xxx.html",
  "center": {"lat": 39.99, "lng": 116.32},
  "venues_count": 8
}
```

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/find_meetspot_agent` | POST | Force Agent Mode (LLM reasoning) |
| `/api/ai_chat` | POST | AI customer service chat |
| `/health` | GET | System health check |
| `/docs` | GET | Interactive API documentation |

---

## Screenshots

<table>
<tr>
<td width="50%"><img src="docs/agent-thinking.jpg" alt="Agent Reasoning"/><p align="center"><b>Agent Chain-of-Thought</b></p></td>
<td width="50%"><img src="docs/result-map.jpg" alt="Interactive Map"/><p align="center"><b>Interactive Map View</b></p></td>
</tr>
<tr>
<td width="50%"><img src="docs/多维度智能评分show4.jpg" alt="AI Scoring"/><p align="center"><b>Multi-Factor AI Scoring</b></p></td>
<td width="50%"><img src="docs/show5推荐地点.jpg" alt="Venue Cards"/><p align="center"><b>Venue Recommendation Cards</b></p></td>
</tr>
</table>

<details>
<summary><b>More Screenshots</b></summary>

<table>
<tr>
<td width="50%"><img src="docs/homepage.jpg" alt="Homepage"/><p align="center"><b>Homepage</b></p></td>
<td width="50%"><img src="docs/finder-input.jpg" alt="Input Interface"/><p align="center"><b>Meeting Point Finder</b></p></td>
</tr>
<tr>
<td width="50%"><img src="docs/result-summary.jpg" alt="Results"/><p align="center"><b>Results Summary</b></p></td>
<td width="50%"><img src="docs/AI客服.jpg" alt="AI Chat"/><p align="center"><b>AI Customer Service</b></p></td>
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
| **AI** | OpenRouter (default `openai/gpt-4o-mini`) for semantic analysis |
| **Deploy** | Render, Railway, Docker, Vercel |

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

# Code quality
black . && ruff check . && mypy app/
```

---

## Contributing

Contributions are welcome! Please:

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

**Email:** Johnrobertdestiny@gmail.com

**GitHub:** [Issues](https://github.com/calderbuild/MeetSpot/issues)

**Blog:** [jasonrobert.me](https://jasonrobert.me/)

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

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**If MeetSpot helps you, please give it a star!**

[![Star History Chart](https://api.star-history.com/svg?repos=calderbuild/MeetSpot&type=Date)](https://star-history.com/#calderbuild/MeetSpot&Date)

</div>
