# HTML 交付规范（PPT 卡片化）

交付物是**单文件 HTML**：双击即开、无外链、无 CDN、图片全部 base64 内嵌。
视觉形态是**逐页滚动的一叠卡片**，每章一张，像翻 PPT。

本文三部分：① 设计 token ② 可直接复制的完整骨架 ③ 面向最终读者的内容清理清单。

---

## 1. 设计 token

| 项 | 值 | 说明 |
|---|---|---|
| 画布宽 | `1120px` | 正文最大宽，超宽屏居中 |
| 卡片 | 白底 `#fff`、圆角 `20px`、内边距 `40px 42px` | 章节容器 |
| 卡片阴影 | `0 14px 36px rgba(16,24,40,.10), 0 2px 6px rgba(16,24,40,.04)` | 双层，近实远虚 |
| 顶色条 | `height:6px`，`--bar` 变量按章分配渐变 | 章节识别色 |
| 页码 | 右上角 `62px / 800`、色 `#eef2f8` | CSS `counter` 自动生成 |
| 卡片间距 | `30px` | 页与页之间 |
| 正文 | `15px / line-height 1.7` | 中文阅读舒适区 |
| h2 | `24px`，下边框分隔 | 章节标题 |
| h3 | `17px`，左侧 `4px` 彩色竖条 | 小节标题 |
| 代码块 | 深底 `#0f172a`、`13px` 等宽 | 命令与输出 |
| 表格 | `13.5px`，表头 `#f3f6fb`，隔行 `#fafbfd` | 对比与清单 |

章节配色（按顺序循环取用，够 9 章）：

| # | 渐变 | 语义 |
|---|---|---|
| 1 | `#7c5cff → #2f6df6` | 速览 |
| 2 | `#7c5cff → #a855f7` | 熟悉 |
| 3 | `#2f6df6 → #22d3ee` | 学习 |
| 4 | `#10a37f → #34d399` | 实战 |
| 5 | `#e8590c → #f59e0b` | 特性探索 |
| 6 | `#e8590c → #ef4444` | 使用流程 |
| 7 | `#f59e0b → #eab308` | Key 清单 |
| 8 | `#0ea5e9 → #6366f1` | 三专题 |
| 9 | `#6366f1 → #8b5cf6` | 费曼自测 |

---

## 2. 完整骨架

复制整段，替换 `<...>` 即可。**改样式时在 `</style>` 前增量追加，绝不整体替换**（曾因区间替换冲掉导图放大规则，导致交互失效）。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title><项目名> 学习笔记</title>
<style>
  :root{
    --bg:#f6f8fb; --paper:#fff; --ink:#1f2733; --muted:#5b6776; --line:#e4e9f0;
    --brand:#2f6df6; --brand-soft:#eaf1ff;
    --fam:#7c5cff; --fam-soft:#f1edff;
    --prac:#10a37f; --prac-soft:#e6f7f1;
    --feat:#e8590c; --feat-soft:#fff1e6;
    --warn:#d97706; --warn-soft:#fdf2e3;
    --code-bg:#0f172a; --code-ink:#e2e8f0;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.7;font-size:15px;
    font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
  a{color:var(--brand);text-decoration:none}

  /* ---------- 封面 ---------- */
  header.hero{max-width:1120px;margin:24px auto;border-radius:20px;padding:46px 42px 38px;
    background:linear-gradient(135deg,#7c5cff,#2f6df6);color:#fff;
    box-shadow:0 16px 38px rgba(47,109,246,.30)}
  header.hero h1{margin:0 0 6px;font-size:30px;letter-spacing:.5px}
  header.hero p{margin:4px 0;opacity:.94}
  header.hero .lead{color:#fff;opacity:.94;font-size:14.5px;font-weight:500}
  .meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
  .chip{background:rgba(255,255,255,.18);padding:4px 12px;border-radius:999px;font-size:12.5px}

  /* ---------- 吸顶目录 ---------- */
  .wrap{max-width:1120px;margin:0 auto;padding:0 20px 40px}
  .toc{position:sticky;top:10px;z-index:60;background:rgba(255,255,255,.94);
    border:1px solid var(--line);border-radius:14px;padding:10px 12px;margin:0 0 24px;
    display:flex;gap:8px;flex-wrap:wrap;box-shadow:0 6px 18px rgba(16,24,40,.07)}
  .toc b{font-size:12.5px;color:var(--muted);align-self:center;padding:0 6px;flex:none}
  .toc a{font-size:12.5px;color:#42506b;background:#f7f9fd;border:1px solid #dfe5f0;
    border-radius:999px;padding:5px 12px;white-space:nowrap}
  .toc a:hover{border-color:var(--brand);color:var(--brand);background:#eef4ff}

  /* ---------- PPT 卡片 ---------- */
  body{counter-reset:slide}
  section{position:relative;background:var(--paper);border:1px solid #e4e9f2;border-radius:20px;
    padding:40px 42px 34px;margin:0 0 30px;overflow:hidden;scroll-margin-top:96px;
    box-shadow:0 14px 36px rgba(16,24,40,.10),0 2px 6px rgba(16,24,40,.04)}
  section::after{content:"";position:absolute;left:0;right:0;top:0;height:6px;background:var(--bar)}
  section::before{content:counter(slide,decimal-leading-zero);counter-increment:slide;
    position:absolute;right:28px;top:14px;font-size:62px;font-weight:800;line-height:1;
    color:#eef2f8;letter-spacing:-3px;pointer-events:none;user-select:none}
  section>*{position:relative;z-index:1}
  section:nth-of-type(1){--bar:linear-gradient(90deg,#7c5cff,#2f6df6);--ac:#5b6bd8}
  section:nth-of-type(2){--bar:linear-gradient(90deg,#7c5cff,#a855f7);--ac:#7c5cff}
  section:nth-of-type(3){--bar:linear-gradient(90deg,#2f6df6,#22d3ee);--ac:#2f6df6}
  section:nth-of-type(4){--bar:linear-gradient(90deg,#10a37f,#34d399);--ac:#10a37f}
  section:nth-of-type(5){--bar:linear-gradient(90deg,#e8590c,#f59e0b);--ac:#e8590c}
  section:nth-of-type(6){--bar:linear-gradient(90deg,#e8590c,#ef4444);--ac:#d9480f}
  section:nth-of-type(7){--bar:linear-gradient(90deg,#f59e0b,#eab308);--ac:#b45309}
  section:nth-of-type(8){--bar:linear-gradient(90deg,#0ea5e9,#6366f1);--ac:#0369a1}
  section:nth-of-type(9){--bar:linear-gradient(90deg,#6366f1,#8b5cf6);--ac:#4338ca}
  section h2{font-size:24px;margin:4px 0 16px;padding-bottom:14px;
    border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px}
  section h3{font-size:17px;margin:28px 0 10px;padding-left:12px;
    border-left:4px solid var(--ac,var(--brand))}
  section h4{font-size:15px;color:#33415c;margin:20px 0 8px}
  p{margin:8px 0}

  /* ---------- 文本与结构化 ---------- */
  .lead{color:var(--muted);font-size:14px;margin-top:2px}
  .tag{font-size:11.5px;padding:2px 9px;border-radius:6px;font-weight:600;white-space:nowrap}
  .tag.fam{background:var(--fam-soft);color:var(--fam)}
  .tag.learn{background:var(--brand-soft);color:var(--brand)}
  .tag.prac{background:var(--prac-soft);color:var(--prac)}
  .tag.feat{background:var(--feat-soft);color:var(--feat)}
  table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.5px}
  th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
  th{background:#f3f6fb;font-weight:600}
  tr:nth-child(even) td{background:#fafbfd}
  pre{background:var(--code-bg);color:var(--code-ink);padding:14px 16px;border-radius:10px;
    overflow:auto;font-size:13px;line-height:1.6;font-family:"SFMono-Regular",Consolas,monospace}
  code{font-family:"SFMono-Regular",Consolas,monospace;background:#eef2f8;padding:1px 6px;
    border-radius:5px;font-size:12.5px;color:#c0392b}
  pre code{background:none;padding:0;color:inherit}
  .note{border-left:4px solid var(--brand);background:var(--brand-soft);padding:10px 14px;
    border-radius:0 8px 8px 0;margin:12px 0;font-size:13.5px}
  .warn{border-left:4px solid var(--warn);background:var(--warn-soft);padding:10px 14px;
    border-radius:0 8px 8px 0;margin:12px 0;font-size:13.5px}

  /* ---------- 截图 ---------- */
  .shot{border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:14px 0;background:#0b1220}
  .shot img{display:block;width:100%;height:auto}
  .shot img.compact{max-height:520px;width:auto;max-width:100%;margin:0 auto;
    object-fit:contain;background:#fff}
  .shot .cap{background:#0b1220;color:#9fb3c8;font-size:12.5px;padding:8px 12px}
  .grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
  .grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
  .grid2 .shot,.grid3 .shot{margin:0}

  /* ---------- 阶段流水线 ---------- */
  .pipeline{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0}
  .pipeline .st{background:#f3f6fb;border:1px solid var(--line);border-radius:8px;
    padding:8px 10px;font-size:12.5px;flex:1;min-width:120px;text-align:center}
  .pipeline .st b{display:block;color:var(--brand);font-size:11px}

  /* ---------- 用户视角操作步 ---------- */
  .flow{display:flex;flex-direction:column;gap:22px;margin:18px 0 8px}
  .step{display:grid;grid-template-columns:44px 1fr;gap:14px;align-items:start}
  .step .no{width:44px;height:44px;border-radius:50%;background:#e8f0fe;border:1.5px solid #4f7fd4;
    color:#2b6cb0;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px}
  .step h4{margin:6px 0 6px;font-size:16px;color:#1a2233;font-weight:700}
  .step p{margin:0 0 10px;color:#4a5568;font-size:14px;line-height:1.8}
  .step .act{display:inline-block;background:#eef4ff;border:1px solid #c3d7f2;color:#2b6cb0;
    border-radius:6px;padding:2px 8px;font-size:12.5px;margin-right:6px}

  /* ---------- Key 问题单 ---------- */
  .tier{display:inline-block;font-size:12px;font-weight:700;border-radius:6px;
    padding:2px 8px;margin-right:8px;white-space:nowrap}
  .t0{background:#e8f7ee;color:#1a7f4b;border:1px solid #b7e4c7}
  .t1{background:#fdf6e3;color:#8a6d1a;border:1px solid #f0dc9a}
  .t2{background:#fdecec;color:#b23b3b;border:1px solid #f5c2c2}
  .ask{background:#f5f8ff;border-left:3px solid #4f7fd4;border-radius:8px;padding:14px 18px;margin:16px 0}
  .ask li{margin:6px 0;color:#33415c;font-size:14px;line-height:1.75}

  /* ---------- 思维导图 + 纯 CSS 全屏放大 ---------- */
  .mindmap-wrap{margin:18px 0 10px;border:1px solid #d8e0ee;border-radius:14px;
    overflow:hidden;background:#0d1220}
  .mindmap{display:block;width:100%;height:auto}
  details.deet{margin:14px 0 6px;border:1px solid #dbe3f0;border-radius:10px;
    background:#f7f9fd;padding:10px 14px}
  details.deet summary{cursor:pointer;color:#2b6cb0;font-size:14px}
  .mmzoom-t{position:absolute;left:-9999px;opacity:0;width:1px;height:1px;pointer-events:none}
  .mmzoom-l{display:inline-block;margin:12px 0 2px;cursor:zoom-in;font-size:13px;color:#2b6cb0;
    border:1px solid #c3d7f2;background:#eef4ff;border-radius:999px;padding:6px 14px}
  .mmzoom-t:checked ~ .mindmap-wrap{position:fixed;inset:0;z-index:999;margin:0;border-radius:0;
    border:none;padding:18px 18px 70px;overflow:auto;display:block;background:#0b0f19}
  .mmzoom-t:checked ~ .mindmap-wrap .mindmap{min-width:1440px;max-width:none;width:100%}
  .mmzoom-t:checked ~ .mmzoom-l{position:fixed;top:14px;right:18px;z-index:1000;cursor:zoom-out;
    background:#1b2742;color:#e8eefc;box-shadow:0 4px 18px rgba(0,0,0,.5)}

  footer{max-width:1120px;margin:0 auto;text-align:center;color:var(--muted);
    font-size:12.5px;padding:20px}
</style>
</head>
<body>

<header class="hero">
  <h1><项目名> 学习笔记</h1>
  <p><一句话主题：它把什么变成什么></p>
  <p class="lead">熟悉 → 学习 → 实战 → 特性探索 · 全部配本地实跑证据</p>
  <div class="meta">
    <span class="chip">仓库 <owner/repo></span>
    <span class="chip">技术栈 <A + B></span>
    <span class="chip">本地跑通 ✔ 实图</span>
  </div>
</header>

<div class="wrap">
  <div class="toc">
    <b>目录</b>
    <a href="#s1">速览</a><a href="#s2">1 熟悉</a><a href="#s3">2 学习</a>
    <a href="#s4">3 实战</a><a href="#s5">4 特性探索</a><a href="#s6">5 使用流程</a>
    <a href="#s7">6 Key 清单</a><a href="#s8">7 三大专题</a><a href="#s9">8 费曼自测</a>
  </div>

  <section id="s1"><h2>项目速览</h2>...</section>
  <section id="s2"><h2><span class="tag fam">熟悉</span> 外围层</h2>...</section>
  <section id="s3"><h2><span class="tag learn">学习</span> 内核层</h2>...</section>
  <section id="s4"><h2><span class="tag prac">实战</span> 跑起来</h2>...</section>
  <section id="s5"><h2><span class="tag feat">特性探索</span> 特性树</h2>
    <input type="checkbox" id="mmzoom" class="mmzoom-t">
    <label for="mmzoom" class="mmzoom-l">🔍 点击放大查看导图</label>
    <div class="mindmap-wrap"><svg class="mindmap" ...>...</svg></div>
  </section>
  <section id="s6"><h2>使用流程</h2>...</section>
  <section id="s7"><h2>Key 问题单</h2>...</section>
  <section id="s8"><h2>三大专题</h2>...</section>
  <section id="s9"><h2>费曼自测</h2>...</section>
</div>

<footer><项目名> 学习笔记 · 结构复用《GitHub 项目学习结构大纲模型》</footer>
</body>
</html>
```

导图放大标签的顺序硬要求：`input.mmzoom-t` → `label.mmzoom-l` → `.mindmap-wrap`，三者必须是**同级相邻**，否则 `~` 选择器不生效。

---

## 3. 内容清理清单

交付对象是**最终读者**，不是作者自己的过程记录。写完全文后逐条对照删除。

| 删掉 | 替换为 |
|---|---|
| 本地绝对路径、commit 短 hash、日期 | 「项目速览」只留仓库地址、版本号、实测环境 |
| 「学习步骤：clone → 读架构 → …」 | 整行删除 |
| 「本次实测」「本机」「我跑了」 | 中性化：「实测环境」「运行后」 |
| 首次启动引导弹窗截图与说明 | 整节删除 |
| 「给我的方式」「拿到 Key 后我会补齐」 | 删除；问题单只留清单与获取地址 |
| 自测结论 note、页脚流水账 | 删除，或压成一行版本说明 |
| 踩坑流水账（时间线式） | 「环境要求与安装提示」：只留读者能直接用的（镜像、依赖版本、SDK 版本） |
| 写作骨架说明、「本节讲什么」元话术 | 删除，标题即结论 |
| 未验证的推测（"应该支持""大概能"） | 删除，或改为「未验证」并说明原因 |

保留项：图注来源（哪个 URL / 哪条命令）、数字口径说明、项目设计限制（写进边界思考而非踩坑表）。

---

## 4. 交付前自检

```python
# 结构断言
assert html.startswith("<!DOCTYPE")
assert html.rstrip().endswith("</html>")
assert html.count("<section") == 9            # 章节数符合预期
assert "IMG_" not in html                     # 无残留占位符
assert html.count("data:image/png;base64,") == 图片数
```

```python
# 渲染断言（playwright）
bad = await pg.evaluate("() => [...document.images].filter(i=>!i.complete||!i.naturalWidth).length")
assert bad == 0
# 导图交互断言：点击放大后容器变 fixed 全屏
await pg.click("label.mmzoom-l")
pos = await pg.evaluate("() => getComputedStyle(document.querySelector('.mindmap-wrap')).position")
assert pos == "fixed"
```

导图交互必须**点开再点合**各验一次，只看首屏截图不算验过。
