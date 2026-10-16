# gr-zpj · 表单驱动作品集生成

> 填一张表，当场得到一个**离线可用、零依赖**的单页作品集 HTML ——
> 手机、微信、企业微信、钉钉里打开都正常。
> 也可以只用一份 `content.json` 走命令行流水线，进 CI。

仓库路径：[`workbuddy/skill/gr-zpj/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/gr-zpj)

## 一句话

**两条入口，一份模板**：`assets/form.html`（浏览器里填 → 生成 → 另存）与
`scripts/build_portfolio.py`（`content.json` → 构建）。两条路产出的页面**结构逐字等价**，
由测试断言。

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
| 改文案后旧词真的清干净了吗？ | `verify.py --must / --absent`，2.4MB 单页肉眼扫不出来 |

## 安装

```bash
cp -r workbuddy/skill/gr-zpj ~/.workbuddy/skills/gr-zpj

cd ~/.workbuddy/skills/gr-zpj
python -m unittest discover -s tests -t . -v      # 56 项，全绿

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
    --expect nh_agentx,nh_digitalhuman --last-section projects \
    --must "全球 AI 客服平台" --absent "HeroDash" --shots shots/
python scripts/package.py "<out>"
```

`--stats` 打印一行 `STATS:{…}`，可直接喂给 CI 比对结构计数。

### 3 · 图片编码策略

| 用途 | 目标宽度 | 格式 | 为什么 |
|---|---|---|---|
| 首屏名片 | 不缩放 | 原格式 | 卡面小字靠点开放大看 |
| 手绘架构图 | 1440 | JPEG q80 | 照片 / 手绘类素材 |
| 技术分层图 | 不缩放 | **PNG8 量化** | 线条 + 大色块，量化后肉眼无损、体积省 50%+ |
| 证书 | 620 | JPEG q84 | 只做缩略展示 |
| 二维码 | 不缩放 | **PNG 无损** | JPEG 会破坏定位图案，直接扫不出来 |

无需缩放且源格式 == 目标格式时**直通原始字节**，不做重编码（避免画质累积损失）。

## 本机实测

### 单测

```
Ran 56 tests in 33.8s
OK
```
构建器 28 + 资产一致性 9 + 浏览器端 19。浏览器端含**两处渲染一致性**（表单生成的页面
与命令行构建的页面：结构计数、章节序号、导航、缩放元素类型序列、可见文本、`<title>`
逐项相等）与**破图断言**。

### 一份 6 项目 / 8 段履历的完整作品集

```
内嵌资源 1.77 MB ｜ index.html 2.41 MB ｜ 区块 capability+stack+career+credential+projects
计数 pillars 3 ｜ metrics 6 ｜ cards 6 ｜ certs 4 ｜ qrs 4 ｜ tl 8 ｜ stack 6 ｜ zoom 18
导航无死链 ✓   无遗留页脚 ✓   body 无游离区块 ✓   末尾非孤立分隔线 ✓
末区块为 projects ✓   章节序号按 DOM 顺序连续 ['01','02','03','04','05'] ✓
名片占屏宽比 77% (1108x624) ✓
主图映射顺序 ✓   项目按时间降序 ✓   项目编号连续 ✓
五端（1440/820/390/360/320）无横向溢出 ✓   关键区块不超宽 ✓   触摸端正文字号 ≥14.5px ✓
PASS: 全部检查通过
```

### 表单路径产物体积

演示尺寸的完整作品集（22 张图内联）**0.65 MB** —— 表单路径不做 PNG8 量化，
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
| `scripts/build_portfolio.py` | `content.json` → 自包含单页 HTML + 归档图 |
| `scripts/verify.py` | 五端渲染自检 + 结构与内容断言（CI 门禁） |
| `scripts/package.py` | 稳定排序打包 zip + CRC 校验 |
| `tests/test_build.py` | 28 项：结构 / 区块裁减 / 配置门禁 / 编码工具 |
| `tests/test_sync.py` | 9 项：资产一致性、离线自包含、示例与生产内容同源 |
| `tests/test_browser.py` | 19 项：表单交互 + 两处渲染一致性 |
| `references/01-workflow.md` | 两条路径、编码策略表、五端检查表 |
| `references/02-pitfalls.md` | 踩坑清单（P0/P1/P2） |
| `references/03-content-schema.md` | `content.json` 全字段规格 + 写作纪律 |
| `references/04-skill-references.md` | 依赖、相关技能、路径换算、六步检查清单 |
