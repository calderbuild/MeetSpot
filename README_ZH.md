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

## Agent 架构

MeetSpot 是一个 **AI Agent**——它根据请求复杂度自主决策处理方式，而不仅仅是执行搜索。

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
  │   (2-4 秒)      │            │          │   (8-15 秒)     │
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

| 因素 | 分值 | 示例 |
|------|------|------|
| 地点数量 | +10/个 | 4 个地点 = 40 分 |
| 复杂关键词 | +15 | "安静的商务咖啡馆，有包间" |
| 特殊需求 | +10 | "停车方便、无障碍设施、有 WiFi" |

- **评分 < 40**：规则模式（快速、确定性、模式匹配）
- **评分 >= 40**：Agent 模式（LLM 推理、语义理解）

### Agent 模式评分

```
最终得分 = 规则得分 × 0.4 + LLM 得分 × 0.6
```

LLM 分析场所与需求的语义匹配度，再与规则评分融合。结果页面包含**可解释 AI** 可视化，展示 Agent 的推理过程。

### 5 步处理流水线

| 步骤 | 功能 | 详情 |
|------|------|------|
| **地理编码** | 地址 → 坐标 | 90+ 智能映射（大学简称、城市地标） |
| **中心计算** | 公平点计算 | 球面几何保证精确性 |
| **POI 搜索** | 场所发现 | 并发异步搜索，自动降级 |
| **智能排序** | 多因素评分 | 基础分(30) + 热度分(20) + 距离分(25) + 场景匹配(15) + 需求匹配(10) |
| **HTML 生成** | 交互式地图 | 集成高德 JS API |

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
  "html_url": "/workspace/js_src/recommendation_xxx.html",
  "center": {"lat": 39.99, "lng": 116.32},
  "venues_count": 8
}
```

### 其他接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/find_meetspot_agent` | POST | 强制使用 Agent 模式（LLM 推理） |
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
| **地图** | 高德地图 - 地理编码、POI 搜索、JS API |
| **AI** | DeepSeek / GPT-4o-mini 语义分析 |
| **部署** | Render, Railway, Docker, Vercel |

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

# 代码质量检查
black . && ruff check . && mypy app/
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

**邮箱：** Johnrobertdestiny@gmail.com

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

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

<div align="center">

**觉得有用？请给个 Star 支持一下！**

[![Star History Chart](https://api.star-history.com/svg?repos=calderbuild/MeetSpot&type=Date)](https://star-history.com/#calderbuild/MeetSpot&Date)

</div>
