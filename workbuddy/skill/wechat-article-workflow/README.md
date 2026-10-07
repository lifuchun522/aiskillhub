# 公众号文章工作流（wechat-article-workflow）

一个把「写公众号文章」这件事完整跑通的 Agent Skill：从选题讨论一路走到**推送草稿箱**，中间每一步都有脚本和踩坑清单兜底。

它解决的不是「怎么写出好文章」——那是人的事。它解决的是**流程里那些反复踩、反复忘的工程问题**：微信不收的 HTML 怎么改、图片占位符怎么塞、去 AI 味怎么去、系列文怎么保证不断线、草稿箱怎么自动推。

> 这是一份**独立的 Agent Skill**，遵循通用的 `SKILL.md` 技能规范，可在 WorkBuddy / Claude Code / Codex / Cursor 等支持 Agent Skills 的工具中安装使用。

---

## 它做什么

工作流覆盖 **10 个步骤**，每步都有明确的输入输出：

1. **素材讨论** —— 聊透再动笔，不聊透不写
2. **拟标题** —— 一次给 3~5 个备选，含爆款钩子拆解
3. **写初稿** —— 结构先定，故事性优先
4. **去 AI 味** —— 消掉「首先/其次/总而言之」这类腔调
5. **生成封面** —— 自动套用 HTML 模板，出 1800×1000 成品
6. **生成配图** —— 两条路线：WorkBuddy ImageGen 自动 / 豆包手动
7. **微信安全排版** —— Markdown → 纯内联 `<section>`，规避微信编辑器吃样式
8. **自动修复** —— `fix_for_wechat.py` 兜住脏字符与非法标签
9. **本地预览** —— 轻量 `index.html`（相对路径，本地双击）
10. **推送草稿箱** —— 微信 API 直推，带图片上传与草稿创建

**系列文章**另有专门规范：`series-plan.md` 前置、七条连贯性铁律、目录篇（第 0 篇）的特殊写法与互链要求。

---

## 核心设计

**微信兼容 HTML 是这块最硬的骨头。** 微信公众号编辑器会吃掉 `<div>`、`<h1>`~`<h3>`、`<style>`、`class`、`display:flex`。这个技能的 `md2wechat.py` 把所有内容压成**纯内联 `style=""` + `<section>`**，并且支持三种自研语法：

- **GFM 表格** —— 渲染为 `<section>` + `display:inline-block` 单元格（微信里表格必换行，所以有专门的列宽策略）
- **`> [!card]` 卡片块** —— 标题行 + 描述行，渲染为左边框强调卡片，比表格更适合手机
- **Markdown 链接** —— 渲染为 `<a href style="color:#576b95">`，站内链接可点

**图片占位符机制**：正文 Markdown 里**永不手写** `{img0}` 这类占位符，而是由 `LAYOUTS` 配置按小节标题自动插入。这条规则来自一次真实事故——手写和自动插入撞车，同一位置出了两张图。

**系列级复用**：目录篇的导航图不要为它单独跑一遍绘图模型。直接取各篇已有的架构图精选拼合，零生成成本，且天然视觉统一。

---

## 目录结构

```
wechat-article-workflow/
├── SKILL.md                      # 技能入口：完整 10 步 SOP + 踩坑清单 + 脚本手册
├── README.md                     # 本文件（安装与使用）
├── references/
│   └── api_reference.md          # 微信 API 参考（draft/add、media/uploadimg）
├── assets/
│   ├── html_template.html        # 正文 HTML 模板
│   └── cover_template_1.html     # 封面 HTML 模板
└── scripts/                      # 全部可执行脚本（15 个）
    ├── md2wechat.py              # 正文.md → 微信安全 HTML（核心）
    ├── generate_preview.py       # 本地预览 index.html（相对路径）
    ├── verify_delivery.py        # 交付前全量自检
    ├── make_cover.py             # 封面生成
    ├── make_diagram.py           # 通用结构图（JSON spec 驱动）
    ├── make_arch_00.py           # 系列总纲图（目录篇专用）
    ├── make_archs_00.py          # 架构图精选拼图（目录篇专用）
    ├── apply_brand_watermark.py  # 品牌水印重绘
    ├── fix_for_wechat.py         # 微信 HTML 自动修复
    ├── finalize_images.py        # 图片终处理
    ├── process_comics.py         # 漫画图批处理
    ├── verify_render_dual.py     # index.html file:// 渲染核验
    ├── wechat_publisher.py       # 微信 API 封装
    ├── push_draft_template.py    # 推送脚本模板
    └── generate_cover.py         # 封面生成（playwright 版）
```

---

## 安装

技能包就是一个含 `SKILL.md` 的目录，把它放进你所用的工具的 **skills 目录**即可。

### WorkBuddy

```bash
# 用户级（全项目可用）
cp -r wechat-article-workflow ~/.workbuddy/skills/

# 或项目级（随仓库共享）
mkdir -p .workbuddy/skills && cp -r wechat-article-workflow .workbuddy/skills/
```

### Claude Code

```bash
# 用户级
cp -r wechat-article-workflow ~/.claude/skills/

# 或项目级
mkdir -p .claude/skills && cp -r wechat-article-workflow .claude/skills/
```

### Cursor

```bash
# 项目级（随仓库共享）
mkdir -p .cursor/skills && cp -r wechat-article-workflow .cursor/skills/

# 或用户级（Windows）
Copy-Item -Recurse wechat-article-workflow "$env:USERPROFILE\.cursor\skills\"
```

Cursor 若不识别 Skills 目录，可把 `SKILL.md` 内容作为项目规则（`.cursor/rules/`）引用，保留 `scripts/` 与 `assets/` 的相对路径即可。

### Codex

把 `wechat-article-workflow/` 放入该工具配置的 skills 目录。Codex 各版本目录可能不同，以其官方 Skills 文档为准（常见为用户级 `~/.codex/` 下的 skills 目录，或项目级 settings 指定的目录）。`SKILL.md` 采用标准 frontmatter（`name` + `description`），无需改动即可被识别。

若工具没有 Skills 机制，直接把 `SKILL.md` 作为系统提示 / 项目规则（如 `AGENTS.md`、`CLAUDE.md`）引用。

---

## 依赖

脚本依赖 Python 3.9+，主要包：

```bash
pip install requests pillow
```

`make_cover.py` 走 HTML 模板截图路线需要 playwright（可选，失败会自动降级到 Pillow 兜底）：

```bash
pip install playwright && playwright install chromium
```

**微信凭据**：推送草稿箱需要 `appid` 与 `appsecret`，从公众号后台 `设置与开发 → 基本配置` 获取，写入 `~/.workbuddy/wechat_config.json`。同页需把本机公网 IP 加入白名单，否则接口返回 40164。

---

## 使用

安装后用自然语言提需求即可，技能会被自动识别：

- 「帮我写一篇公众号文章，主题是……」
- 「这篇推文排一下版，推到草稿箱」
- 「我要写一个系列，先出系列规划」
- 「正文表格太乱了，改成卡片」

生成流程（技能内部按序执行）：

1. 聊素材 → 定选题与角度
2. 拟 3~5 个标题备选
3. 写初稿（结构先行，故事性优先）
4. 去 AI 味
5. 生成封面 + 配图
6. `md2wechat.py` 转微信安全 HTML
7. `fix_for_wechat.py` 修复 → `generate_preview.py` 出双预览
8. 本地确认排版 → `push_draft.py` 推草稿箱
9. `verify_delivery.py` 全量自检

---

## 踩坑清单

`SKILL.md` 里维护了一份持续累积的踩坑清单，按 **P0（致命，踩了重来）/ P1（严重，影响质量）/ P2（影响体验）** 三级分类，目前 37 条。这是这个技能最有价值的部分——每条都对应一次真实的返工。

几条典型的：

- **表格在微信里必换行** —— 列多、字长的表格在手机上会碎成一片，改用卡片
- **正文绝不手写图片占位符** —— 会与自动插入撞车，同位置出两张图
- **系列互链必须用已发布的真实标题** —— 自拟标题在发布后会对不上
- **导航图不要为它单独跑绘图模型** —— 取现有素材拼合，零成本且视觉统一
- **不再生成 preview.html** —— 本地预览只用相对路径 `index.html`

---

## 作者

**李福春 · 资深架构师**

个人信条：「把复杂系统，设计成简单可依赖的产品。」

- 邮箱：hello@carter.li
- GitHub：[@lifuchun522](https://github.com/lifuchun522)
