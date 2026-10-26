# aiskillhub

**AI Agent Skills 集合** —— 把日常工作中反复踩坑的流程，沉淀成可安装、可复用的技能包。

每个技能都遵循通用的 `SKILL.md` 规范，可在 WorkBuddy、Claude Code、Codex、Cursor 等支持 Agent Skills 的工具中安装使用。

作者：[李福春 · 资深架构师](https://github.com/lifuchun522)　·　信条：「把复杂系统，设计成简单可依赖的产品。」

---

## 目录组织

仓库按**宿主工具**分目录，每个工具下按**技能类型**再分一层；不绑定宿主的通用技能统一放 `sa/`：

```
aiskillhub/
├── workbuddy/                    # 面向 WorkBuddy 的技能
│   └── skill/                    # 通用 Skill（标准 SKILL.md 规范）
│       ├── wechat-article-workflow/
│       ├── aicheck/
│       ├── d12/                  # 交付前十二项门禁（宿主无关版 v1.0.0）
│       ├── cdpfetch/
│       ├── cleanc/               # Windows C 盘可清理目录扫描与安全清理（v1.0.0）
│       ├── eli5a/                # ELI5 微信图文：1000 字以内 + 配图 + 单文件 HTML（v1.0.0）
│       ├── zpj/                  # 表单驱动作品集生成（v2.0.0）
│       └── zaobao/               # 早报三问（hy3 出图版 v6.2）
├── gpt/                          # 面向 GPT / ChatGPT 自定义 Skill 的技能
│   └── skill/
│       └── zaobao/               # 同一技能的 GPT 版（Image 2.5 出图 v6.1）
└── sa/                           # 通用技能（不绑定宿主工具，WorkBuddy / Claude Code / Codex / Cursor 通用）
    └── skill/
        └── ontology-dev/         # 本体驱动业务系统开发（需求探索 → 本体建模 → 应用构建，v9）
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

### ELI5 微信图文（eli5a）

把一件刚发生的技术事件，写成 **500 字（上限 1000）**、配 3-6 张图、**能直接粘进公众号源码模式**的单文件 HTML 图文。写法是 ELI5，篇幅是纪律，微信兼容性靠实测。

它解决的不是「怎么让 AI 写出好文章」——那是内容本身。它解决的是**发出去之后才发现是废的**那些工程问题：`<style>` 块被微信吃掉导致版式全塌、`radio + :checked` 做的 tab 在编辑器里失效后两个面板同时亮、base64 图微信正文不接收、图注写在页面上把 1000 字配额啃掉 40-70 字、标题用 `<br>` 换行在微信端渲染不一致。

五条硬约束全部可验证：

- **篇幅**：页面正文 ≤1000 中文字（目标 500），`[\u4e00-\u9fff]` 正则计数，先写 1000 再砍到 500
- **标题**：单行 ≤12 字，爆炸点是反常识/反差/数字冲突，渲染后量 `h1` 高度 / 行高 = 1
- **章节**：编号徽章 01 + 论点式短名（≤10 字），固定四幕递进：是什么 → 变了什么 → 卡在哪 → 一句话带走
- **图注**：画进图片底部 84px 深蓝条**左侧**，品牌水印在**右侧**同一行；页面无图注 div、无「图一/图二」
- **结尾**：无品牌口号行，最后一幕「一句话带走」给全文唯一要记住的那句

最有价值的一条踩坑：占位符写成 `<img {{IMG1}}>` 而不是 `<img src="{{IMG1}}">`，替换后 data URI 变成一个无值属性，`src` 根本不存在——图不是破图，而是变成**一条 2px 带描边的细线**，肉眼像分隔线。`img` 计数、`data:` 计数、外链布尔全部正常，**只有实渲染截图能抓到**。这条现在已经是 `build.py` 的固定检查项。

- 技能目录：[`workbuddy/skill/eli5a/`](./workbuddy/skill/eli5a/)
- 使用说明：[`workbuddy/skill/eli5a/README.md`](./workbuddy/skill/eli5a/README.md)
- 技能入口：[`workbuddy/skill/eli5a/SKILL.md`](./workbuddy/skill/eli5a/SKILL.md)
- 踩坑清单：[`workbuddy/skill/eli5a/references/pitfalls.md`](./workbuddy/skill/eli5a/references/pitfalls.md)
- Wiki 摘要：[`wiki/eli5a.md`](./wiki/eli5a.md)

**它包含什么**：`SKILL.md`（交付标准 + 七步流程 + 四条排版铁律）、4 份 references（风格速查 / 微信红线 / 流水线与校验 / 踩坑清单）、一个 677px 天蓝纸感模板、一个 `build.py`（水印+图注 → 压缩 → base64 内联 → 独立 JPG → 13 项字符级校验），以及三篇成稿拆解加一份可运行样例（`qiyuan-demo.html`，572 字 / 4 图 / 384 KB）。

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

### 交付前十二项门禁（d12）

同一套 D1–D12 门禁的**宿主无关可移植版**：不绑定任何平台的工具名，措辞里不出现「调用 Skill 工具」这类专属表述。四个宿主（WorkBuddy / Cursor / Claude Code / Codex）共用同一份 `SKILL.md`，差别只在两件事——**怎么算真加载**、**常开规则写在哪**。

它解决的是**能力足够却主动降级**：四起真实返工里没有一起报错，全是「做不到却写成做完了」。最危险的不是「忘了做」，是**用一句合规声明掩盖没做**：

- **D5 尾巴豁免** —— 正文审过，最后一句写「这两步不阻塞当前」；而「已过门禁」的声明只覆盖正文，尾巴被发了免检通行证
- **D12 先盖章后干活** —— 回合开头先加载技能，干活，再宣称已审。那是盖章，不是拦截：审的是「计划要发的内容」，不是「实际要发的最终内容」
- **D11 语言后门** —— 写规则时预埋「不得为某目的而…」这类动机条件式禁止，等于给自己留一个「我目的不是 X」的开脱钩子

配套三份 references（逐项手册 / 四宿主接线 / 四起事故复盘）与三份 examples（合格快照 ×3 / 命中→返工→重跑全过程）。

- 技能目录：[`workbuddy/skill/d12/`](./workbuddy/skill/d12/)
- 使用说明：[`workbuddy/skill/d12/README.md`](./workbuddy/skill/d12/README.md)
- 技能入口：[`workbuddy/skill/d12/SKILL.md`](./workbuddy/skill/d12/SKILL.md)
- 逐项手册：[`workbuddy/skill/d12/references/gates.md`](./workbuddy/skill/d12/references/gates.md)
- Wiki 摘要：[`wiki/d12.md`](./wiki/d12.md)

**它包含什么**：一份宿主无关的 `SKILL.md`（加载契约 + 十二门禁 + 快照格式 + 返工四步 + 五条常见误用）、逐项检查手册（查什么/命中信号/证据要求/常见误判）、四宿主可直接粘贴的常开规则片段与五个接线陷阱、四起真实返工复盘，以及三份可直接照抄的快照样例。

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

### Windows 磁盘可清理目录扫描与安全清理（cleanc）

把「C 盘满了，帮我清一下」变成 **只读扫描 → 授权清单 → 网页逐条确认 → 全字段日志** 的一条闭环。低风险项给清理按钮一键清，中风险项只写清清理后果，系统目录只给命令不代跑。

它解决的不是「怎么找出大文件」——那是基础能力。它解决的是删磁盘时那些**反复踩、反复忘的工程问题**：删除调用被宿主策略**静默忽略**却返回成功、任务挂起导致页面永远停在「执行中」、Windows 的 `SO_REUSEADDR` 让新旧两个服务实例同时监听同一端口、`.bat` 被统一成 LF 之后双击报解析错误。

三条最硬的约束：

- **不碰操作系统文件是代码级的** —— `C:\Windows`、`C:\Program Files*`、`C:\ProgramData`、`C:\Users` 裸根、盘根、`$RECYCLE.BIN` 等进独立于清单的 `NO_GO` 黑名单，即使写进 `targets.json` 且 `authorized: true` 也删不动；外加双闸门（只有 `risk=low && authorized=true` 可删，且路径必须落在本次扫描解析出的授权集合内）。
- **不报假绿** —— 删除后**必须重新测量体积**才判 `OK`。只凭「调用没抛异常」就报成功，会在删除被静默忽略时给用户一个撒谎的结果。
- **删不掉就交还命令** —— 权限不足给 `takeown` + `icacls`，进程占用给 `Remove-Item` / `rmdir`，批量删除被拦截则如实标 `BLOCKED` / `TIMEOUT` 并给出可复制的手工命令，不绕过策略、不硬扛。

- 技能目录：[`workbuddy/skill/cleanc/`](./workbuddy/skill/cleanc/)
- 使用说明：[`workbuddy/skill/cleanc/README.md`](./workbuddy/skill/cleanc/README.md)
- 完整使用文档：[`workbuddy/skill/cleanc/references/usage-windows.md`](./workbuddy/skill/cleanc/references/usage-windows.md)
- 技能入口：[`workbuddy/skill/cleanc/SKILL.md`](./workbuddy/skill/cleanc/SKILL.md)
- Wiki 摘要：[`wiki/cleanc.md`](./wiki/cleanc.md)

**它包含什么**：一个 736 行的纯标准库 `server.py`（只读扫描 + 授权清理 + HTTP API + 内置管理页）、一张带 `impact` 后果说明的授权清单 `targets.json`、37 项断言的端到端自检 `selftest.py`、一个可选的真实浏览器实跑脚本 `tests/verify_browser.py`，以及两份 references（安全边界 / 完整使用文档）。实测基线来自一台真实开发机：C 盘 298 GB 已用、仅剩 1.8 GB，`C:\Users` 独占 222 GB。

---

### 表单驱动作品集生成（zpj）

填一张**离线表单**，当场得到一个离线可用、零依赖的单页作品集 HTML —— 手机、微信、企业微信、钉钉里打开都正常；也可以只用一份 `content.json` 走命令行流水线，进 CI。**两条入口，一份模板**，产出的页面结构逐项等价，这一点由测试断言。

它解决的不是「怎么排版」——那是模板的事。它解决的是作品集**反复改版**时那些容易悄悄坏掉的连带修改：删了一个区块、导航里那个链接还指着它；删掉最后一块、留下一条光秃秃的分隔线；项目顺序调了，章节序号 01/02/03 却没跟着动。上一代（`jl-zpj`，简历 PDF → 命令行）靠的是一份「删区块要连带清九处」的人工纪律，漏一处不报错，只是页面悄悄坏掉。

这一版把它换成了四种**声明式标记**：

- `<!--SEC:key-->` —— 数据为空则整块消失；
- `<!--NAV:id-->` —— 区块消失，导航项一起消失（`verify.py` 断言无死链）；
- `<!--HR-->` —— 区块间分隔线，渲染后归一（限定在 `<main>` 内，首尾与重复的一律去掉）；
- `<!--N-->` —— 章节序号按 DOM 顺序自动编号，不可能与顺序脱钩。

- 技能目录：[`workbuddy/skill/zpj/`](./workbuddy/skill/zpj/)
- 采集表单：[`workbuddy/skill/zpj/assets/form.html`](./workbuddy/skill/zpj/assets/form.html)
- 使用说明：[`workbuddy/skill/zpj/README.md`](./workbuddy/skill/zpj/README.md)
- 技能入口：[`workbuddy/skill/zpj/SKILL.md`](./workbuddy/skill/zpj/SKILL.md)
- Wiki 摘要：[`wiki/zpj.md`](./wiki/zpj.md)

**它包含什么**：一张 723 KB 的离线采集表单（九个区块 + 内嵌模板与示例 + 浏览器端渲染引擎 + 进度/检查面板）、一份 573 行的模板骨架（单一事实来源）、5 个脚本（注入校验 / 演示数据 / 构建 / 五端渲染自检 / 打包）、3 个示例（3 KB 最小可用 / 9 项目满配 / 表单内联版）、67 项自动化测试（含「表单生成的页面 vs 命令行构建的页面」逐项比对），以及 4 份 references。开发期抓到四个**不报错、文字全对**的真 bug（资源字典形状错位导致图全破、动态列表行只写 `placeholder` 导致导出全空、分隔线归一未限定 `<main>` 导致删首块后多一条线、自检把「未配证书 / 二维码」判成失败），四条都已变成硬断言。

---

### 架构师早报三问与同盟讨论（zaobao · WorkBuddy 版 v6.2）

把「三栏早报」变成可发群、可进微信、可二次创作的一套产物：芒格三问三答、同盟讨论帖、两份微信友好 HTML、hy3 手绘白板与分栏截图。日常用法只有两步——**一段早报原文 + 一个技能名 `/zaobao`**，默认只交付一个带本地时间戳的 `article-YYYYMMDDHHMM.zip`，不含 Skill 目录。

它解决的不是「怎么写早报」——那是内容本身。它解决的是流水线里那些**容易偷工或混包**的工程合同：栏目不得挪用、图必须来自真实出图模型、首页导航只准三个入口、全部链接新页签、交付前过 D1–D12。

这一版最值得记的是**换模型带出的两个坑**：出图模型 hy3 不按你给的尺寸出图（实测 `1440×1072` 与 `1024×1024`），而裁剪坐标是按 `1448×1086` 写死的 → 补上画布归一 + ±28% 宽高比守卫；检测脚本把一张好图误判为「特征不足」，根因是采样网格 `160×90` 太粗、把细密线条平均掉了 → 改成 `320×180` 后恢复正常。**检测脚本报错时，先问「是图错了，还是尺子错了」。**

- 技能目录：[`workbuddy/skill/zaobao/`](./workbuddy/skill/zaobao/)
- 使用说明：[`workbuddy/skill/zaobao/README.md`](./workbuddy/skill/zaobao/README.md)（含完整实战记录）
- 技能入口：[`workbuddy/skill/zaobao/SKILL.md`](./workbuddy/skill/zaobao/SKILL.md)
- Wiki 摘要：[`wiki/zaobao-workbuddy.md`](./wiki/zaobao-workbuddy.md)

**它包含什么**：`build.py`（校验 → 画布归一 → 切图 → 生成 HTML/MD → 打包命名）、浏览器渲染 QA、单测回归样例、白板风格参考图、真实交付包 `article-202610101434.zip`，以及 D1–D12 / wxp-json / v6.2 release notes 等 references。

---

### 架构师早报三问与同盟讨论（zaobao · GPT 版 v6.1）

把「三栏早报」变成可发群、可进微信、可二次创作的一套产物：芒格三问三答、同盟讨论帖、两份微信友好 HTML、Image 2.5 手绘白板与分栏截图。默认只交付一个带本地时间戳的 `article-YYYYMMDDHHMM.zip`，不含 Skill 目录。

它解决的不是「怎么写早报」——那是内容本身。它解决的是流水线里那些**容易偷工或混包**的工程合同：栏目不得挪用、图必须来自真实 ImageGen、首页导航只准三个入口、全部链接新页签、交付前过 D1–D12。

- 技能目录：[`gpt/skill/zaobao/`](./gpt/skill/zaobao/)
- 使用说明：[`gpt/skill/zaobao/README.md`](./gpt/skill/zaobao/README.md)
- 技能入口：[`gpt/skill/zaobao/SKILL.md`](./gpt/skill/zaobao/SKILL.md)
- Wiki 摘要：[`wiki/zaobao.md`](./wiki/zaobao.md)

**它包含什么**：`build.py` 确定性打包、浏览器冒烟、单测回归样例、白板风格参考图，以及 D1–D12 / wxp-json 等 references。

---

### 本体驱动业务系统开发（ontology-dev · v9）

把「一段业务需求」变成「一套可运行管理系统」的技能：**需求探索 → 本体建模 → 应用构建**三步法，全程以七模型本体 YAML（M1/M2/M3/M5/M6/M7/MU）为唯一语义来源，最终产出严格对齐需求文档、本体模型与代码的 BS 系统。

它解决的不是「AI 会不会写代码」——那是模型的事。它解决的是**语义漂移**：需求做完就丢、模型一套代码一套、生成完了也不知道哪个功能对应需求哪一条。手段是三道门禁——需求探索 8 阶段逐阶段硬暂停等人确认、建模期可追溯性与引用一致性强制核对、开发期严格对齐四份规范。

最有价值的部分是它**自带可运行实物**：双技术底座（Python: Flask+SQLite / Go: Gin+PostgreSQL）+ 一个跑通的合同管理样例，两套端到端 `smoke_test.py` 实测全通过，复制即用，不是骨架加 TODO。

- 技能目录：[`sa/skill/ontology-dev/`](./sa/skill/ontology-dev/)
- 使用说明：[`sa/skill/ontology-dev/README.md`](./sa/skill/ontology-dev/README.md)
- 技能入口：[`sa/skill/ontology-dev/SKILL.md`](./sa/skill/ontology-dev/SKILL.md)
- Wiki 摘要（含实测测评）：[`wiki/ontology-dev.md`](./wiki/ontology-dev.md)

**它包含什么**：`SKILL.md`（三阶段 + 门禁 + 纪律）、5 份方法论文档（需求探索提示词 V9 / 七模型元规范 / 开发指导书 / 技术架构 / UI-UE 规范）、黄金范例（合同管理需求规格 + 七模型 YAML）、双技术底座，以及一个 13 项端到端全通过的完整应用样例。

> 来源与授权：本技能同步自上游 [`sharptoolbox/ontology-driven-dev`](https://github.com/sharptoolbox/ontology-driven-dev)（MIT License），保留原作者署名与 [`LICENSE`](./sa/skill/ontology-dev/LICENSE)。

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
