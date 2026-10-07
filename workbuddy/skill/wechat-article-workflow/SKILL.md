---
name: wechat-article-workflow
display_name: 公众号文章工作流
display_name_en: WeChat Article Workflow
description: |
  公众号文章完整工作流（10步SOP）。当用户说\"写文章\"、\"发推文\"、\"推到草稿箱\"、\"公众号排版\"，或需要完成从素材讨论到推送草稿的完整流程时使用。包含踩坑清单（P0/P1/P2级）、微信兼容HTML规则、Seedream 4.5漫画生成、push_draft.py推送脚本使用说明、推送后复盘模板。
description_zh: >-
  公众号文章完整工作流：选题→素材→写作→去 AI 味→配图→封面→排版→推送草稿箱。
description_en: >-
  End-to-end WeChat article pipeline from topic to draft push, including illustration and layout.
version: 2.7.1
author: 李福春 资深架构师
---

# 公众号文章完整工作流

## 何时使用此 Skill

此 skill 在以下场景触发：
- 用户要求写公众号文章、发推文、推送到草稿箱
- 用户说"按之前的工作流来"、"走一遍流程"
- 用户要求写**系列文章**、"继续写剩下的 N 篇"
- 文章需要微信安全HTML排版 + 配图 + 推送草稿

---

## 零、目录码放规范（先说这个，不然后面全乱）

**所有产物按编号有序码放，一个系列一个根目录。这是硬要求。**

```
<workspace>/
  articles/
    <系列名>/                       # 系列根目录（一个系列一个）
      00/                           # 系列规划（编号目录，不带中文）
        series-plan.md              # 系列定位/故事线/逐篇推进表/叙事模板
        style-guide.md              # 全系列统一风格（人称/节奏/诗引/配图风格/水印）
      _series/                      # 系列共享资源（脚本/中间产物，不进篇目录）
        templates/                  # 所有 *.py 脚本
        build/<编号>/               # arch_spec.json / image_mapping.txt / 验证截图
        assets/
      01/                           # 篇目录：纯序号，不带中文
        index.html                  # ★ 本地预览：相对路径引用，双击即看
        正文.md                      # 纯文本终稿
        article_body.html           # 微信安全 HTML（含 {imgN} 占位符，推送脚本消费）
        metadata.json               # 本篇元信息（标题/摘要/承接/悬念）
        publish_config.json         # 推送配置
        images/                     # 全部配图（已打品牌水印）
          img0.png ~ imgN.png       # 正文图
          img_arch.png              # 结构图（如有）
          cover_final.png           # 封面
      02/ 03/ ... 09/
  video/
    <系列名>/
      00_系列推广视频/
        script.md                   # 口播脚本
        storyboard.md               # 分镜表
```

**命名铁律（用户明确要求）：**
- **篇目录只用两位序号，不带中文**：`01/`、`02/`、…、`09/`。标题写在 `metadata.json` 的 `title` 里，不要写进目录名——中文目录名在跨平台复制、URL 引用、脚本传参时都要额外转义
- 系列规划目录固定 `00/`；共享资源目录 `_series/` 以下划线开头，与编号目录自然分开排序
- 每篇必须有 `metadata.json`，记录本篇在系列中的位置（承接谁、留下什么悬念）——系列连贯性的唯一真相源
- 视频产物放 `video/` 独立目录，与 `articles/` 平行，**不要混在文章目录里**

**篇目录只留 6 项**（`index.html` / `正文.md` / `article_body.html` / `metadata.json` / `publish_config.json` / `images/`）。
**不再生成 `preview.html`**（base64 自包含版已移除，本地双击 `index.html` 即可预览）。
脚本（`*.py`）、`arch_spec.json`、`image_mapping.txt` 一律收到 `_series/` 下，不要在篇目录里堆。

---

## 一、系列文章规范（写系列必读）

### 1.1 动笔前先产出 `series-plan.md`

不要直接写第 1 篇。先读用户给的大纲文档，产出系列规划，**经用户确认后再批量创作**。

| 章节 | 内容 |
|------|------|
| 系列定位 | 一句话核心命题；各篇之间关系（如"总—分—总"） |
| 唯一故事线 | 主人公设定、创业方向、产品边界、商业模式假设 |
| 逐篇推进表 | 篇号 / 标题 / 对应主线 / 承接上一篇什么结果 / 本篇解决什么问题 / 留下什么悬念 |
| 统一叙事模板 | 每篇固定展开节奏（如：上一式结果→本式危机→框架入场→具体决策→结果验证→留下悬念） |
| 技术与内容边界 | 哪些能写、哪些暂缓（避免每篇重复堆砌） |
| 每篇实践输出 | 每篇末尾交付的具体产出（图/清单/模板），作为系列可累积资产 |

### 1.2 七条系列连贯性铁律

1. **禁止另起案例。** 所有篇目围绕同一主人公、同一门生意连续推进。每篇开头必须交代"上一篇走到哪了"。
2. **每篇留钩子。** 结尾抛出本篇未解决的问题，明确指向下一篇。钩子要具体（"第一个 30 天做什么"），不要空洞（"未来可期"）。
3. **跨篇埋线。** 值得后文展开的细节，当篇不解答，明确标注"放到第 N 式再讲"。
4. **统一叙事人称。** 系列锁定后不切换。
5. **统一视觉体系。** 配图风格、水印、排版模板完全一致；封面只换文字不换版式。
6. **篇幅节奏一致。** 各篇字数控制在 ±20% 区间内。
7. **诗引主线连续（可选）。** 若用古诗做叙事主线，提前规划每篇用哪一句，避免重复。

### 1.3 批量创作流程

```
读大纲 → 产出 series-plan.md → 用户确认
   → 逐篇循环（每篇走「完整10步 SOP」）
   → 每篇结束后更新 metadata.json
   → 全部完成后写第 0 篇（目录/推广篇）
```

**批量时注意：** 每篇都要独立跑 `fix_for_wechat.py` 与 `generate_preview.py`，不要因为"和上一篇差不多"就跳过验证。

---

## 二、第 0 篇（目录/推广篇）规范

系列全部发布后写，作为导航入口。**不重复正文内容，只做导航与钩子。**

| 要素 | 说明 |
|------|------|
| 系列缘起 | 为什么写这个系列，一两段，讲人话 |
| 九篇一览 | 表格或卡片列表：篇号 + 标题 + 一句话讲什么 + 链接 |
| 阅读路径建议 | 按顺序读 / 按兴趣跳读，各一条 |
| 系列金句 | 从各篇提炼 3-5 句原文 |
| 数据与成果 | 系列可累积资产（多少张图、多少份模板、多少个可复用结论） |
| 未来计划 | 更新频率、下一篇方向、互动引导 |
| 系列总图 | 一张贯穿全系列的主线图 |

**链接占位：** 用户发布完前 N 篇后提供地址，届时用 `{link01}`~`{link09}` 占位符统一替换。写脚本扫描占位符，缺链接的位置标注醒目提示，不要静默留空。

---

## 三、完整 10 步 SOP（单篇）

### 第1步：素材讨论（聊透再动笔）

**不要直接开写！** 先跟用户聊：核心观点是什么、用什么角度切入、结构怎么搭、哪些内容放进去、哪些砍掉。

用户说"开写"/"可以了"再开始创作。写系列时先走「1.1 series-plan.md」再聊单篇。

---

### 第2步：拟爆款标题（3-5个供选）

**标题是第一步，先定题再动笔。** 标题铁律：必须和内容高度匹配，绝不标题党。

| 文章类型 | 标题套路 | 示例 |
|---------|---------|------|
| 读书笔记 | 反常识观点型 / 痛点共鸣型 | "读了3遍《原则》，才发现达利欧在撒谎" |
| 干货教程 | 数字清单型 / 结果承诺型 | "做了15年安全管理，我总结出这3条要命的红线" |
| 随笔感悟 | 故事钩子型 / 金句型 | "今天在现场，一个焊工教会我的事" |
| 投资理财 | 警示型 / 揭秘型 | "你以为在理财，其实在给银行打工" |
| 系列连载 | 系列感型 / 反常识钩子型 | "独孤九剑①总诀式：一个人如何干完一支团队的活" |

用户选定后，再进行下一步。

---

### 第3步：写初稿

**写作风格要求：**
- 用"我"的视角，不用"笔者"/"我们"
- 接地气，说人话，不堆砌专业术语
- 有具体场景（现场细节、对话、动作），不用空洞说教
- 允许不完美（"有个事儿"、"说个真事"），不用"首先、其次、最后"
- 敢说真话，有自己的判断，不写正确的废话

**故事性硬要求（用户 2026-09-30 明确）：**
正文不能只有道理，必须有完整故事要素——人物（有名字有身份）、时间地点细节（几点、在哪、什么天气）、对话戏（直接引语）、转折、悬念。结构关系（层级/流程）不许用文字堆，要配结构图。

---

### 第4步：去AI味（humanizer）

**必做环节。** 初稿写完后必须跑 humanizer 处理。

**重点检测模式（24种AI痕迹）：** 空洞强调（"至关重要"）、凑三件套（"首先、其次、最后"）、-ing拖尾、花哨词汇（"颠覆性"、"赋能"）、模糊引用（"研究表明"）、每段长度完全一致。

**注入人味：** 有观点有立场敢说"我觉得"；节奏有变化（短段/长段/单句成段交替）；允许口语化（"说实话"、"有个事儿"）。

---

### 第5步：生成封面（自动套用HTML模板）

**必做环节。** 写完初稿、定好标题后，先生成封面再配图。

#### 5.1 准备工作

确保以下文件就位：
```
articles/<系列名>/<编号>/
  publish_config.json    # 封面配置（标题/副标题/标签/模板）
  generate_cover.py     # 从共享工具包复制
```

`publish_config.json` 格式：
```json
{
  "title": "文章标题",
  "digest": "文章摘要",
  "cover": {
    "enabled": true,
    "title": "封面标题（可与文章标题不同）",
    "subtitle": "封面副标题",
    "tag": "电力安全",
    "template": "模板1-电力安全.html"
  }
}
```

#### 5.2 自动生成（推荐）

运行 `generate_cover.py`：

```bash
cd articles/<系列名>/<编号>/
python generate_cover.py "标题" "副标题" --tag "标签" --template "模板1-电力安全.html"
```

**⚠️ 封面标题铁律（007篇踩坑）：**
- 封面标题**必须单独设置**，不能与文章标题相同
- **≤10个中文字符**（最好6-8字），超出必溢出
- 文章标题可以长（≤64字），但封面标题必须短
- 配置方式：`publish_config.json` 里 `"cover": {"title": "短标题"}`

**脚本逻辑：**
1. 读取HTML模板（默认 `模板1-电力安全.html`，稳定路径 `本地公众号素材目录/封面模板/`；本地目录有则优先）
2. 自动替换标题、副标题、标签、品牌名
3. 用 playwright 打开HTML，等待字体渲染完成（2秒）
4. 截图保存为 `covers/cover_final.png`（900×500px）

**封面模板（已简化）：**
- **默认只用 `模板1-电力安全.html`（深蓝渐变 + 金色）**，适配绝大多数电力安全/干货文。
- 模板稳定路径：`本地公众号素材目录/封面模板/模板1-电力安全.html`（已建共享目录，不再依赖沙箱临时路径）。
- 模板2~5 未建，不再使用。

#### 5.3 标题自动换行规则

脚本自动处理标题过长问题：
- 主标题：每行最多 **14个中文字符**，超出自动换行
- 副标题：每行最多 **18个中文字符**
- 字体大小自适应（标题最多3行，副标题最多2行）

#### 5.4 推送时自动生成（集成方案）

在 `push_draft.py` 中已集成封面生成逻辑：

```python
# 在 push_draft.py 开头
if config['cover']['enabled']:
    cover_path = generate_cover(
        title=config['cover']['title'],
        subtitle=config['cover']['subtitle'],
        tag=config['cover']['tag'],
        template=config['cover']['template']
    )
    # 上传为永久素材，获取 thumb_media_id
    thumb_media_id = upload_permanent_image(cover_path)
```

**运行方式：**
```bash
cd articles/<系列名>/<编号>/
python push_draft.py   # 自动生成封面 → 上传 → 创建草稿
```

#### 5.5 兜底方案（playwright 失败时）

若 playwright 未安装或截图失败，改用 **Pillow 纯色背景方案**：

```bash
python generate_cover.py "标题" "副标题" --tag "标签" --fallback
```

输出：纯色渐变背景 + 文字（无装饰元素），可用作临时封面。

---

### 第6步：生成配图（路线 A：WorkBuddy ImageGen 自动 / 路线 B：豆包手动）

**默认走路线 A。** 用户明确说"手动出图"时才走路线 B。

#### 路线 A：WorkBuddy ImageGen（自动，推荐）

2026-09-30 起可用。**不需要切换对话模型**，内置 `ImageGen` 工具直接出图（混元）。
**调用前必须告知用户积分消耗：单张约 5-10 积分**（额外计费）。

**执行流程：**

1. **规划图片位**：逐段分析文章，列出所有需要图片的位置，定下 `{img0}`（封面）~`{imgN}`（正文）
2. **逐张调用 ImageGen**：prompt 用英文，风格统一前缀，`size` 建议 `1536x1024`，`quality=high`
3. **跑 `process_comics.py`**：裁掉右下角水印 + 按 `imgN.png` 归位命名
4. **重跑 `generate_preview.py`**：本地确认版式

**三条硬约束（2026-09-30 踩坑，必看）：**

- **图里绝不放中文。** 模型渲染中文 100% 乱码。诗句、标题、序号一律用 HTML 文字排版，图片只负责意境。prompt 结尾固定加：
  `Absolutely no text, no letters, no words, no calligraphy, no watermark, no seal, no numbers.`
- **生成文件名会撞车。** 落盘文件名 = prompt 首个词 + 时间戳。**前缀相同的两次调用若落在同一秒会互相覆盖**（本次 5 张丢了 1 张，重出才发现）。→ 每张图 prompt 的首词必须互不相同（如 `Cover artwork...` / `Modern minimal...` / `Traditional Chinese ink wash painting...`）。
- **右下角有强制水印**（"AI生成 / WORKBUDDY"）。`process_comics.py` 默认裁掉底部 90px 消除，裁完比例仍为 1.65:1，不影响正文排版。

#### 路线 B：手动豆包生成（备用）


**执行流程：**

1. **计算图片数量**：逐段分析文章，列出所有需要图片的位置（含封面）
2. **写入 `comic_prompt.txt`**：为每张图片写一段 Seedream 风格英文 prompt，适合豆包APP识别
3. **输出 prompt 清单**：在对话中展示所有 prompt，告知用户"复制这段 → 打开豆包APP → 粘贴生图 → 下载"
4. **等待用户给图**：用户把图片放到 `comics/` 目录后告诉我文件名
5. **填入文章**：把 `article_body.html` 里的 `{imgN}` 替换为图片路径，或等用户给齐后统一替换

**`comic_prompt.txt` 格式（路线 B 专用）：**
```
01_封面.jpg: Safety education comic illustration, beige background, thick black outlines. [场景]. Text top right: [短标题≤8字]
02_引言.jpg: 同上格式...
...
```

**图片数量计算公式：**
- 漫画数 = 文章步骤数 + 2（1张封面 + 1张收尾大图）
- 或按"每个细节配一图"原则，逐段确认

**⚠️ 占位符连续性检查（路线 B 更要小心）：**
- `{img0}` = 封面，`{img1}`~`{imgN}` = 正文漫画，必须连续不得跳号
- 写 `comic_prompt.txt` 前，先列出文章结构清单，再逐条写 prompt
- 生成后检查：每个 `{imgN}` 都有对应图片文件

**❌ 禁止：** ImageGen（Hunyuan）生成带中文的漫画，文字100%乱码。

---

### 第7步：微信安全 HTML 排版

**核心原则：微信会过滤 `<style>` 标签和 `class=""` 属性，所有样式必须用纯内联 `style=""`。**

#### 6.1 HTML 结构规则（必须遵守）

| ❌ 禁止 | ✅ 正确做法 |
|---|---|
| `<div>` | `<section>` |
| `<h1>`/`<h2>` | `<p>` + `style="font-size:...;font-weight:bold;"` |
| `display:flex` | `display:inline-block` + `text-align:center` |
| `<style>` 标签 | 所有样式写在内联 `style=""` 里 |
| `class=""` 属性 | 删除，改用内联样式 |

#### 6.2 排版模板

参考 `assets/html_template.html`（第七篇文章验证过的微信安全模板）。

**核心结构：**
```html
<!-- 顶部关注提示 -->
<section style="text-align:center;padding:10px 0;">
  <span style="font-size:13px;color:#999;">你的公众号名称 · 点击上方蓝字关注</span>
</section>

<!-- 标题区 -->
<section style="background:#1a1a2e;padding:24px 20px;border-radius:8px;margin-bottom:16px;text-align:center;">
  <p style="font-size:20px;font-weight:bold;color:#fff;...">文章标题</p>
  <p style="font-size:13px;color:#e35d28;...">原创 · 你的公众号名称</p>
</section>

<!-- 封面图 -->
<p style="text-align:center;margin:0 0 16px 0;">
  <img src="{img0}" alt="" style="width:100%;border-radius:8px;">
</p>

<!-- 正文段落（米色底色 + 橙色左边框） -->
<section style="background:#fafaf7;padding:20px;border-radius:8px;margin-bottom:14px;border-left:4px solid #e35d28;">
  <p style="margin:0;color:#333;font-size:15px;line-height:1.9;">正文内容...</p>
</section>

<!-- 圆形编号（用 display:inline-block 居中） -->
<section style="display:inline-block;background:#e35d28;color:#fff;font-size:18px;font-weight:bold;width:36px;height:36px;line-height:36px;text-align:center;border-radius:50%;margin:20px 0 8px 0;">
  N
</section>

<!-- 漫画配图 -->
<p style="text-align:center;margin:16px 0;">
  <img src="{imgN}" alt="" style="width:100%;border-radius:8px;">
</p>

<!-- 结尾卡片 -->
<section style="background:linear-gradient(135deg,#1a1a2e,#16213e);...">
  ...
</section>

<!-- 话题标签（居中段落） -->
<section style="text-align:center;margin:24px 0 16px 0;font-size:15px;color:#e35d28;">
  <p style="margin:0;">#电力安全  #迎峰度夏  #你的公众号标签</p>
</section>
```

#### 6.3 图片占位符规则

| 占位符 | 用途 | 位置 |
|--------|------|------|
| `{img0}` | **篇首图** | **诗引之后、正文第一个小节标题之前**（与诗引匹配） |
| `{img1}`~`{imgN}` | 正文配图 | 对应小节标题下方 |
| `{img_arch}` | 结构图 | 对应小节标题下方 |

**⚠️ `{img0}` 固定为篇首图**（2026-09-30 用户明确要求）：
- 位置在**诗引之后、第一个正文小节标题之前**，不要放在首节标题下方
- 语义上与开篇诗引呼应（诗引给情绪，首图给画面），形成一个「引子区」
- `md2wechat.py` 已内置：`img0` 不进 `LAYOUTS`，由 `emit_lead()` 在诗引行之后统一输出一次

**⚠️ 占位符连续性检查：**
- `{img0}`~`{imgN}` **必须连续**，不得跳号
- 写完后必须全文搜索确认：所有占位符都存在
- 跳号会导致推送时部分图片未上传（如缺少 `{img1}`，则 img1.png 不会被上传）

**⚠️ 正文末尾不加署名行**（2026-09-30 用户明确要求）：
- **不要**在 `</section>` 前加 `<p>李福春 · 资深架构师</p>` 这类署名
- 品牌露出靠**图内水印**（右下角圆头像 + 「资深架构师 李福春」），不靠文末文字
- `md2wechat.py` 已移除该输出（原 `C["sign"]` 分支）

**⚠️ 正文 md 里不要手写占位符**（2026-09-30，坑32）：
- 占位符**全部由 `LAYOUTS` 配置自动插入**，作者手写会与自动插入的撞车，同一张图渲染两次
- 交付前必查：`grep -c "{img" 正文.md` == **0**

#### 6.4 表格规则

`md2wechat.py` 支持 GFM 表格，渲染为微信安全的 `<section>` + `<span style="display:inline-block;width:N%">`。

| 项 | 规定 |
|---|---|
| 语法 | 标准 GFM：表头行 + `\|---\|` 分隔行 + 数据行 |
| 列数 | 建议 3~5 列；超过 5 列在手机上会挤压 |
| 分隔行 | 必须带竖线（`\|---\|---\|`）；裸 `---` 是水平分隔线，不是表格 |
| 表头 | 自动加 `#f5f2ec` 底色 + 加粗 |
| 单元格内 | 支持 `**粗体**`；不支持换行、图片、列表 |

**交付前检查：** `grep -c '^<p[^>]*>|' article_body.html` 必须为 **0**（非 0 说明有表格未被渲染，见坑31）

#### 6.4 话题标签规则

- **加的位置**：`article_body.html` 末尾、结尾卡片之后
- **格式**：用微信可识别的 `#话题名` 格式，放在居中 `<section>` 里
- **数量**：每篇 2-3 个，不超过3个
- **`#你的品牌标签` 每篇必加**（打造个人品牌聚合页）

标签选择规则：

| 文章类型 | 固定标签 | 可变标签 |
|---------|---------|---------|
| 电力安全干货 | `#电力安全` `#你的品牌标签` | 按主题（如 `#迎峰度夏`） |
| 读书笔记 | `#读书笔记` `#你的品牌标签` | 书名或主题 |
| 办公效率 | `#办公效率` `#你的品牌标签` | 工具名 |
| 投资理财 | `#投资理财` `#你的品牌标签` | 主题 |

---

### 第8步：运行 fix_for_wechat.py 自动修复

**必做环节。** 写完 `article_body.html` 后必须跑此脚本。

```bash
python fix_for_wechat.py articles/010_xxx/article_body.html
```

**脚本功能（自动执行）：**
1. 去除 BOM、零宽字符等不可见脏字符
2. 将残留的 `<div>` 转为 `<section>`
3. 将残留的 `<h1>`/`<h2>` 转为 `<p>`
4. 去除 `display:flex` 属性
5. 去除 HTML 注释 `<!-- -->`
6. 压缩多余空行

**输出示例：**
```
✔ WeChat-safe HTML 已写入: article_body.html
  残留 <div>:  0 个（已修复）
  残留 <h2>:   0 个（已修复）
  display:flex:  0 处（已修复）
  HTML注释:  6 个（已清理）
```

**⚠️ 若输出显示有残留标签未修复，立即停止，手动检查 HTML 源码。**

---

### 第9步：本地预览（仅 `index.html`）

**目的：** 推送草稿前，本地双击查看排版效果。

**只出一种产物：**

| 产物 | 图片方式 | 体积 | 适用场景 |
|---|---|---|---|
| `index.html` | 相对路径 `images/xxx.png` | 13~22 KB | **本地双击看版式**（file:// 下 images/ 可达） |

**不再生成 `preview.html`**（base64 自包含版已移除，流程简化）。

运行：
```bash
python _series/templates/generate_preview.py --dir articles/<系列名>/02/
```

**⚠️ 铁律：**
- **占位符必须整体替换为完整 `<img>` 标签**。只把路径字符串塞进占位符位置会得到一段裸文本 —— HTML 里 `<img>` 数量为 0。自检：`grep -c '<img ' index.html` 必须等于图数
- **占位符在 `article_body.html` 里必须单独成行，不能包在 `<p>...</p>` 中**（`md2wechat.py` 已按此输出）
- **必须有 `<meta charset="UTF-8">`**，否则中文乱码
- **相对路径版不能直接粘贴进公众号编辑器**（图片不会跟着走）。推送走 `article_body.html` + `push_draft.py`
- 验证：`python scripts/verify_render_dual.py --series-dir <系列根目录>`（file:// 确认 `index.html` 图片全部可见）
---

### 第10步：推送草稿箱

**⚠️ 铁律：先预览、再推送。绝不跳过预览直接推草稿箱。**

#### 9.1 准备 `push_draft.py`

在文章目录下创建 `push_draft.py`（参考 `scripts/push_draft_template.py`）。

**核心逻辑：**
```python
wp = WeChatPublisher(APPID, APPSECRET)

# 1. 上传漫画获取URL
comic_urls = {}
for cf in comic_files:
    url = wp.upload_image(os.path.join(COMICS_DIR, cf))
    comic_urls[cf] = url

# 2. 读取HTML模板 + 清洗脏字符
with open("article_body.html", "r", encoding="utf-8") as f:
    html_template = f.read()
html_template = re.sub(r'[\ufeff\u200b\ufffe]', '', html_template)

# 3. 用 format() 注入图片URL（避免f-string嵌套问题）
content = html_template.format(
    img0=comic_urls.get(comic_files[0], ""),
    img1=comic_urls.get(comic_files[1], ""),
    # ...
)

# 4. 创建草稿
media_id = wp.create_draft(title, content, author, digest)
```

#### 9.2 执行推送

```bash
cd articles/010_xxx/
python push_draft.py
```

**输出示例：**
```
==================================================
推送文章：安全生产月搞排查，这5条以前不算事，7月1日后全是重大隐患
标题字数：29 字
漫画数量：6 张
==================================================

[1/3] 上传漫画到微信素材库...
  上传：01_封面.jpg ... [OK]
  ...

[2/3] 读取文章 HTML 模板...
HTML 模板已加载，图片 URL 已替换

[3/3] 创建草稿...
[草稿] 创建成功! media_id: abc123...
  → 去公众号后台「草稿箱」发布即可
```

#### 9.3 后台确认发布

1. 登录公众号后台：`https://mp.weixin.qq.com/`
2. 进入「草稿箱」
3. 找到刚推送的草稿，点击「预览」
4. 确认排版、图片、内容无误
5. 手动点击「发布」

**⚠️ 绝不自动发布，必须保留最终确认权。**

---

## 四、系列视频配套规范

每篇文章可配一条 3~5 分钟口播视频（视频号 / 抖音 / B站竖屏）。**视频与文章一对一映射，共用同一套叙事骨架**，不另起炉灶。

### 4.1 目录与文件

```
video/<系列名>/
├── 00_系列总纲.md              # 整个系列的视频节奏表（可选，0篇配发）
├── NN_<篇名>/
│   ├── script.md               # 口播脚本（可直接念）
│   ├── storyboard.md           # 分镜表
│   └── assets/                 # 该期视频素材（截图/演示录屏/题图）
```

命名与文章目录**同号同序**：文章 `01_总诀式` ↔ 视频 `01_总诀式`。改文章编号必须同步改视频编号。

### 4.2 script.md 六段结构（硬性）

| 段 | 时长占比 | 作用 | 写法要求 |
|---|---|---|---|
| 钩子 Hook | 0~15s | 3 秒内抓住人 | 一个反常识结论 / 一个具体数字 / 一句冲突性提问。**禁止**"大家好我是XX"开头 |
| 承接 Setup | 15~40s | 交代场景与人 | 复用文章里的**同一个故事**（人物、时间、地点、对话），不换案例 |
| 冲突 Turn | 40~90s | 转折与悬念 | 把文章的"卡点"讲透：原来怎么做 → 撞到什么墙 |
| 方法 Method | 90~200s | 核心干货 | 3 点以内，每点一句话结论 + 一个可操作动作。可插入架构图/演示录屏 |
| 金句 Punch | 200~230s | 记忆点 | 直接引用文章里的原创古诗或一句凝练总结，**画面定格 + 字幕放大** |
| 引导 CTA | 末 15s | 转化 | "完整版在公众号『XX』，搜『标题关键词』" + 关注/在看引导 |

**口播字数配比：中文约 240~260 字/分钟**。3 分钟视频 ≈ 750 字，5 分钟 ≈ 1250 字。

### 4.3 storyboard.md 分镜表（七列，必须齐全）

| 镜号 | 时间 | 画面 | 时长 | 旁白 | 字幕/特效 | 素材来源 |
|---|---|---|---|---|---|---|
| S01 | 00:00-00:12 | 主播半身近景，直视镜头 | 12s | （钩子全文） | 大字标题弹出 | 实拍 |
| S02 | 00:12-00:35 | 办公室场景/桌面前景 | 23s | （承接全文） | 关键名词高亮 | 实拍 + 图文贴纸 |
| S03 | 00:35-01:20 | 架构图 / 白板推演 | 45s | （冲突全文） | 箭头动画逐步出现 | **复用文章 `comics/img_arch.png`** |
| S04 | 01:20-02:50 | 分点讲解，切屏幕演示 | 90s | （方法全文） | 序号角标①②③ | 录屏 / 截图 |
| S05 | 02:50-03:10 | 定格 + 古诗竖排 | 20s | （金句） | 诗文字幕居中放大 | **复用文章配图 / 书法字** |
| S06 | 03:10-03:25 | 主播回到画面 | 15s | （CTA） | 公众号二维码浮层 | 实拍 + 二维码 |

### 4.4 视频与文章的一致性铁律

1. **故事不能换**：视频里的案例、人物、对话必须与文章完全一致，否则观众跨平台会产生割裂感。
2. **金句必须是原文**：古诗或总结句逐字引用，不许改写。
3. **架构图复用**：文章里的 `img_arch.png` 直接作为方法段的主画面，不另画一版。
4. **标题呼应**：视频标题 = 文章标题 + 情绪前置（如"一个人干完一支团队的活，我用了这 9 招"）。
5. **编号对齐**：`NN` 号在文章、视频、视频标题在系列规划表四处必须一致。

### 4.5 完整系列批量产出顺序

**不要一篇一篇串行做**（前 9 篇好写，第 0 篇依赖前 9 篇的标题、金句、链接）。正确顺序：

```
阶段1：出 series-plan.md（逐篇推进表）→ 用户确认
         ↓
阶段2：串行创作第 1~9 篇（每篇走完 10 步 SOP，但可暂不推送）
         每篇产出：index.html / article_body.html / metadata.json / 视频 script+storyboard
         ↓
阶段3：用户发布第 1~9 篇 → 回收链接
         ↓
阶段4：写第 0 篇（目录/推广篇），替换 {link01}~{link09}
         ↓
阶段5：系列总纲视频（00_系列总纲.md）可与第 0 篇同期产出
```

**阶段2 的可并行点**：出图（ImageGen 调用）与写正文解耦——先定稿正文与图片 prompt 清单，一次性批量出图，再统一打水印、统一生成预览。避免反复切换上下文。

### 4.6 系列连贯性检查（阶段2 每篇收尾必做）

对照 `00_系列规划/series-plan.md` 的推进表逐项打勾：

- [ ] 古诗引与推进表分配的句子一致（不重复、不跳号）
- [ ] 承接上篇的钩子存在（回指上一篇的结论或悬念）
- [ ] 结尾留了下篇的钩子（悬念句）
- [ ] 术语首次出现处有解释，后续篇目直接复用不重复解释
- [ ] 原创诗与正文方法段一一对应（诗里每句能在正文找到落点）
- [ ] `metadata.json` 的 `series`/`index`/`prev`/`next` 字段已填

### 4.5 单篇视频制作流程

1. 文章 10 步 SOP 走完（此时故事、古诗、架构图均已定稿）
2. 从文章抽取：钩子句、故事段、方法段 3 点、金句、CTA
3. 写 `script.md`（六段结构，控字数到目标时长）
4. 写 `storyboard.md`（按 script 逐段切镜，七列填满）
5. 标注可复用的文章素材路径

---

## 踩坑清单（每次创作前必看）

### 🔴 P0级：致命坑，踩了就重来

#### 坑0：`<div>` + `<h2>` + `display:flex` 组合导致微信吞样式

- **现象：** 推送成功，CSS 样式全部丢失，白底黑字纯文本
- **真凶：** `<div>` / `<h2>` / `display:flex` 组合（第三次推送确认）
- **✅ 正确做法：**
  - 所有 `<div>` → `<section>`
  - 所有 `<h2>` → `<p>`（用 `font-weight:bold` + `font-size` 模拟标题样式）
  - 禁止使用 `display:flex`、`align-items`、`justify-content` 等 flexbox 属性
  - 圆形编号用 `display:inline-block` + `line-height` + `text-align:center` 居中

#### 坑1：`<style>` 标签被微信全部过滤

- **现象：** 排版全丢、CSS 消失、图片不显示、文字乱码
- **原因：** 公众号编辑器不支持 `<style>` 标签和 `class=""` 属性，全部被过滤
- **✅ 正确做法：** 所有样式必须用纯内联 `style=""` 写

#### 坑30：预览面板拿不到 `images/` 子目录（历史坑，已简化）

- **现象（旧）：** 预览面板按单文件映射，相对路径 `index.html` 图片全挂
- **现策略（简化）：** **不再生成 `preview.html`**。本地预览一律双击 `index.html`（file://，`images/` 可达）。Agent/面板若只能映射单文件，改为打开篇目录或直接看 `article_body.html` 结构，不必再维护 base64 自包含版
- **验证：** `verify_render_dual.py` 只查 `index.html@file://` 图片是否全部可见

#### 坑2：预览页占位符未替换

- **现象1：** 预览版里 `{img0}`~`{imgN}` 显示为纯文本
- **现象2：** 占位符替换了但图片不显示——只把路径字符串塞进占位符位置，得到一段文本节点
- **✅ 正确做法：** 用 Python 脚本把 `{imgN}` 整体替换为**完整 `<img src="images/xxx.png">` 标签**（见坑24；2026-09-30 起改为相对路径方案）

#### 坑3：ImageGen 中文 100% 乱码

- **现象：** Hunyuan/ImageGen 模型生成的漫画里，中文文字全是乱码方块
- **✅ 解决方案：** 只用豆包AI（Seedream API 或 APP 手动）

#### 坑4：漫画编号与占位符错位

- **现象：** HTML 里 `{img0}` 标为"漫画①"，但 `push_draft.py` 实际 `{img0}`=封面图
- **✅ 正确做法：** 文章正文的漫画从 `{img1}` 开始编号为"漫画①"，`{img0}` 单独作为封面图

---

### 🟠 P1级：严重坑，影响质量

#### 坑5：标题超过64个字符

- **限制：** 微信公众号 API `title` 字段最长 **64个中文字符**
- **现象：** `errcode=45003 "title size out of limit"`
- **✅ 正确做法：** 标题控制在64字以内（含标点）

#### 坑6：Python f-string 中文符号语法错误

- **现象：** f-string 里包含中文引号 `""` 或括号 `（）`，导致 Python 语法错误
- **✅ 正确做法：** 避免在 f-string 里嵌套中文符号，改用 `.format()` 或拼接

#### 坑7：`requests.post(json=...)` 中文被转义为 `\uXXXX`

- **现象：** 推送成功后，公众号后台文章标题/摘要显示乱码
- **❌ 错误写法：**
  ```python
  resp = requests.post(url, json={"articles": [article]}, timeout=30).json()
  ```
- **✅ 正确写法：**
  ```python
  payload = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")
  resp = requests.post(
      url,
      data=payload,
      headers={"Content-Type": "application/json; charset=utf-8"},
      timeout=30
  ).json()
  ```

#### 坑13：云环境IP不在公众号白名单

- **现象：** `requests` 调用微信 API 报错 `40164：invalid ip`
- **✅ 正确做法：** 在公众号后台「设置与开发」→「IP白名单」中添加服务器IP

#### 坑14：`push_draft.py` 参数签名不匹配

- **现象：** `TypeError: create_draft() got an unexpected keyword argument 'author'`
- **原因：** `WeChatPublisher.create_draft()` 方法签名与调用不匹配
- **✅ 正确做法：** 检查 `wechat_publisher.py` 的 `create_draft()` 方法签名，确保参数名一致

#### 坑15：HTML文件含不可见脏字符，微信API吞CSS

- **现象：** 推送成功但样式丢失
- **原因：** HTML 文件含 BOM（`\ufeff`）、零宽字符（`\u200b`）等不可见字符，微信 API 解析时出错
- **✅ 正确做法：** 每次推送前用 `fix_for_wechat.py` 清洗脏字符

#### 坑16：ImageGen 生成图右下角带强制水印（2026-09-30）

- **现象：** 用 WorkBuddy `ImageGen` 出的图，右下角固定有"AI生成 / WORKBUDDY"字样，直接放进公众号很难看
- **原因：** 工具侧强制加的水印，prompt 里写 no watermark 也去不掉
- **✅ 正确做法：** 出图后跑 `process_comics.py`，默认裁掉底部 90px；裁完 1080x656，比例不影响排版

#### 坑17：ImageGen 生成文件名撞车互相覆盖（2026-09-30）

- **现象：** 并行出 5 张图，实际只落盘 4 张
- **原因：** 落盘文件名 = prompt 首个单词 + 时间戳。两张图 prompt 前缀相同（都以 `Traditional Chinese ink wash...` 开头）且落在同一秒 → 后者覆盖前者
- **✅ 正确做法：** 每张图的 prompt **首词必须不同**；出图后 `ls` 一次确认张数，缺了立刻补出

#### 坑18：正文层级关系用文字堆，读者理不清（2026-09-30）

- **现象：** "分四层：第一层是…第二层是…" 纯文字描述结构，读三遍还是记不住
- **✅ 正确做法：** 用 `make_arch_diagram.py` 生成结构图（Pillow 直排中文，不走模型，无乱码）。占位符用 `{img_arch}`（非数字），放在 `images/img_arch.png`
- **注意：** `generate_preview.py` / `push_draft_template.py` 均已支持非数字占位符。

#### 坑19：占位符正则会吃掉分隔下划线（2026-09-30）

- **现象：** `{img_arch}` 被 `re.findall(r"\{img(\w+)\}")` 捕获为 `_arch`，再拼 `img_%s.png` 得到 `img__arch.png`，图片永远找不到
- **✅ 正确做法：** 捕获后统一 `key.lstrip("_")` 归一化，再按 数字/文本 两路拼文件名

#### 坑20：ImageGen 强制水印要去掉，换成个人品牌水印（2026-09-30）

- **现象：** 右下角 "AI生成 / WORKBUDDY" 是工具强制加的，prompt 写 no watermark 无效
- **✅ 正确做法：** 跑 `apply_brand_watermark.py --all`：先裁掉底部 90px，再在右下角绘制「资深架构师 李福春」+ 圆形头像（半透明胶囊底，任何底色都可读）
- **品牌素材固化路径**（跨项目复用，可通过环境变量 `BRAND_PORTRAIT` / `BRAND_HERO` 覆盖）：
  - 头像：`$HOME/.workbuddy/assets/author-lfc-portrait.png`
  - 头图：`$HOME/.workbuddy/assets/author-lfc-hero.png`
  - 水印文案：`资深架构师 李福春`（**仅用于图内水印**）

#### 坑21：Pillow 圆头像合成报 `images do not match`（2026-09-30）

- **现象：** 打水印时头像合成全部失败，日志刷 `[warn] avatar failed: images do not match`，水印只剩文字胶囊没有头像
- **真凶：** `circular_avatar()` 里混用了 `Image.alpha_composite`（要求两图同尺寸）和 `paste(img, pos, mask)`（允许不同尺寸），先 alpha_composite 再 paste 会尺寸冲突
- **✅ 正确做法：** 只走 paste 路线——对头像 `putalpha(mask)` 做圆形遮罩，再 `canvas.paste(av, (2,2), av)`，描边用 `ellipse` 画在画布上
  ```python
  av.putalpha(mask)                      # 圆形遮罩
  ring = Image.new("RGBA", (d+4, d+4), (0,0,0,0))
  ring.paste(av, (2, 2), av)
  ImageDraw.Draw(ring).ellipse((1,1,d+2,d+2), outline=(255,255,255,235), width=2)
  ```

#### 坑22：bash heredoc 写含中文引号的 JSON 会坏掉（2026-09-30）

- **现象：** `cat > spec.json <<'EOF'` 写入含中文引号「」的 JSON，`json.load()` 报 `Invalid control character at: line 15 column 32`
- **真凶：** heredoc 里的中文引号在某些编码组合下被写成真实换行符，JSON 字符串里不允许裸控制字符
- **✅ 正确做法：** **不要用 shell 写 JSON**。改用 Python `json.dump(spec, f, ensure_ascii=False, indent=2)` 生成文件。同理，含中文的配置/映射文件一律用 Write 工具或 Python 写

#### 坑23：批量出图必须用「映射表 + 归位脚本」，不能手工重命名（2026-09-30）

- **背景：** 一个系列 8 篇文章 = 40+ 张 ImageGen 图，文件名是 prompt 首词 + 时间戳，手工对不上
- **✅ 正确做法：**
  1. 每篇目录放 `image_mapping.txt`，格式 `<目标名>|<prompt前缀>`（如 `img0.png|Ink_wash_painting__a_lone_figu`）
  2. 跑 `finalize_images.py --dir <篇目录>`：按前缀 glob 匹配原图 → 缩放至 1080 宽 → 存为 `imgN.png` → 自动裁平台水印 + 打品牌水印
  3. 用**互不相同**的 prompt 首词（如 `Ink_wash_painting__` / `Sumi_e_ink__` / `Brush_and_ink__` / `Minimal_ink_art__` / `Chinese_ink_painting__` 轮换），避免同秒覆盖
- **注意：** `image_mapping.txt` 只写 `<名>|<前缀>` 两列，别在里面留注释行或通配符行，否则脚本会报 `[MISS]`

#### 坑24：预览页图片不显示——只替换了 base64 字符串，没生成 `<img>` 标签（2026-09-30）

- **现象：** `index.html` 有 6.6 MB、内含 6 处 `data:image/png;base64`，但 `grep -c '<img '` 返回 **0**；浏览器里图变成一大段 base64 乱码文本，正文图片位全空
- **真凶（两层，必须同时修）：**
  1. `md2wechat.py` 把占位符包进 `<p>`：`out.append("<p>{%s}</p>" % ph)` —— 占位符**必须单独成行**，否则替换后是一段裸 base64 文本节点
  2. `generate_preview.py` 只做 `html.replace(token, "data:image/png;base64,...")`，**没有生成 `<img>` 标签** —— 必须整体替换成 `<img src="data:..." style="...">`
- **✅ 正确做法：** 见 §9.1。两处同时改：
  ```python
  # md2wechat.py：裸占位符，不要包 <p>
  out.append("{%s}" % pending.pop(kw))

  # generate_preview.py：整体替换为完整 <img>
  tag = '<img src="%s" style="%s">' % (uri, IMG_STYLE)
  html, _ = re.subn(r"<p[^>]*>\s*" + re.escape(token) + r"\s*</p>", tag, html)  # 已包 <p> 的
  html = html.replace(token, tag)                                              # 裸占位符的
  ```
- **自检口径（必做）：** `<img>` 数量 == base64 数量 == 图数；占位符残留 0；`<p...>data:image` 出现次数 0

#### 坑25：批量重建时占位符前缀写重，得到 `{imgimg0}`（2026-09-30）

- **现象：** 9 篇重跑后全部缺图，日志刷 `{imgimg0} <- 占位图（缺图）`
- **真凶：** `LAYOUTS` 里值本身就带 `img` 前缀（`"img0"`），输出时又套了 `{img%s}` → `{imgimg0}`
- **✅ 正确做法：** **先定死 LAYOUTS 的书写约定**：值写带前缀全名（`img0` / `img_arch`），输出一律 `"{%s}" % value`。改完立即全文搜 `\{img` 确认没有双前缀
- **同类隐患：** 篇目录改名后脚本仍按旧名找文件（`初稿.md` → `正文.md`）。脚本必须做**多候选名兼容**：
  ```python
  for cand in ("正文.md", "初稿.md"):
      if os.path.exists(os.path.join(d, cand)): md = os.path.join(d, cand); break
  ```
  规范变更（如目录重构、文件改名）后，**先跑一遍全量重建再交付**，不要只改一份。

#### 坑26：新增篇目忘了加 LAYOUTS 条目，静默产出一张图都没有（2026-09-30）

- **现象：** `01` 篇重跑后 `index.html` 只有 0.01 MB、`<img>` 0 个，无任何报错
- **真凶：** `md2wechat.py` 的 `LAYOUTS` 缺 `01` 键，`layout = []`，`pending` 为空 → 不插任何占位符，`generate_preview.py` 也就无事可做（`[WARN] 未找到任何 {img*}` 容易被日志淹没）
- **✅ 正确做法：**
  - 新增篇目**先补 LAYOUTS 条目**，小节关键字必须与 `正文.md` 的 `## ` 标题能模糊匹配上
  - 加两道断言：`convert()` 返回的 `left`（未匹配关键字数）必须为 0；`generate_preview.py` 在 `<img>` 数为 0 或有残留占位符时打 `[ERR]` 并非零退出

#### 坑27：预览页别内嵌 base64，改相对路径（2026-09-30）

- **现象：** 9 篇 `index.html` 合计 **64 MB**，单篇 6~8 MB。用 `present_files` 打开卡顿；`grep`/`git diff` 直接放弃；文件管理器里一堆巨型 HTML
- **真凶：** 为了「一个文件双击即看」，把图片全量 base64 内嵌。图片本身才 5 MB/篇，内嵌后膨胀到 8 MB（base64 编码 +33%）
- **✅ 正确做法：** **图片走相对路径** `<img src="images/imgN.png">`，`index.html` 降到 **13~22 KB**，总量 **64 MB → 175 KB**
  - 前提：图片必须在 `<篇目录>/images/` 下，与 `index.html` 同级子目录
  - 缺图时**跳过**不生成占位图（灰色占位图也会撑大体积）
- **代价（必须知道）：** 相对路径版**不能直接粘贴进公众号编辑器**，图片不会跟着走。所以：
  - `index.html` 定位 = **本地看版式**（双击就开）
  - 推送仍走 `article_body.html` + `push_draft.py`（图片上传微信素材库，与内嵌无关）
- **自检口径：** `index.html` < 60 KB、`data:image` 出现 0 次、`<img src="images/...">` 数 == 图数、6 个相对引用全部 `os.path.exists` 为真

#### 坑28：章节目录名不要带中文（2026-09-30）

- **现象：** `01_总诀式` / `02_破剑式` 这种中文目录名，在跨平台复制、URL 引用、命令行传参时都要额外转义；脚本里写死中文目录名，改名就断链
- **✅ 正确做法：** **篇目录只用两位序号** `00/ 01/ 02/ … 09/`
  - 标题信息写进 `metadata.json` 的 `title` 字段，不要写进目录名
  - 系列规划目录固定 `00/`；共享资源 `_series/` 用下划线开头自然分开排序
- **改名时的连带项（漏一个就断链）：**
  1. `_series/build/` 下的同名目录
  2. `metadata.json` 的 `prev` / `next` 字段
  3. `series-plan.md` 里引用的目录路径
  4. 脚本 `LAYOUTS` 字典的 key（`md2wechat.py` 用篇名当 key，改名后要同步）

#### 坑29：坑28 的连带项——目录改名后 LAYOUTS key 断链（2026-09-30）

- **现象：** 篇目录 `01_总诀式` → `01` 后，`md2wechat.py` 的 `LAYOUTS["01_总诀式"]` 匹配不上，重跑 `article_body.html` 会退化成 0 个占位符
- **✅ 正确做法：** 改名脚本里同步 `LAYOUTS` 的 key；或在 `convert()` 里做归一化查找（取 key 的两位数字前缀匹配）
- **通用原则：** 任何「用目录名当字典 key / 路径片段」的地方，都在改名清单里列一项

#### 坑31：GFM 表格被当普通段落输出，正文里冒出一堆竖线（2026-09-30）

- **现象：** 正文写了 markdown 表格，`md2wechat.py` 不认识，逐行输出成 `<p>| 式 | 标题 | ... |</p>`，公众号里显示为一行行竖线文本
- **✅ 正确做法：** `md2wechat.py` 已内置 GFM 表格支持。检测连续的 `|...|` 行成块，走 `render_table()` 渲染为微信安全的 `<section>` + `<span style="display:inline-block;width:N%">` 单元格；表头行加 `#f5f2ec` 底色 + 加粗
- **关键实现：** `split_row()` 支持首尾竖线可省略；`is_sep_row()` 只认 `|---|` 这种带竖线的分隔行（**不要把 `---` 误判为表格分隔行**，那是 hr）
- **通用原则：** 只要允许用户在正文里写 markdown，就要在转换前 grep 一遍 `^<p[^>]*>\|`，非 0 即说明有表格未被渲染

#### 坑32：写正文时手写了 `{img_arch}` 占位符，与 LAYOUTS 自动插入的撞车（2026-09-30）

- **现象：** 输出占位符列表变成 `['0','1','2','3','_arch','_arch','4']`，同一张图渲染两次，`preview.html` 体积无故变大
- **根因：** LAYOUTS 已负责按小节标题插入占位符，作者又在正文里手写了一个
- **✅ 正确做法：** **正文 md 里永远不写 `{imgN}` 占位符**，全部交给 `LAYOUTS` 配置。交付前查一遍：`grep -c "{img" 正文.md` 必须为 **0**
- **连带修复：** 同一小节标题若同时命中多个 LAYOUTS 关键字，`for kw in pending` 循环里要 `break`，否则插多张图

#### 坑33：系列级素材放 00 篇目录，被 verify_delivery 当成"多余文件"（2026-09-30）

- **现象：** `series-plan.md`、`style-guide.md`、`series_overview.png` 放在 `00/` 下，自检报「多余文件」
- **✅ 正确做法：** `verify_delivery.py` 里加 `ALLOW_00` 白名单，仅在 `name == "00"` 时并入 `ALLOW`
- **通用原则：** 目录整洁检查要有"例外目录"概念，别为了过检查把系列级素材搬来搬去

#### 坑34：目录篇（第 0 篇）的定性不要写成"操作指南"（2026-09-30）

- **现象：** 初稿把全文写成"四类人 + 九篇清单 + 三条阅读建议"，信息齐全但没有灵魂，用户反馈要"提高维度到心灵成长"
- **✅ 正确做法：** 目录篇必须有**一段升华段**，把九式的招式（技术动作）重新解释为心性修炼。结构建议：
  1. 业务缘起讲透（为什么选这件事，不是"我要做数字人"，是"我为什么要开这家公司"）
  2. 目标读者 + 自测三问
  3. 双骨架（剑式 = 该破什么 / 习惯 = 用什么判断）
  4. 九式一览表（链接占位）+ 递进关系（分 4 段）
  5. **升华段：把七个习惯逐条翻译成"七关"**，点明"钱是一关一关挣出来的，人是一关一关长出来的"
  6. 原创诗 + 阅读路径
- **通用原则：** 系列总纲篇的价值不在"列清单"，在"给整条线一个精神内核"。定性定好了，后面每篇都会跟着稳

#### 坑35：系列内互链必须用「真实发布标题」，不能自己编号（2026-09-30）

- **现象：** 为目录篇写导航表时，按内容自拟了一套大白话标题（如"破剑式：想了五十六天，我删掉了六十三个收藏"），与各篇**实际发布标题**（`独孤九剑第2式破剑式—积极主动`）不一致。读者按导航去找，找不到
- **✅ 正确做法：**
  1. **先向用户索取 9 篇的真实标题**（或直接读已发布链接的标题），再写导航
  2. 命名规律要**机械可推**：`独孤九剑第N式<式名>—<习惯/心法>`
  3. 导航表用**真实标题做锚文本**，大白话钩子另起一列或另起一段（"一句话看懂每一式在讲什么"），两层分开，不要混为一谈
  4. 同步回填各篇的 `正文.md` 首行 / `metadata.json` / `publish_config.json`
- **通用原则：** 系列文里凡是引用其他篇的地方，一律以**已发布的真实标题**为准。自拟标题只作内部草稿，交付前必须替换

#### 坑36：系列互链要「头尾各放一次」，且三处都放（2026-09-30）

- **现象：** 目录篇只在中间放一次链接清单。读者点进来读到底，想跳到下一篇还得往上翻
- **✅ 正确做法：** 链接放 **3 处**：
  1. **头** —— 九式一览表（表格内锚文本，阅读前就能选）
  2. **中** —— 递进关系段落后，紧跟"九式直达链接"清单
  3. **尾** —— 结尾"建议收藏这一篇"再放一次
- **锚文本格式：** 用 markdown `[标题](url)`，`md2wechat.py` 的 `inline_md()` 会渲染为 `<a href style="color:#576b95">`。**不要用裸 URL**（长链接破坏排版）
- **微信外链限制：** `mp.weixin.qq.com` 是自家域名，正文 `<a>` **可点击**；站外域名只有白名单能跳，其余渲染为普通文字（仍可看，不影响阅读）
- **交付前检查：** `grep -c '<a href' index.html` 应为**三处链接数之和**（本例 9+9+9=27）

#### 坑37：目录篇导航图——用「架构图精选」而非「封面拼图」（2026-09-30）

- **结论（已经过一轮返工验证）：** 目录篇的九式导航位，**放架构图比放封面更有说服力**。封面只说明"有哪些篇"，架构图直接说明"这九式在解什么结构"
- **❌ 曾走过的弯路：** 先做 3×3 封面拼图（`make_nav_00.py` → `img_nav.png`）。信息量低，读者看不出各篇的方法论，已弃用删除
- **❌ 第二个弯路：** 把 9 张架构图全拼进一张（2 列 × 5 行，1500×4532）。后果是每图被压到 681px、总高 4532px，**微信端整体缩放后文字完全糊掉**
- **✅ 正确做法：** **精选 4 张**架构图，**单列**排布（`make_archs_00.py`）
  - 选图原则：覆盖**不同结构类型**，避免同质化。本例取
    - `01` 四层能力分工 → 回答"谁干什么"
    - `04` MVP 优先级四象限 → 回答"先干什么"
    - `07` 能力编排五层分工 → 回答"怎么串起来"
    - `09` OPC 经营闭环 → 回答"怎么转起来"
  - 排版：画布宽 **1200**，卡内图宽 `IMG_W = 1200-80-32 = 1088`，等比缩放**绝不拉伸**（各篇架构图宽高比在 0.76~1.24 之间波动）
  - 每卡顶部 `BAR_H=78` 标签条：式号徽标 + 式名 + 「· 短定位」+ 一句说明
- **格式与体积：**
  - 输出 **JPG q88**（`subsampling=1`），而非 PNG。本例 1200×5435：PNG 1.39 MB → JPG 0.74 MB
  - 占位符 `{img_archs}` → 需 `candidate_paths()` 支持非数字分支的 `.jpg` 回退（原先只找 `.png`，**已补**）
  - base64 预览体积：`BASE64_MAXW=750` 下该图占约 **417 KB**，`preview.html` 总计 944 KB。**高瘦长图是 preview 体积主因，可接受但别再叠更多长图**
- **脚本：** `make_archs_00.py`（Pillow 中文直排，零积分成本）
  - 用法：`python make_archs_00.py --series-dir <系列目录> --out-dir <系列>/00`
  - 选图改 `SELECTED` 数组即可；字体跨平台自动查找（Windows/macOS/Linux）
  - 脚本**自带 PNG→JPG q88 转换并删除 PNG**，不要手动补这一步

---

---

### 🟡 P2级：影响体验

#### 坑10：根目录文件杂乱

- **现象：** 所有文章的文件都放在根目录，难以管理
- **✅ 正确做法：** 每篇文章独立目录 `articles/010_xxx/`，包含 `初稿.md`、`article_body.html`、`push_draft.py`、`comics/` 等

#### 坑11：分隔线 `· · ·` 用户不喜欢

- **现象：** 用户反馈"这条线太花哨"
- **✅ 正确做法：** 删除分隔线，用段落间距和背景色区分内容块

#### 坑12：开篇太犀利

- **现象：** 文章开篇用"我必须告诉你一个事实"等过于犀利的语言
- **✅ 正确做法：** 开篇直接说"我们怎么干"，不用制造焦虑

---

## 工具与资源

### 脚本（`scripts/`）—— 2026-09-30 已补齐

| 脚本 | 用途 |
|------|------|
| `generate_cover.py` | 生成封面（playwright 截图 HTML 模板，失败自动 Pillow 兜底）。用法：`python generate_cover.py "标题" "副标题" --tag "AI转型"` |
| `generate_preview.py` | **`article_body.html` → `index.html`（相对路径）**。用法：`python generate_preview.py --dir <篇目录>`。**必须把占位符整体换成完整 `<img>` 标签**。不生成 `preview.html` |
| `verify_render_dual.py` | **渲染级验证**：file:// 打开 `index.html`，确认图片全部可见 |
| `fix_for_wechat.py` | 微信兼容 HTML 自动修复 + 占位符连续性检查 |
| `process_comics.py` | ImageGen 出图后处理：裁右下角水印 + 归位命名 `imgN.png` |
| `apply_brand_watermark.py` | 裁掉 ImageGen 强制水印，改打个人品牌水印（资深架构师 李福春 + 头像）。用法：`python apply_brand_watermark.py --all` |
| `make_arch_diagram.py` | 生成「四层能力分工」结构图（Pillow 直排中文，零乱码）→ `images/img_arch.png`。按需改 `specs` 列表即可复用 |
| `finalize_images.py` | **系列批量出图必备**。按 `image_mapping.txt` 把 ImageGen 原图归位为 `imgN.png`，自动缩至 1080 宽 + 裁平台水印 + 打品牌水印。用法：`python finalize_images.py --dir <篇目录>` |
| `make_diagram.py` | **通用结构图生成器**（JSON spec 驱动）。多层/多分组结构图一把梭，中文 Pillow 直排。用法：`python make_diagram.py --spec arch_spec.json --out images/img_arch.png` |
| `md2wechat.py` | **正文.md → 微信安全 HTML**。①`img0` 固定插在**诗引之后、正文首节标题之前**（篇首图，与诗引匹配）；②其余占位符按内置 `LAYOUTS`（key = **两位编号**，如 `"02"`）插在小节标题后（**裸占位符，不包 `<p>`**）；③**支持 GFM 表格**（渲染为 `<section>`+`inline-block` 单元格）；④**文末不输出署名行**。用法：`python md2wechat.py --key 02 --dir <篇目录>` |
| `make_arch_00.py` | **系列总纲图生成器**（目录篇专用）。九式 × 七习惯 × 三层依赖关系图，中文 Pillow 直排。改 `STAGES`/`SWORDS`/`BREAKS`/`EXEC` 四个数组即可复用。用法：`python make_arch_00.py --out <系列>/00/images/img_arch.png` |
| `make_archs_00.py` | **架构图精选拼图**（目录篇「九式一览」位专用）。从各章取 `img_arch.png`，按 `SELECTED` 数组**精选 4 张**（覆盖分工/取舍/编排/闭环四类结构），**单列**排布（画布宽 1200，等比缩放不拉伸），每卡带式号徽标 + 式名 + 短定位标签条（`BAR_H=78`）。**自动转 JPG q88 并删 PNG**（体积减半）。用法：`python make_archs_00.py --series-dir <系列目录> --out-dir <系列>/00`。详见坑37 |
| `make_cover.py` | 生成封面（playwright 截 HTML 模板，失败自动 Pillow 兜底）。用法：`python make_cover.py --dir <篇目录> --title "独孤九剑·破剑式" --sub "别等风来，先下水" --tag "AI转型"` |
| `wechat_publisher.py` | 微信 API 封装。凭据从 `~/.workbuddy/wechat_config.json` 读。含草稿 `create_draft` 与非群发发表 `freepublish_*`（账号需有 freepublish 权限，否则 48001） |
| `push_draft_template.py` | `push_draft.py` 模板。复制到文章目录，只改 `IMAGE_FILES`。**推送时必须得到完整 `<img src=URL>`**；裸 `{imgN}` 会自动补成 `<img>`，禁止只把 URL 文本塞进正文（否则草稿里显示成一串链接） |

**依赖**（装在 managed venv：`~/.workbuddy/binaries/python/envs/default`）：
```bash
<envs/default>/Scripts/python.exe -m pip install requests playwright
<envs/default>/Scripts/python.exe -m playwright install chromium
```

**凭据文件 `~/.workbuddy/wechat_config.json`：**
```json
{"appid":"...", "appsecret":"...", "author":"公众号名"}
```
从 `https://mp.weixin.qq.com/` → 设置与开发 → 基本配置 获取。调用方机器公网 IP 必须加入 IP 白名单，否则报 `40164 invalid ip`。

### 参考文档（`references/`）

| 文件 | 用途 |
|------|------|
| `pitfalls.md` | 完整踩坑清单（P0/P1/P2级） |
| `wechat_html_rules.md` | 微信兼容HTML规则详解 |

### 模板与资源（`assets/`）

| 文件 | 用途 |
|------|------|
| `html_template.html` | 微信安全HTML模板（第七篇验证版） |
| `cover_template_1.html` | 封面模板（900×500 深蓝+橙，`generate_cover.py` 使用） |

### 品牌素材（用户级，跨项目复用）

固化路径：`$HOME/.workbuddy/assets/`（Windows 即 `C:/Users/<用户名>/.workbuddy/assets/`）。

| 素材 | 路径 | 用途 |
|------|------|------|
| 头像 | `~/.workbuddy/assets/author-lfc-portrait.png` | 图片水印圆形头像 |
| 头图 | `~/.workbuddy/assets/author-lfc-hero.png` | 文章头图 / 海报 |
| 水印文案 | `资深架构师 李福春` | 所有生成图右下角 |
| ~~文末署名~~ | 已移除 | **用户明确要求删掉文末「李福春 · 资深架构师」**，不要在正文末尾加署名行 |

**注意：** 不再使用「架构师手记」「点击上方蓝字关注」「原创 · xxx」、话题标签 `#xxx` 段落，**以及文末署名行**——用户已明确要求去掉。图内水印保留，正文末尾不署名。

---

## 编码问题修复（appendix）

### Windows 终端乱码修复

在 `if __name__ == "__main__":` 块中添加：
```python
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

### 公众号 AppID 与 AppSecret

在 `wechat_publisher.py` 中配置你自己的 AppID 和 AppSecret：

```python
APPID = "你的公众号AppID"
APPSECRET = "你的公众号AppSecret"
AUTHOR = "你的公众号名称"  # 草稿作者署名
```

注册路径：登录 https://mp.weixin.qq.com/ → 设置与开发 → 基本配置，获取 AppID 和 AppSecret。

---

## 标准文章目录结构（每篇文章必须照此）

```
articles/<系列名>/<编号>/         # 例：articles/OPC时代的独孤九剑/02/
  index.html                 # ★ 本地预览：图片走相对路径，13~22 KB，双击即看
  正文.md                     # 纯文本终稿
  article_body.html          # 微信安全 HTML，{img0}~{imgN} 占位，纯内联 style
  metadata.json              # 本篇元信息（系列连贯性的真相源）
  publish_config.json        # 文章配置（标题/摘要/封面参数）
  images/                    # 全部配图（已打品牌水印）
    cover_final.png          # 封面（make_cover.py 出，900×500px）
    img0.png                 # {img0} — 封面（另作 thumb 备选）
    img1.png                 # {img1} — 正文图①
    img2.png                 # {img2} — 正文图②
    img3.png                 # {img3} — 正文图③
    img_arch.png             # {img_arch} — 结构图
    img4.png                 # {img4} — 结尾图

_series/
  templates/                 # 全部 *.py 脚本（不放进篇目录）
    md2wechat.py             # 正文.md -> article_body.html
    generate_preview.py      # article_body.html -> index.html
    finalize_images.py       # ImageGen 原图 -> imgN.png（+水印）
    make_diagram.py          # 结构图
    make_cover.py            # 封面
    wechat_publisher.py      # 微信 API 封装
    push_draft.py            # 推送脚本
    fix_for_wechat.py        # HTML 修复
  build/<篇名>/               # arch_spec.json / image_mapping.txt 等中间产物
```

**六个保留项就是上限。** 脚本、spec、映射表一律收进 `_series/`；篇目录堆工具文件会被用户退回。

**注：** 所有脚本统一从 `_series/templates/` 调用，**用 `--dir <篇目录>` 显式指定路径**，不要依赖脚本自身所在目录推断（脚本已不在篇目录里了）。

**铁律：** 每篇新文章产出的**唯一可见物**是 `index.html`（看图看版式）+ `images/`（出图）。其余都是给推送脚本吃的中间件，不该让用户在篇目录里翻。

---

## 【必读】每个步骤的最佳路径（13篇文章复盘）

经过001~013共13篇文章的实战，以下是每个步骤的唯一正确做法。**别试别的，这些是踩出来的路。**

| 步骤 | 踩坑次数 | ❌ 走过的弯路 | ✅ 唯一正确路径 |
|------|---------|-------------|--------------|
| S5 封面生成 | 2次 | Pillow纯色→playwright | **`generate_cover.py` 截图HTML模板**。等待2秒确保字体渲染 |
| S6 漫画生成 | 5次 | ImageGen(乱码)→豆包APP(手工)→4.0→4.5→列表乱码 | **Seedream 5.0 API + generate_comics.py**。prompt只写场景+≤8字短标题，绝不在图里放列表/序号/多条规则 |
| S6 HTML排版 | 7+次重推 | 每篇从零写→样式丢失→排查→重推循环 | **从已验证模板复制骨架**，不自己造标签。写完跑 `fix_for_wechat.py` |
| S8 本地预览 | 5种方案 | file://→HTTP→base64→双产物 | **只出 `index.html`（相对路径）**，本地双击看；跑 `verify_render_dual.py` 做 file:// 渲染验证。不再生成 `preview.html` |
| S9 推送草稿 | 8+次 | 缺APPID/缺requests/白名单/编码/**从零写push_draft.py** | **push_draft.py从上一篇复制，只改TITLE/DIGEST/cover配置**。wechat_publisher.py从上一篇复制，不重新导入 |
| 目录结构 | 每篇重来 | 文件散落根目录/tmp_comics、**脚本堆在篇目录** | **标准模板 + `_series/` 收脚本**。篇目录只留 7 项；规范变更后**先全量重建再交付** |

### 最浪费时间的三大坑

| 排名 | 环节 | 浪费次数 | 根因 |
|------|------|---------|------|
| 🥇 | **微信排版样式丢失** | 7+ 次重推 | 先推再排查，没有预检机制 |
| 🥈 | **漫画生成方案切换** | 5 次 | ImageGen→豆包APP→Seedream 4.0→4.5→列表乱码 |
| 🥉 | **预览方案反复** | 4 种 | file:// → HTTP → base64 → 相对路径（最终） |

### 核心原则

1. **从上一篇文章复制，别从零写。** 013 是当前最成熟模板。包括 push_draft.py、generate_cover.py 也从上一篇复制。
2. **先预览、再推送。** 预览里样式正常才能推。
3. **推送完马上复盘。** 记录啥对了啥错了，好的固化为规则，坏的加进"永远不要做"。
4. **出问题先跑 fix_for_wechat.py。** 排查顺序：脏字符→标签→flex，别倒过来。
5. **漫画文字不超过8个字。** 列表、序号、多条规则留在正文。

---

## 永远不要做的事

- ❌ 不要用ImageGen生成带中文的漫画（100%乱码）
- ❌ 不要用Seedream画封面（用HTML模板+generate_cover.py自动生成）
- ❌ 不要手动截图封面（用playwright自动截图HTML模板）
- ❌ 不要直接发布（必须手动确认后发布）
- ❌ 不要在文章里暴露个人身份信息（国企环境）
- ❌ 不要跳过预览直接推草稿箱
- ❌ 不要再生成 `preview.html`（base64 自包含已移除；本地预览只用 `index.html`）
- ❌ 不要在推草稿时把 `{imgN}` 只替换成裸 URL 字符串（正文会显示成 `http://mmbiz.qpic.cn/...` 链接文本；必须是 `<img src="URL">`）
- ❌ `article_body.html` 里优先写 `<img src="{img0}" style="...">`，不要只写一行裸 `{img0}`
- ❌ 不要每篇文章换目录结构（照上面的标准来，保持一致）
- ❌ 不要从零写 article_body.html（从011/012复制已验证模板）
- ❌ 不要在漫画里放列表/序号/多条规则（纯场景+短标题）
- ❌ 不要先推再排查排版问题（预览通过才推送）
- ❌ 不要从零写 push_draft.py（从上一篇复制，只改 TITLE/DIGEST/cover配置）
- ❌ 不要跳过推送复盘（推完就拉倒=下次重蹈覆辙）
- ❌ 不要在生成图里放任何中文/诗句/序号（100% 乱码，文字一律走 HTML 排版）
- ❌ 不要让多张图的 prompt 用同一个开头词（文件名撞车会互相覆盖，2026-09-30 丢过图）
- ❌ 不要直接拿 ImageGen 原图进公众号（右下角有强制水印，先跑 process_comics.py 裁掉）
- ❌ 不要把 AppID/AppSecret 写进 push_draft.py（统一从 `~/.workbuddy/wechat_config.json` 读）

---
## 每篇复盘模板（推送后必填）

推送完马上复盘，存入当天工作日志。坚持复盘才能越用越好用。

```markdown
## 第N篇推送复盘

| 环节 | 对/错 | 说明 |
|------|-------|------|
| 目录结构 | ✅/❌ | |
| 正文写作 | ✅/❌ | |
| 去AI味 | ✅/❌ | |
| 漫画生成 | ✅/❌ | 成功N张/失败N张 |
| 预览 | ✅/❌ | |
| 推送 | ✅/❌ | |
| 新增踩坑 | — | 本次新踩的坑 |

### 改进项
- [ ] 需要修复的流程问题
```

### 013 复盘示例

| 环节 | 对/错 | 说明 |
|------|-------|------|
| 目录结构 | ✅ | 照搬012，一次就位 |
| 正文写作 | ✅ | 一次过，确认后直接动笔 |
| 去AI味 | ✅ | 精准3处修改，不过度 |
| 漫画生成 | ✅ | 6张全部成功，蓝白科技风 |
| 预览 | ✅ | index.html 13~22KB 相对路径（本地双击） |
| **推送** | ❌→✅ | 第1次失败（push_draft.py从零写，缺APPID/APPSECRET），照012重写后成功 |
| 新增踩坑 | push_draft.py 也绝不能从零写 | 从上一篇复制 `wechat_publisher.py`（凭据用 `load_wechat_config()` 从 `~/.workbuddy/wechat_config.json` 读，不要 `import APPID`，publisher 不导出这些）；`push_draft.py` 的 `IMAGE_FILES` 按本篇实际文件名填（封面=`covers/cover_final.png` 另作 thumb，正文=`comics/img1.png`~`img5.png`），`create_draft()` 传 `thumb_path=封面图` |

**改进项：**
- [x] 已加入"永远不要做的事"清单
- [x] 已加入 S9 最佳路径说明
