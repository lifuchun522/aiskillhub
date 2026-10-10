# zaobao（WorkBuddy 版 v6.2）｜架构师早报三问与同盟讨论

仓库路径：[`workbuddy/skill/zaobao/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/zaobao)

完整使用说明：[`README.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/README.md)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/SKILL.md)

GPT 版（v6.1，Image 2.5 出图）：[`gpt/skill/zaobao/`](https://github.com/lifuchun522/aiskillhub/tree/main/gpt/skill/zaobao) · [Wiki 摘要](zaobao)

## 一句话

输入【科技热点】【架构文章推荐】【今日一言】三栏原文，闭环产出芒格三问、同盟讨论、微信 HTML、手绘白板图，最终只交付一个 `article-YYYYMMDDHHMM.zip`。

## 与 GPT 版（v6.1）的差异

同一个技能的两份宿主适配。WorkBuddy 里没有 GPT 上的 Image 2.5，所以本版把出图统一换成 WorkBuddy 可用的 **hy3（混元图像 3.0）**——它在中文标注渲染上更强，正好对得上「手绘白板 + 中文技术标注」这个场景。除出图环节外，输入输出契约、风格规则、D1–D12 闸门全部沿用。

| 文件 | 改动 |
|---|---|
| `SKILL.md` | 出图模型改为 hy3，版本 6.2.0，新增「hy3 出图与画布归一强制回归」 |
| `scripts/build.py` | 新增 `normalize_canvas()`；质量检测采样 `160×90 → 320×180`；溯源字段写 hy3；`tags` 可配置 |
| `scripts/browser_smoke.py` | 移除 Linux 硬路径 `/usr/bin/chromium`，改走 Playwright 自带内核 |

换模型牵出两个只有真跑才暴露的问题：**hy3 出图尺寸不固定**（实测 `1440×1072` 与 `1024×1024`），而裁剪坐标是按 `1448×1086` 写死的 → 之前先做画布归一（溯源记为 `normalize → crop`）再加 ±28% 宽高比守卫；**检测阈值误判好图**——讨论白板黑色比例只有 `0.010`（阈值 `0.015`）被判「特征不足」，根因是采样网格 `160×90` 太粗把细线平均掉了，改成 `320×180` 后恢复到 `0.041`。

## 安装

```bash
# 从本仓库拷贝整目录到 WorkBuddy 用户级技能目录
cp -r workbuddy/skill/zaobao ~/.workbuddy/skills/zaobao
```

装完在 WorkBuddy 左侧「专家 · 技能 · 连接器 → 技能 → 已安装」里搜 `zaobao`，卡片显示 `version: 6.2.0` 才算被正式加载。

## 自然语言用法

在 WorkBuddy 输入框敲 `/zaobao`，粘贴三栏原文即可，例如「用 zaobao 跑今天这期早报：……」。Agent 按 `SKILL.md` 自动完成结构化、出图、成稿、切图、打包与 D1–D12 闸门；最终回复**只给一个**带本地时间戳的 ZIP 下载链接（默认时区 `Asia/Shanghai`）。

## 本地打包（已有核验 hy3 原画时）

```bash
cd workbuddy/skill/zaobao
python scripts/build.py \
  --input examples/zaobao-2026-10-10.json \
  --brief-image /path/to/verified_hy3_brief.png \
  --talk-image /path/to/verified_hy3_talk.png \
  --gen-brief "<真实溯源>" --gen-talk "<真实溯源>" \
  --out ./zaobao-build --timezone Asia/Shanghai
```

## 交付物结构

```text
article-YYYYMMDDHHMM.zip
├── index.html / talk.htm / index.json
├── md/zaobao.md, talk.md, talk-prompts.txt
├── img/ 2 张 hy3 原画 + 2 张成品 + 6 张分栏截图
└── imagegen-provenance.json
```

硬约束：ZIP 不含 `skill/`；首页导航仅 `index.html`、`talk.htm`、`md/zaobao.md`；全部 `<a>` 须 `_blank` + `noopener noreferrer`；`checkStatus=unaudited`；交付前过 D1–D12。

## 相关文件

| 文件 | 说明 |
|---|---|
| `scripts/build.py` | 确定性打包与时间戳命名 |
| `scripts/browser_smoke.py` | 成品渲染 QA |
| `tests/test_zaobao_v5.py` | 结构与回归单测 |
| `examples/article-202610101434.zip` | 真实交付发布包（17 文件） |
| `examples/article-20261010/` | 实战记录用图（16 张） |
| `assets/style-reference-*.png` | 白板风格锚点 |
| `references/D1-D12.md` | 交付前闸门 |
| `references/wxp-json.md` | index.json 契约 |
| `references/release-notes-v6.2.md` | v6.2 增强记录 |

更多细节以仓库内 `SKILL.md` 为准。

---

## 实战记录（2026-10-10）：【征文】早报我不再只读一遍，而是让 WorkBuddy 逼我想清楚

![腾讯云架构师深圳同盟群里 10 月 10 日的三栏早报原文](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/00-brief-message.jpg?raw=true)

> 周六早上 8 点 40 分，架构师群里弹出一条早报。三栏，一共不到 400 字。
> 我读完它用了两分钟。而把它变成我真正能用的东西，用掉了接下来的半小时——每一天，都是这半小时。

### 一、缘起：我不想只是"读过"

我是一名架构师。每天上班的第一件事，是把架构师群里那三栏早报读完：一条科技热点、一篇值得推的架构文章、一句让人清醒的话。

但我一直不太甘心。

**早报最大的问题不是信息少，而是它太容易"读完就忘"。** 一条发布、一个新产品，扫一眼就过去了，晚上再问自己"今天看了什么"，只剩下一点模糊的印象。我想要的不是"知道"，是把它拆开、嚼碎、变成自己的东西。

所以读完早报之后，我会接着做三件事：

**第一件，做深度思考。** 一条新闻我至少从三个切面去看：技术上它是怎么实现的、产品上它卖给谁、商业模式上它怎么转钱。同一个事实，换个切面就是完全不同的问题。

**第二件，从里面挖出问题，再结构化地想。** 我不想复述新闻，我想从新闻里挖出真正让人卡住的问题，然后用芒格那套思维模型去压它——反演思维、安全边际、能力圈、检查清单。问题挖得越准，思考的密度越高。

**第三件，把它存下来。** 存进我的知识库，也存进脑子。它既是我的技能的一部分——下次遇到同类问题，我有一套已经推演过的判断可以直接调用；它同时还是我的创作素材——社区发帖、长文选题、短视频脚本，全从这里长出来。

这是一个完整的闭环。但它同时也是一个**每天都要重跑一遍的流程**，我把它的 SOP 画了下来：

![架构师早报每日深度思考 SOP 流程图](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/01-sop-flow.jpg?raw=true)

看着这张图，我意识到一件事：**这 30 分钟里，真正值钱的只有 Phase 2。**

提问、建模、下判断——这部分只能长在我身上。它决定我能不能把一条新闻变成可复用的判断力，谁也替不了。可 Phase 3 呢？把思考写成帖子、画出两张带中文标注的手绘白板、按栏目切图、拼 HTML、生成 Markdown、按时区命名打包——纯搬运，熟练到闭着眼睛都能做。**它做得再熟练也只是熟练，消耗的是时间，不是判断力。**

我算了一下，Phase 3 大概吃掉 17 分钟，占了一大半。

于是我给自己定了个目标：**把 Phase 3 整段交出去。** 我只要喂进当天那三栏原文、再叫一声它的名字，出图、成稿、切图、打包，一次闭环。

我手上刚好有一个半成品——一个叫 `zaobao` 的技能包（skill），版本 v6.1.0。它离"能天天用"还差一步。这篇文章记录的，就是这一步。

### 二、先定义"什么算完成"

按我一贯的习惯，动手之前先把模糊任务翻译成可验证的目标。这次我写了三条验收标准：

| 目标 | 验收标准 |
|---|---|
| 技能能装进 WorkBuddy | 装到 `~/.workbuddy/skills/zaobao/`，在 WorkBuddy 里能被搜到、能召唤 |
| 出图环节必须能在 WorkBuddy 里跑起来 | 白板图由 WorkBuddy 可用的出图模型生成，中文标注清晰可读，风格与参考图一致 |
| 跑通一次真实早报 | 交付一个 `article-YYYYMMDDHHMM.zip`，内含两份 HTML、三份 Markdown、10 张图片，逐项打得开、拿起来就能用 |

第三条是关键。**"跑通"不等于"脚本没报错"，而是"产物存在、内容正确、链接可点、图片能用"。** 这句话是后面所有验收动作的来源。

### 三、第一步：先读懂这个 Skill 的骨架

改造之前先读代码。`zaobao` 这个技能包不大，但结构很讲究：

```text
zaobao/
├── SKILL.md              # 技能说明：输入/输出契约、风格规则、质量闸门
├── README.md
├── assets/
│   ├── style-reference-brief.png   # 早报白板风格参考
│   └── style-reference-talk.png    # 讨论白板风格参考
├── examples/zaobao-2026-10-10.json # 今天这期的输入
├── references/                     # D1-D12 闸门、JSON 契约、研究记录
└── scripts/
    ├── build.py                    # 核心：校验 + 画布归一 + 切图 + 生成 HTML/MD + 打包
    └── browser_smoke.py            # 成品渲染 QA：链接、断行、破图
```

它最大的优点是**把"审美"写成了"规则"**：

- 白板图必须是纯白底、粗细不齐的黑色马克笔边框、橙红为重点色；
- 三个栏目必须各自占据一个**完整的独立矩形**，互不交叉，这样才能按栏目裁图；
- 首页资源导航**严格只有三个入口**（两个 HTML + 一个 Markdown），且全部新页签打开；
- 输出文件名必须是**用户本地时区**的 `article-YYYYMMDDHHMM.zip`，精确到分钟。

这些规则我一行都不打算改。**我要改的只有一件事：出图。**

### 四、第二步：为什么第一步必须先换掉出图模型

这里要更正一个说法。

这个 skill 最早是**在 GPT 上跑的**，那时候出图环节用的是它的文生图模型 **Image 2.5**，脚本、风格锚点、质量阈值都是围着它调出来的。

但 **WorkBuddy 里并没有 Image 2.5 这个文生图模型。** 也就是说，这份 skill 直接搬过来，第一步就会卡死在"出图"这个动作上——它依赖的那个模型，这里不存在。

所以改造的第一件事不是改代码，是**换模型**：把出图环节换成 WorkBuddy 里可用的 **hy3（混元图像 3.0）**。它在中文渲染上明显更强，正好对得上"手绘白板 + 中文技术标注"这个场景。

但换模型不是改个名字那么简单。它牵出两个真实问题，都是跑起来才暴露的。

**问题一：hy3 的出图尺寸不固定，而裁剪坐标是写死的。**

原版脚本里藏着一句硬断言：图片必须正好是 `1448×1086`，否则直接报错——因为后面的分栏裁剪坐标是按这个尺寸标定的。

而 hy3 这次给我的两张图，一张是 `1440×1072`，另一张居然是 `1024×1024` 的**方图**。如果直接拉伸到标准画布，方图会被横向拉长 41%，字全变形。

我的处理是两个动作：

1. **加一道"画布归一"**：把 hy3 原图等比归一到标准画布 `1448×1086` 再裁剪，并且把这一步**如实写进 `imagegen-provenance.json`**——原始字节保留不动，衍生操作标注清楚（`normalize → crop`），不冒称"直接生成"。
2. **加一道比例守卫**：如果出图宽高比偏离标准画布超过 ±28%，直接判定不合格、要求重生成。那张 1024×1024 的方图，就是被这道守卫拦下来的。

**问题二：质量检测的阈值太严，把好图误判了。**

脚本里有个"白底黑线红橙强调"的像素比例检查。第一张图顺利通过，第二张却报错"特征不足"。我把它拆开测了一下：

| 图片 | 白底比例 | 黑色线条 | 橙红强调 | 判定 |
|---|---|---|---|---|
| 早报白板 | 0.617 | 0.044 | 0.055 | 通过 |
| 讨论白板 | 0.570 | **0.010** | 0.063 | 误判（阈值 0.015） |

原因不是图不好，是**采样太粗**：脚本把图缩到 160×90 才统计像素，讨论图线条更细密，缩完黑线被平均掉了。改成 320×180 采样后，黑色比例回到 0.041，恢复正常。

**这一条是我这次改造里最有价值的发现：检测脚本报错时，先问"是图错了，还是尺子错了"。**

改造清单最终只有 4 处：

| 文件 | 改动 |
|---|---|
| `SKILL.md` | 出图模型改为 hy3，版本升到 6.2.0，新增"hy3 出图与画布归一强制回归"小节 |
| `README.md` | 同步 hy3 说明与画布归一规则 |
| `scripts/build.py` | 新增 `normalize_canvas()`；质量检测采样改为 320×180；溯源字段写 hy3；tags 改为可配置 |
| `scripts/browser_smoke.py` | 移除 Linux 专用的 `/usr/bin/chromium` 硬路径，改走 Playwright 自带内核 |

### 五、第三步：装进 WorkBuddy，然后在里面找到它

技能包改完之后，装进 WorkBuddy 的用户级技能目录。整个过程就是三条命令，我把它完整跑了一遍并留了图：

![在终端中解压技能包并安装到 WorkBuddy 用户级技能目录](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/04-term-install.jpg?raw=true)

放在 `~/.workbuddy/skills/` 下是有意为之：这是**用户级**技能目录，装一次，所有项目都能用。早报这件事我天天要做，它不该被绑在某一个工作目录上。

#### 关键的一步：确认 WorkBuddy 真的"看见"了它

装完文件不算完，**装完能被 WorkBuddy 认出来、搜得到，才算完。** 我打开左侧的「专家·技能·连接器」，切到「技能」页，点右上角「已安装」，在搜索框里输入 `zaobao`：

![在 WorkBuddy 技能页按名字搜索 zaobao](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/02-wb-skill-search.jpg?raw=true)

结果很干净：**已安装技能 466 个，其中「用户自定义」只有 1 个，就是 `zaobao`**——左侧栏也标着它属于「专家·技能·连接器」，正是用户级技能目录的入口。说明它不是一个散落在磁盘上的文件，而是被 WorkBuddy 正式纳管了。

点开卡片，能看到它读到的是哪个版本：

![zaobao 技能详情：名称、描述与版本 v6.2.0](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/03-wb-skill-detail.jpg?raw=true)

卡片上写着 `name: zaobao`、`version: 6.2.0`，描述里那句"图片生成统一使用 hy3（混元图像 3.0）"，正是我这次改进去的内容。**版本号对上了，说明 WorkBuddy 加载的是改造后的新版本，而不是什么旧缓存。**

装完之后，真正的工作环境就是 WorkBuddy 本身。下面这张是我在做这件事时的真实界面——左边是任务与技能、连接器的入口，中间是对话和工具调用轨迹，右边是它顺手帮我渲染出来的文章预览：

![WorkBuddy 中的真实使用界面](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/05-wb-app.jpg?raw=true)

**这张图是我特意截的，因为它最能说明"工作交给 WorkBuddy"是什么意思**：我不是在某个终端里手敲脚本，而是在一个对话里把事情说完——读技能包、解压安装、调构建、出图、生成 HTML，中间每一步的执行记录都留在对话里，可回看、可复现。

### 六、第四步：一次完整调用——我给两样东西，它回一个成品

前面都是准备工作。真正每天要跑的那一下，是这样的：

![一次完整调用：输入 → zaobao v6.2 → 输出](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/06-pipeline.jpg?raw=true)

#### 我给它什么：一段早报，加一个技能名

说来简单——**我实际给出去的，只有两样东西。**

1. **一段早报原文。** 三栏，一共不到 400 字，我从群里原样复制，连链接都没改一个字；
2. **一个技能名：`zaobao`。** 在 WorkBuddy 输入框敲一个 `/`，打 `zaobao`，把上面那段贴进去。

没有任何模板要填，没有参数表要传，也不用写"你是一位资深架构师……"那种长提示词。**输入越短，说明该想清楚的事我提前想清楚了。**

因为那些事，我在改造这个 skill 的时候就已经写进契约里了：三栏必须齐全、每栏只提一个问题、问题必须落在本栏原文里、芒格推演要有哪几段、讨论要带一段能直接复制的群发开场白……**我把"怎么想"固化成了规则，它负责按规则执行。**

今天这期，我贴进去的就是这么三段字：

> 🚀**【科技热点】**
> 谷歌云在 Gemini at Work 2026 发布会上推出面向企业客户的 Gemini Agent，定位为"通用工作智能体"，用一个提示框和 1 个 API 覆盖问答、知识工作、媒体生成和代码编写，托管于 Gemini Enterprise 应用中，可在后台跨应用和设备工作。TechCrunch 称其可接受目标而非仅指令，自行规划任务、使用技能与工具并连接企业内部系统。
> 该智能体目前支持 Gemini 和 Claude 模型，默认由 AI 选择最合适的模型，用户也可自行指定；官方将提供 API 供开发者集成到第三方应用。
> 官网介绍：https://cloud.google.com/blog/products/ai-machine-learning/welcome-to-gemini-at-work-2026/
>
> 📝**【架构文章推荐】**
> AI编程和VibeCoding-有哪些高效的做法和习惯？- 作者：何明璐
> https://cloud.tencent.com/developer/article/2756348
>
> 🔆**【今日一言】**
> 技术判断力无法只靠阅读获得。看过再多故障复盘，也替代不了自己在生产环境里被叫醒一次。判断力来自承担后果的次数，这件事没有捷径。

#### 怎么调用：两条路，日常只走第一条

**第一条，在 WorkBuddy 里直接召唤。** 这是每天的默认动作：输入框敲一个 `/`，打 `zaobao`，这个技能就出现在候选里，回车即调：

![在 WorkBuddy 输入框用 /zaobao 召唤这个技能](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/08-wb-slash.jpg?raw=true)

**它把"跑一个脚本"变成了"说一句话"**——一段原文贴进去，剩下的它自己接上；调用记录还留在会话里，第二天想复现随时能翻回来。

WorkBuddy 会把这段原文先翻成 skill 要的结构化输入（三栏逐字保留、每栏一问、芒格推演、三道讨论），再把后面的生产走完。

**第二条，命令行走脚本。** 首次构建、或者想手工核对每个参数时，我走这条，日志原样贴出来：

![一次真实调用：构建脚本的命令与输出](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/07-term-run.jpg?raw=true)

注意几个参数：两张白板图是分开传的，因为它是 hy3 的产物；`--gen-brief / --gen-talk` 老老实实写着"hy3 未返回生成 ID，仅有本地文件名"——**能溯源到哪一步就写到哪一步，不编。**

#### 它给我什么：一个拿起来就能发的归档包

跑完之后唯一该出现在我面前的东西，是一个归档包：

![构建完成后的归档包内容](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/09-term-build.jpg?raw=true)

```text
article-202610101434.zip        # 17 个文件，按完成时刻（北京时间）命名
├── index.html                  # 早报原文 + 三问三答
├── talk.htm                    # 同盟讨论：引导语 → 配图 → 参考答案
├── index.json                  # 元数据（checkStatus=unaudited）
├── md/zaobao.md  md/talk.md  md/talk-prompts.txt
├── img/  ×10                   # 2 张 hy3 原画 + 2 张成品 + 6 张分栏截图
└── imagegen-provenance.json    # hy3 溯源、SHA-256、归一与裁切记录
```

**一段原文走到一个可发布产物，中间的对应关系是可核对的：**

| 栏目原文 | 抽出的问题 | 产出 |
|---|---|---|
| 【科技热点】谷歌云 Gemini Agent，一个提示框 + 1 个 API 覆盖问答、知识工作、媒体生成和代码编写 | 企业 Agent 能跨系统自主执行，谁能阻止它越权、失控和误操作？ | 早报白板第 1 栏 → `brief-topic-1.png` |
| 【架构文章推荐】AI编程和VibeCoding-有哪些高效的做法和习惯？ | AI 编程越来越快，为什么团队可能交付得更慢？ | 早报白板第 2 栏 → `brief-topic-2.png` |
| 【今日一言】技术判断力无法只靠阅读获得……判断力来自承担后果的次数 | 故障复盘读了很多，关键时刻为什么仍做不出正确决策？ | 早报白板第 3 栏 → `brief-topic-3.png` |

**到这里，闭环才真正接上：一小段原文、一个技能名进去，一个按本地时间命名的可发布产物出来，中间没有一处需要我手工搬运。**

到这一步，Phase 3 那 17 分钟就已经交出去了。剩下的问题只有一个：**它跑出来的东西，我敢不敢直接用。**

### 七、第五步：验收——两道闸门，盯的都是产物

跑通不是"脚本没报错"。我的验收不看打了多少行日志，只看两道闸门，两道都过了才算交付。

**第一道：归档包本身要立得住。** zip 能完整解开——17 个文件、无损坏；命名是我本地时区的 `article-202610101434.zip`；里面的 `imagegen-provenance.json` 逐步记着出图、画布归一、分栏裁切的来源。

**一个包交出去，别人能自己核对它是怎么做出来的，这才叫可交付。**

**第二道：成品在浏览器里真的能看。** 桌面端与移动端各渲染一遍，共 4 项通过：3 个导航链接全部有效、全部新页签打开，两个页面都没有横向溢出，10 张配图一张不破。

这两道闸门，就是"我敢不敢直接用"的答案。

### 八、成果：那天早上真正跑出来的东西

**hy3 生成的早报白板**（三栏：科技热点 / 架构文章推荐 / 今日一言，每栏底部一个橙红尖锐问题框）：

![hy3 生成的架构师早报三栏手绘白板图](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/10-brief-whiteboard.jpg?raw=true)

**hy3 生成的同盟讨论白板**（每题带背景、角度、尖锐问题、芒格模型、项目方案、改进项）：

![hy3 生成的架构师同盟三题讨论手绘白板图](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/11-talk-whiteboard.jpg?raw=true)

注意看图里的字——"模型路由""幂等凭证""熔断重试""口型简化→静态形象→文字客服→人工坐席"，**全是清晰可读的中文。** 这就是换成 hy3 最直接的收益。

因为每栏是独立矩形，脚本能按固定坐标把它们切出来单独发：

![早报科技热点栏目独立截图](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/12-brief-topic-1.jpg?raw=true)

![同盟讨论话题三独立截图](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/13-talk-topic-3.jpg?raw=true)

白板图会自动拼进 HTML。下面这张是最终 `index.html` 的真实渲染截图——首图、三条问答、原始文案、参考链接，**全部是可选中复制的真文字**，不是把截图糊上去的：

![index.html 桌面端渲染效果](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/14-index-render.jpg?raw=true)

`talk.htm` 则是另一种排法：每题先给"可直接复制到微信群"的引导语，再给配图，最后才是主持人参考答案。

![talk.htm 桌面端渲染效果](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/zaobao/examples/article-20261010/15-talk-render.jpg?raw=true)

### 九、踩过的坑，比成果更值得记

**坑 1：出图模型会无视你给的尺寸。** 我两次都传了 `1440×1080`，第一次得到 `1440×1072`，第二次直接给了 `1024×1024`。**不要相信出图尺寸，要给出图结果做归一和守卫。**

**坑 2：检测阈值要用真图校准。** 那个"黑线不足"的误判，浪费了我一轮排查。后来我固定了一个动作：**阈值报警时，先把指标打出来看数量级**，再决定是改图还是改尺子。

**坑 3：跨平台路径是隐形的坑。** 原脚本里写死了 `/usr/bin/chromium`，在 Windows 上必然失败；Windows 也没有系统时区库，得单独装 `tzdata`。这类"在别人机器上跑不通"的问题，只有真跑一次才会暴露。

**坑 4：不要把"没做过"写成"已做过"。** 出图工具这次没返回生成 ID，我在溯源文件里就写"hy3 未返回生成 ID，仅有本地文件名"，而不是编一个。**溯源的价值在于可信，不在于好看。**

**坑 5：装完不算完，能被搜到才算完。** 文件复制到技能目录，只是"放对了地方"；要到 WorkBuddy 里搜出名字、看到版本号，才知道它真的被加载了。这一步只花十秒，却能挡掉绝大部分"我明明装了但没生效"。

### 十、沉淀：把一次工作，变成一次能力

这次改造最让我满意的，不是省下了那十几分钟，而是**这十几分钟被固化成了规则**：

- 出图有风格锚点，不会再画出四不像；
- 内容有硬约束，话题锚点必须落在本栏原文里；
- 链接有强制检查，任何 `<a>` 少了 `_blank` 都会被拒绝；
- 产物有唯一命名，按本地时间戳，不会再出现"article 最终版 2"。

回到开头那张 SOP 图：现在 Phase 1 和 Phase 2 还是我亲自做，因为那才是我真正要练的东西；而 Phase 3——出图、成稿、切图、打包、验收——我只要把当天的三栏原文丢进去、叫一声 `zaobao`，它就自己跑完。

于是闭环真正接上了：**一段早报原文进来（Phase 1）→ 我想清楚（Phase 2）→ 它把成果做成能直接发布的产物（Phase 3）→ 发回给同盟群和社区 → 第二天，新的一段原文又进来。** 每一期都留下一个可核对的归档包，每一期的判断也都长在我身上。

**这才是"把工作交给 WorkBuddy"最实在的意义：不是让它替我思考，而是让它把我从不需要思考的事情里捞出来。**

我在公司里常说一句话：**好的架构不是让人更忙，而是让人可以不做。** 一个 Skill 值不值得沉淀，判断标准很简单——它有没有把你从"每天重复的操作"里彻底摘出来。

这次，WorkBuddy 帮我做到了。

---

本文所有截图均来自本次真实运行：终端截图取自实际执行的命令输出，界面截图取自本机 WorkBuddy（技能搜索、技能详情、`/` 召唤菜单均为真实操作），白板图与页面渲染图取自技能归档包 `article-202610101434.zip`，未使用任何演示数据。
