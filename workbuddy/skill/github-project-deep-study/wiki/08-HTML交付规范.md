# HTML 交付规范

完整 CSS 骨架在 [`references/html-style-spec.md`](../references/html-style-spec.md)，这里讲**为什么**和**怎么验**。

---

## 为什么是 PPT 卡片化

长文在线阅读有两个失败模式：滚动疲劳（看到一半放弃）与定位困难（想回看某段找不到）。

卡片化同时解决两个：

- 每章一张卡，**有明确的开始和结束**，滚动有节奏
- 顶部吸顶目录 + 章节编号，**任意跳转**
- 章节色条 + 大号页码，形成空间记忆（"那张橙色的卡片"）

代价是要控制每张卡片的信息量 —— 一张卡塞 3000 字反而更难读。

---

## 硬性样式点

| 点 | 值 | 不做的后果 |
|---|---|---|
| 卡片圆角 | `20px` | 直角像文档，不像幻灯片 |
| 双层阴影 | `0 14px 36px rgba(16,24,40,.10)` + `0 2px 6px ...` | 单层阴影发灰、没层次 |
| 顶色条 | `6px` 渐变，`--bar` 变量 | 章节之间没有视觉分界 |
| 页码 | `62px / 800`、色 `#eef2f8`、CSS counter | 手写编号，插章节就跳号 |
| `scroll-margin-top` | `96px` | 点目录跳转，标题被吸顶栏压住 |
| 卡片间距 | `30px` | 太挤像段落，太松散架 |

页码用 counter 是关键：

```css
body{counter-reset:slide}
section::before{content:counter(slide,decimal-leading-zero);counter-increment:slide; ...}
```

加章节、删章节、调顺序，编号自动重排。

---

## 内容规范：面向最终读者

这一条比样式重要。读者关心**结论与方法**，不关心你的过程。

### 必须删掉的

| 删 | 为什么 |
|---|---|
| 本地绝对路径、commit hash、日期 | 对读者无意义，还暴露环境 |
| 「学习步骤：clone → 读架构 → …」 | 这是方法论文档的内容，不是文章内容 |
| 「本次实测」「本机」「我跑了」 | 换成「实测环境」「运行后」 |
| 首次启动引导截图与说明 | 读者自己会看到，不用你教 |
| 「拿到 Key 后我会补齐…」 | 这是待办，不是交付 |
| 自测结论 note、页脚流水账 | 流水账说明你在汇报过程 |
| 时间线式踩坑记录 | 读者要的是「现在怎么办」 |

### 应该替换成

| 原内容 | 替换 |
|---|---|
| 踩坑流水账 | 「环境要求与安装提示」：镜像源、依赖版本、SDK 版本 |
| "我踩了个坑，花了两小时" | 「Windows 需装 .NET 10 SDK，仅运行时无法 build」 |
| 未验证的推测 | 「未验证：缺少 <具体凭据>」 |
| 写作骨架说明 | 删除，标题即结论 |

判断标准：**这句话删掉，读者会少知道一件有用的事吗？** 不会就删。

---

## 结构约定

```html
<header class="hero">           封面：标题 + 一句话主题 + chips
<div class="wrap">
  <div class="toc">             吸顶目录（sticky）
  <section id="s1">             章节卡片，顺序决定配色与页码
  ...
<footer>
```

- 每个 `<section>` 自带编号，**不要在里面插 `.toc` 或 `<header>`**
- 章节 id 用 `s1`…`s9`，目录锚点对齐
- 每张卡内部结构：`h2` → 一句导语 → `h3` 小节 → 表格/图/代码

h2 前的标签用 `<span class="tag fam">熟悉</span>` 这类，颜色区分四段。

---

## 增量改样式铁律

**绝不整体替换 CSS 段。** 曾经的教训：用「从 `/* 某注释 */` 到 `</style>` 整体替换」改样式，把后来加的导图放大规则一起删了，结果 checkbox 裸露在页面上、点击放大失效。

正确做法：

```python
# 在 </style> 前追加，不动已有规则
h = h.replace("</style>", "  .new-rule{...}\n</style>", 1)
```

改完必须渲染验证交互仍工作（点开点合各一次）。

---

## 交付前自检

```python
# 结构
assert html.startswith("<!DOCTYPE")
assert html.rstrip().endswith("</html>")
assert len(re.findall(r"<section[\s>]", html)) == 预期章节数
assert "IMG_" not in html
```

注意 `h.count("<section>")` 会把 `<section id="s1">` 数成 0 —— 必须用正则。

```python
# 渲染
bad = await pg.evaluate("() => [...document.images].filter(i=>!i.complete||!i.naturalWidth).length")
assert bad == 0

await pg.click("label.mmzoom-l")
assert await pg.evaluate(
    "() => getComputedStyle(document.querySelector('.mindmap-wrap')).position") == "fixed"
await pg.click("label.mmzoom-l")
assert await pg.evaluate(
    "() => getComputedStyle(document.querySelector('.mindmap-wrap')).position") == "relative"
```

体积参考：9 章 + 15 张内嵌图 ≈ 800–900 KB，能接受。超过 2 MB 说明没压缩图片。

---

## 排版细节

- 代码块用深底，与正文强对比；行内 `code` 用浅底 + 红字
- 表格一律 `width:100%`，隔行浅底，方便横向扫读
- 提示用 `.note`（蓝）与 `.warn`（黄），别用超过两种语义色
- 长表格超过 8 行考虑拆成两张，或折叠
- 中文标点全角，中英之间留空格（排版习惯，不影响正确性）
