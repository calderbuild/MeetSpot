# ThatWare x MeetSpot — Meeting Cheatsheet
# 会议备忘单

> 一句话定位：你是带着答案进会的人，他们以为你是来听答案的。
> One-liner: You walk in with answers. They think you're there to receive them.

---

## BEFORE YOU START — 先记住这个框架

SEO 本质上是增长漏斗的 **Acquisition（获客）** 环节。
用 AARRR 框架来理解我们现在的处境：

```
Acquisition  ← 我们在这里，organic = 0，这是今天谈的核心
Activation   ← 用户用一次就能理解产品，这个还不错
Retention    ← 聚会工具天然低频，这是结构性问题
Revenue      ← freemium，每天免费 1 次
Referral     ← 口碑传播，目前靠这个活着
```

**所以问他们的核心问题只有一个**：
> "Given that we have zero organic traffic today, what does the Acquisition curve realistically look like — month by month?"
> 「我们现在 organic 流量是零，能不能给我画一条现实的获客曲线，按月？」

---

## PART 1 — 介绍自己，30 秒说清楚
## PART 1 — Your Intro

**English (say this):**
> "MeetSpot solves one specific problem — when a group of people need to meet somewhere, nobody can agree on a fair location. We calculate the geographic midpoint for up to 10 people, then AI-ranks nearby venues. Free tool, open source, China-focused, 50 cities, no marketing budget — pure organic growth play."

**要强调的点 / Emphasize these:**
- "Pure organic growth play" —— 这句话很重要，提前框定你们不是来买 ads 的
- "No marketing budget" —— 早说，省掉后面推销的时间
- "Open source" —— 打开 case study 合作的门

---

## PART 2 — 你的底牌，憋着别说
## PART 2 — Your Hidden Hand (don't reveal yet)

After reading their audit, you already fixed 4 real issues yourself.
他们发来的审计，你读完之后自己修了 4 个问题。

Think of it this way: they found the **symptoms**, not the **root causes**.
用增长的语言理解这件事：他们找到的是**症状**，没找到**病因**。

| Symptom (what they said) / 症状 | Root cause (what it actually was) / 病因 | Fixed? |
|--------------------------------|----------------------------------------|--------|
| 105 schema validation errors | `City` is not a valid schema.org type — 50 cities x 2 languages = 100 errors | Yes |
| Non-indexable URL in sitemap | The sitemap itself had `X-Robots-Tag: noindex` — crawlers couldn't even read it | Yes ← **they completely missed this** |
| 100 non-sequential headings | 2 templates jumping straight from h1 to h3 | Yes |
| LocalBusiness schema issues | Null values in required fields, making the JSON-LD invalid | Yes |

**How to use this / 怎么用:**
Ask them: "You flagged 105 schema errors — can you give me one specific example of what was causing them?"
问他们："那 105 个 schema 错误，能说一个具体例子吗？"
- If they say `City` isn't a valid schema.org type → they know their stuff / 懂行
- If they say "those are just general warnings" → they're reading tool output without understanding it / 只是在跑工具看数字

---

## PART 3 — 问题清单，按节奏出
## PART 3 — Questions by Phase

### 开场热身 / Warm-up (let them talk first)

> "Walk me through the most important finding in your audit — the one you'd fix first if you were us."
> 「如果你们是我们，审计里最先修哪一条？」

听他们怎么回答。如果第一个说的不是 sitemap noindex 问题，说明他们没挖到最深的那层。

---

### 实体 SEO — 他们的核心卖点 / Entity SEO (their pitch)

增长背景知识：**Entity SEO** 本质是告诉 Google "这个品牌/产品是真实存在的、有一定影响力的实体"。类似于你在增长里说的 Brand Awareness，只不过对象是搜索引擎而不是用户。

**问他们 / Ask:**
> "MeetSpot has zero press mentions, no Wikipedia page, no significant social following. What's the realistic entity-building path for a utility tool like this — and how long before Google starts treating us as a known entity?"
> 「MeetSpot 没有新闻报道，没有维基百科，社交媒体也没什么粉丝。对工具类产品来说，实体权威的建立路径是什么，现实时间线是多长？」

> "Is there a difference in how Google handles entity signals for a Chinese-market product vs a Western product?"
> 「中国市场产品和西方产品，Google 处理实体信号的方式有差别吗？」

---

### 子域名问题 — 主动抛 / Subdomain (you raise this)

增长背景知识：域名权重（DA/AS）就像增长里的 **Brand Trust**。你在 Render 子域名上，就像借用别人的信用卡分数——数字好看，但那不是你的。

**直接说 / Say this:**
> "Something I want your honest take on — we're on `meetspot-irq2.onrender.com`. The DA 56 in your report is Render's domain authority, not ours. Our actual trust is basically zero. At what point does staying on a subdomain become the ceiling for all our SEO efforts?"
> 「我想听你们的真实判断——我们现在在 Render 的子域名上，DA 56 是 Render 的，不是我们的。我们自己的信任度基本是零。子域名什么时候会成为所有 SEO 努力的天花板？」

**正确答案 / Right answer:** 他们应该直接说"你需要一个自定义域名，越快越好"。
**危险信号 / Red flag:** 说"子域名影响不大，我们可以在这个基础上做"。

---

### 挑战方案 — 戳漏洞 / Challenge their proposal

增长背景知识：好的增长策略是**ICE 框架** — Impact、Confidence、Ease。他们方案里的一些战术 Impact 低、Confidence 低，但是 Ease 看起来高，所以出现在清单里只是为了让单子显得满。

**问 Local SEO 的逻辑 / On Local SEO:**
> "Your proposal has a full Local SEO track — GMB, NAP consistency, local citations. MeetSpot has no physical location. Can you explain the logic? Are you recommending this because it applies to us, or is it a standard part of your package?"
> 「方案里有完整的本地 SEO 方向——GMB、NAP、本地引用。我们没有实体地址。能解释一下这个逻辑吗？是真的适用于我们，还是这是你们的标准套餐？」

**问 backlink 战术 / On backlink tactics:**
> "In Month 3 I noticed tiered backlinks and link wheels. Those are tactics Google has been actively penalizing. What's your approach to risk management there?"
> 「第 3 个月我看到了 tiered backlinks 和 link wheels。这些是 Google 一直在惩罚的手法。你们怎么做风险管理？」

---

### 效果衡量 — 逼他们给数字 / Measurement (make them commit)

增长背景知识：没有 baseline 的 SEO 承诺就像没有对照组的 A/B test，什么都证明不了。

**问 / Ask:**
> "What does success look like at the end of Month 3 — not Month 6, Month 3 — in specific, measurable terms? Not 'improved rankings', but actual numbers."
> 「第 3 个月结束的时候，用具体数字定义成功长什么样？不是'排名提升'，是实际数字。」

> "How many organic clicks per month is a realistic goal for us in 6 months, given where we're starting?"
> 「从我们现在的起点，6 个月之后每个月有多少 organic clicks 是现实目标？」

---

## PART 4 — 你的底线，提前想清楚
## PART 4 — Your Boundaries

**增长逻辑 / The growth logic:**
MeetSpot 是 PLG（Product-Led Growth）产品——产品本身是最好的获客工具。SEO 的作用是**让更多人在搜索的时候撞见这个产品**，而不是代替产品说服用户。这个定位决定了 SEO 投入的上限。

**可以谈的 / Open to:**
- 学他们的方法，自己实现（entity SEO 怎么做、Click Gap 分析怎么跑）
- Case study 合作：他们出策略，你出执行，结果一起发布
- 一次性针对某个具体问题的深度咨询

**不谈的 / Not open to:**
- 月付 retainer —— 免费工具，ROI 算不过来
- Backlink building 套餐 —— 新域名 + 人工链接 = 风险大于收益
- Grey-hat 战术 —— PBN、tiered links、link wheels，一律不碰

**怎么说 / How to say it — 直接但不失礼:**
> "We're an open-source side project. There's no paid marketing budget, so a retainer is off the table. But I'm genuinely interested in learning from you — if there's a case study format where you guide strategy and we execute, that's a conversation worth having."
> 「我们是开源项目，没有市场预算，月付合同不在考虑范围。但我真的想向你们学东西——如果有一种 case study 合作形式，你们出策略方向，我们负责执行，我有兴趣谈。」

---

## PART 5 — 评分卡，边聊边标
## PART 5 — Live Scorecard

| 测试 | 好信号 | 坏信号 |
|-----|-------|-------|
| 审计最重要的发现是什么 | 说到 sitemap 或 schema 根因 | 说 duplicate titles 或 DA 低 |
| Schema 错误原因 | 说出 `City` 不是标准类型 | 说"general warnings" |
| 子域名问题 | 主动提，说必须迁移 | 说影响不大 |
| 中国市场理解 | 提到百度 vs Google 差异 | 把中国当普通 geo |
| Backlink 策略 | 说自然获取、editorial links | 推 Web 2.0 / tiered links |
| 给数字 | 敢给具体预期 | 只说"持续优化" |
| Local SEO 解释 | 承认那块不适用于我们 | 坚持说本地 SEO 对工具也有用 |

3 个以上坏信号：这次学学就行，不合作。
全是好信号：认真谈 case study。

---

## PART 6 — 结尾话术，按场景选
## PART 6 — Closing Lines by Scenario

**如果聊得好 / If it went well:**
> "This has been genuinely useful. I want to think about the case study angle — can you send me a one-pager on what that would look like from your side? Scope, timeline, what you'd need from us."
> 「今天聊得很有收获。我想认真考虑 case study 合作的方式——能不能给我发一份简单的说明，你们那边怎么定义这个合作，需要我们配合什么？」

**如果聊得一般 / If it was so-so:**
> "I need some time to review this against what we've already implemented. Let me come back to you with specific questions."
> 「我需要时间对照我们已经做了的事情来评估一下。我有具体问题了再回来找你们。」

**如果他们全程只推销 / If they just pitched the whole time:**
> "I appreciate you walking us through the proposal. We're not in a position to commit to a retainer right now, but I'll reach out if that changes."
> 「感谢你们详细介绍了方案。我们现在没有条件签月付合同，如果有变化我会主动联系。」

---

## PART 7 — Their Documents, Slide by Slide
## PART 7 — 他们的 PPT，逐页拆解

会上他们大概率会翻这两份文件。提前标好哪些值得追问，哪些可以忽略。
They'll likely walk through these decks. Mark what to challenge, what to skip.

---

### Doc 1: In Depth SEO Audit

**Chapter 1 — Semrush Stats（他们说的）**
> Authority Score: 2 / Organic Traffic: Not Detected / Referring Domains: 9 / Backlinks: 16

你的反应 / Your read:
- AS 2 是真实的，坦然承认
- "Organic Traffic: Not Detected" 就是 0，没必要粉饰
- DA 56 他们没提，因为那是 Render 的，不是我们的——**你来提这件事**

---

**Chapter 2 — Technical SEO（重点章节）**

| 他们说的 They said | 实际情况 Reality | 要不要追问 |
|------------------|----------------|----------|
| 1 个 4XX 错误 | 小问题，修起来快 | 不用追 |
| 3 个 URL 含下划线，2 个含参数 | 极小影响，Google 能处理 | 不用追 |
| Sitemap 有 1 个不可索引 URL | **他们说反了——是 sitemap 本身被 noindex，不是里面某个 URL** | **追：让他们解释这一条** |
| 2 个 canonical 问题 | 值得检查，但不严重 | 可以问 |
| Robots.txt 需要"更高级的指令" | 模糊说法，没有具体建议 | 追：需要加什么指令，为什么 |
| 结构化数据：105 错误 + 110 警告 | **根因是 `City` 不是标准类型，这是底牌** | **追：举一个具体例子** |

---

**Chapter 3 — Mobile Usability**
> 网站响应式 ✓，HTTP/2 ✓，移动端性能"一般"

Nothing to challenge here. 这章没什么好追问的，说声"noted"就行。

---

**Chapter 4 — On-Page SEO（数字最多的一章）**

| 他们说的 They said | 你的判断 Your read |
|------------------|-----------------|
| 100 个重复 Page Title | **不准确。**每个页面 title 都不同，只是结构相似。Screaming Frog 的误判。 |
| 100 个重复 Meta Description | 同上，城市名不同，不是真正的重复 |
| 100 个 Non-Sequential Heading | 数字对，但根因是 2 个模板跳级，不是 100 个独立问题——已修 |
| 54 个低内容页面 | 这个是真的，SEO 落地页内容确实薄 |
| 2 张图片超 100KB，2 张缺 size 属性 | 真实但影响极小 |

**最值得追问 / Most worth challenging:**
> "You flagged 100 duplicate page titles. Can you show me two specific URLs with identical titles? Because our city pages all have the city name in the title — Beijing, Shanghai, Guangzhou — those aren't duplicates, they just follow the same template structure."
> 「你们报了 100 个重复 page title。能给我看两个具体 URL 的 title 完全一样的例子吗？我们城市页面每个都带了城市名——北京、上海、广州——这不是重复，只是模板结构相似。」

---

**Chapter 5 — Off-Page Stats**
> DA = 56 / PA = 40 / Spam Score: 38%

全部都是 Render 域名的数据，不是 MeetSpot 的。
All of these are Render's domain metrics, not MeetSpot's.

**直接说 / Say:**
> "The DA 56 and Spam Score you're showing — that's render.com's profile, not ours. We're on a subdomain. How does that change your off-page strategy recommendations?"
> 「你们展示的 DA 56 和 Spam Score 是 render.com 的，不是我们自己的。我们是子域名。这对你们的外链策略建议有什么影响？」

---

### Doc 2: SEO Strategy — 6 Month Plan

**Part 1 — Keywords & Content Planning**
KOB Analysis（关键词机会评分）+ Topic Cluster + Content Calendar

这部分是真实有价值的方法论。值得认真学。
This part has genuine value. Pay attention.

**问 / Ask:**
> "For a Chinese-market tool with bilingual pages — do you do keyword research in Chinese and English separately, or together? How do you handle the difference in search volume between Baidu and Google for the same intent?"
> 「对于中英双语的中国市场工具，你们是分开做中英文关键词研究，还是一起做？同一个搜索意图在百度和 Google 上的搜索量差异，你们怎么处理？」

---

**Part 2 — Technical & On-Page SEO**

21 个清单条目，大部分是标准 checklist，我们已经做了大半。
21-item checklist, mostly standard. We've done most of it already.

值得确认的 3 条 / 3 worth confirming:
1. "XML Sitemap re-submission" — we fixed the noindex issue, should resubmit to GSC
2. "URL Canonicalization" — worth checking our canonical tags are correct
3. "Schema Markup" — we fixed the City type, worth running through validator again

---

**Part 3 — Backlink Drive**

这是最需要警惕的部分。
This is the section to be most careful about.

他们列的战术 / Their listed tactics:
- ✅ High TLD Links — 合理，真实域名的链接
- ✅ Competitor Link Acquisition — 合理，分析竞争对手的链接来源
- ✅ Broken Link Building — 合理，白帽手法
- ⚠️ Web 2.0 — 灰色地带，Blogger/WordPress 上建站再链接
- ⚠️ Tiered Links — Google 明确打压的手法
- ⚠️ Link Wheels — 同上，人工链接网络
- ⚠️ Google Stacking — 用 Google 自家产品（Docs/Sites）建链，钻空子的手法
- ⚠️ Backlink Indexing using Python — 用脚本强制索引链接，风险高

**直接问 / Say directly:**
> "I see tiered backlinks and link wheels in Month 3. Those are tactics Google has been cracking down on for years. If we get hit with a manual penalty, what's your recovery plan, and do you take responsibility for that?"
> 「第 3 个月我看到 tiered backlinks 和 link wheels。这些是 Google 多年来一直在打压的手法。如果我们因此收到手动处罚，你们的恢复方案是什么，这个责任你们承担吗？」

---

**Part 4 — Programmatic SEO Tactics**

Click Gap Analysis + Dynamic Schema with Tag Manager + FAQ Schema + Passage Indexing

这部分技术含量最高，也是最值得学的。
Highest technical value in the whole deck. Most worth learning from.

**问 / Ask:**
> "The Click Gap Analysis using Regex on GSC data — can you walk me through exactly how you do that? What's the query pattern you use to filter branded vs non-branded terms?"
> 「用 Regex 在 GSC 数据上跑 Click Gap Analysis——能详细说说怎么做吗？你们用什么 query pattern 来区分品牌词和非品牌词？」

> "For the dynamic schema injection via GTM — we don't currently use GTM. Is there a server-side equivalent approach that would work with our FastAPI backend?"
> 「GTM 动态注入 schema——我们目前没用 GTM。有没有服务端的等效方案，可以配合我们的 FastAPI 后端？」

---

**Part 5 & 6 — Monthly Activities (Months 1-6)**

Slide 36-41，每个月的任务清单。

一眼扫完就够，不用逐条看。关键判断：
Skim through it. The key judgment:

- Month 1-2：合理，标准 on-page + 少量外链
- Month 3：出现 tiered links、high TLD backlinks — 这里要追问
- Month 4：Google Stacking、Voice Search — 前者风险，后者对中文市场意义不大
- Month 5：CTR Optimization、Entity Schema for Knowledge Graph — 这两个值得深聊
- Month 6：Link Wheel 又出现了 — 再次确认他们的风险态度

---

**🚩 The Slide They Forgot to Edit / 他们忘了改的一页**

Slide 24 in the Strategy doc literally says:
> "…featured snippets for important informational search terms **in insurance based businesses**."

第 24 页原文里出现了"insurance based businesses"（保险类业务）。
这是从其他客户提案直接复制过来没改的。

**可以轻松一句 / You can say lightly:**
> "Quick one — Slide 24 mentions insurance-based businesses. I think that might be from a different client's deck?"
> 「小问题——第 24 页提到了 insurance-based businesses，这应该是从别的客户方案复制过来没改掉的？」

这句话不用刁难，轻描淡写说就行。他们会怎么反应，你自己判断。

---

## QUICK CHEAT — 最后 30 秒过一遍
## QUICK CHEAT — 30-second scan before the call

- 底牌：sitemap noindex 他们没发现，schema 根因他们说不清
- 主动抛：Render 子域名 = 借来的 DA，不是自己的
- 逼数字：Month 3 具体目标，不接受模糊答案
- 底线：不谈 retainer，可以谈 case study
- 增长框架：我们在 AARRR 的 Acquisition = 0，PLG 产品，SEO 是发现渠道不是说服渠道
- 那页没改的 slide：insurance based businesses，轻描淡写提一下

---

- Hidden hand: sitemap noindex they missed, schema root cause they can't explain
- Raise first: Render subdomain = borrowed DA, not ours
- Push for numbers: Month 3 specific targets, no vague answers
- Bottom line: no retainer, open to case study
- Growth lens: we're at Acquisition = 0 in AARRR, PLG product, SEO is a discovery channel not a persuasion channel
- The slide they forgot to edit: "insurance based businesses" — mention it lightly
