# MeetSpot 使用与部署指南

版本：v1.1（2026-08-25）

## 1. 快速开始（本地开发）

前置条件：

- Python 3.11 或 3.12
- 高德地图 Web 服务 key（AMAP_API_KEY）
- DeepSeek 或其他 OpenAI 兼容接口的 key

步骤：

```bash
cp .env.example .env
# 编辑 .env，填入 AMAP_API_KEY、AMAP_SECURITY_JS_CODE、LLM_API_KEY 等
pip install -r requirements.txt
python web_server.py
```

访问 http://localhost:8000 ，健康检查 http://localhost:8000/health 。

## 2. Docker 一键启动

```bash
cp .env.example .env
docker compose up --build
```

容器启动后 /health 与首页均可用，端口 8000。

## 3. 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| AMAP_API_KEY | 是 | 高德 Web 服务 key，地理编码与 POI |
| AMAP_SECURITY_JS_CODE | 否 | 高德 JS API 安全密钥 |
| AMAP_JS_API_KEY | 否 | 前端地图 JS key，与 Web key 不同 |
| GOOGLE_MAPS_API_KEY | 否 | 英文场景地图与 POI；启用通勤公平性校验还需在 GCP 控制台单独启用 Routes API 并加入该 key 的限制列表 |
| LLM_API_KEY | 是 | DeepSeek 或其他兼容接口 key |
| LLM_API_BASE | 否 | 默认 https://api.deepseek.com |
| LLM_MODEL | 否 | 默认 deepseek-v4-flash |
| DATABASE_URL | 否 | SQLite 默认，生产建议 PostgreSQL |
| FREE_DAILY_LIMIT | 否 | 每 IP 每日免费次数，0 表示关闭 |
| PORT | 否 | 默认 8000 |
| CORS_ALLOW_ORIGINS | 否 | 逗号分隔白名单，默认 * |
| LOG_LEVEL | 否 | 日志级别 |
| PAY302_APP_ID、PAY302_SECRET、PAY302_API_URL | 否 | 302 支付 |
| BAIDU_TONGJI_ID、GA4_MEASUREMENT_ID | 否 | 统计 |

## 4. 用户操作流程

1. 打开首页，输入 2 至 10 个参与者地址
2. 选择场所类型（咖啡馆、餐厅、茶馆等 12 类）
3. 填写特殊需求（安静、停车、人均预算等）和筛选条件（评分、距离、价格档位）
4. 填写特殊需求（安静、停车、人均预算等）和筛选条件（评分、距离、价格档位）
5. 提交后查看结果页：地图、评分卡片、五步推理链、交通与停车建议
6. 可复制结果链接或重新搜索；AI 对话支持预设问题与多轮问答

### 3a. 通勤公平性校验（可选，仅英文/国际站点）

在 `/` 或 `/en/*` 页面每个地址输入框旁会出现一个可选的"Max commute (min)"输入框，可以为部分或全部参与者填写最大可接受通勤分钟数（乘坐公共交通）。任意一位参与者填写后，系统会在原有的直线距离公平中心之外，再用 Google Routes API 校验真实通勤时间：如果几何中心对某人不公平（超出其填写的分钟数），会自动尝试附近其他候选点，直到找到对所有人都满足预算的地点（找不到则选违规人数最少的候选）。结果页的推理链会展示每个被拒候选超时的原因和最终候选每位参与者的真实通勤时间。

不填写该输入框的行为与之前完全一致（几何中心，不发起通勤时间查询）。中文 `/zh/*` 页面目前不提供该输入框（高德路径的真实通勤时间校验暂不支持）。

地址输入建议：完整地址（北京市海淀区中关村大街27号）、知名地标（北京大学、天安门广场）、商圈（三里屯）、交通枢纽（北京南站）、学校简称（北大、清华）。

## 5. API 调用示例

自动路由推荐：

```bash
curl -X POST http://localhost:8000/api/find_meetspot \
  -H "Content-Type: application/json" \
  -d '{"locations":["北京市海淀区中关村大街27号","北京市朝阳区建国路88号"],"keywords":"咖啡馆","user_requirements":"安静","price_range":"economy"}'
```

强制 Agent 模式：

```bash
curl -X POST http://localhost:8000/api/find_meetspot_agent \
  -H "Content-Type: application/json" \
  -d '{"locations":["北京市海淀区中关村大街27号","北京市朝阳区建国路88号"],"keywords":"咖啡馆","user_requirements":"安静"}'
```

带通勤公平性校验（仅 Google 路径，`commute_budgets` 与 `locations` 等长）：

```bash
curl -X POST http://localhost:8000/api/find_meetspot \
  -H "Content-Type: application/json" \
  -d '{"locations":["Times Square, New York","Prospect Park, Brooklyn","Flushing, Queens"],"keywords":"cafe","language":"en","commute_budgets":[20,20,30],"transport_mode":"TRANSIT"}'
```

AI 对话：

```bash
curl -X POST http://localhost:8000/api/ai_chat \
  -H "Content-Type: application/json" \
  -d '{"message":"三个人分别在海淀、朝阳、西城，推荐一个公平的咖啡馆"}'
```

## 6. 响应字段说明

推荐接口返回：

| 字段 | 说明 |
|---|---|
| success | 是否成功 |
| html_url | 结果页地址 |
| output | 推荐文本 |
| mode | rule_llm / agent / rule_fallback |
| complexity_score、complexity_reasons | 复杂度评分与原因 |
| processing_time | 耗时（秒） |
| agent_data | Agent 模式的中间结果（geocode、中心点、搜索、步数） |

## 7. 注意事项

- FREE_DAILY_LIMIT 默认按 IP 计免费次数，比赛演示建议调高或设为 0
- LLM key 无效时系统静默降级规则评分，结果仍可用，但日志会记录错误
- 前端地图需要 AMAP_JS_API_KEY，否则地图区域优雅降级只显示列表
- Google Maps key 必须在 GCP 控制台配置 referer 限制
- workspace/js_src 下的结果页会自动清理，无需手动删除

## 8. 常见问题

找不到地址：检查输入格式（完整地址或地标）、高德 key 配额是否耗尽；失败提示中带排查说明。

请求慢：规则路径约 5 秒；Agent 模式受模型延迟影响可能 30 秒以上，超时后自动降级规则模式。

返回 rule_fallback：强制 Agent 接口在 Agent 异常时降级，响应中的 agent_error 字段会给出原因。

地图不显示：检查 AMAP_JS_API_KEY 或 Google key 的 referer 限制配置。
