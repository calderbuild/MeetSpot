# 交接清单：MeetSpot GOAI 2026（Codex -> Claude Code）

日期：2026-08-07。代码侧与材料第一版已完成，以下是你接手后的处理顺序。

## 当前状态（已验证）

- 测试 43 个全绿：`./venv/bin/python -m pytest tests/ -q`
- lint 全绿：`ruff check .` 0 错误；flake8 关键项 0 错误
- Docker：`docker compose up --build` 可用，镜像构建与 /health、首页 200 实测通过
- 本地端到端：部分失败提示、Agent 超时降级、强制 Agent 接口 rule_fallback 均实测通过（记录在样例输入输出.md）
- 线上 Demo：规则链路实测通过；免费额度默认 1 次/天需改环境变量
- CI：已补 pytest 与 ruff 步骤（2026-08-07），提交后留意 GitHub Actions 结果

## 仓库未提交改动

- 修改：api/index.py、app/tool/meetspot_recommender.py、web_server.py、app/agent/*、app/llm.py、app/design_tokens.py、app/models/payment.py、api/routers/seo_pages.py、api/services/seo_content.py、tools/postmortem_check.py、README.md、README_ZH.md、.env.example
- 新增：tests/ 下 6 个测试文件、.dockerignore、docker-compose.yml、.ruff.toml、docs/ARCHITECTURE.md、docs/BENCHMARK.md、tools/build_goai_ppt.py、hackathon/ 材料包
- 建议：feature/goai-2026 分支提交，Conventional Commits，第一人称，无 AI 署名

## 部署与验证（按顺序）

1. Render 环境变量：`FREE_DAILY_LIMIT=2`（评审期可设 0 关闭）；核对 `LLM_API_KEY` 有效性（本地 deepwisdom key 已被封，403 User has been banned）；建议配置独立 `AMAP_JS_API_KEY`（前端地图用，后端 Web key 不再返回前端）
2. 部署后用 Chrome 验证：首页与地图渲染、复杂请求触发 Agent 模式、单个地址失败提示、结果页五步推理链、免费额度不拦第二次
3. 确认 Google Maps key 在 GCP 控制台已做 referer 限制
4. #50 若线上复现，查 Render 日志中 POI 搜索 API 错误（配额/限流），失败提示已带排查说明

## 材料终版

- PPT：MeetSpot-GOAI2026-初赛PPT-v1.1.pptx 已含品牌视觉与截图，替换为浏览器实拍截图后重跑 tools/build_goai_ppt.py
- Demo 视频：用线上真实流程录制 3 至 5 分钟（初赛可选交付物）
- 第 11 页补"原有基础 + 本次新增贡献"表述（手册红线要求）
- 提交前逐条对照官方要求对照清单.md

## 用户侧待办（提醒）

- 官网注册报名（8 月 16 日 23:59 截止）：注册 https://www.goaihz.com/register ，报名 https://www.goaihz.com/enrollment
- LLM key：本地 .env 已切换 DeepSeek（deepseek-v4-flash）并实测通过；Render 部署需同步 LLM_API_BASE=https://api.deepseek.com、LLM_API_KEY、LLM_MODEL=deepseek-v4-flash
- Agent 模式注意：DeepSeek 延迟有波动（29.8 至 71 秒），自动路由 25 秒超时会降级规则模式（结果仍可用）；现场演示建议用强制 Agent 接口或录制备用视频
