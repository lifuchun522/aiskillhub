# zpj · 表单驱动作品集生成

> 填一张表，当场得到一个**离线可用、零依赖**的单页作品集 HTML ——
> 手机、微信、企业微信、钉钉里打开都正常。
> 也可以只用一份 `content.json` 走命令行流水线，进 CI。

仓库路径：[`workbuddy/skill/zpj/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/zpj)

## 一句话

**两条入口，一份模板**：`assets/form.html`（浏览器里填 → 生成 → 另存）与
`scripts/build_portfolio.py`（`content.json` → 构建）。两条路产出的页面**结构逐字等价**，
由 parity 断言逐项比对。

## 30 秒跑通

```bash
# 只要装了 Python + Pillow
python scripts/build_portfolio.py examples/minimal-content.json --skill-dir . --stats
python scripts/verify.py "dist/minimal-demo/index.html" \
    --last-section projects --must "订单履约平台重构"
```

产物：`dist/minimal-demo/index.html`（31 KB）+ `img/card/namecard.jpg`（30 KB）。
输出以 `PASS: 全部检查通过` 收尾，说明结构、导航、五端渲染全部达标。

不想装 Python 就双击 `assets/form.html`，点「载入示例」→「生成作品集」→「另存 HTML」。

## 目录结构

```
zpj/
├── SKILL.md                    技能规范：触发条件、五条设计原则、标记语法
├── README.md                   本文件
├── TEST-REPORT.md              62 项单测明细 + 双路径自检原始输出 + 4 个 bug 复盘
├── assets/
│   ├── form.html               采集表单（离线单文件，内嵌模板 + 示例 + 渲染引擎）
│   └── template.html           作品集模板骨架（单一事实来源）
├── scripts/
│   ├── build_portfolio.py      content.json → index.html（内嵌 / 外置两种模式）
│   ├── verify.py               五端渲染自检 + 结构与内容断言（CI 门禁）
│   ├── sync_assets.py          模板 / 示例 → 表单 的注入与一致性校验
│   ├── make_demo.py            生成演示尺寸的内联示例数据
│   └── package.py              稳定排序打包 zip + CRC 校验
├── examples/
│   ├── README.md               三个示例的区别与跑法
│   ├── minimal-content.json    最小可跑输入（1 项目 / 2 段履历）
│   ├── content.json            真实案例（13 项目 / 8 段履历 / 22 张图）
│   ├── demo-content.json       表单内联用（由 make_demo.py 生成，勿手改）
│   └── assets/namecard-demo.jpg  示例占位名片
├── references/
│   ├── 01-workflow.md          两条路径、编码策略、五端检查表
│   ├── 02-pitfalls.md          踩坑清单（P0 / P1 / P2）
│   ├── 03-content-schema.md    content.json 全字段规格 + 写作纪律
│   └── 04-skill-references.md  依赖、相关技能、路径换算
└── tests/                      62 项：构建器 34 + 资产一致性 9 + 浏览器端 19
```

## 它解决什么问题

做个人主页 / 作品集的人往往手上只有零散材料：一段自述、几个项目、几张架构图、几张证书图。
真正磨人的不是排版，而是**反复改版**：

| 每次改版都要问自己的问题 | 本技能的做法 |
|---|---|
| 我把这一块删了，导航里那个链接还在吗？ | 区块消失，**导航项跟着消失**（`<!--NAV:…-->`），`verify.py` 断言无死链 |
| 我把最后一块删了，会不会留下一条光秃秃的分隔线？ | 分隔线归一**限定在 `<main>` 内**处理，首尾 / 重复的一律去掉 |
| 项目顺序调了，章节序号 01/02/03 要手改吗？ | 序号按 DOM 顺序**自动生成**（`<!--N-->`），不可能与顺序脱钩 |
| 页面写着「8 段履历」，实际只有 7 段？ | 记数文案由数据生成（`CAREER_LEAD` / `PROJ_LEAD`） |
| 我删掉第一个项目，剩下的编号要重排吗？ | 编号由数组顺序生成，删完仍从 01 开始 |
| 改完模板，表单预览还是旧的？ | `sync_assets.py --check` + 单测守着「两处必须是同一份」 |
| 「手机上打开对不对」怎么证明？ | 真实 UA 起 5 个 profile，每端查四件事，退出码非 0 即不过 |
| 改文案后旧词真的清干净了吗？ | `verify.py --must / --absent`，整页肉眼扫不出来 |
| 图片要能单独替换，不想每次都重新构建整页？ | 配 `paths.external`，图落到 `img/<项目>/<名>.<ext>`，页面只存相对路径 |
| 早期项目没留架构图，会不会占一个空图位？ | `fig` 留空即只出文字卡，编号仍连续，不留空占位 |
| 没配证书 / 二维码，会不会留两个空网格？ | 整条 `CREDENTIAL` 区块连同导航项一起下线，序号自动重排（实测 `01…04`） |

## 安装

```bash
cp -r workbuddy/skill/zpj ~/.workbuddy/skills/zpj

cd ~/.workbuddy/skills/zpj
python -m unittest discover -s tests -t . -v      # 62 项，全绿

# 可选：命令行路径与自检需要
pip install pillow playwright
python -m playwright install chromium
```

**只走表单路径的话，一个依赖都不用装** —— 双击 `assets/form.html` 就能用。

## 使用步骤

### 1 · 表单路径（30 秒上手）

```bash
assets/form.html        # 双击 / 拖进浏览器都行
```

1. **载入示例** —— 先看成品长什么样（含真实图片，离线可用）
2. 九个区块按需填写，右上角常驻**进度条 + 检查面板**
3. **生成作品集** → 弹层预览 → **另存 HTML**
4. **导出 JSON** 存断点

九个区块：基础信息 / 首屏数据条 / 首屏名片 / 第一人称自述 / 核心能力支柱 /
技术栈分组 / 工作经历 / 教育背景·认证·主页 / 我的项目。都能增删，项目卡还能加多张补充架构图。

### 2 · 命令行路径

```bash
python scripts/build_portfolio.py examples/content.json --stats

python scripts/verify.py "<out>/index.html" \
    --expect nh_digitalhuman,nh_gfs,nh_herodash,nh_game,nh_lowcode,yunshu_tech \
    --last-section projects --must "我的项目" --absent "重点项目" --shots shots/

python scripts/package.py "<out>"
```

`--stats` 打印一行 `STATS:{…}`，可直接喂给 CI 比对结构计数。
`--expect` 只列**有主图的项目**：`fig` 留空的项目渲染成纯文字卡，不占位。

### 3 · 图片编码策略

| 用途 | 目标宽度 | 格式 | 为什么 |
|---|---|---|---|
| 首屏名片 | 不缩放 | 原格式 | 卡面小字靠点开放大看 |
| 手绘架构图 | 1440 | JPEG q80 | 照片 / 手绘类素材 |
| 技术分层图 | 不缩放 | **PNG8 量化** | 线条 + 大色块，量化后肉眼无损、体积省 50%+ |
| 证书 | 620 | JPEG q84 | 只做缩略展示 |
| 二维码 | 不缩放 | **PNG 无损** | JPEG 会破坏定位图案，直接扫不出来 |

无需缩放且源格式 == 目标格式时**直通原始字节**，不做重编码（避免画质累积损失）。

### 4 · 图片内嵌还是外置

| 模式 | 配置 | 产物 | 适用 |
|---|---|---|---|
| 内嵌（默认） | 不写 `paths.external` | 单文件，图全在 `data:` URI 里 | 要发一份文件给别人的场合 |
| 外置 | `"paths": {"external": "img"}` | `img/<分组>/<名>.<ext>` + 只存相对路径的 `index.html` | 要换图、要进 CDN、要页面瘦身 |

外置模式的三条硬规矩：

1. **扩展名按实际编码出的 MIME 决定** —— 源图 png 被压成 jpeg 时文件必须叫 `.jpg`，
   否则浏览器按后缀猜类型，静默破图；
2. **外置即跳过 `archive`** —— 同一份字节不在 `img/` 和 `diagrams/` 各落一份；
3. **外置产物不再是单文件** —— 交付时要整个目录一起发，`package.py` 会连 `img/` 一起打包。

## 例子

| 文件 | 体量 | 用途 |
|---|---|---|
| `examples/minimal-content.json` | 3 KB | 最小可跑（1 项目 / 2 段履历 / 2 支柱），验证环境 |
| `examples/content.json` | 39 KB | 真实案例（13 项目 / 8 段履历 / 22 张图） |
| `examples/demo-content.json` | 640 KB | 表单「载入示例」用的压缩版，由脚本生成，勿手改 |

详见 [`examples/README.md`](./examples/README.md)。

## 本机实测

### 单测

```
Ran 62 tests in 43.5s
OK
```

（浏览器端 19 项要起 Chromium，耗时随机器负载在 35–100s 间浮动，项数恒为 62。）
构建器 34 + 资产一致性 9 + 浏览器端 19。浏览器端含**两处渲染一致性**（表单生成的页面
与命令行构建的页面：结构计数、章节序号、导航、缩放元素类型序列、可见文本、`<title>`
逐项相等）与**破图断言**。

### 一份 13 项目 / 8 段履历的完整作品集（外置图）

```
外置资源 1.77 MB ｜ index.html 0.07 MB ｜ 区块 capability+stack+career+credential+projects
计数 pillars 3 ｜ metrics 6 ｜ cards 13 ｜ certs 4 ｜ qrs 4 ｜ tl 8 ｜ stack 6 ｜ zoom 18
导航无死链 ✓   无遗留页脚 ✓   body 无游离区块 ✓   末尾非孤立分隔线 ✓
末区块为 projects ✓   章节序号按 DOM 顺序连续 ['01','02','03','04','05'] ✓
名片占屏宽比 77% ✓
主图映射顺序 ✓（6 项）   项目按时间降序 ✓   项目编号连续 01–13 ✓
五端（1440/820/390/360/320）无横向溢出 ✓   关键区块不超宽 ✓   触摸端正文字号 ≥14.5px ✓
PASS: 全部检查通过
```

22 张图按项目分成九组落在 `img/` 下（`p01-digital-human` / `p02-gfs` / `p03-ai-cs` /
`p04-chanyou` / `p05-mofang` / `p06-yunshu` / `card` / `certs` / `qr`），
`index.html` 落盘 74,690 B（`STATS.bytes` 记 74,033，差 657 = Windows 每行 CRLF +1）。
换一张架构图不用碰页面。

### 最小示例（最小可用输入）

```
外置资源 0.03 MB ｜ index.html 0.03 MB ｜ 区块 capability+stack+career+credential+projects
计数 pillars 2 ｜ metrics 3 ｜ cards 1 ｜ certs 0 ｜ qrs 0 ｜ tl 2 ｜ stack 1 ｜ zoom 1
计数 certs / qrs                    SKIP（未配，区块整块不出现）
PASS: 全部检查通过
```

### 表单路径产物体积

演示尺寸的完整作品集（22 张图内联）**0.66 MB** —— 表单路径不做 PNG8 量化，
体积会大于命令行产物；检查面板在超过 5MB 时直接给出改用命令行的建议。

## 判不了的部分（一律不写 PASS）

1. **内容好不好**：文案是否打动人、项目是否够分量 —— 人的判断，脚本给不了；
2. **图片审美**：架构图清不清晰、配色是否协调；
3. **浏览器之外**：真实微信 / 企业微信客户端内的最终渲染（本技能用真实 UA 近似，
   但不是真机）；
4. **表单路径的体积优化**：浏览器里做不了 PNG8 调色板量化，这是能力边界，不是 bug。

## 相关文件

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 技能规范、触发条件、五条设计原则、模板标记说明、关键注意事项 |
| `assets/form.html` | 采集表单（离线单文件，内嵌模板 + 示例 + 浏览器端渲染引擎） |
| `assets/template.html` | 作品集模板骨架（**单一事实来源**） |
| `scripts/sync_assets.py` | 模板 / 示例 → 表单 的注入与一致性校验 |
| `scripts/make_demo.py` | 生成演示尺寸的内联示例数据 |
| `scripts/build_portfolio.py` | `content.json` → 作品集 HTML（内嵌单文件 / 图片外置两种模式） |
| `scripts/verify.py` | 五端渲染自检 + 结构与内容断言（CI 门禁） |
| `scripts/package.py` | 稳定排序打包 zip + CRC 校验（含 `img/` 外置图） |
| `tests/test_build.py` | 34 项：结构 / 区块裁减 / 配置门禁 / 编码工具 / 图片外置 / 无图项目 |
| `tests/test_sync.py` | 9 项：资产一致性、离线自包含、示例与生产内容同源 |
| `tests/test_browser.py` | 19 项：表单交互 + 两处渲染一致性 |
| `references/01-workflow.md` | 两条路径、编码策略表、五端检查表 |
| `references/02-pitfalls.md` | 踩坑清单（P0/P1/P2） |
| `references/03-content-schema.md` | `content.json` 全字段规格 + 写作纪律 |
| `references/04-skill-references.md` | 依赖、相关技能、路径换算、六步检查清单 |
| `TEST-REPORT.md` | 测试报告：62 项单测明细、双路径 `verify.py` 输出、4 个 bug 复盘、不可判定项清单 |

完整测试报告见 [`TEST-REPORT.md`](./TEST-REPORT.md)。
