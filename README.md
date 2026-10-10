# aiskillhub

**AI Agent Skills 集合** —— 把日常工作中反复踩坑的流程，沉淀成可安装、可复用的技能包。

每个技能都遵循通用的 `SKILL.md` 规范，可在 WorkBuddy、Claude Code、Codex、Cursor 等支持 Agent Skills 的工具中安装使用。

作者：[李福春 · 资深架构师](https://github.com/lifuchun522)　·　信条：「把复杂系统，设计成简单可依赖的产品。」

---

## 目录组织

仓库按**宿主工具**分目录，每个工具下按**技能类型**再分一层：

```
aiskillhub/
├── workbuddy/                    # 面向 WorkBuddy 的技能
│   └── skill/                    # 通用 Skill（标准 SKILL.md 规范）
│       ├── wechat-article-workflow/
│       ├── aicheck/
│       └── cdpfetch/
└── gpt/                          # 面向 GPT / ChatGPT 自定义 Skill 的技能
    └── skill/
        └── zaobao/
```

之所以先按工具分，是因为不同平台的技能虽然都叫 `SKILL.md`，但在**安装路径、元数据字段、脚本依赖**上各有各的约定。按工具分目录，安装时直接整目录拷贝，不用挑文件。

---

## 技能列表

### 公众号文章工作流

把「写公众号文章」这件事完整跑通的技能：从选题讨论一路走到推送草稿箱，十个步骤每一步都有脚本兜底。

它解决的不是「怎么写出好文章」——那是人的事。它解决的是流程里那些**反复踩、反复忘的工程问题**：微信编辑器吃掉的 HTML 怎么救回来、图片占位符怎么塞才不撞车、去 AI 味怎么去、系列文怎么保证不断线、草稿箱怎么自动推。

最有价值的部分是那份持续累积的**踩坑清单**（P0/P1/P2 三级，目前 37 条），每条都对应一次真实的返工。

- 技能目录：[`workbuddy/skill/wechat-article-workflow/`](./workbuddy/skill/wechat-article-workflow/)
- 使用说明：[`workbuddy/skill/wechat-article-workflow/README.md`](./workbuddy/skill/wechat-article-workflow/README.md)
- 技能入口：[`workbuddy/skill/wechat-article-workflow/SKILL.md`](./workbuddy/skill/wechat-article-workflow/SKILL.md)

**它包含什么**：完整的 10 步 SOP、微信兼容 HTML 规则（纯内联 `<section>` 方案）、自研的三种 Markdown 扩展语法（GFM 表格 / `> [!card]` 卡片 / 可点击链接）、双预览产物机制、系列文章连贯性七条铁律，以及 15 个可直接调用的 Python 脚本。

---

### AI 交付前全自动自检（aicheck）

一个**行为级**技能：在每一次向用户交付结果**之前**，强制加载并实跑一道 12 项闸门（D1–D12），拦截两类缓干形态——**把活推回用户**，和**用声明替代扫描**。

它没有脚本、没有 API，管的是**交付纪律**：责任归属、交付完整性、自检可信度。最核心的贡献是防「假装做了」而不只是「忘了做」：

- **D5 尾巴豁免** —— 正文自检过，收尾一句「这两步不阻塞当前」把最优步藏进免检区（技能自身最容易犯的形态）
- **D11 语言后门** —— 写规则时预埋「我目的不是 X」式开脱钩子；**措辞本身即违规，不论意图**
- **D12 加载时机** —— 禁止「先加载技能当合规盖章、后干活」的 stamp 模式，必须是发送前最后一道拦截

配套提供 `references/` 三份速查（闸门检测器 / 自带例子 / 前后对比）和一份可视化导读 `aicheck-guide.html`。

- 技能目录：[`workbuddy/skill/aicheck/`](./workbuddy/skill/aicheck/)
- 使用说明：[`workbuddy/skill/aicheck/README.md`](./workbuddy/skill/aicheck/README.md)
- 技能入口：[`workbuddy/skill/aicheck/SKILL.md`](./workbuddy/skill/aicheck/SKILL.md)
- 可视化导读：[`workbuddy/skill/aicheck/aicheck-guide.html`](./workbuddy/skill/aicheck/aicheck-guide.html)

---

### 真实浏览器抓取与证据看板（cdpfetch）

把「抓多个网页做对比」从「打开页面抄几行」变成**可回溯、可验证、可交付**的一条流水线。

它解决的不是「怎么把网页内容读出来」——那是基础能力。它解决的是抓取类任务里那些**反复踩、反复忘的工程问题**：懒加载没滚动导致拿到**看似完整实则残缺**的正文、CDP 通道根本不回传 HTTP 状态码（错误页也会显示 `status: 200`）、二手站点传播已下架的旧定价、单文件 HTML 被 CDN 依赖污染、报「验证通过」实则没覆盖全。

两条抓取通道，产出格式完全一致，下游无差别消费：

- **CDP 直连** —— 复用你日常的 Chrome / Edge，**天然携带登录态**，适合内部系统与强反爬站点
- **Playwright 无头** —— 独立 Chromium，**零侵入**，适合公开站点批量取数

最有价值的部分是那份 15 条**踩坑清单**（P0/P1/P2），包括一条反直觉的：**验证器自己的假阳性比不验证更危险**——初版验证器对一份已确认合格的看板报出 2 项 FAIL，两项都是验证器的错。

- 技能目录：[`workbuddy/skill/cdpfetch/`](./workbuddy/skill/cdpfetch/)
- 使用说明：[`workbuddy/skill/cdpfetch/README.md`](./workbuddy/skill/cdpfetch/README.md)
- 技能入口：[`workbuddy/skill/cdpfetch/SKILL.md`](./workbuddy/skill/cdpfetch/SKILL.md)
- 踩坑清单：[`workbuddy/skill/cdpfetch/references/pitfalls.md`](./workbuddy/skill/cdpfetch/references/pitfalls.md)

**它包含什么**：五步 SOP（编目 → 抓取 → 取一手事实 → 出看板 → 验证）、5 个可直接调用的脚本、4 份 references（双通道选型 / 存证字段规范 / 单文件看板规范 / 踩坑清单）。所有脚本都实跑验证过，含 CDP 通道端到端（起真实 Chromium + 抓取）与验证器的正例反例双向验证。

---

### 架构师早报三问与同盟讨论（zaobao）

把「三栏早报」变成可发群、可进微信、可二次创作的一套产物：芒格三问三答、同盟讨论帖、两份微信友好 HTML、Image 2.5 手绘白板与分栏截图。默认只交付一个带本地时间戳的 `article-YYYYMMDDHHMM.zip`，不含 Skill 目录。

它解决的不是「怎么写早报」——那是内容本身。它解决的是流水线里那些**容易偷工或混包**的工程合同：栏目不得挪用、图必须来自真实 ImageGen、首页导航只准三个入口、全部链接新页签、交付前过 D1–D12。

- 技能目录：[`gpt/skill/zaobao/`](./gpt/skill/zaobao/)
- 使用说明：[`gpt/skill/zaobao/README.md`](./gpt/skill/zaobao/README.md)
- 技能入口：[`gpt/skill/zaobao/SKILL.md`](./gpt/skill/zaobao/SKILL.md)
- Wiki 摘要：[`wiki/zaobao.md`](./wiki/zaobao.md)

**它包含什么**：`build.py` 确定性打包、浏览器冒烟、单测回归样例、白板风格参考图，以及 D1–D12 / wxp-json 等 references。

---

## 如何安装

每个技能目录都是一份自包含的技能包，**整目录拷贝**到你所用工具的 skills 目录即可。具体路径各工具不同，详见各技能自己的 README。

通用思路是：用户级放 `~/.<工具名>/skills/`（全项目可用），项目级放 `<项目>/.<工具名>/skills/`（随仓库共享，团队协作时更合适）。

安装后不需要额外配置。用自然语言提需求，技能会被自动识别。

> **例外**：`aicheck` 这类**行为级纪律**技能，装进 skills 目录还不够——它需要在每次请求都被注入的位置声明为「常开规则」（Cursor 用 `~/.cursor/rules/*.mdc` + `alwaysApply: true`，WorkBuddy 用用户级 `MEMORY.md`，Claude Code 用 `CLAUDE.md`，Codex 用 `AGENTS.md`）。各工具的具体落点见该技能 README。

---

## 一些约定

**技能必须有 `SKILL.md`**，且 frontmatter 至少含 `name` 与 `description`——`description` 写得好不好，直接决定技能能不能在正确的时机被唤起。写的时候要包含**触发句式**（用户会怎么说），而不只是功能罗列。

**踩坑清单比亚马逊最佳实践更有用。** 一个技能里最该持续更新的，不是「正确做法」那一节，而是「曾经错在哪」那一节。前者是常识，后者是经验。

**脚本与技能同目录。** 脚本放在技能的 `scripts/` 下，通过相对路径调用，避免散落到用户环境的各处。

---

## 授权

本仓库技能可自由用于个人与商业项目。转载或二次分发请保留作者署名。

---

## 联系

- 邮箱：hello@carter.li
- GitHub：[@lifuchun522](https://github.com/lifuchun522)
