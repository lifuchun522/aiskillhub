---
name: cdpfetch
display_name: 真实浏览器抓取与证据看板
display_name_en: Real-Browser Fetch & Evidence Dashboard
description: |
  用真实浏览器并发抓取多个目标页的渲染后内容，落盘留证，再产出可回溯的单文件 HTML 对比看板。
  两条通道：CDP 直连本地 Chrome/Edge（带登录态，适合内部系统与强反爬站点），
  或 Playwright 无头 Chromium（隔离、适合公开站点批量取数）。
  触发场景：用户说「抓取/调研这几个官网或仓库做对比」「做一份竞品对比看板」「多来源取数并标注来源和抓取时间」
  「把这些页面的定价/模型/参数整理成对比表」「需要登录才能看的页面抓下来」「批量打开 N 个网页汇总」。
  核心纪律：数据必须真实抓取、逐条可回溯到 URL 与抓取时间，不得编造或用二手转述充当一手事实。
description_zh: >-
  真实浏览器抓取 + 证据看板。CDP 直连本地浏览器（带登录态）或 Playwright 无头并发抓取，
  落盘正文/链接/DOM 与存证清单，产出全内联单文件 HTML 对比看板，并在真实浏览器中做确定性验证。
description_en: >-
  Fetch pages with a real browser (CDP to your local Chrome/Edge with login state, or headless
  Playwright), persist evidence manifests, and ship a self-contained single-file HTML comparison
  dashboard verified in a real browser.
version: 1.0.0
author: 李福春 资深架构师
---

# 真实浏览器抓取与证据看板（cdpfetch）

## 何时使用此 Skill

- 「抓取 A、B、C 这 5 个产品的官网，整理成对比看板」
- 「调研这几个开源仓库，比一下定位、协议、活跃度」
- 「把这些页面的定价档位拉下来做张表」
- 需要**登录态**才能看的页面、内部系统、强反爬站点
- 任何「多来源并行取数 + 结果要标注来源与抓取时间」的任务

**不适用**：单页单字段的查询（直接 WebFetch 更快）；纯搜索发现问题（用搜索引擎）。

---

## 零、三条不可让步的纪律

这三条决定了产出物是「调研结果」还是「看起来很专业的编造」：

1. **数据只能来自真实抓取。** 页面没写的信息就写「未公开」，绝不用印象补全。
   定价、配额、协议、模型、上下文长度这类会变的数值，**必须回官网一手页**。
2. **每条数据都要能回溯**到 URL + 抓取时间 + HTTP 状态。落盘存证是硬要求，不是可选项。
3. **一手优先于二手。** 多个媒体引用同一个错误会造成循环印证假象。
   搜索引擎只用于**发现**来源，不用于**证明**真伪。

---

## 一、前置检查

```bash
node scripts/cdp_probe.mjs --json          # CDP 通道是否可用（available: true/false）
python -c "import playwright" 2>&1         # Playwright 是否就绪
```

按结果选通道，**不要默认 CDP**：

| 情况 | 走哪条 |
|---|---|
| 需要登录态 / 内部系统 / 强反爬 | CDP 直连；端口未开时优先自解（见 `references/channels.md` 第三节） |
| 公开官网、文档站、批量取数 | **Playwright 无头**（默认，零侵入） |
| Node < 22 | Playwright 无头（`cdp_fetch.mjs` 需 Node 22+ 的原生 WebSocket） |

依赖缺失时自行补齐，不要把这个前置问题抛给用户：

```bash
pip install playwright && playwright install chromium
```

---

## 二、五步流程

### 第 1 步 · 编目：把「要采什么」变成结构化清单

先想清楚**每个目标要采哪些维度**，再写清单。维度决定了你要抓哪些页面——
例如对比产品时，一个产品通常需要「官网首页 + 定价页 + 文档站 + 仓库页」四类。

```json
[
  { "key": "vendorA_home",    "url": "https://www.example-a.com/" },
  { "key": "vendorA_pricing", "url": "https://www.example-a.com/pricing" }
]
```

- `key` 必须唯一（决定落盘文件名，重复会互相覆盖——脚本会直接报错拦下）
- `key` 带来源前缀，便于后续按产品聚合
- 模板见 [`templates/targets.example.json`](templates/targets.example.json)

### 第 2 步 · 抓取：真实浏览器渲染，并发落盘

```bash
# Playwright 无头通道（默认）
python scripts/fetch_pages.py --targets targets.json --out ./raw --concurrency 5

# CDP 直连通道（带登录态）
node scripts/cdp_fetch.mjs --targets targets.json --out ./raw --concurrency 3
```

脚本已内置三件容易漏的事，**不要自己另写一遍**：

- 导航后**基础等待**（SPA 水合、接口回调需要时间，等太短抓到空壳）
- **滚动触发懒加载**（不滚到底，页面下半部分根本不进 DOM）
- **失败即数据**（单个目标失败写进存证不中断整批）
- **浏览器错误页识别**（CDP 通道不回传状态码，导航失败会停在错误页上——
  靠 `chrome-error://` 与 `#main-frame-error` 判定，否则会把错误页记成抓取成功）

同时落盘 `.txt`（正文）/ `.links.txt`（链接）/ `.html`（DOM 快照）/ `_manifest.json`（存证）。

**抓完先看 `_manifest.json`**：`text_len` 明显偏小的目标要加大 `--scroll` 重抓，
不要拿一份残缺正文去下结论。

### 第 3 步 · 取一手事实 + 交叉印证

- 关键数值回**官网一手页**（定价页 / 文档 / 仓库）
- 开源项目的客观指标走平台 API，别转述页面文字：

```bash
node scripts/gh_metrics.mjs agentscope-ai/agentscope langchain-ai/langchain microsoft/autogen \
  --out gh_metrics.json
```

- 一手与二手冲突 → **把冲突写进洞察**，指明「哪些站点仍在传播旧数据」
- 拿不到的字段写「未公开」，不猜

字段规范与交叉印证口径见 [`references/evidence-schema.md`](references/evidence-schema.md)。

### 第 4 步 · 出看板：全内联单文件 HTML

产出单文件 HTML，含产品卡片矩阵 + 维度横向对比表 + 可视化（价格条形图、能力雷达图）+ 证据表。
硬约束：所有 CSS/JS/SVG 内联、**0 个外部引用**、导航用按钮滚动而非锚点、中英双侧编译。
完整规范见 [`references/dashboard-spec.md`](references/dashboard-spec.md)。

自建的评分/指数必须在页内公开规则并标注「非厂商官方评分」。

### 第 5 步 · 验证：在真实浏览器里做确定性核验

```bash
python scripts/verify_dashboard.py --file dashboard.html --spec spec.json \
  --shots ./shots --sections "#sec-cards,#sec-price" --toggle-lang
```

报「全绿」之前先确保覆盖全，报「有问题」之前先证伪自己。检查项：

| 检查 | 期望 |
|---|---|
| 控制台错误 | 0（有 `pageerror` 更要警惕） |
| 外部资源引用 | 0（`link` / `script[src]` / `img[src]`） |
| 锚点 `a[href]` | 0（纯单文件交付） |
| 各区块 DOM 计数 | 与规格一致，**意外减少即为回归** |
| 中英切换 | **整页正文指纹**切过去变化、切回来还原；`lang` 属性同步变化 |
| 按钮导航 | **逐按钮**验证是否真滚到目标区块（目标顶边贴齐视口顶，含容差） |

截图只作补充证据，**不作唯一依据**——单点肉眼确认在 12px 文字上不可靠。

> **判据要锚定语义，不要锚定表象。** 「首个按钮点击后 `scrollY > 0`」是错的判据——
> 首个按钮通常指向页首区块，点完 `scrollY` 本就该是 0；
> 用某个元素做语言切换的取样也可能踩到中英同形的词（如产品名）。
> 这两个坑都真实发生过，见 [`references/pitfalls.md`](references/pitfalls.md) P1-5。
>
> 验证器写完必须**拿故意做坏的样本反向跑一遍**，确认它真会报红——
> 只验证「能报绿」的验证器，等于没验证。

---

## 三、交付时说什么

明说三件事，缺一不可：

1. **抓取窗口**：`_manifest.json` 里 `fetched_at` 的最小值 → 最大值（写明时区）
2. **采集范围**：N 个目标、成功 M 个、失败项及原因
3. **口径说明**：哪些是官网一手、哪些来自平台 API、哪些是自建指数、哪些字段「未公开」

---

## 四、脚本索引

| 脚本 | 通道 | 作用 |
|---|---|---|
| [`scripts/cdp_probe.mjs`](scripts/cdp_probe.mjs) | — | 探测本地浏览器 CDP 调试端点是否可用 |
| [`scripts/cdp_fetch.mjs`](scripts/cdp_fetch.mjs) | CDP | 直连本地浏览器抓取，**带登录态**，只用自建后台 tab |
| [`scripts/fetch_pages.py`](scripts/fetch_pages.py) | Playwright | 无头并发抓取，零侵入，产出格式与 CDP 通道一致 |
| [`scripts/gh_metrics.mjs`](scripts/gh_metrics.mjs) | — | GitHub REST API 取 star / 协议 / 最近提交等客观指标 |
| [`scripts/verify_dashboard.py`](scripts/verify_dashboard.py) | Playwright | 产出物确定性验证 + 分区块截图 |

## 五、References 索引

| 文件 | 何时读 |
|---|---|
| [`references/channels.md`](references/channels.md) | 不确定走哪条通道、需要开 CDP 端口时 |
| [`references/evidence-schema.md`](references/evidence-schema.md) | 要写存证、生成证据表、处理来源冲突时 |
| [`references/dashboard-spec.md`](references/dashboard-spec.md) | 构建看板、选可视化、写验证规格时 |
| [`references/pitfalls.md`](references/pitfalls.md) | **开始前先扫一遍**，每条都是真实返工 |
