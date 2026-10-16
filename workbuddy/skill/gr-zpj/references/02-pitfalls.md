# 02 · 踩坑清单

按「有多贵」分级：
**P0** = 静默产出错页面（不报错、肉眼也未必看得出来）；
**P1** = 报错或明显坏掉；
**P2** = 体验 / 体积问题。

---

## P0 —— 静默的错

### P0-1 · 资源字典形状错位：`{key:{src}}` vs `{key:dataURI}`

`content.json` 里 `images` 用 `{key: {src, max_w, …}}`（带编码参数，是配置）；
模板里 `ASSETS[key]` 要的是**字符串**（是运行时数据）。两处混淆的后果：

```js
el.src = ASSETS[k];          // ASSETS[k] 是对象 → src 变成 "[object Object]"
```

页面照样渲染，**文字全对、计数全对、只有图是破的** —— 用文本比对的测试根本发现不了。

对策：
- JS 渲染入口做一次显式转换（`assets[k] = payload.images[k].src`）；
- 测试里必须有一条**「水到渠成的破图断言」**：把两处渲染的页面都灌进浏览器，
  查 `naturalWidth === 0` 的图。只比 innerText 的 parity 测试是漏的。

### P0-2 · 列表行只写 placeholder，不回填 value

动态生成的重复行（项目 / 经历 / 支柱 …）如果只把示例值写进 `placeholder`，
`collect()` 读回来的就是**空字符串**。现象：表单看着填满了，导出的 JSON 里全是 `""`，
生成的页面缺整块内容 —— 而且不报任何错。

对策：**渲染行之后必须紧跟一次回填**。`renderLists()` 末尾直接调 `fillFixed()`；
`refresh()` 里不要把 `fillFixed()` 放在 `renderLists()` 前面（那时行还不存在）。

### P0-3 · 分隔符歧义：标签里的「 / 」

`split_tags` 的规则是「有 ` / ` 就按 ` / ` 切，否则按 `/` 切」。于是：

| 输入 | 结果 |
|---|---|
| `Java / Python` | `["Java","Python"]` ✓ |
| `CI/CD` | `["CI/CD"]` ✓（没有带空格的斜杠，不切） |
| `Agent / LLM / RAG` | 三个标签 —— 但如果本意是「一个叫 `Agent / LLM` 的标签」，就丢了 |

单行文本输入**天生无法区分**「分隔符」与「标签内容里的斜杠」。所以：
- 分隔符固定为 **` / `（带空格）**，文档里写明；标签内部别再写带空格的斜杠；
- 真的需要（如 `Agent / LLM`）就走 JSON 的数组形态：`"tags": ["Agent / LLM"]` ——
  `split_tags` 对数组原样返回，无损。

---

## P1 —— 报错 / 明显坏掉

### P1-1 · 分隔线归一必须限定在 `<main>` 内

「删掉区块后去掉孤立分隔线」的朴素实现是对**整篇 HTML** 做
`split("<!--HR-->")` 再丢掉空片段。页面前缀（`<head>`/`nav`/`hero`）永远非空，
于是删掉**第一个**区块时，那条前缀会被当成第一个片段 —— 页面开头凭空多出一条分隔线，
数量校验「区块数 - 1」直接对不上。

对策：`re.sub(r"(?s)(<main>)(.*?)(</main>)", fix, html)`，只在 `<main>` 内切分。
JS 侧同理（`/<main>([\s\S]*?)<\/main>/`）。

### P1-2 · token 必须**始终**有值，哪怕是空串

构建时做「模板 `{{X}}` ↔ `texts` 双向一致」门禁之后，任何**可能为空**的 token
都会让构建直接失败（如用户没填 `TAGLINE`）。两个选择：报错让用户补，或者给空默认。

本技能的做法：`NAME/ROLE/ROLE_SHORT/TAGLINE` 允许空默认（空值语义明确 —— tagline 空则整行不渲染），
其余（`MARK/TITLE/META_DESC/CAP_LEAD/STACK_LEAD/CRED_H2/CAREER_LEAD/PROJ_LEAD`）由构建器**派生**。
派生 token 不参与「配置必须显式提供」的检查，否则用户每加一个字段都要手动补。

⚠️ JS 侧漏了这一步的后果更隐蔽：`{{NAME}}` 没被替换会**留在页面源码里**，
浏览器把它当普通文本渲染，肉眼扫不出来。兜底：生成后扫一遍 `\{\{[A-Z0-9_]+\}\}`。

### P1-3 · 用标记表达结构，而不是靠人工数着删

「删一处要连带改九处」（DOM / 占位符 / token / CSS / 断点 / 兜底层 / 白名单 / 渲染函数 /
导航 / 自检计数）这类连带改版，靠清单和记忆一定会漏。本技能改成**声明式标记**：

```html
<!--SEC:stack--> … 整块 … <!--/SEC:stack-->    数据为空 → 整块消失
<!--NAV:stack--> <li>…</li> <!--/NAV:stack-->  对应区块消失 → 导航项一起消失
<!--HR-->                                      区块之间的分隔线，渲染后统一归一
<!--N-->                                       章节序号，按 DOM 顺序自动编号
```

收益（都被测试守着）：
- 删区块**不会**留下死链（`href="#stack"` 指向不存在的 id）；
- 删掉首/尾区块**不会**留下孤立分隔线；
- 移动区块顺序**不必**改编号，序号与顺序不可能脱钩。

代价：`number_sections()` 会吞掉模板里的 `<!--N-->`，所以**输出里出现 `<!--N-->` 就是 bug** ——
`verify.py [0]` 专门断言这四种标记的残留数为 0。

### P1-4 · 表单在 `file://` 下读不到本地文件

`fetch('examples/demo-content.json')` 在 `file://` 会被同源策略拦掉，
「双击就能用」这个前提直接崩。所以模板与示例数据都以字符串常量**内联**在 `form.html` 里，
由 `scripts/sync_assets.py` 从单一事实来源注进去；`sync_assets.py --check` 与
`tests/test_sync.py` 守着「内联的那份 == 文件那份」，否则表单预览会和命令行产物漂移。

### P1-5 · 内联模板必须转义 `</script>`

模板里有 `<script>…</script>`。把它当字符串塞进宿主页面自己的 `<script>` 里，
`</script>` 会**提前闭合**宿主脚本元素，后面所有 JS 变成纯文本。
对策：`json.dumps(...).replace("</", "<\\/")`（`<\/` 在 JS 与 JSON 字符串里都等于 `/`）。
`tests/test_sync.py` 断言 `form.html` 里 `</script>` 恰好出现 1 次。

### P1-6 · 两种输入形态必须等价

同一份内容，手写 JSON 常写数组、表单导出是「一行一条」的字符串。
`paras / facts / steps / bullets / tags` 都要能吃两种形态，且**渲染结果逐字相同** ——
`tests/test_build.py::test_string_inputs_shorthand` 就是把两者构建出的页面去空白后直接比。

最容易漏的是 `split_tags`：它一开始只接受字符串，传数组时会走 `str(list)` 分支，
把一个标签渲染成 `['高并发', '分布式']`。这个 bug 就是被这条测试抓出来的。

### P1-7 · 改版后必须验「旧文案真的没了」

`verify.py --must "<新词>" --absent "<旧文案>"`。2.4MB 单页靠肉眼扫不出
「区块删了但 CSS 与旧键还在」。本技能重构自 jl-zpj 时，就是把
`国泰 / 瑞众 / HeroDash / 200+ 关键指标` 作为 `--absent` 断言清单跑通的。

---

## P2 —— 体验 / 体积

### P2-1 · 成品体积 > 5MB 要处理

内嵌 PNG 走 PNG8 量化，删掉不再被引用的图。表单路径做不了量化，
所以在检查面板里直接给出体积与建议。

### P2-2 · 演示数据要压到「演示尺寸」

`examples/demo-content.json` 会内联进 `form.html`。用生产原图会让表单涨到几 MB。
`scripts/make_demo.py` 统一压到演示尺寸（名片 560 / 手绘 460 / 分层 520 PNG8 /
证书 260 / 二维码 150），当前合计约 450KB 图片。
`tests/test_sync.py` 断言 demo JSON < 900KB，防止有人直接塞原图。

### P2-3 · 窄屏横向溢出不要只测 390px

2px 溢出只在 320/360 暴露。两个来源：flex 项 `min-width:auto` 被内容撑宽、
伪元素负偏移出血。本例的具体修复：

```css
/* 导航条作为 flex 项，不补 min-width:0 会被内容撑宽 → 整页可左右晃 */
.nav ul{width:100%;min-width:0;max-width:100%;overflow-x:auto}
/* 名片光晕用负偏移出血；窄屏收窄，否则这 16px 被算进文档宽度 */
@media(max-width:860px){.hero-card::after{top:-8px;right:-8px;bottom:-8px;left:-8px}}
```

### P2-4 · 窄屏灯箱别把图压到 100% 宽

320px 上把 1672px 的名片压成 296px，「点击放大」就成了假动作。
窄屏改按原始像素宽渲染（`width:auto;max-width:none`），可拖动 + 手势缩放。

### P2-5 · 老内核兜底（微信 / 企业 IM 内置 WebView、iOS 14 以下）

`inset:0` 展开成 `top/right/bottom/left`；渐变文字先给 `color` 兜底；
`-webkit-sticky` 前缀写在前；`@supports not (gap:1px)` 补 margin 兜底。

### P2-6 · 二维码必须 PNG 无损且不缩放

JPEG 压缩会破坏定位图案导致扫不出来。`as_png: true` + 不设 `max_w`。

### P2-7 · 描述性文字的审查口径

不接受「提升约 3 倍 / 200+ 关键指标」这类**无法证伪**的表述 ——
要落到具体动作与技术名词（ELK 日志采集分析告警、xxl-job 调度、Apollo 配置中心）。
表单的检查面板对「项目没写成果 / 没写关键动作 / 没写技术标签」直接给提示。
