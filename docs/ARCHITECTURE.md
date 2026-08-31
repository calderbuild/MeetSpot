# MeetSpot 架构说明

版本：v2.1（2026-08-25）

## 1. 项目概述

MeetSpot 是一个多人会面地点公平决策 Agent。用户输入多方位置与需求，系统完成地址解析、公平中心计算、POI 检索、多因子评分与可解释推荐，输出带地图、评分依据和推理链的结果页。

参赛定位：GOAI 2026 无界应用赛道，本地生活服务的多人线下协作决策细分场景。

## 2. 总体架构

系统按入口、编排、核心引擎、Agent、LLM、数据、前端七层组织：

```text
浏览器 / 外部调用
   |
   v
web_server.py（启动入口，加载 .env）
   |
   v
api/index.py（FastAPI 应用、路由、复杂度路由、配额、静态挂载）
   |-- api/routers/auth.py        手机验证码登录
   |-- api/routers/payment.py     302 支付与免费额度
   |-- api/routers/seo_pages.py   SEO 页面
   |
   v
app/tool/meetspot_recommender.py（CafeRecommender，五步流水线）
app/agent/（ReAct Agent 与四工具）
app/llm.py（OpenAI 兼容客户端，默认 DeepSeek）
app/config.py（config.toml + 环境变量）
app/db/（用户、支付、消息、房间模型）
data/cities.json（50 个精选城市）
public/ templates/ static/（前端页面与资源）
workspace/js_src/（生成式结果页，不提交仓库）
```

## 3. 核心请求流程

### 3.1 自动路由（POST /api/find_meetspot）

1. 语言检测：URL 前缀、Cookie、Accept-Language
2. 免费额度检查：`FREE_DAILY_LIMIT > 0` 时按 IP 查询当日使用次数，超限返回 need_payment
3. 复杂度评估：地点数量、场所类型数量、需求关键词、筛选条件加权计分，上限 100
4. 路由决策：分数不低于 40 且 Agent 模块可用时进入 Agent 分支，否则规则分支
5. Agent 分支有 25 秒超时，超时或异常自动降级规则分支
6. 规则分支执行五步流水线并生成结果页
7. 成功后记录当日免费使用次数，返回 html_url、输出文本、模式标识

### 3.2 五步流水线（CafeRecommender.execute）

1. 地址解析：优先使用前端预解析坐标；否则并发地理编码，POI 文本检索优先，失败回退到高德 geocode。单个地址失败不中止请求，跳过并提示，其余地址继续。
2. 公平中心计算：两点用球面中点，多点用球面平均，确保跨城输入不被强行拉同城。
3. POI 检索：多关键词并发搜索后按名称和坐标去重；无结果时依次回退到无类型搜索、类别回退（餐厅/咖啡馆/商场/美食）、扩大半径到 50 公里。
4. 多因子评分：基础 30 分、热度 20 分、距离 25 分、场景 15 分、需求 10 分；支持最低评分、最大距离、价格档位（economy/mid/high）软筛选；多场景输入按场景平衡。
5. 结果生成：文本摘要加自包含 HTML，包含地图、五步推理链、评分依据、交通与停车建议。

### 3.3 Agent 模式（MeetSpotAgent）

- ReAct 循环：think 决定工具，act 执行，最多 15 步
- 四工具：geocode、calculate_center、search_poi、generate_recommendation
- 智能中心算法：几何中心周围生成 3x3 网格候选（9 个），按 POI 密度、交通便利性、公平性评分选择最优
- generate_recommendation 在规则评分基础上叠加 LLM 智能排序，综合得分按规则 40% 加 LLM 60%
- 失败处理：路由路径 25 秒超时降级规则；强制 Agent 接口无超时，适合演示

### 3.4 通勤公平性校验（Commute-Time Fairness，2026-08 新增）

直线距离公平不等于真实通勤公平：同样的直线距离，开车和转乘公交的耗时可能相差数倍。该能力在 `_calculate_smart_center`（`app/tool/meetspot_recommender.py`）已有的多候选评估循环上叠加一次真实通勤时间校验：

1. 前置条件：请求携带 `commute_budgets`（每位参与者的最大可接受通勤分钟数，允许部分为空）且当前 `map_provider == "google"`（仅国际场景，高德路径不受影响、行为不变）。未满足任一条件时直接走原有的 `_calculate_center_point` 几何中点逻辑，零额外开销。
2. 第一阶段沿用既有的廉价评分（POI 密度 + 交通便利性 + 直线距离公平性）对 3x3 网格候选打分，取排名前 3 的候选。
3. 第二阶段仅对这 3 个候选发起**一次**批量调用：`app/tool/google_directions_client.py` 封装的 Google Routes API `computeRouteMatrix`（3 候选 × 最多 10 参与者 = 30 个元素，远低于 TRANSIT 模式 100 元素上限），一次请求拿到所有候选到所有参与者的真实通勤时间。
4. 校验逻辑（`_verify_commute_fairness`）：依次检查每个候选是否满足全部参与者的预算，选中第一个全部满足的候选；若三个都不满足，退化为"违规人数最少"的候选。结果（每个候选的通勤时间、被拒原因）写入 `details["commute_check"]`，覆盖第一阶段选出的候选点。
5. 结果页新增一段推理链内容（`_render_commute_check_html`，插入 Step 2 "公平中心计算"内）：展示被拒候选及超预算的参与者和分钟数、最终候选每位参与者的真实通勤时间徽章。未提供 `commute_budgets` 时该方法返回空字符串，现有五步骤内容不变。

依赖与降级：任一环节失败（未启用 Routes API、超时、无 key）均 fail-soft 返回空结果，`_calculate_smart_center` 自动回退到第一阶段选出的候选，不影响推荐主流程。仅覆盖 Google Maps 路径（`/`、`/en/*`），高德路径的真实通勤时间校验不在本次范围内。

## 4. 模块清单

| 模块 | 职责 | 关键文件 |
|---|---|---|
| 启动与入口 | 加载环境变量，启动 uvicorn | web_server.py |
| API 编排 | 路由、复杂度路由、配额、静态挂载 | api/index.py |
| 核心推荐 | 五步流水线、评分、回退、HTML 生成 | app/tool/meetspot_recommender.py |
| 通勤时间查询 | Google Routes API 批量矩阵查询、响应解析 | app/tool/google_directions_client.py |
| Agent | ReAct 循环与工具封装 | app/agent/meetspot_agent.py、base.py、tools.py |
| LLM 客户端 | OpenAI 兼容接口、重试、token 统计 | app/llm.py |
| 配置 | config.toml 与环境变量解析 | app/config.py |
| 数据 | 用户、支付、消息模型 | app/db/、app/models/ |
| 城市数据 | 城市推断与 SEO 内容 | data/cities.json |
| 前端 | 输入页、SEO 页、样式 | public/、templates/、static/ |
| 生成物 | 结果页 HTML，自动清理 | workspace/js_src/ |

## 5. API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/find_meetspot | 自动路由推荐入口 |
| POST | /api/find_meetspot_agent | 强制 Agent 模式 |
| GET | /api/ai_chat/preset_questions | 预设问题列表 |
| POST | /api/ai_chat | AI 客服对话 |
| GET | /health | 健康检查与配置状态 |
| GET | /api/status | 服务状态 |
| GET | /api/config/amap | 高德前端配置（仅 JS key） |
| GET | /api/config/google_maps | Google Maps 前端配置 |
| GET | /api/config/analytics | 统计配置 |
| POST | /recommend | 兼容旧入口 |
| POST | /api/auth/send_code、/verify_code | 手机验证码登录 |
| GET | /api/auth/me | 当前用户 |
| POST | /api/payment/create | 创建支付 |
| POST | /api/payment/webhook | 支付回调 |
| GET | /api/payment/status、/balance、/free-remaining | 支付与额度查询 |
| GET | /、/zh、/en、/meetspot/{city}、/about 等 | SEO 页面 |

### 推荐请求 Schema（MeetSpotRequest）

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| locations | string[] | 必填 | 2 至 10 个参与者位置 |
| keywords | string | 咖啡馆 | 场所关键词，多个用空格分隔 |
| place_type | string | 空 | 高德类型编码 |
| user_requirements | string | 空 | 特殊需求，如安静、停车 |
| min_rating | float | 0 | 最低评分筛选 |
| max_distance | int | 100000 | 最大距离（米） |
| price_range | string | 空 | economy / mid / high |
| location_coords | object[] | null | 前端 Autocomplete 预解析坐标 |
| language | string | 空 | zh / en |
| commute_budgets | (int\|null)[] | null | 与 locations 等长，每位参与者最大通勤分钟数；仅 Google 路径生效，触发 3.4 节的通勤公平性校验 |
| transport_mode | string | TRANSIT | Google Routes API 出行方式：TRANSIT / DRIVE / WALK / BICYCLE / TWO_WHEELER |

## 6. 数据流与数据管理

用户地址文本 -> 地图 API 地理编码 -> 坐标与城市 -> 公平中心 -> POI 检索 -> 规则评分（Agent 内叠加 LLM 评分）-> 推荐结果与推理摘要 -> HTML 结果页。

- 缓存：geocode 与 POI 结果在进程内存缓存，上限分别约 30 与 15 条，进程重启即清空
- 持久化：数据库仅存用户、支付、消息相关数据；推荐请求不落库
- 结果页：workspace/js_src 保存最多 50 份后自动清理旧文件，不提交仓库
- 免费额度：按 IP 记录当日次数，仅用于配额计数

## 7. 失败处理矩阵

| 场景 | 行为 | 用户提示 |
|---|---|---|
| 单个地址解析失败 | 跳过并继续其余地址 | 文本与结果页提示跳过清单 |
| 全部地址解析失败 | 返回输入建议 | 地址格式示例、别名建议、配额排查 |
| POI 无结果 | 无类型搜索、类别回退、扩大半径 | 提示回退类别或搜索失败原因 |
| LLM 不可用或超时 | 规则评分与默认交通建议 | 不影响推荐结果返回 |
| Agent 超时或异常 | 自动降级规则模式 | 返回 rule_llm，日志记录原因 |
| 免费额度超限 | 拒绝处理 | need_payment 响应 |
| 地图 API QPS 超限 | 记录错误并继续 | 失败分支提示配额排查 |

## 8. 安全与合规

- 密钥通过环境变量或 config.toml 配置，不提交仓库
- 高德后端 Web key 不下发前端，前端地图使用独立 JS key 与安全密钥
- Google Maps key 需在 GCP 控制台按 referer 限制
- 通勤公平性校验依赖 GCP 控制台单独启用的 Routes API（与 Places/Geocoding 是独立开关），未启用时 fail-soft 降级，不影响主流程
- 慢速限流中间件已引入（slowapi）
- 地址文本不留存，结果页自动清理，商业 API 依赖（DeepSeek、高德、Google）如实披露

## 9. 部署

- Docker：`cp .env.example .env` 后 `docker compose up --build`，健康检查 /health
- Render / Railway：配置 PORT、DATABASE_URL、地图与 LLM 密钥、FREE_DAILY_LIMIT
- 环境变量清单见 docs/USER_GUIDE.md 第 3 节

## 10. 测试与质量

- 43 个 pytest 用例全绿，覆盖部分失败、POI 回退、Agent 成功与降级、配额、配置脱敏、跨城推断、价格筛选等
- ruff 与 flake8 关键项 0 错误，CI 执行 pytest、ruff、Docker 构建
- Docker 镜像构建并实测 /health 与首页 200
- 性能实测：规则路径约 5 秒（DeepSeek），Agent 模式 30 至 70 秒波动（受 DeepSeek 偶发空响应重试影响）

## 11. 已知限制

- Agent 模式延迟波动较大，现场演示建议用规则路径或强制 Agent 接口，自动路由依赖 25 秒超时降级
- Issue #50 的线上复现需结合 Render 日志确认是否高德配额
- app 包测试覆盖率约 44%，为历史存量，核心推荐器约 53%
- 通勤公平性校验（3.4 节）仅覆盖 Google Maps 路径，高德路径的真实通勤时间校验暂不支持；单次校验仅对每位参与者用同一种出行方式（transport_mode 为请求级参数，非逐人配置）
