# eli5a｜ELI5 微信图文（v1.0.0）

> 把一件刚发生的技术事件，写成 **500 字（上限 1000）**、配 3-6 张图、**能直接粘进公众号源码模式**的单文件 HTML 图文。写法是 ELI5，篇幅是纪律，兼容性靠实测。

仓库路径：[`workbuddy/skill/eli5a/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/eli5a)

使用说明：[`workbuddy/skill/eli5a/README.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/eli5a/README.md) ｜ 技能入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/eli5a/SKILL.md)

可运行样例：[`examples/qiyuan-demo.html`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/eli5a/examples/qiyuan-demo.html)（384 KB，4 图 base64 内联）

## 一句话

输入一个刚发生的技术事件，产出一篇 **572 字级别的短文 + 4 张带图注的图 + 一个单文件 HTML**，粘进公众号就能发。读者读完能带走一句话。

## 它解决什么问题

「让 AI 写一篇公众号图文」不难，难的是**发出去之后发现是废的**。这个技能固化的是几次真实返工换来的东西。

| 痛点 | 本技能的做法 |
|---|---|
| 微信编辑器吃掉 `<style>` 块和 class/id，本地好看粘进去全塌 | 样式 100% 内联在 `style` 属性；JS / `<style>` / class / id / 表单 / 外链 / SVG / 渐变 全部禁用 |
| 用 radio + `:checked` 做 tab，微信过滤 input 后两个面板同时亮 | 改成上下并列的左边框卡片：金棕=通俗讲，深蓝=严谨讲，不点也能看全 |
| 图注写在页面里，吃掉 40-70 字配额 | 图注**画进图片底部深蓝条左侧**，品牌水印在右侧，同一行；页面字数只算正文 |
| 标题用 `<br>` 换行，微信渲染不一致且不好传播 | 标题**单行 ≤12 字**，爆炸点是反常识/反差/数字冲突；渲染后量 `h1.clientHeight / lineHeight` 必须 = 1 |
| 章节写成「◇ 叁 · 白话讲讲那三座大山 ◇」，又长又散看不出逻辑 | 改成 **编号徽章 01 + 论点式短名**（≤10 字），固定四幕递进：是什么 → 变了什么 → 卡在哪 → 一句话带走 |
| 结尾挂品牌口号行，读者记不住重点 | 删掉口号，最后一幕固定「一句话带走」，19px 居中金句，全文唯一要记住的句子 |
| 只跑计数类校验就报「全部通过」 | 计数 + **Playwright 实渲染**双层：图 `naturalWidth > 0`、标题行数、逐图截图 |

## 五条硬约束

| 约束 | 判定方式 |
|---|---|
| 页面正文 ≤1000 中文字（目标 500） | `[\u4e00-\u9fff]` 正则计数 |
| 标题单行 ≤12 字 | 渲染后 h1 高度 / 行高 取整 = 1 |
| 章节编号递进、名是论点句 | 01 是什么 → 02 变了什么 → 03 卡在哪 → 04 一句话带走 |
| 图注在图内底带左侧、水印在右侧、无「图一/图二」 | 页面里 0 个图注 div，`图[一二三四五六七八]` 计数 = 0 |
| 结尾无品牌口号行 | `"把复杂系统，设计成简单可依赖的产品"` 检测 = False |

## 能力边界

| 做 | 不做 |
|---|---|
| 1000 字以内的微信图文（目标 500） | 4000-8000 字长文（用 `khazix-writer`） |
| 3-6 张图，含「形象说明」与「逻辑推演」两类 | PPT / 视频 / 海报 |
| 单文件 HTML，base64 内联，零外链 | 需要 JS 交互的页面 |
| 源码模式可直接粘贴 | 自动发布到公众号（用 `wechat-article-workflow`） |
| 已核实素材的通俗化 | 编数据。每个数字都要能追到来源 |

## 安装

```bash
git clone https://github.com/lifuchun522/aiskillhub.git
cp -r aiskillhub/workbuddy/skill/eli5a ~/.workbuddy/skills/eli5a
```

- 依赖：**Python 3.9+**，`pip install pillow`
- 中文字体自动探测（simhei / PingFang / Noto CJK），找不到用 `--font` 指定
- Playwright 仅用于交付前实渲染验证（可选，但强烈建议）

## 使用步骤

### 1. 喊一句

> 用 eli5a 写一篇：`启元机器人开启消费级人形机器人交付`

### 2. 它按七步走

| 步骤 | 做什么 | 关键纪律 |
|---|---|---|
| 1 | 核实素材 | 联网检索，落地事实清单（时间/主体/价格参数/原话/第三方数据/反面声音），**禁止凭记忆写数字** |
| 2 | 定角度与结构 | 四幕起步，选一个角度（反差型/原理型/现实型/时间型），不要全上 |
| 3 | 写正文 | 先写 1000 再砍到 500；砍铺垫不砍数据与金句 |
| 4 | 生成配图 | 场景图用 ImageGen（图内绝不放中文）；示意图用 Pillow 直排中文 |
| 5 | 构建 | `build.py`：水印+图注 → 压缩 → base64 内联 → 独立 JPG → 校验报告 |
| 6 | 校验 | 字符级 7 项 + Playwright 实渲染 4 项 |
| 7 | 交付闸门 | 发送前最后一步才加载 `delivery-no-pseudoblock`，贴 D1-D12 逐项快照 |

### 3. 也可以只用脚本

```bash
cp templates/wechat-article.html draft.html
# 写满正文，图片位置保留 <img src="{{IMG1}}"> 结构
python scripts/build.py --src draft.html --out 成稿.html \
  --img img1.png img2.png img3.png \
  --cap "开箱那一刻" "T1 的两种形态" "电池、零件、数据"
```

## 产物

```
成稿.html          # 单文件，图片 base64 内联，浏览器直接打开
成稿_img1.jpg      # 微信后台上传用（正文不接受 base64）
成稿_img2.jpg
成稿_img3.jpg
```

## 校验报告

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

再跑一层实渲染：

```python
dims = page.evaluate("[...document.querySelectorAll('img')].map(i=>({nw:i.naturalWidth,h:i.clientHeight}))")
# 每张图 naturalWidth > 0，否则就是 data URI 没进 src
```

## 版式参数

| 项 | 值 |
|---|---|
| 外底 / 纸面 / 描边 / 主色 / 辅色 | `#bcdcf2` / `#e8f4fd` / `#8fb9d6` / `#0b3d63` / `#3d6b8c` |
| 纸面 | `max-width:677px`、`padding:36px 26px`、`border-top:3px double #0b3d63` |
| 标题 | 36px 衬线居中**单行** |
| 正文 | 16px 宋体栈 / `line-height:1.8` / 两端对齐 / `text-align:justify` |
| 章节 | `margin:34px 0 18px` + 虚线上边 + 12px 白字深蓝徽章 + 19px 论点名 |
| 图片 | `margin:22px 0`，`width:100%`，1px 描边，底带 84px |
| 底带 | 左图注（≤12 字，过长自动缩字号）+ 右水印「资深架构师 李福春」 |

## 示例

| 篇目 | 类型 | 字数 / 图 | 角度 | 收束句 |
|---|---|---|---|---|
| 启元机器人 | 产品交付 | 572 / 4 | 现实型 | 机器人进家门不难，难的是三年后它还在 |
| roadster2 | 技术演示 | 981 / 6 | 反差型 | 技术不怕晚，怕的是你只看了热闹 |
| DeepSeek | 服务故障 | 794 / 4 | 原理型 | 不是它笨，是太多人同时想让它现做一道菜 |

三篇的结构拆解在 [`examples/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/eli5a/examples)，其中 `qiyuan-example.md` 是**篇幅与版式基准**，照它抄。

## 踩坑（摘）

完整版：[`references/pitfalls.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/eli5a/references/pitfalls.md)

### P0 · 占位符漏掉 `src="`，图变一条细线

模板写 `<img {{IMG1}} ...>`，替换后变成 `<img data:image/jpeg;base64,... style="...">`——**data URI 成了无值属性，`src` 根本不存在**。

页面渲染出来的不是破图图标，而是**一条 2px 带描边的细线**，肉眼像分隔线。

而 `img` 计数 = 4、`data:` 计数 = 4、外链布尔 False，校验全绿。**只有实渲染截图能抓到**（`naturalWidth` = 0）。

这条已经变成 `build.py` 的固定检查项 `img 缺少 src 属性: 0`，以及本技能最硬的一条纪律：**计数类校验全绿不等于页面正确，必须看至少一张带图的实渲染截图。**

### 其余 P0

- `<style>` 块 / class / id 写样式 → 微信全丢
- 表单元素做 tab → 过滤后两个面板同时亮
- 外链图片 → 微信不接收；base64 也不能直接发布，必须另存 JPG
- ImageGen 图里放中文 → 100% 乱码

### P1

- Pillow 画布底部不留白 → 84px 底带压住卡片
- 图注占字数 → 1000 上限被图注吃掉
- 章节名写成名词短语 → 看不出递进
- 标题用 `<br>` → 微信渲染不一致
- 图片已带底带再跑一次 → 双层水印
- 只凭「没抛异常」报成功 → 必须有字符级校验

## 两条元经验

1. **验证器报错时，先问「是稿子错了，还是尺子错了」。** 有一次字数脚本把图注算进正文，误报超标——改的是尺子不是稿子。
2. **最该持续更新的是「曾经错在哪」那一节，不是「正确做法」那一节。** 前者是经验，后者是常识。

## FAQ

**Q：为什么不用 tab 切换，读者不能自己选看哪版？**
A：微信过滤表单元素，`:checked` 方案在编辑器里失效，两个面板会同时显示。改成上下并列后，读者从上往下读，通俗和严谨都能看到，反而比点两下更省事。

**Q：base64 内联了，为什么还要另存 JPG？**
A：公众号**正文**不接受 base64 图片。HTML 里的 base64 用于本地预览和交付确认；真正发布要在后台上传独立 JPG 替换。两件事都要做。

**Q：字数能不能超 1000？**
A：不能。1000 是硬上限，500 是目标。超了就是没砍干净——先砍背景铺垫、再砍第二组并列证据、最后砍形容词，数据和金句不动。

**Q：和 `khazix-writer` 什么关系？**
A：风格同源。`khazix-writer` 写 4000-8000 字长文；`eli5a` 只做 1000 字以内的微信图文，把排版、配图、图注、字数校验全部固化进脚本。

**Q：能自动发布吗？**
A：本技能只交付到「单文件 HTML + 独立 JPG」。自动推草稿用 `wechat-article-workflow`。
