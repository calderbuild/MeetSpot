---
title: "feat: Add English Multilingual Support"
type: feat
date: 2026-03-08
---

# feat: Add English Multilingual Support (i18n)

## Overview

MeetSpot 全站双语支持（中文 + 英文）。当前 ~540+ 中文硬编码字符串分布在 13 个文件中，无任何 i18n 基础设施。采用轻量级 JSON 翻译文件方案，避免引入重型框架（512MB Render 免费层限制）。

分两期交付：
- **Phase 1**: 营销页面 + Finder UI + API 响应 + SEO 页面 + AI Chat
- **Phase 2**: 生成的推荐结果 HTML（`_generate_html_content()`）

## Problem Statement / Motivation

MeetSpot 有国际用户访问（GitHub 520 stars 来自全球），但整站只有中文。英文用户无法理解界面、错误提示和 SEO 页面。多语言支持是扩大用户群的基础。

## Proposed Solution

### Architecture: Lightweight JSON i18n

```
locales/
  zh.json          # 中文翻译（从现有硬编码字符串提取）
  en.json          # 英文翻译

app/i18n.py        # 翻译加载 + 缓存 + 工具函数
```

**核心设计决策：**

1. **翻译文件**: `locales/zh.json` + `locales/en.json`，启动时加载到内存缓存（~100KB，可忽略）
2. **语言检测链**: URL 前缀 `/en/` > Cookie `lang` > `Accept-Language` header > 默认中文
3. **URL 路由**: 中文保持现有 URL（无前缀），英文加 `/en/` 前缀。向后兼容
4. **Jinja2 模板**: 通过 context dict 注入翻译函数 `t()`
5. **Finder HTML**: 客户端 JS i18n，`data-i18n` 属性 + fetch JSON
6. **AMap 限制**: 保持高德地图，英文界面标注"地址建议为中文"，Google Maps 作为后续迭代

### Translation Key Convention

点分隔扁平 key，按页面/组件分组：

```json
{
  "nav.home": "首页",
  "nav.about": "关于",
  "nav.guide": "使用指南",
  "nav.faq": "FAQ",
  "home.hero_title": "智能聚会地点推荐",
  "home.hero_subtitle": "多人聚会，一键找到公平中点",
  "finder.submit": "查找最佳会面点",
  "finder.amap_note": "地址建议为中文（使用高德地图）",
  "api.error.quota_exceeded": "今日免费次数已用完",
  "api.error.rate_limit": "请求过于频繁, 请稍后再试",
  "chat.welcome": "你好！我是 MeetSpot AI...",
  "seo.home.title": "MeetSpot 聚点 - 多人聚会地点智能推荐",
  "seo.home.description": "..."
}
```

### Route Architecture

```python
# api/routers/seo_pages.py

# 现有路由保持不变（中文）
@router.get("/")
async def homepage(request: Request):
    return _render_page(request, "home", lang="zh")

# 英文路由：/en/ 前缀
@router.get("/en/")
async def homepage_en(request: Request):
    return _render_page(request, "home", lang="en")

# 共享渲染函数
def _render_page(request, page_type, lang="zh"):
    t = get_translations(lang)
    context = {**_common_context(request), "t": t, "lang": lang}
    return templates.TemplateResponse(f"pages/{page_type}.html", context)
```

### Language Detection Flow

```
Request arrives
    ↓
URL starts with /en/ ? → lang = "en"
    ↓ no
Cookie "lang" exists? → lang = cookie value
    ↓ no
Accept-Language contains "en"? → lang = "en"
    ↓ no
lang = "zh" (default)
```

Cookie 设置：name=`lang`, path=`/`, expiry=365 days, SameSite=Lax

### Language Toggle UI

Header nav 右侧（FAQ 后面），简洁文本链接：
- 中文页面显示 "EN"，点击跳转 `/en/` 对应页面并设置 cookie
- 英文页面显示 "中文"，点击跳转无前缀页面并设置 cookie

## Technical Considerations

### AMap 地址输入限制

高德地图 Autocomplete API 返回中文地址建议。英文用户体验方案：
- Placeholder 文本改为英文（如 "Enter a location, e.g., Peking University"）
- 添加提示信息："Address suggestions are in Chinese (powered by Amap)"
- 后续迭代：英文用户切换到 Google Maps Autocomplete（需要 Google Maps API Key，独立 feature）

### Finder HTML (standalone) i18n

`public/meetspot_finder.html` 是独立 HTML，不经过 Jinja2。方案：

1. 所有可翻译文本元素加 `data-i18n="key"` 属性
2. 页面加载时 JS 检测语言（cookie > Accept-Language > 默认 zh）
3. Fetch `/locales/{lang}.json`，遍历 DOM 替换文本
4. `data-type` 属性值保持中文（API contract 不变），显示文本从翻译文件读取
5. 翻译文件缓存到 `localStorage`

```javascript
// 伪代码
async function initI18n() {
    const lang = getCookie('lang') || detectBrowserLang() || 'zh';
    const translations = await fetch(`/locales/${lang}.json`).then(r => r.json());
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (translations[key]) el.textContent = translations[key];
    });
    document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
}
```

### AI Chat 双语

- 维护两个 system prompt：`MEETSPOT_SYSTEM_PROMPT_ZH` + `MEETSPOT_SYSTEM_PROMPT_EN`
- `/api/ai_chat` 端点接受 `language` 参数
- Chat widget JS 根据当前页面语言传递 language 参数
- Preset 问题和欢迎消息从翻译文件读取

### SEO 双语

- 英文页面：`/en/about`, `/en/faq`, `/en/how-it-works`, `/en/meetspot/{city_slug}`
- `<html lang="en">` 动态设置
- hreflang 标签双向链接：`<link rel="alternate" hreflang="zh" href="/about" />` + `<link rel="alternate" hreflang="en" href="/en/about" />`
- Schema.org `inLanguage` 动态设置为 `"en"` 或 `"zh-CN"`
- Sitemap 包含所有英文 URL 变体 + `xhtml:link` hreflang
- Meta tags（title, description, keywords）从翻译文件读取
- City slug 已经是拼音（`beijing`, `shanghai`），中英文共用

### 内存影响评估

| 项目 | 内存占用 |
|------|---------|
| 两个 JSON 翻译文件缓存 | ~100KB |
| 额外路由注册 | ~negligible |
| 无新依赖 | 0 |
| 总计 | ~100KB（在 512MB 限制内可忽略） |

## Acceptance Criteria

### Phase 1: 营销页面 + Finder UI + API + SEO + Chat

- [x] `locales/zh.json` 包含所有提取的中文字符串（~540 keys）
- [x] `locales/en.json` 包含所有对应英文翻译
- [x] `app/i18n.py` 实现翻译加载、缓存、`get_translations(lang)` 函数
- [x] `templates/base.html` 支持动态 `lang` 属性和翻译上下文
- [x] 所有 Jinja2 模板页面（home, about, faq, how-it-works, city）支持中英文
- [x] Header 有语言切换按钮（EN / 中文）
- [x] `public/meetspot_finder.html` 客户端 i18n 正常工作
  - [x] 所有 UI 文本可切换
  - [x] `data-type` 值保持中文发送给 API
  - [x] AMap 限制有英文提示
  - [x] 付费弹窗/额度提示支持英文
- [x] API 响应支持英文错误消息（通过 `lang` 参数或 `Accept-Language`）
- [x] AI Chat 支持英文（system prompt, preset questions, welcome message）
- [x] SEO: `/en/` 页面有正确的 meta tags, hreflang, Schema.org inLanguage
- [x] Sitemap 包含英文 URL 变体
- [x] Cookie 语言偏好持久化正常
- [x] 自动语言检测（Accept-Language）正常工作

### Phase 2: 推荐结果 HTML（已完成）

- [x] `_generate_html_content()` 接受 `language` 参数
- [x] `MeetSpotRequest` 模型增加 `language` 字段
- [x] `PLACE_TYPE_CONFIG` 显示字符串支持英文
- [x] 结果页 HTML 所有标签、描述、提示支持英文
- [x] 搜索过程可视化（thinking steps）支持英文

## Implementation Phases

### Phase 1A: 基础设施（~2h）

| Task | Files | Notes |
|------|-------|-------|
| 创建 `app/i18n.py` | `app/i18n.py` (new) | 翻译加载、缓存、`get_translations()` |
| 提取中文字符串到 `locales/zh.json` | `locales/zh.json` (new) | 从 13 个文件提取 ~540 keys |
| 创建英文翻译 `locales/en.json` | `locales/en.json` (new) | 翻译所有 keys |
| 添加 `/locales/` 静态文件路由 | `api/index.py` | finder HTML 的 JS 需要 fetch |

### Phase 1B: Jinja2 模板改造（~3h）

| Task | Files | Notes |
|------|-------|-------|
| `base.html` 动态 lang + 翻译 | `templates/base.html` | nav, footer, modals |
| 语言切换按钮 | `templates/base.html` | Header nav 右侧 |
| `home.html` 翻译 | `templates/pages/home.html` | Hero, features, stats, CTA |
| `about.html` 翻译 | `templates/pages/about.html` | All content |
| `faq.html` 翻译 | `templates/pages/faq.html` | FAQ items from Python |
| `how_it_works.html` 翻译 | `templates/pages/how_it_works.html` | Steps, tips, CTA |
| `city.html` 翻译 | `templates/pages/city.html` | City-specific content |
| `ai_chat.html` 翻译 | `templates/components/ai_chat.html` | Widget text, presets |

### Phase 1C: 路由 + SEO（~2h）

| Task | Files | Notes |
|------|-------|-------|
| 英文路由注册 `/en/*` | `api/routers/seo_pages.py` | 共享渲染函数 |
| hreflang 标签 | `templates/base.html` | 双向链接 |
| Meta tags 双语 | `api/services/seo_content.py` | 从翻译文件读取 |
| Schema.org inLanguage | `api/services/seo_content.py` | 动态切换 |
| Sitemap 英文 URL | `api/routers/seo_pages.py` | 包含 xhtml:link |
| City content 英文 | `api/services/seo_content.py` | `generate_city_content()` |

### Phase 1D: Finder HTML + API（~3h）

| Task | Files | Notes |
|------|-------|-------|
| Finder HTML i18n JS | `public/meetspot_finder.html` | `data-i18n` + fetch JSON |
| 语言切换按钮（finder） | `public/meetspot_finder.html` | 独立于 base.html |
| AMap 限制提示 | `public/meetspot_finder.html` | 英文提示文本 |
| 付费弹窗翻译 | `public/meetspot_finder.html` | Credits, quota 相关 |
| API 错误消息本地化 | `api/index.py` | 语言检测 + 翻译 |
| AI Chat 英文 prompt | `api/index.py` | 双语 system prompt |
| AI Chat widget 语言传参 | `templates/components/ai_chat.html` | 发送 lang 参数 |

## Dependencies & Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| 翻译质量 | 英文文案不自然 | 可后续迭代优化，先保证功能完整 |
| AMap 限制 | 英文用户地址输入体验差 | 明确标注限制，后续加 Google Maps |
| 540+ 字符串提取遗漏 | 部分页面混合中英文 | grep 全量扫描验证 |
| SEO 权重分散 | 英文页面分走流量 | hreflang 正确配置，canonical 明确 |
| Cookie vs URL 冲突 | 语言不一致 | URL 前缀优先，cookie 只用于默认值 |

## Success Metrics

- 英文页面 Lighthouse 性能分数 >= 中文页面
- 英文 SEO 页面被 Google 索引（通过 Search Console 验证）
- 英文 Finder 页面完整可用（除 AMap 地址为中文外）
- 无新增内存占用超过 1MB

## References & Research

### Internal References

- 硬编码中文字符串分布：13 files, ~540+ strings（详见研究报告）
- SEO 路由架构：`api/routers/seo_pages.py`
- 翻译文本主要来源：`templates/base.html`, `templates/pages/home.html`, `public/meetspot_finder.html`
- 模板渲染上下文：`_common_context()` in `api/routers/seo_pages.py`
- 已有 SSR 动态注入模式：env var 通过 context dict 而非 `templates.env.globals`（见 CLAUDE.md Debugging）

### Known Limitations

- AMap Autocomplete 只返回中文地址建议（后续迭代 Google Maps）
- Phase 1 不含推荐结果 HTML 翻译（Phase 2）
- 城市页面 slug 共用拼音，不提供英文城市名 slug
