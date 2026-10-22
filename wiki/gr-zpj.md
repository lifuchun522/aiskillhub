# gr-zpj｜表单驱动作品集生成（v1.1.0）

> 填一张表，当场得到一个**离线可用、零依赖**的单页作品集 HTML —— 手机、微信、企业微信、钉钉里打开都正常；也可以只用一份 `content.json` 走命令行流水线，进 CI。

仓库路径：[`workbuddy/skill/gr-zpj/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/gr-zpj)

采集表单（离线单文件，可直接双击）：[`assets/form.html`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/gr-zpj/assets/form.html)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/gr-zpj/SKILL.md) ｜ 概览：[`README.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/gr-zpj/README.md)

## 一句话

**两条入口，一份模板。** `assets/form.html` 在浏览器里填 → 生成 → 另存；`scripts/build_portfolio.py` 吃一份 `content.json` 直接构建。两条路产出的页面**结构与文本逐项等价**，这一点由测试断言，不靠人工保证。

## 它解决什么问题

做作品集的人手上往往只有零散材料：一段自述、几个项目、几张架构图、几张证书图。真正磨人的不是排版，是**反复改版**。

上一代作品集技能（`jl-zpj`）走的是「简历 PDF → 命令行流水线」，改一次版要按人工纪律同步九处（模板 DOM / 区块占位符 / token 段 / CSS / 手机断点 / 兜底层 / 白名单 / 渲染函数 / 导航与校验计数）。漏一处不报错，只是页面悄悄坏掉。

`gr-zpj` 把这件事换成**声明式标记**，让「删掉一块」不再需要连带改任何地方：

| 每次改版都要问自己的问题 | 本技能的做法 |
|---|---|
| 我把这一块删了，导航里那个链接还在吗？ | 区块消失则**导航项一起消失**（`<!--NAV:id-->`），`verify.py` 断言无死链 |
| 我把最后一块删了，会不会留下一条光秃秃的分隔线？ | 分隔线归一（`<!--HR-->`）**限定在 `<main>` 内**处理，首尾 / 重复的一律去掉 |
| 项目顺序调了，章节序号 01/02/03 要手改吗？ | 序号按 DOM 顺序**自动生成**（`<!--N-->`），不可能与顺序脱钩 |
| 页面写着「8 段履历」，实际只有 7 段？ | 记数文案由数据生成（`CAREER_LEAD` / `PROJ_LEAD`），不写死 |
| 我删掉第一个项目，剩下的编号要重排吗？ | 编号由数组顺序生成，删完仍从 01 开始 |
| 改完模板，表单里的预览还是旧的？ | `sync_assets.py --check` + 单测守着「两处必须是同一份」 |
| 「手机上打开对不对」怎么证明？ | 真实 UA 起 5 个 profile，每端查四件事，退出码非 0 即不过 |
| 改文案后旧词真的清干净了吗？ | `verify.py --must / --absent` —— 整页肉眼扫不出来 |
| 图片要能单独替换，不想每次都重新构建整页？ | 配 `paths.external`，图落到 `img/<项目>/<名>.<ext>`，页面只存相对路径 |
| 早期项目没留架构图，会不会占一个空图位？ | `fig` 留空即只出文字卡，编号仍连续，不留空占位 |

## 安装

```bash
cp -r workbuddy/skill/gr-zpj ~/.workbuddy/skills/gr-zpj

cd ~/.workbuddy/skills/gr-zpj
python -m unittest discover -s tests -t . -v      # 62 项，全绿

# 只有命令行路径与自检需要
pip install pillow playwright
python -m playwright install chromium
```

**只走表单路径的话，一个第三方依赖都不用装** —— 双击 `assets/form.html` 就能用。

## 使用步骤

### 1 · 表单路径（双击就能用）

```bash
assets/form.html        # 双击 / 拖进浏览器都行
```

1. **载入示例** —— 先看成品长什么样（示例图片内联，离线可用）
2. 九个区块按需填写，右上角常驻**进度条 + 检查面板**
3. **生成作品集** → 弹层预览 → **另存 HTML**
4. **导出 JSON** 存断点，下次「导入 JSON」接着填

九个区块：基础信息 / 首屏数据条 / 首屏名片 / 第一人称自述 / 核心能力支柱 / 技术栈分组 / 工作经历 / 教育背景·专业认证·个人主页 / 我的项目。列表行都能增删，项目卡还能挂多张补充架构图。

检查面板会主动报出：姓名未填、项目无主图、项目没写关键动作、项目没写成果、项目无标签、二维码缺链接、产物体积超 5 MB、以及**导入的图是本机磁盘路径需要重新选**（磁盘路径图无法内联，会记入 `_dropped` 逐条列出，不静默丢弃）。

> 表单里的模板与示例是**内联字符串常量**（`/*@TPL-START@*/…` 与 `/*@DEMO-START@*/…`）。原因见踩坑 P1-4：`file://` 协议下无法 `fetch` 本地文件。

### 2 · 命令行路径

```bash
python scripts/build_portfolio.py examples/content.json --stats

python scripts/verify.py "<out>/index.html" \
    --expect nh_digitalhuman,nh_gfs,nh_herodash,nh_game,nh_lowcode,yunshu_tech \
    --last-section projects \
    --must "我的项目" --absent "重点项目" --shots shots/

python scripts/package.py "<out>"
```

`--stats` 打印一行 `STATS:{…}`，可直接喂给 CI 比对结构计数。

> `--expect` 只列**有主图**的项目（本项目里 07/08/09 没留架构图，`fig` 为空 → 只出文字卡，
> 不占图位）。无图项目用 `(无)` 标在 `[5]` 段输出里，不参与顺序比对。

### 3 · 图片编码策略

| 用途 | 目标宽度 | 格式 | 为什么 |
|---|---|---|---|
| 首屏名片 | 不缩放 | 原格式 | 卡面小字靠点开放大看 |
| 手绘架构图 | 1440 | JPEG q80 | 照片 / 手绘类素材 |
| 技术分层图 | 不缩放 | **PNG8 量化** | 线条 + 大色块，量化后肉眼无损、体积省一半以上 |
| 证书 | 620 | JPEG q84 | 只做缩略展示 |
| 二维码 | 不缩放 | **PNG 无损** | JPEG 会破坏定位图案，直接扫不出来 |

无需缩放且源格式 == 目标格式时**直通原始字节**，不做重编码 —— 避免画质累积损失。

### 3.5 · 图片内嵌还是外置

| 模式 | 配置 | 产物 | 适用 |
|---|---|---|---|
| 内嵌（默认） | 不写 `paths.external` | 单文件，图全在 `data:` URI 里 | 要发一份文件给别人的场合 |
| 外置 | `"paths": {"external": "img"}` | `img/<分组>/<名>.<ext>` + 只存相对路径的 `index.html` | 要换图、要进 CDN、要页面瘦身 |

外置模式的三条硬规矩：

1. **扩展名按实际编码出的 MIME 决定** —— 源图 png 被压成 jpeg 时文件必须叫 `.jpg`。
   写错不报错、文字也全对，只是浏览器按后缀猜类型会**静默破图**（踩坑 P0-4）；
2. **外置即跳过 `archive`** —— 同一份字节不在 `img/` 和 `diagrams/` 各落一份；
3. **产物从「一个文件」变成「一个目录」** —— 单独拷走 HTML 会全页破图，交付走 `package.py`。
   只想要单文件发出去时**不要配 `external`**。

图片按项目分组落在 `img/` 下，换一张架构图不必碰 `index.html`：

```
img/
├── card/namecard.jpg
├── p01-digital-human/{main.jpg, layer.png, agentx-main.jpg, agentx-layer.png}
├── p02-gfs/main.jpg
├── p03-ai-cs/{main.jpg, layer.png}
├── p04-chanyou/{main.jpg, layer.png}
├── p05-mofang/{main.jpg, layer.png}
├── p06-yunshu/{main.png, biz.png}
├── certs/  4 张
└── qr/     4 张
```


### 4 · 页面叙事顺序

`01 CAPABILITY → 02 TECH STACK → 03 CAREER → 04 CREDENTIAL → 05 MY PROJECTS`。
先把能力/技术栈/履历讲清，再用项目做实证；**没填的区块整块不出现**，序号自动重排。

## 本机实测

### 单测

```
Ran 62 tests in 67.7s

OK
```

分布：构建器 `test_build.py` 34 项 + 资产一致性 `test_sync.py` 9 项 + 浏览器端 `test_browser.py` 19 项。浏览器端 19 项要起 Chromium，耗时随机器负载在 65–100s 间浮动，项数恒为 62。

浏览器端 19 项里最要紧的是**两处渲染一致性（parity）**：把表单生成的页面与命令行构建的页面都灌进浏览器，逐项比对结构计数、章节序号、导航、缩放元素类型序列、可见文本、`<title>`、破图列表。「表单和命令行会不会漂移」从「但愿不会」变成一条可复算的断言。

新增两小组守着本轮改动：`TestExternalAssets`（4 项，图片真落盘 / 相对路径与落盘一致 / `file`+`group` 生效 / 外置跳过归档）与 `TestProjectWithoutFigure`（2 项，无主图只出文字卡 / 混排时编号连续）。

### 一份 13 项目 / 8 段履历的完整作品集（命令行路径 + 图片外置）

```
外置资源 1.77 MB ｜ index.html 0.07 MB ｜ 区块 capability+stack+career+credential+projects
计数 pillars 3 ｜ metrics 6 ｜ cards 13 ｜ certs 4 ｜ qrs 4 ｜ tl 8 ｜ stack 6 ｜ zoom 18
导航无死链 ✓  无遗留页脚 ✓  body 无游离区块 ✓  末尾非孤立分隔线 ✓
末区块为 projects ✓  章节序号按 DOM 顺序连续 ['01','02','03','04','05'] ✓
名片占屏宽比 77% (1108×624) ✓  名片已加载 ✓ 1672×941（外置）
主图映射顺序 ✓（6 项）  项目按时间降序 ✓  项目编号连续 01–13 ✓
五端（1440 / 820 / 390 / 360 / 320）无横向溢出 ✓  关键区块不超宽 ✓  正文字号 ≥14.5px ✓
PASS: 全部检查通过
```

`cards 13` 但 `主图映射` 只比 6 项 —— 只有 01–06 六个项目留存了架构图；云枢 PaaS、乐心健康云、乐心医生 SaaS、乐心保险中台、跨境电商供应链、第七大道页游平台、游戏官网群这 7 个 `fig` 留空走文字卡，编号仍然连续到 `13`。

`index.html` 从 v1.0.0 的 **2.41 MB 降到 68 KB**，22 张图按项目分到九组落在 `img/` 下。

### 同一次运行里，表单路径产物也过同一套自检

表单路径不做 PNG8 量化（浏览器里做不了调色板量化），演示尺寸内联 22 张图，产物 **0.66 MB**。把它丢进同一个 `verify.py`：

```
[0] 产物文本   无残留 模板 token / 区块标记 / 分隔线标记 / 序号标记   PASS
[2] 资源      破图 PASS []   图片总数>0 PASS imgs=23
[3] 结构      计数与命令行产物逐项一致  导航无死链 PASS  末尾非孤立分隔线 PASS
              末区块为 projects PASS  章节序号 ['01','02','03','04','05'] PASS
[7] 五端渲染  1440 / 820 / 390 / 360 / 320 全部无横向溢出、正文字号 ≥14.5px
PASS: 全部检查通过
```

### 开发期抓到的三个真 bug（都不报错、文字全对）

| 现象 | 真根因 | 是靠什么暴露的 |
|---|---|---|
| 表单生成的页面**全是破图**，文字与计数全对 | 资源字典形状错位：配置里是 `{key:{src:…}}`，运行时要字符串 `ASSETS[key]`，`el.src` 变成了 `"[object Object]"` | 截图肉眼看出来的；随后补了 `test_form_output_images_all_load` 断言 |
| 表单看着填满，导出的 JSON 全是空数组 | 动态生成的列表行**只写 `placeholder`、从不写 `value`**，且回填发生在行创建之前 | `window.__grzpj.payload()` 打出来看到 `[['','','']]` |
| 删掉首个区块后，页面开头凭空多一条分隔线 | 分隔线归一在**整篇 HTML** 上切分，页面前缀（nav / hero）被当成第一个非空片段 | 单测断言 `hr == 区块数 - 1` |

三条的共同点：**不抛异常、不报错，只是页面悄悄错**。这也是为什么这个技能的测试里破图、分隔线数量、序号连续性都是硬断言。

完整测试报告（62 项逐条明细、双路径 `verify.py` 原始输出、P0 bug 复盘、不可判定项清单）：[`TEST-REPORT.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/gr-zpj/TEST-REPORT.md)

## 判不了的部分（一律 NA，不写 PASS）

1. **内容好不好**：文案是否打动人、项目是否够分量 —— 人的判断，脚本给不了；
2. **图片审美**：架构图清不清晰、配色是否协调；
3. **浏览器之外**：真实微信 / 企业微信客户端内的最终渲染 —— 本技能用真实 UA 近似，**不是真机**；
4. **表单路径的体积优化**：浏览器里做不了 PNG8 调色板量化，这是能力边界，不是 bug；超过 5 MB 时检查面板会直接给出「改用命令行」的建议。

## 相关文件

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 技能规范、触发条件、五条设计原则、模板标记说明、关键注意事项 |
| `README.md` | 概览、安装、三条使用步骤、实测基线、能力边界 |
| `assets/form.html` | 采集表单（离线单文件，720 KB：内嵌模板 + 示例 + 浏览器端渲染引擎） |
| `assets/template.html` | 作品集模板骨架（**单一事实来源**，519 行） |
| `scripts/sync_assets.py` | 模板 / 示例 → 表单 的注入与一致性校验（`--check` 可入 CI） |
| `scripts/make_demo.py` | 生成演示尺寸的内联示例数据（`demo-content.json`，634 KB） |
| `scripts/build_portfolio.py` | `content.json` → 作品集 HTML（默认内嵌单文件；配 `paths.external` 则图片外置，645 行） |
| `scripts/verify.py` | 五端渲染自检 + 结构与内容断言（CI 门禁，344 行） |
| `scripts/package.py` | 稳定排序打包 zip + CRC 校验（`os.walk` 整个产物目录，含 `img/`） |
| `tests/test_build.py` | 34 项：结构 / 区块裁减 / 配置门禁 / 编码工具 / 图片外置 / 无图项目 |
| `tests/test_sync.py` | 9 项：资产一致性、离线自包含、示例与生产内容同源 |
| `tests/test_browser.py` | 19 项：表单交互 + 两处渲染一致性 |
| `references/01-workflow.md` | 两条路径（+ 外置开关）、图片编码策略表、页面叙事顺序、五端检查表 |
| `references/02-pitfalls.md` | 踩坑清单（P0 / P1 / P2） |
| `references/03-content-schema.md` | `content.json` 全字段规格 + 写作纪律 |
| `references/04-skill-references.md` | 依赖、相关技能、路径换算、六步检查清单 |
| `TEST-REPORT.md` | 测试报告：62 项单测明细、双路径 `verify.py` 输出、3 个 P0 bug 记录、不可判定项清单 |

## 版本历史

| 版本 | 变更 |
|---|---|
| v1.1.0 | 图片可外置：`paths.external` 非空时把图写到 `<out_dir>/img/<分组>/…` 并用相对路径引用，`index.html` 2.41 MB → 68 KB；项目卡支持无主图（`fig` 留空 → 只出文字卡）；`verify.py` 名片断言从「必须是 data URI」改为「必须解码出像素」，主图映射只比有图项目。62 项单测（43 项离线 + 19 项浏览器端）。内容层面按既有简历重建为 13 个项目 / 8 段履历（9 个项目级条目 + 4 个 Word 里并列写明的具名子产品：云枢 PaaS、乐心医生 SaaS、乐心保险中台、第七大道游戏官网群）|
| v1.0.0 | 首个版本。表单驱动采集 → 即时生成单页作品集；声明式区块标记（`SEC / NAV / HR / N`）；表单与命令行两处渲染一致性由测试守护；56 项单测 |


相关技能：`jl-zpj`（「简历 PDF → 命令行流水线」的上一代版本，本技能的模板与构建器由它重构而来）、`aicheck`（交付前 D1–D12 闸门，本技能交付前同样要过）。
