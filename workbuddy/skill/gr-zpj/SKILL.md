---
name: gr-zpj
description: 用一张离线表单采集结构化个人信息（基础信息 / 首屏数据条 / 名片 / 自述 / 能力支柱 / 技术栈 / 工作经历 / 教育认证主页 / 项目），当场生成离线可用、手机·微信·企业 IM 都能正常打开的单页 HTML 作品集；也支持「content.json → 命令行构建」的完整流水线。适用于：用户想「填个表就能生成作品集 / 个人主页 / 简历网页 / portfolio」；给了一份零散材料（简历文本、项目清单、架构图、证书图片）要求整理成个人主页；要求把作品集做成自包含单文件 HTML 并能在手机上打开；要求按数据自动增删区块（没填的整块不出现、不留死链与孤立分隔线）；要求把表单填好的内容导出成 JSON 再交给脚本渲染；要求在既有作品集上压体积、多端适配、内容断言。含 2 个入口（表单 / 命令行）、5 个脚本、62 项自动化测试（含两处渲染一致性比对与五端渲染自检）。触发词：表单生成作品集、作品集表单、采集信息生成网页、个人主页生成器、portfolio、作品集 HTML、填表出作品集、gr-zpj。
description_zh: 表单采集 → 即时生成离线单页作品集（手机/微信/企业 IM 可用），亦支持 content.json 命令行构建；区块按数据自动增删，含 62 项自动化测试。触发词：表单生成作品集、采集信息生成网页、个人主页生成器、gr-zpj。
description_en: Collect structured profile data with an offline HTML form, then instantly generate a self-contained single-page portfolio that renders correctly on mobile, WeChat and enterprise IM browsers. Also supports a content.json CLI pipeline. Sections appear only when they have data (no dead nav links, no orphan separators); 62 automated tests including form-vs-CLI render parity and a five-profile render check.
agent_created: true
---

# gr-zpj · 表单驱动作品集生成

把「一堆零散的个人材料」变成一页**离线可用、零依赖**的作品集 HTML ——
入口可以是**一张表单**（双击就能用），也可以是一份 `content.json`（进流水线 / 进 CI）。

## 何时使用

- 「我要做个人主页 / 作品集 / portfolio」而手头只有零散材料 → 走**表单路径**
- 「帮我把这些信息整理成一个网页」「填个表就能出页面」 → 走**表单路径**
- 「把简历 / 项目清单做成网页，手机上打开要正常」 → 两条路都行，看有没有素材目录
- 「没填的区块别显示」「别留下点不动的导航」 → 本技能天生如此（声明式区块标记）
- 「页面上那条数字写错了（说 8 段实际 7 段）」 → 记数文案由数据生成，不会脱节
- 「要能反复改，改完重出」 → 导出 / 导入 JSON 往返，命令行可重复构建
- 「成品发我要能在微信里看」 → 单文件自包含 + 五端渲染自检
- 「图片要能单独换，别每次都重新构建整页」 → `paths.external`，图落 `img/<项目>/`、页面存相对路径
- 「页面上有几个项目没留架构图」 → `fig` 留空即只出文字卡，编号仍连续、不留空图位
- 「顺便把架构图归档出来，我要拖进 PPT」 → `images[].archive`（外置模式下自动跳过，避免重复落盘）

不适用：在线站点（服务端渲染）、纯文字简历排版（走 `workbuddy-docx`）、
PPT 制作（走 `workbuddy-pptx`）。需要从**简历 PDF 抽素材**时先走 `jl-zpj` 的抽取阶段。

## 核心设计原则（先读这五条）

1. **两条路，一份模板** —— 表单内联的模板与 `assets/template.html` 是同一份东西
   （`sync_assets.py` 注入、`sync_assets.py --check` 守门）。表单预览和命令行产物
   **结构逐字等价**，由 `tests/test_browser.py` 的 parity 用例断言。
2. **区块由数据决定存在，不由人决定删改** —— `<!--SEC:key-->` / `<!--NAV:id-->` /
   `<!--HR-->` / `<!--N-->` 四种标记把「删区块要连带改九处」变成零改。
   没数据 → 整块消失；导航项跟着消失；分隔线首尾与重复的自动去掉；章节序号按 DOM 顺序生成。
3. **一次构建 = 一次校验** —— token 双向一致、资源键可解析、层级白名单、占位符零残留，
   任一不满足即 `sys.exit(1)`，绝不产出半成品。
4. **先证伪自己** —— 视觉 / 截图异常先怀疑观测工具（滚动时序、平滑滚动），再判定产物缺陷。
5. **一处一事** —— 数据条管概览数字，项目 `result` 管成果数字，`steps` 只管动作，
   技术名词归 `chips`。重复不是「更完整」，是让人一眼看出内容的稀薄。

## 路径 A：表单（30 秒上手）

```bash
# 直接双击打开，不需要任何服务端 / 依赖
assets/form.html
```

1. 点 **「载入示例」** → 立刻看到一份填满的作品集长什么样（含真实图片）
2. 九个区块按需填写；右上角有**进度条 + 检查面板**（缺什么、哪条太虚、体积有没有超）
3. **「生成作品集」** → 弹层预览 → **「另存 HTML」**
4. **「导出 JSON」** 存断点，下次 **「导入 JSON」** 接着改

图片在浏览器里就按用途压好（名片 / 二维码不缩放不重压，手绘 1440、分层 1280、证书 620）。
内嵌总量 > 5MB 时面板告警 —— 该改走路径 B（能 PNG8 量化）。

调试 / 自动化：`window.__grzpj`（`state / payload / load / render / summary`）。

## 路径 B：命令行

```
① 素材        images/
② 内容        content.json     ← 字段规格见 references/03-content-schema.md
③ 构建        python scripts/build_portfolio.py content.json --stats
④ 自检        python scripts/verify.py "<out>/index.html" --expect <主图键> \
                  --last-section projects --must "<新词>" --absent "<旧文案>"
⑤ 打包        python scripts/package.py "<out>"
⑥ 交付闸门    加载 delivery-no-pseudoblock，实跑 D1–D12
```

**改模板或改示例之后必须先 `python scripts/sync_assets.py`**，否则表单里内联的还是旧模板。

## 模板标记（改模板前必读）

```html
<!--SEC:stack-->   … 整块 …   <!--/SEC:stack-->   数据为空 → 整块消失
<!--NAV:stack-->   <li>…</li> <!--/NAV:stack-->   区块消失 → 导航项一起消失
<!--HR-->                                          区块间分隔线，渲染后统一归一
<!--N-->                                           章节序号，按 DOM 顺序自动编号
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

判断「有没有数据」的规则：`tagline` 看 `texts.TAGLINE`，`metrics` 看数据条，
`intro / capability / stack / career / projects` 看对应内容数组，
`credential` 看「教育背景 / 认证 / 二维码」三者是否至少有一项。
裁减后 `verify.py` 会断言：**导航无死链、无遗留页脚、body 无游离区块、末尾非孤立分隔线、
章节序号与 DOM 顺序连续**。

## 自带脚本

| 脚本 | 作用 |
|---|---|
| `scripts/sync_assets.py` | 把 `assets/template.html` + `examples/demo-content.json` 注入 `assets/form.html`；`--check` 只校验 |
| `scripts/make_demo.py` | 从 `examples/content.json` 生成演示尺寸的内联版 `demo-content.json` |
| `scripts/build_portfolio.py` | `content.json` → `index.html`（默认自包含单页；配 `paths.external` 则图片外置） |
| `scripts/verify.py` | 五端渲染 + 结构与内容断言（可用作 CI 门禁，退出码非 0 即不过） |
| `scripts/package.py` | 稳定排序打包 zip + CRC 校验 |

## 自带资源

| 路径 | 说明 |
|---|---|
| `assets/form.html` | 采集表单（离线单文件；内嵌模板与示例数据；含浏览器端渲染引擎） |
| `assets/template.html` | 作品集模板骨架（**单一事实来源**；深色专业风、灯箱、滚动动效、老内核兜底） |
| `examples/content.json` | 完整示例（命令行用，图片走磁盘路径） |
| `examples/demo-content.json` | 同一份内容的演示尺寸版（表单用，图片内联 data URI） |
| `tests/` | 62 项单测：构建器 34 + 资产一致性 9 + 浏览器端 19 |
| `TEST-REPORT.md` | 测试报告：62 项逐条明细、双路径 `verify.py` 原始输出、3 个 P0 bug 复盘、不可判定项清单 |
| `references/01-workflow.md` | 两条路径 + 编码策略表 + 五端检查表 |
| `references/02-pitfalls.md` | 踩坑清单（P0/P1/P2，含本次开发中真实踩到的 3 个 P0） |
| `references/03-content-schema.md` | `content.json` 全字段规格 + 写作纪律 |
| `references/04-skill-references.md` | 依赖、相关技能、路径换算、检查清单、版本历史 |

## 依赖

```bash
pip install pillow playwright
python -m playwright install chromium
```

只走表单路径的话，两个都不需要。

## 关键注意事项

- **资源字典有两种形状，别混淆** —— `content.json` 的 `images` 是
  `{key:{src,…}}`（配置），模板里的 `ASSETS[key]` 要字符串（运行时）。
  混淆的后果是**文字全对、只有图全破**，纯文本比对的测试发现不了（P0-1）。
- **动态生成的行必须紧跟一次回填** —— 只写 `placeholder` 不写 `value`，
  采集到的就是空值，而且不报错（P0-2）。
- **标签分隔符 ` / ` 有歧义** —— 单行输入分不清「分隔符」和「标签里的斜杠」。
  `CI/CD` 这种不带空格的斜杠没事；要表达「`Agent / LLM` 是一个标签」就走 JSON 数组（P0-3）。
- **分隔线归一必须限定在 `<main>` 内** —— 否则删掉第一个区块时，页面前缀会被当成
  第一个片段，开头凭空多一条分隔线（P1-1）。
- **模板 token 必须始终有值** —— 空默认也要给，否则页面上会留下没替换的 `{{NAME}}`；
  JS 侧漏了这步尤其隐蔽（浏览器把 `{{X}}` 当普通文本渲染）。
- **表单在 `file://` 下不能 fetch 本地文件** —— 模板与示例必须内联；
  内联模板里的 `</script>` 必须转义成 `<\/script>`（P1-4 / P1-5）。
- **字符串与数组两种输入形态必须等价** —— `paras / facts / steps / bullets / tags`
  都要能吃两种，且渲染结果逐字相同（P1-6）。
- **改版后必须验「旧文案真的没了」** —— `verify.py --must / --absent`；
  2.4MB 单页靠肉眼扫不出残留（P1-7）。
- **窄屏横向溢出不要只测 390px** —— 2px 溢出只在 320/360 暴露，真机上就是整页可左右晃（P2-3）。
- **二维码必须 PNG 无损且不缩放** —— JPEG 会破坏定位图案（P2-6）。
- **成品体积 > 5MB 要处理** —— 内嵌 PNG 走 PNG8 量化（表单路径做不了，得走命令行）。

更多细节见 `references/` 下的四份文档。
