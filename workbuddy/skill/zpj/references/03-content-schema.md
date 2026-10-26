# 03 · content.json 字段规格

顶层只允许六个键：`paths / texts / card / metrics / images / content`。
多一个就报错退出（`build_portfolio.py` 的白名单门禁）—— 这是为了拦「键写错层级导致整块静默消失」。

```jsonc
{
  "paths":   { "out_dir": "…", "src_dir": "…" },
  "texts":   { "NAME": "…", "ROLE": "…", "ROLE_SHORT": "…", "TAGLINE": "…" },
  "metrics": [ ["15", "年+", "研发经验 / 7 年架构"] ],
  "card":    { "title": "…", "sub": "…", "hint": "…" },
  "images":  { "namecard": {"src": "…", "archive": "…"}, "…": {} },
  "content": { "intro": {}, "profile": {"rows": []}, "pillars": [], "stack": [],
               "timeline": [], "edu": {}, "cert_label": [], "qrs": [], "projects": [] }
}
```

---

## paths

| 字段 | 说明 |
|---|---|
| `out_dir` | 产物目录（`index.html` 与 `archive` 归档都落在这里）。必填 |
| `src_dir` | `images[].src` 写相对路径时的基准目录（缺省则按当前工作目录解析） |
| `external` | 图片外置目录名，如 `"img"`。**留空 = 全部内嵌成单文件** |

`external` 非空时，图片写到 `<out_dir>/<external>/…`，页面里存相对路径字符串而不是
`data:` URI。代价是产物从「一个文件」变成「一个目录」，收益是 `index.html` 从数 MB
降到几十 KB，且换图不必重新构建。

## texts

| token | 来源 | 缺省行为 |
|---|---|---|
| `NAME` | 用户 | 空串（构建时告警：标题与文件名会是空的） |
| `ROLE` | 用户 | 空串。只作为 `META_DESC` 的输入，模板不直接引用 |
| `ROLE_SHORT` | 用户 | 空串。只作为默认 `TITLE` 的输入（导航栏不再有品牌块），模板不直接引用 |
| `TAGLINE` | 用户 | 空串 → 首屏那行英文小字**整行不渲染** |
| `TITLE` | 派生 | `"{NAME} · {ROLE_SHORT} | 作品集"` |
| `META_DESC` | 派生 | `"{NAME} · {ROLE} 个人作品集"` |
| `CAP_LEAD` | 派生 | 01 区块引导语（用户可覆盖） |
| `STACK_LEAD` | 派生 | 02 区块引导语（用户可覆盖） |
| `CRED_H2` | 派生 | 04 区块标题，按实际渲染的「专业认证 / 个人主页」拼接；教育背景已独立成 06 区块 |
| `CAREER_LEAD` | 派生 | `"共 N 段履历，按时间由近及远排列。"` |
| `PROJ_LEAD` | 派生 | `"共 N 个项目，按时间由近及远排列…"` |

**记数文案由数据自动生成**，所以增删履历 / 项目之后不会出现「页面上写着 8 段、实际只有 7 段」。

## metrics —— 首屏数据条

```json
[ ["15", "年+", "研发经验 / 7 年架构"],
  ["800", "万+", "平台日活峰值"] ]
```
`[数值, 单位, 说明]`，单位可为空串。建议 4–6 条，全部是可核对的硬数字。
列数由条数自动写入 CSS 变量 `--mc`，条数与列数不会脱节。

**可以留空**（`"metrics": []`）：整条数据带不渲染，首屏直接是「名片 → 个人档案 → 自述」。
空数据带不会留下空白行，`verify.py` 对此打印 `SKIP` 而不是判缺。

## card —— 首屏名片

```json
{ "title": "李福春 · 名片", "sub": "资深架构师 · 深圳", "hint": "点击名片可放大 ↗" }
```
图片不走这里，走 `images.namecard`。**有 card 且 `images` 里真有 `namecard` 才渲染** ——
否则首屏只剩一行 tagline（不报错、不留空图）。

## images —— 资源字典

```json
"images": {
  "namecard": { "src": "…/author-lfc-card.jpg", "archive": "assets/名片.jpg" },
  "nh_agentx": { "src": "01-agentx.jpg", "max_w": 1440, "quality": 80,
                 "archive": "diagrams/手绘版/01-AgentX.jpg" },
  "agentx":    { "src": "…/pf_p7.png", "png8": true,
                 "archive": "diagrams/技术分层版/01-AgentX.png" },
  "qr_wechat": { "src": "qr-wechat.jpg", "as_png": true,
                 "archive": "assets/个人主页/qr-微信公众号.png" }
}
```

| 字段 | 默认 | 说明 |
|---|---|---|
| `src` | — | **磁盘路径** 或 **data URI**（表单导出格式）。相对路径按 `paths.src_dir` 解析 |
| `max_w` | 不缩放 | 超过该宽度则等比缩小 |
| `quality` | 82 | JPEG 质量（1–95 整数） |
| `as_png` | 按扩展名推断 | 强制输出 PNG |
| `png8` | false | PNG 量化为 256 色（架构图适用） |
| `passthrough` | true | 无需缩放且源格式 == 目标格式时直通原始字节 |
| `archive` | 不归档 | 原分辨率副本的相对路径（相对 `out_dir`）。**外置模式下跳过** |
| `group` | `misc` | 外置模式的默认子目录：`<external>/<group>/<key>.<ext>` |
| `file` | — | 外置模式的完整相对路径，优先于 `group` |

**资源键必须被正文引用到，或至少存在**：正文引用了 `images` 里没有的键 → 构建报错
（防「图永远加载不出来」）；`images` 里有没被引用的键 → 只是多占体积，不报错。

### 外置模式的扩展名规则

扩展名取的是**实际编码出的 MIME**，不是源文件后缀：

| 场景 | 源 | 编码后 | 落盘名 |
|---|---|---|---|
| 照片类被压成 JPEG | `main.png` | `image/jpeg` | `main.jpg` ✅ |
| 技术分层图量化 | `layer.png` | `image/png` | `layer.png` |
| 二维码无损 | `qr.jpg`（`as_png`） | `image/png` | `qr.png` |

写错这一步不会报错、文字也全对，只是浏览器按后缀猜 MIME 时**整页破图**。
所以 `tests/test_build.py::TestExternalAssets` 里的第一条断言就是「引用路径 == 落盘路径」。

## content

### intro
```json
{ "label": "ABOUT ME", "who": "李福春", "where": "资深架构师 · 深圳",
  "lead": "做了 <b>15 年研发</b>……", "paras": ["…", "…"], "facts": [["15 年+", "研发经验"]] }
```
- `who` / `where` 是左上角小栏（署名 / 城市）。**两者都留空则不渲染侧栏**，
  正文占满整行（`.intro.noside`）—— 姓名与定位已经由名片和档案条承载。
- `lead` / `paras` / `facts` 的 `说明` 位**允许内联 `<b>`**（渲染时不转义）。
- `paras` 可以是数组，也可以是「一行一段」的字符串。
- `facts` 可以是 `[[值, 说明]]`，也可以是「`值 | 说明` 一行一条」的字符串。

### pillars
```json
[{ "icon": "arch", "title": "系统架构", "desc": "…", "tags": ["高并发", "分布式"] }]
```
`icon` 取值：`arch / ai / lead / code / data / cloud / shield / rocket`（未知键回落 `arch`）。
`desc` 允许内联 `<b>`；`tags` 支持数组或 `" / "` 分隔的字符串。

### stack
```json
[ ["AI 应用与编排", "Java / Python / LLM / RAG", "可选：这一组用来做什么"] ]
```
标签串按 ` / ` 切分。第三项可选，允许内联 `<b>`。

### timeline
```json
[ ["2025.07 — 2026.07", "KA 项目负责人", "北京红棉小冰科技有限公司", true, ["要点一", "要点二"]] ]
```
`[时间, 职位, 公司, 是否现职, 要点]`。要点支持数组或「一行一条」字符串。
按时间**由近及远**排列（`verify.py` 会断言降序）。

### profile —— 首屏「个人档案」归纳条
```json
{ "rows": [ ["求职意向", "架构师 / 研发经理 <em>已离职 · 可即时到岗</em>"],
            ["基本信息", "1988.01 · 男 · 湖南常宁 <em>现居深圳</em>"] ] }
```
紧跟名片渲染的键值条（`.pf-i`），用来归纳税历表格里那些「不配进图片」的字段。
`rows` 可以是 `[[键, 值]]`，也可以是「`键 | 值` 一行一条」的字符串；值**不转义**，
允许内联 `<b>` / `<em>`。空数组 / 全空行 → 整块不渲染。

与名片的分工：名片（图片）只负责「脸 + 身份 + 联系方式」，
求职意向 / 基本信息 / 擅长领域 / 岗位优势走这里用文本渲染 —— 图片里的字在 320px 屏上读不出来。

### edu —— 教育背景（页面末区块）
```json
{ "tags": ["北华大学 · 软件工程 · 统招本科", "2011 年毕业", "英语 CET-4（515 分）"] }
```
`tags` 支持数组或字符串。**第一条作为主行**（学校 · 专业 · 学历），其余落成标签；
为空则 06 区块整段不渲染（导航项一起消失）。`label` 字段已废弃（区块标题固定为「教育背景」）。

### cert_label / qrs
```json
"cert_label": [ ["cert_lecturer", "腾讯云合作讲师", "WorkBuddy 开发者沙龙 · 深圳站"] ],
"qrs":        [ ["qr_wechat", "微信公众号", "http://weixin.qq.com/r/mp/…"] ]
```
第一项是 `images` 的资源键。**键为空则整项跳过**（还没选图不留空卡）；
二维码缺链接也跳过（不可点击的二维码没有意义）。

### projects
```json
[{
  "title": "AgentX 企业级智能体与工作流平台",
  "period": "2025.07 — 2026.07",
  "sub": "企业智能体 · 多模型调度 · MCP 工具协议",
  "desc": "问题是什么、平台承接什么",
  "result": "核心接口 <b>P99 下降 60%</b>，数据库负载下降 <b>40%</b>。",
  "steps": ["模型与工具统一接入：主导 <b>Java Agent Runtime</b>……", "…"],
  "chips": "Java / Spring Boot / MCP / RabbitMQ",
  "fig": "nh_agentx",
  "fig_title": "AgentX 企业级智能体与工作流平台 · 架构图",
  "fig_sub": "企业用户 → Web 管理台 → API Gateway → 编排引擎 → 中间件",
  "extra": [ ["agentx", "技术分层版：AgentX 系统架构图", "客户端层 → API 网关层 → …"] ]
}]
```

- **编号（01/02/…）不写在数据里**，由数组顺序生成 —— 删掉第一个项目后剩下的仍从 01 开始。
- `desc` / `result` / `steps` 允许内联 `<b>`。`steps` 是「动作」，`result` 是「成果」，
  技术名词归 `chips` —— 各管一处，不要重复。
- `fig` 是这个项目的**主架构图**；`extra` 是补充图（自动排成网格）。
- 顺序即展示顺序，请按时间由近及远。

---

## 写作纪律

1. **量化优先**：每个项目至少一条带数字的成果（`result`）。
2. **四段式**：`desc`（问题）→ `result`（成果）→ `steps`（动作）→ `chips`（技术栈）。
3. **不编造**：源材料里没有的指标不要写。
4. **不重复**：「提升约 3 倍 / 200+ 关键指标」这类无法证伪的表述换成具体动作与技术名词。
5. **不枚举**：正文里不硬编码项目名清单 —— 那会与卡片顺序各自漂移，读起来像「顺序不对」。

## 输出形状

| 配置 | 产物 |
|---|---|
| 不写 `paths.external`（默认） | `paths.out_dir/index.html` —— 自包含单页，图片全内联 |
| 写了 `paths.external` | `paths.out_dir/index.html`（只有几万字节）+ `<external>/<group\|file>` 下每张图一个文件 |

两种模式下 `images[].archive` 指定的原分辨率归档副本都会生成；**外置模式例外**——
同一份字节已经在 `<external>/` 落过一份，不再往 `diagrams/` 重复归档。

`--stats` 会把结构计数打印成一行 `STATS:{…}`，可直接喂给 CI 比对。外置模式下额外多三个键：
`external`（目录名）、`external_files`（`[{key, file, bytes}]`）、`assets_bytes`（字节合计）。

