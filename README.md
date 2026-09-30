# aiskillhub

**AI Agent Skills 集合** —— 把日常工作中反复踩坑的流程，沉淀成可安装、可复用的技能包。

每个技能都遵循通用的 `SKILL.md` 规范，可在 WorkBuddy、Claude Code、Codex、Cursor 等支持 Agent Skills 的工具中安装使用。

作者：[李福春 · 资深架构师](https://github.com/lifuchun522)　·　信条：「把复杂系统，设计成简单可依赖的产品。」

---

## 目录组织

仓库按**宿主工具**分目录，每个工具下按**技能类型**再分一层：

```
aiskillhub/
└── workbuddy/                    # 面向 WorkBuddy 的技能
    └── skill/                    # 通用 Skill（标准 SKILL.md 规范）
        └── wechat-article-workflow/
```

之所以先按工具分，是因为不同平台的技能虽然都叫 `SKILL.md`，但在**安装路径、元数据字段、脚本依赖**上各有各的约定。按工具分目录，安装时直接整目录拷贝，不用挑文件。

---

## 技能列表

### 公众号文章工作流

把「写公众号文章」这件事完整跑通的技能：从选题讨论一路走到推送草稿箱，十个步骤每一步都有脚本兜底。

它解决的不是「怎么写出好文章」——那是人的事。它解决的是流程里那些**反复踩、反复忘的工程问题**：微信编辑器吃掉的 HTML 怎么救回来、图片占位符怎么塞才不撞车、去 AI 味怎么去、系列文怎么保证不断线、草稿箱怎么自动推。

最有价值的部分是那份持续累积的**踩坑清单**（P0/P1/P2 三级，目前 37 条），每条都对应一次真实的返工。

- 技能目录：[`workbuddy/skill/wechat-article-workflow/`](./workbuddy/skill/wechat-article-workflow/)
- 使用说明：[`workbuddy/skill/wechat-article-workflow/README.md`](./workbuddy/skill/wechat-article-workflow/README.md)
- 技能入口：[`workbuddy/skill/wechat-article-workflow/SKILL.md`](./workbuddy/skill/wechat-article-workflow/SKILL.md)

**它包含什么**：完整的 10 步 SOP、微信兼容 HTML 规则（纯内联 `<section>` 方案）、自研的三种 Markdown 扩展语法（GFM 表格 / `> [!card]` 卡片 / 可点击链接）、双预览产物机制、系列文章连贯性七条铁律，以及 15 个可直接调用的 Python 脚本。

---

## 如何安装

每个技能目录都是一份自包含的技能包，**整目录拷贝**到你所用工具的 skills 目录即可。具体路径各工具不同，详见各技能自己的 README。

通用思路是：用户级放 `~/.<工具名>/skills/`（全项目可用），项目级放 `<项目>/.<工具名>/skills/`（随仓库共享，团队协作时更合适）。

安装后不需要额外配置。用自然语言提需求，技能会被自动识别。

---

## 一些约定

**技能必须有 `SKILL.md`**，且 frontmatter 至少含 `name` 与 `description`——`description` 写得好不好，直接决定技能能不能在正确的时机被唤起。写的时候要包含**触发句式**（用户会怎么说），而不只是功能罗列。

**踩坑清单比亚马逊最佳实践更有用。** 一个技能里最该持续更新的，不是「正确做法」那一节，而是「曾经错在哪」那一节。前者是常识，后者是经验。

**脚本与技能同目录。** 脚本放在技能的 `scripts/` 下，通过相对路径调用，避免散落到用户环境的各处。

---

## 授权

本仓库技能可自由用于个人与商业项目。转载或二次分发请保留作者署名。

---

## 联系

- 邮箱：hello@carter.li
- GitHub：[@lifuchun522](https://github.com/lifuchun522)
