# eli5a · ELI5 微信图文

把一件刚发生的技术事件，写成**约 500 字、上限 1000 字**、配 3-6 张图、能直接粘进公众号源码模式的单文件 HTML 图文（v1.0.0）。

一句话：**短、有图、能发、读者能一句话带走。**

- **写法是 ELI5**：每个抽象论点必须落回案例的一个具体部件或场景。给「说明」不给「科普」。
- **篇幅是纪律**：目标 500 字，硬上限 1000。先写 1000 再砍到 500，砍铺垫不砍数据。
- **产物是两件**：一个图片全 base64 内联的单文件 HTML（可直接预览/交付），一份独立 JPG（微信后台发布时替换用）。
- **兼容是可验证的**：不靠「本地看着没问题」，靠 7 项字符级校验 + Playwright 实渲染。

## 能力边界

| 做 | 不做 |
|---|---|
| 1000 字以内（目标 500）的微信图文 | 4000-8000 字长文（用 `khazix-writer`） |
| 3-6 张图，含「形象说明」与「逻辑推演」两类 | PPT / 视频 / 图文混排海报 |
| 单文件 HTML，图片 base64 内联，零外链 | 需要 JS 交互的页面（微信会剥离） |
| 微信源码模式可直接粘贴 | 自动发布到公众号（另见 `wechat-article-workflow`） |
| 已核实素材的通俗化表达 | 编数据。所有数字必须能追到来源 |

## 安装

```bash
git clone https://github.com/lifuchun522/aiskillhub.git
cp -r aiskillhub/workbuddy/skill/eli5a ~/.workbuddy/skills/eli5a
```

其他宿主按各自约定放置（Claude Code / Codex / Cursor 均可直接用 `SKILL.md`）。

依赖：**Python 3.9+**，`pip install pillow`。Playwright 仅用于交付前的实渲染验证（可选）。

中文字体自动探测（simhei / PingFang / Noto CJK），找不到时用 `--font` 指定。

## 用法

直接对 Agent 说：

> 用 eli5a 写一篇：`启元机器人开启消费级人形机器人交付`

然后按 `SKILL.md` 的七步走。也可以只用脚本，自己写正文：

```bash
# 1) 抄骨架
cp templates/wechat-article.html draft.html

# 2) 写满正文，图片位置保留 <img src="{{IMG1}}"> 结构

# 3) 构建（水印 + 图注 + 压缩 + base64 内联 + 校验报告）
python scripts/build.py --src draft.html --out 成稿.html \
  --img img1.png img2.png img3.png \
  --cap "开箱那一刻" "T1 的两种形态" "电池、零件、数据"
```

产物：

```
成稿.html          # 单文件，图片 base64 内联，可直接预览
成稿_img1.jpg      # 发布时后台上传，替换对应位置的图
成稿_img2.jpg
成稿_img3.jpg
```

## 它解决什么问题

「用 AI 写一篇公众号图文」不难，难的是**发出去之后发现是废的**。这个技能固化的是那几次返工换来的五条：

| 坑 | 后果 | 本技能怎么防 |
|---|---|---|
| 用 `<style>` 块 / class / id 写样式 | 粘进微信版式全塌 | 样式全内联在 `style` 属性，无 `<style>` 块 |
| 用 radio + `:checked` 做 tab 切换 | 微信过滤表单元素后两个面板同时亮 | 改成上下并列的左边框卡片，金棕=通俗、深蓝=严谨 |
| 用外链图片 | 微信正文不接收 | base64 内联 + 同时另存独立 JPG |
| 图注写成页面的 div | 吃掉 40-70 字配额，1000 字上限被啃掉 | 图注画进图片底部深蓝条左侧，字数不计入页面 |
| 标题用 `<br>` 换行 | 微信渲染不一致，也不方便口头传播 | 标题单行 ≤12 字，渲染后量 `h1.clientHeight / lineHeight = 1` |

外加一条**只能靠实渲染抓到**的：占位符写成 `<img {{IMG1}}>` 而不是 `<img src="{{IMG1}}">`，替换后 data URI 变成一个无值属性，`src` 根本不存在——图不显示破图，而是变成**一条 2px 的细线**，肉眼像分隔线。`img` 计数、`data:` 计数、外链布尔全部正常，只有截图能发现。

## 五条硬约束

| 约束 | 判定 |
|---|---|
| 页面正文 ≤1000 中文字（目标 500） | `[\u4e00-\u9fff]` 正则计数，不靠感觉 |
| 标题单行 ≤12 字 | 渲染后 `h1` 高度 / 行高 取整 = 1 |
| 章节编号递进、论点是论点句 | 01 是什么 → 02 变了什么 → 03 卡在哪 → 04 一句话带走 |
| 图注在图内底带左侧、水印在右侧 | 同一条 84px 深蓝底带，页面无图注 div、无「图一/图二」 |
| 结尾无品牌口号行 | `结尾口号行残留` 必须为 False |

## 校验报告长什么样

`build.py` 跑完直接打印，**每一项都是正则确定性检查**：

```
页面CJK: 572 | 图内图注CJK: 23 | 合计: 595 -> 达标(<=1000)
字数档位: 优(<=600)
img: 4 | data: 4 | 外链 http: False
img 缺少 src 属性: 0
JS: False | style块: 0 | class: False | id: False | input: 0
HTML实体残留: 0
「图一/图二」编号残留: 0
结尾口号行残留: False
占位残留: 0
<br> 换行残留: 0
div/p/h1/section/b/span  开闭全部 OK
文件大小: 384KB
```

再补一层实际渲染（**必须做，计数类校验抓不到视觉问题**）：

1. 标题行数 = 1、栏宽 677
2. 4 张图 `naturalWidth > 0`（破了就是 0）
3. 逐图截图确认中文无乱码、底带左图注右水印

## 目录

```
SKILL.md                      # 入口：交付标准、标题/章节/图注/结尾规则、七步流程
README.md                     # 本篇
references/style.md           # 卡兹克风格速查 + ELI5 三段式
references/wechat-compat.md   # 微信兼容红线 + 版式参数 + 图片底带规范
references/workflow.md        # 六步流水线 + 校验清单 + Playwright 必查四项
references/pitfalls.md        # 踩坑清单（4 个 P0 / 7 个 P1）
templates/wechat-article.html # 677px 天蓝纸感骨架，{{IMGn}} 占位
scripts/build.py              # 水印+图注 → 压缩 → base64 内联 → 独立 JPG → 校验报告
examples/                     # 三篇成稿拆解 + 一份可运行样例（draft + demo）
```

## 示例

| 篇目 | 类型 | 字数 / 图 | 角度 |
|---|---|---|---|
| [启元机器人](examples/qiyuan-example.md) | 产品交付 | 572 / 4 | 现实型 · 交付是换了张考卷 |
| [roadster2](examples/roadster2-example.md) | 技术演示 | 981 / 6 | 反差型 · 能买的那台不会飞 |
| [DeepSeek](examples/deepseek-example.md) | 服务故障 | 794 / 4 | 原理型 · 现做后厨占着灶台 |

成品可运行样例：[`examples/qiyuan-demo.html`](examples/qiyuan-demo.html)（384KB，4 图内联）。

## 风格来源

文本风格提炼自「卡兹克」公众号写法（有见识的普通人在认真聊一件打动他的事），本技能只做**微信图文这一种形态**的收敛版。需要 4000-8000 字长文用 `khazix-writer`。

## 踩坑摘要

完整版见 [`references/pitfalls.md`](references/pitfalls.md)。

| 级别 | 坑 |
|---|---|
| P0 | `<style>` 块写样式 → 微信全丢 |
| P0 | 表单元素做 tab → 过滤后两个面板同时亮 |
| P0 | 外链图片 → 微信不接收；base64 也不能直接发布，必须另存 JPG |
| P0 | ImageGen 图里放中文 → 100% 乱码 |
| P1 | Pillow 画布底部不留白 → 84px 底带压住卡片 |
| P1 | 图注占字数 → 1000 上限被图注吃掉 |
| P1 | 章节名写成名词短语 → 看不出递进 |
| P1 | 标题用 `<br>` → 渲染不一致 |
| P1 | 图片已带底带再跑一次 → 双层水印 |
| P1 | 只凭「没抛异常」报成功 → 必须有字符级校验 |
| P1 | 占位符漏 `src="` → 图变细线，计数全绿只有截图能抓 |
