<div align="center">

# MeetSpot 聚点

<img src="docs/logo.jpg" alt="MeetSpot Logo" width="200"/>

### 多人会面地点智能推荐 AI Agent

*不是搜索工具，而是能自主决策的智能体，为每个人找到最公平的会面点。*

[![在线体验](https://img.shields.io/badge/在线-体验-brightgreen?style=for-the-badge)](https://meetspot-irq2.onrender.com)
[![演示视频](https://img.shields.io/badge/Bilibili-演示-00A1D6?style=for-the-badge&logo=bilibili)](https://www.bilibili.com/video/BV1aUK7zNEvo/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Build Status](https://github.com/calderbuild/MeetSpot/actions/workflows/ci.yml/badge.svg)](https://github.com/calderbuild/MeetSpot/actions)
[![GitHub stars](https://img.shields.io/github/stars/calderbuild/MeetSpot?style=social)](https://github.com/calderbuild/MeetSpot)

**Qloo Agentic Hackathon 2026：** [群体口味公平](#群体口味公平qloo) · [纽约示例组在线体验](https://meetspot-irq2.onrender.com/public/meetspot_finder.html?lang=en)

**RevenueCat Shipaton 2026：** [演示视频（1:48）](https://youtu.be/_y6peCnn-8w) · [Devpost](https://devpost.com/software/meetspot-for-macos) · [macOS 应用与 RevenueCat](#macos-应用与-revenuecat)

[English](README.md) | 简体中文

</div>

---

## 为什么选择 MeetSpot?

传统地图工具搜索的是**你附近**的地点。MeetSpot 计算所有参与者的**地理中心点**，用 AI 智能排序推荐场所，让每个人的出行时间都最小化。

| 传统工具 | MeetSpot |
|----------|----------|
| 搜索你附近的地点 | 计算所有人的公平中心点 |
| 关键词匹配排序 | AI 多因素智能评分 |
| 静态搜索结果 | 双模式自适应路由 |
| 无法解释推荐理由 | 可解释 AI，展示思维链 |

<div align="center">
<img src="docs/show1.jpg" alt="MeetSpot 界面" width="85%"/>
</div>

---

## 最近更新

| 时间 | 内容 | 背景 |
|------|------|------|
| 2026-10 | **群体口味公平**：每个人填写自己喜欢的东西，Qloo 对同一批场所逐人打分，按最不满意的那个人排序（[详情](#群体口味公平qloo)，PR #92） | Qloo Agentic Hackathon 2026 |
| 2026-10 | **macOS 应用与 RevenueCat 付费墙**：Electron 桌面版，`meetspot_pro` 权益由服务端校验，目前跑在 RevenueCat 测试商店（[详情](#macos-应用与-revenuecat)，PR #89、#90） | RevenueCat Shipaton 2026（10 月 20 日公布结果） |
| 2026-09 | **真实通勤时间校验**：用户给每个人设定通勤上限后，用 Google Routes 的真实通勤时间检查候选中心点，有人超时就换下一个（[详情](#真实通勤时间校验)，PR #84） | AI Builders Hackathon 2026 |

---

## 群体口味公平（Qloo）

多人选地方，常常有人被拖去自己绝不会选的店。MeetSpot 原本解决的是位置公平，从 2026-09-30 起也按每个人的口味解决场所公平。

每个人列几样喜欢的东西（歌手、电影、剧、品牌、书）。MeetSpot 把它们解析成 Qloo 实体，让 Qloo 对中心点附近的同一批场所**逐人**打分，再按**最不满意的那个人**排序（对每个人的百分位取 maximin），而不是取平均。两个人喜欢、第三个人讨厌的场所会被排除，页面会说明谁会不满意、为什么。理由来自 Qloo 的数据，不是 LLM 编的。

`MeetSpotAgent`（基于 DeepSeek 的 ReAct Agent）新增了 `group_taste_rank` 工具；结果页的 **Ask the agent** 会用同一组输入跑一遍 Agent，并展示每次工具调用。这个功能目前只在英文（Google Maps）路径上提供，不带口味的请求行为不变。完整说明见 [英文 README](README.md#group-taste-fairness-with-qloo)。

---

## 真实通勤时间校验

几何中点也可能不公平：一个人有直达地铁，另一个人要换乘两次。在国际版（Google Maps）路径上，每个参与者可以设定以分钟计的**最长通勤时间**。MeetSpot 会取几个候选中心点，用 Google Routes（`computeRouteMatrix`）查每个人到每个候选点的真实通勤时间，留下不让任何人超时的那个；如果每个候选点都有人超时，就选总超时最少的，查不到路线的按最坏情况算。结果页会显示哪些候选点被接受、哪些被拒绝以及原因。

不设通勤上限的请求、以及高德（国内）路径，行为不变。代码见 `app/tool/google_directions_client.py` 和 `app/tool/meetspot_recommender.py` 里的 `_verify_commute_fairness`。

---

## Agent 架构

MeetSpot 是一个 **AI Agent**：它根据请求复杂度自主决策处理方式，而不仅仅是执行搜索。

```
                              用户请求
                                 │
                  ┌──────────────┴──────────────┐
                  │        复杂度路由器          │
                  │       (自主决策引擎)         │
                  └──────────────┬──────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
            ▼                    │                    ▼
  ┌─────────────────┐            │          ┌─────────────────┐
  │    规则模式      │            │          │   Agent 模式    │
  │  规则 + LLM     │            │          │   ReAct Agent   │
  │   确定性处理     │            │          │   LLM 增强      │
  └────────┬────────┘            │          └────────┬────────┘
           │                     │                   │
           └─────────────────────┼───────────────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  │       5 步处理流水线          │
                  └──────────────┬──────────────┘
                                 │
      ┌──────────┬──────────┬────┴────┬──────────┬──────────┐
      │          │          │         │          │          │
      ▼          ▼          ▼         ▼          ▼          ▼
   地理编码    中心计算    POI搜索   智能排序   HTML生成    结果
```

### 智能模式选择

Agent 自主决定使用哪种处理模式：

| 因素 | 分值 |
|------|------|
| 地点数量 | 3 个 +15，4 个及以上 +30 |
| 场所类型（`keywords`） | 2 种 +12，3 种及以上 +25 |
| 特殊需求 | 命中 2 个 +15，3 个及以上 +25；或自由描述超过 50 字 +20 |
| 筛选条件 | `min_rating`、10 公里以内的 `max_distance`、`price_range` 各 +5 |

- **评分 < 40**：规则模式（确定性规则，更快）
- **评分 >= 40**：Agent 模式（LLM 推理、语义理解）；Agent 超时或出错时自动回退到规则模式

打分逻辑在 `api/index.py` 的 `assess_request_complexity`。

### Agent 模式评分

```
最终得分 = 规则得分 × 0.4 + LLM 得分 × 0.6
```

LLM 分析场所与需求的语义匹配度，再与规则评分融合。结果页面包含**可解释 AI** 可视化，展示 Agent 的推理过程。

### 5 步处理流水线

| 步骤 | 功能 | 详情 |
|------|------|------|
| **地理编码** | 地址 → 坐标 | 60+ 智能映射（大学简称、城市地标） |
| **中心计算** | 公平点计算 | 球面几何保证精确性 |
| **POI 搜索** | 场所发现 | 并发异步搜索，自动降级 |
| **智能排序** | 多因素评分 | 基础分(30) + 热度分(20) + 距离分(25) + 场景匹配(15) + 需求匹配(10) |
| **HTML 生成** | 交互式地图 | 高德 JS API（国内）或 Google Maps JS API（国际） |

---

## 快速开始

```bash
# 克隆并安装
git clone https://github.com/calderbuild/MeetSpot.git && cd MeetSpot
pip install -r requirements.txt

# 配置（从 https://lbs.amap.com/ 获取密钥）
cp config/config.toml.example config/config.toml
# 编辑 config.toml，填入你的 AMAP_API_KEY

# 运行
python web_server.py
```

浏览器访问 http://127.0.0.1:8000

---

## macOS 应用与 RevenueCat

MeetSpot 有一个为 RevenueCat Shipaton 2026 做的 macOS 桌面版（Electron，在 `desktop/` 目录）。免费额度是每天一次搜索，**MeetSpot Pro** 权益可以解除限制。服务端不信任客户端：每次搜索都用密钥调用 RevenueCat `GET /v1/subscribers/{id}` 校验 `meetspot_pro`，校验失败就按免费额度处理（`app/payment/revenuecat.py`）。

现状：购买流程只在 **RevenueCat 测试商店（Test Store）** 里完整跑通，应用没有上架任何商店，也还不收真钱，需要从源码运行。本地运行步骤见 [英文 README](README.md#macos-app--revenuecat)。

---

## 免费额度与收费

线上网页版每位访客（按 IP 计）每天可免费搜索一次，之后通过网页支付流程（302.ai 收银台，`api/routers/payment.py`）购买次数。自己部署的实例默认不限次数，除非配置 `FREE_DAILY_LIMIT`。

---

## API 接口

### 主接口

`POST /api/find_meetspot`

```json
{
  "locations": ["北京大学", "清华大学", "中国人民大学"],
  "keywords": "咖啡馆 餐厅",
  "user_requirements": "停车方便，环境安静"
}
```

**响应：**
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

### 其他接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/find_meetspot_agent` | POST | 强制使用 Agent 模式（LLM 推理）；带 `tastes` 时通过 `group_taste_rank` 调用 Qloo，返回 `taste_ranking` 和 `tool_trace` |
| `/api/ai_chat` | POST | AI 智能客服对话 |
| `/health` | GET | 系统健康检查 |
| `/docs` | GET | 交互式 API 文档 |

---

## 产品截图

<table>
<tr>
<td width="50%"><img src="docs/agent-thinking.jpg" alt="Agent 推理"/><p align="center"><b>Agent 思维链展示</b></p></td>
<td width="50%"><img src="docs/result-map.jpg" alt="交互式地图"/><p align="center"><b>交互式地图视图</b></p></td>
</tr>
<tr>
<td width="50%"><img src="docs/多维度智能评分show4.jpg" alt="AI 评分"/><p align="center"><b>多维度 AI 评分</b></p></td>
<td width="50%"><img src="docs/show5推荐地点.jpg" alt="场所卡片"/><p align="center"><b>场所推荐卡片</b></p></td>
</tr>
</table>

<details>
<summary><b>更多截图</b></summary>

<table>
<tr>
<td width="50%"><img src="docs/homepage.jpg" alt="首页"/><p align="center"><b>首页</b></p></td>
<td width="50%"><img src="docs/finder-input.jpg" alt="输入界面"/><p align="center"><b>会面点查找</b></p></td>
</tr>
<tr>
<td width="50%"><img src="docs/result-summary.jpg" alt="结果"/><p align="center"><b>推荐结果汇总</b></p></td>
<td width="50%"><img src="docs/AI客服.jpg" alt="AI 客服"/><p align="center"><b>AI 智能客服</b></p></td>
</tr>
</table>

</details>

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI, Pydantic, aiohttp, SQLAlchemy 2.0, asyncio |
| **前端** | HTML5, CSS3, 原生 JavaScript, Boxicons |
| **地图** | 高德地图（国内）+ Google Maps Platform（国际），按语言自动切换 |
| **AI** | DeepSeek（默认 `deepseek-flash`，OpenAI 兼容接口）语义分析 |
| **部署** | Docker（在线 Demo 部署在 Render） |

### Docker 快速开始

1. 复制环境变量模板并填入 key：`cp .env.example .env`
2. 构建并启动：`docker build -t meetspot . && docker run --env-file .env -p 8000:8000 meetspot`
3. 打开 http://localhost:8000，健康检查地址 http://localhost:8000/health

---

## 项目结构

```
MeetSpot/
├── api/
│   └── index.py                 # FastAPI 应用入口
├── app/
│   ├── tool/
│   │   └── meetspot_recommender.py  # 核心推荐引擎
│   ├── config.py                # 配置管理
│   └── design_tokens.py         # WCAG 无障碍配色系统
├── templates/                   # Jinja2 模板
├── public/                      # 静态资源
└── workspace/js_src/            # 生成的结果页面
```

---

## 开发

```bash
# 开发服务器（热重载）
uvicorn api.index:app --reload

# 运行测试
pytest tests/ -v

# 代码质量检查（与 CI 一致）
ruff check . && flake8 . --select=E9,F63,F7,F82
```

---

## 参与贡献

欢迎贡献代码！步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

---

## 联系方式

<table>
<tr>
<td>

**邮箱：** johnrobertdestiny@gmail.com

**GitHub：** [Issues](https://github.com/calderbuild/MeetSpot/issues)

**博客：** [calderbuild.github.io](https://calderbuild.github.io/)

</td>
<td align="center">

<img src="public/docs/vx_chat.png" alt="微信" width="150"/>

**个人微信**

</td>
<td align="center">

<img src="public/docs/vx_group.png" alt="微信交流群" width="150"/>

**微信交流群**

</td>
</tr>
</table>

---

## 致谢

特别感谢 [AIGC Link](https://xhslink.com/m/80ngts127cA) 在小红书的推广支持。

---

## 路线图

- 把 RevenueCat 的 app user id 绑定到 MeetSpot 账号，防止 Pro 权益被别的设备复用
- 企业会议规划模式（团建、带特殊需求的外部会议）
- 推荐质量评测基准

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

<div align="center">

**觉得有用？请给个 Star 支持一下！**

[![Star History Chart](https://api.star-history.com/svg?repos=calderbuild/MeetSpot&type=Date)](https://star-history.com/#calderbuild/MeetSpot&Date)

</div>
