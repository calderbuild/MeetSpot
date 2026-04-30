# AIGCLink 开源项目推广计划 -- 填表文档

> 整理时间：2026-04-30
> 对应问卷：AIGCLink 开源项目推广计划问卷
> 当前网页表单已勾选：Q10/Q11 = 是，Q12 全勾（公众号 + 小红书 + X + 其他），Q13 = 开源赞助 + 社区资源互换

---

## 一、MeetSpot 项目现状（截至 2026-04-30）

| 指标 | 数据 |
|------|------|
| GitHub Stars | 537 |
| Forks | 65 |
| 创建时间 | 2025-05-25 |
| 最近更新 | 2026-04-29 |
| License | MIT |
| Open Issues | 11 |
| 主语言 | Python |
| 在线演示 | https://meetspot-irq2.onrender.com |
| GitHub | https://github.com/calderbuild/MeetSpot |
| **国际化** | **中英双语**（`/` 默认英文 / `/zh/` 中文，URL 前缀 + Cookie + Accept-Language 三层检测） |
| **海外地图** | **Google Maps 已接入**（地理编码 + Places API + 前端 Places Autocomplete，2026-04-30 完成） |
| 演示视频 | Bilibili: BV1aUK7zNEvo |

---

## 二、关于 AIGCLink

- **定位**：公益性 AI 开发者社区，聚集 15,000+ AI Native 开发者，80% 是国内 AI 应用核心开发者
- **主要渠道**：微信公众号（AIGCLINK）、小红书（4,381 粉丝，获赞 4.6 万）、X / YouTube
- **旗舰活动**：年度 AIGC 开发者大会（ACDC），第五届于 2026-01-17 在北京举办，数千人参与
- **开源推广计划**：「AIGC 开发者双百计划」，联合凌柯云首批扶持 10 个优秀 AI 开源项目，权益包括：
  1. 小红书官方账号推广，精准触达 AI 开发者
  2. 公众号深度测评 + AI 排行榜收录 + 年度白皮书案例
  3. 路演/黑客松等赛事快速报名通道
- **开发者基金**：「AIGCLINK 开发者基金」，支持 OPC（个人开发者）商业落地与早期启动

**结论**：他们有真实的内容分发能力和开发者受众，对 MeetSpot 的目标用户（AI 应用开发者）高度匹配，值得参与。

---

## 三、建议填表内容

### 1. 您的姓名/昵称
```
Calder
```

### 2. 您的邮箱
```
Johnrobertdestiny@gmail.com
```
（项目 README 上公开的联系邮箱）

### 3. 您的微信
```
（请填你的微信 ID，README 里只有二维码图片）
```

### 4. 您所在城市
```
（请填你所在城市）
```

### 5. 项目名称
```
MeetSpot
```

### 6. 项目链接
```
https://github.com/calderbuild/MeetSpot
```
（在线演示可放在 Q9 描述里：https://meetspot-irq2.onrender.com）

### 7. 是否商用免费

**建议选：是，商用免费**

理由：MIT License，代码完全开源可商用；在线演示每天 1 次免费额度只是托管服务的运营限制，不影响代码本身。对开发者社区来说强调"开源免费可商用"更有吸引力。

### 8. 项目所属公司/组织/个人名称
```
个人开发者（Calder）
```

### 9. 详细描述（项目背景、功能、亮点）-- 推荐版

```
MeetSpot 是一个 AI 驱动的多人公平会面点推荐工具，解决"我们在哪见面"的高频社交痛点。在线体验：https://meetspot-irq2.onrender.com

核心逻辑：用户输入多个出发地点（如"北京大学、清华大学、望京"），系统自动计算地理中心，并发搜索周边 POI，结合评分、距离衰减、品牌特征、场景匹配等多维算法排序，生成带交互地图的可视化结果页。

国际化能力：
- 中英双语全站支持，默认英文（`/`），中文用户走 `/zh/` 或点击导航中文切换
- 国内场景：高德地图 API（POI 搜索 + 地理编码 + 前端 Autocomplete）
- 海外场景：Google Maps Platform 已接入（Geocoding API + Places API New v1 + 前端 Places Autocomplete）
- 双 provider 架构，按语言自动路由：英文路径用 Google，中文路径用高德，互不影响

技术亮点：
- AI Agent 架构：根据请求复杂度自动路由 Rule Mode（2-4 秒）或 Agent Mode（LLM 语义评分，8-15 秒），融合得分 = 规则分×0.4 + LLM分×0.6
- 百点评分系统：基础分(30) + 热度分(20) + 距离分(25) + 场景分(15) + 需求分(10)
- 品牌知识库：内置 50+ 品牌画像（星巴克、海底捞等），支持停车/安静/商务/儿童友好等需求精准匹配
- 地址智能增强：90+ 高校/地标别名映射，跨城市歧义自动消解
- 轻量部署：不依赖 tiktoken / jieba 等重量级库，512MB 内存稳定运行

项目数据：537 Stars，65 Forks，MIT 开源，FastAPI + DeepSeek/GPT-4o-mini，已部署上线，有 Bilibili 演示视频。
```

（约 450 字，字数超限可删"地址智能增强"或"项目数据"那行）

### 10. 是否愿意参与 AIGCLINK 精准评选和深度测评
```
✓ 是  ← 表单已勾选
```

### 11. 是否愿意分享到社群
```
✓ 是  ← 表单已勾选
```

### 12. 希望获得哪些曝光

表单中已经全部勾选，建议**保持**：
```
✓ 公众号推广   -- 主要曝光渠道，必选
✓ 小红书推广   -- 4.6 万获赞，AI 开发者集中
✓ X（推特）   -- 多一个海外曝光渠道，与 MeetSpot 国际化方向一致
✓ 其他（YouTube、LinkedIn 等）  -- 多渠道无害，不增加你的工作量
```

### 13. 是否有商业合作需求

表单中已勾选两项，建议**保持**：
```
✓ 开源赞助       -- Afdian 已开通，承接小额支持
☐ 技术合作       -- 不需要（除非你想接外包）
✓ 社区资源互换   -- 互推流量，零成本
☐ 其他           -- 不必勾
```

### 14. 其他需求或建议 -- 推荐版

```
后续会持续迭代国际化能力，正在接入 Google Maps 让海外用户也能用 MeetSpot；如果 AIGCLink 社区里有海外华人开发者群体的曝光机会，可以一起合作。也欢迎社区开发者来项目 Star / Fork / 提 Issue。
```

（这一句把"国际化扩展计划 + 求海外曝光"明确写出来，给后续合作留接口）

---

## 四、待你确认的字段

| 字段 | 原因 | 建议 |
|------|------|------|
| 微信 ID | README 只有二维码，没有文字 ID | 你直接填 |
| 城市 | 不在公开信息里 | 你直接填 |
| 第 9 题描述 | 字数限制未知 | 推荐版 450 字，超限自行裁剪 |

---

## 五、Google Maps 集成完成情况（2026-04-30 已上线）

**状态：已完成。代码从 BossTrip 复用并适配，本地端到端验证通过。**

### BossTrip 已有的可复用资产

| 文件 | 用途 |
|------|------|
| `BossTrip/app/google_client.py` | 后端 Google API 封装（httpx async），三个函数：`google_geocode()` / `google_geocode_with_city()` / `search_places()`。用 Places API New v1，`searchText` + `searchNearby` 双模式，`X-Goog-FieldMask` 控字段开销 |
| `BossTrip/app/config.py:32` | `GoogleSettings(api_key=...)` 单例配置，从 `GOOGLE_MAPS_API_KEY` 读 |
| `BossTrip/.env.example:7` | 环境变量样例 |
| `BossTrip/app/nlp/orchestrator.py:435` | **关键路由模式**：根据 `is_international` 判断走 Google 还是高德 |
| `BossTrip/static/js/shared.js:451-528` | `initGoogleMap(containerId, recommendations, googleKey)` -- 懒加载 `maps.googleapis.com/maps/api/js?key=KEY&loading=async&callback=_bossGoogleMapCb`，全局 key 通过 `window._BossTrip_GoogleKey` 注入 |

### 实际改动清单

| 模块 | 文件 | 内容 |
|------|------|------|
| 后端客户端 | `app/tool/google_maps_client.py` | 新建，httpx async + Places API New v1 + 输出归一化为高德 POI 格式 |
| 配置层 | `app/config.py` | 新增 `GoogleMapsSettings`，从 `GOOGLE_MAPS_API_KEY` 环境变量读 |
| API 端点 | `api/index.py` | 新增 `GET /api/config/google_maps`，前端获取 key |
| MinimalConfig | `api/index.py` | Vercel fallback 路径同步加 `google_maps` |
| 推荐引擎路由 | `app/tool/meetspot_recommender.py` | `_geocode` / `_search_pois` 按 `map_provider` 字段分发 Google/高德 |
| 结果页地图 | `app/tool/meetspot_recommender.py` | `_generate_html_content` 双 JS 模板（Google Maps JS API + 高德 JS API） |
| 前端 finder | `public/meetspot_finder.html` | URL/query 检测语言，对应加载 Google Places Autocomplete 或 AMap.AutoComplete |
| 国际化 | `app/i18n.py` | `DEFAULT_LANG` 改为 `en`，新增 `/zh/` 路径检测 |
| 路由 | `api/routers/seo_pages.py` | `/` 默认英文（cookie 优先），新增 `/zh/` 显式中文路由 |
| 翻译 | `locales/en.json` | placeholder 改为国际地点示例（Times Square / Empire State Building），hint 改为 "powered by Google Maps" |
| 安全 | `.gitignore` | 加入 `Googlemapkey.md`、`*mapkey*`、`*api_key*`、`stripe_backup_code.txt` |

### 验证结果

- ✅ 单元测试：`google_geocode("Times Square, New York")` 返回正确坐标 `-73.985,40.758`
- ✅ POI 搜索：返回归一化后的 5 个 cafe，rating/location/name 字段齐全
- ✅ 路由切换：`map_provider="google"` 时走 Google，`"amap"` 时走高德，互不污染
- ✅ 前端：`/en/` 路径 console 输出 "Google Maps loaded successfully" + "Address autocomplete ready (provider: google)"
- ✅ 多语言路由：`/` → English，`/zh/` → 中文，cookie `lang=zh` → 中文
- ✅ 默认语言：浏览器 Accept-Language 为 zh-CN 时 `/` 仍返回英文（硬默认）

### 注意事项

- 高德路径完全未改动逻辑，只是 marker 颜色对齐到 MeetSpot 品牌色（深海蓝 + 日落橙 + 薄荷绿），视觉更一致
- Google Places Autocomplete 用的是 legacy `places.Autocomplete`（控制台 warn 但仍可用），后续可迁移到 `PlaceAutocompleteElement`
- 海外驾车距离暂未接入 Google Distance Matrix，后续可作为增强项
- `Googlemapkey.md` 文件已 gitignore，开发完后请把 key 移到 `.env` 或部署平台的环境变量

---

## 六、备注

- AIGCLink 公众号偏技术向，受众和 MeetSpot 目标用户高度重叠
- 第 9 题"国际化"段是亮点，AIGCLink 自身做海外（YouTube/X）渠道，强调国际化能让你在 10 个名额里更有差异化
- 微信里他们说"可能得晚点"已回复，不紧急，填完提交即可
- Google Maps 集成代码是另起一个会话的事，本会话先把表填完
