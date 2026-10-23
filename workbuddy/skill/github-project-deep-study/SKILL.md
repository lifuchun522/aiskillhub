---
name: github-project-deep-study
description: 把一个 GitHub 开源项目做成「熟悉 → 学习 → 实战 → 特性探索」的深度学习文章，产出单文件 PPT 卡片化 HTML（实图 base64 内嵌、特性树思维导图、使用流程实拍、Key 问题单），并沉淀可复现的实战证据链。当用户要求学习/研究/分析某个 GitHub 项目、写项目学习文章或笔记、"把项目跑起来看看到底能干什么"、整理特性树、跑通并截图取证时使用。覆盖 Web 服务与桌面应用两类项目。
---

# GitHub 项目深度学习

把任意开源项目变成「一篇面向最终读者的学习文章 + 一套可复现的实战证据」。核心原则：**每条结论都要有源码 / UI / 接口三源之一佐证，不转述 README；每个数字都要实测，不靠 grep 手数。**

## 何时用

- "帮我写一篇 XXX 项目的学习文章 / 笔记 / HTML"
- "把这个 GitHub 项目 clone 下来跑起来，截图，整理成文档"
- "分析这个项目的特性、边界、内核架构"

## 文章骨架（固定四段 + 三专题）

| 段 | 必须回答 | 合格判据 |
|---|---|---|
| **熟悉** | 它是什么 / 给谁用 / 为什么存在 | 一句话电梯演讲能说清问题与用户 |
| **学习** | 它怎么做到的 | C4 四层 + 核心抽象 + 关键路径（标代码位置与行号）+ ADR 权衡 |
| **实战** | 真能跑吗 | 真实命令输出 + 界面实图 + 可复现踩坑表 |
| **特性探索** | 到底有哪些能力、哪些能白跑 | 特性树思维导图（八域）+ 特性矩阵（标注是否需 Key）+ 用户视角逐步操作 + 零 Key 验证 |

三专题横切全程：**应用场景**（5W1H）、**边界思考**（适用/不适用/性能/成本/运维/vs 同类 六维）、**内核架构**（一句话 + 链路图）。

## 执行流程

### Step 1 克隆 + 三源枚举

```bash
# 正常路径
git clone --depth 1 <repo-url> <dir>
# git 隧道 502 时的降级路径（codeload 直连通常仍通）
curl -sL -o repo.tar.gz "https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/<branch>"
tar -xzf repo.tar.gz -C <dir> --strip-components=1

python scripts/enum_features.py <dir> [--api http://127.0.0.1:8080] [--out feature-enum.md]
```

三源交叉枚举（缺一容易漏项）：

1. **源码** — 服务模块清单、Provider 注册表、schema 字段
2. **接口** — 启动后抓 `/openapi.json`，拿真实端点而非文档转述（仅 Web 项目有）
3. **UI** — 页面控件标签 / 官方自带探测工具（如 `tools/PresetProbe`），等于产品经理视角的功能清单

### Step 2 环境搭建与启动

Web 项目：

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 60
```

桌面项目（WPF/WinForms/Avalonia 等）：

- 先 `dotnet --list-sdks`；**只有 runtime 没有 SDK 时 build 不了**
- 装 SDK：`dotnet-install.ps1 -Channel <主版本> -InstallDir <项目内 .dotnet>`，不装全局
- build + 跑项目自带探测工具（`tools/` 下的 console 工程通常 ProjectReference 主项目，是最佳证据源）
- **无头环境起不了 GUI 是常态**：如实记录，不伪造截图；证据链改用 build 输出 + 探测工具运行结果 + 源码结构图

启动后先探活再截图：Web 用 `curl -o /dev/null -w "%{http_code}"`，桌面用探测工具退出码与 stdout。

### Step 3 截图取证

Web UI：

```bash
python scripts/shot_pages.py --api http://127.0.0.1:8080/docs \
       --webui http://127.0.0.1:8501 -o shots/
```

已处理：Edge 内核回退、引导浮层关闭、Streamlit 大视口整页、Swagger 端点展开、按 y 区间裁切。

**使用流程实拍**（区别于静态面板截图）：按真实用户操作顺序驱动界面——每完成一步立刻截图，图注写清「这一步做了什么」。非标准控件点不动时，改走项目官方配置项（如 `config.toml`）绕过，并在文章中说明。

### Step 4 特性树（八域）+ 思维导图

按固定八域组织，每域都问"免费通道在哪"：

```
A 文案/LLM   B 配音/TTS   C 素材   D 字幕   E 背景音乐
F 合成/产物  G 接口层     H 工程特性（安全 / 缓存 / i18n / 状态机）
```

每域写清三件事：**有哪些选项**、**哪些要外部 Key**、**本次实测走了哪条**。

交付形态：**SVG 思维导图内联进 HTML**（矢量、缩放不糊），不要 ASCII 树或表格了事。

```bash
# 先写 JSON 数据（格式见 examples/mindmap.sample.json），再由脚本生成 SVG
python scripts/gen_mindmap.py --data tree.json --out mindmap.svg [--theme light] [--width 1800]
# [ok] mindmap.svg | 1800x862 | domains=8 | chars=22232 | theme=dark
```

数据 JSON 必填字段：`domains[].name`、`domains[].children`；`needkey` 取 `免 Key` / `部分免 Key` / `需 Key` 决定徽章色；`center` 放项目名与版本。

导图要求：

- 中心节点 + 域双列放射，每域带 Key 徽章，免 Key / 本地 / 内置条目绿字高亮（脚本自动识别）
- 由脚本从实测数据生成，不手画
- 导图下方加「🔍 点击放大查看导图」，**纯 CSS 实现**（离屏 checkbox + `:checked ~` 全屏规则）；checkbox 必须离屏，不能裸露；`input` / `label` / `.mindmap-wrap` 三者必须同级相邻
- 保留完整枚举明细，折叠进 `<details>`

### Step 5 零 Key 验证（最高价值的一步）

目的：证明"不付一分钱也能跑通"，同时暴露项目的真实依赖边界。通用找法：

1. **可手填的输入** → 跳过 LLM（文案、关键词直接传值）
2. **免费 TTS / 本地模型** → 跳过付费语音（本地 ASR/LLM 是天然零 Key 路线）
3. **本地素材** → 跳过素材检索 API；缺素材就用 ffmpeg 自造
4. **提交 → 轮询 → 取产物**，每步响应原文记进文章

```bash
# 造测试素材（纯色竖屏 5 秒）
ffmpeg -f lavfi -i "color=c=0x1a5f9c:s=1080x1920:d=5:r=30" \
       -c:v libx264 -pix_fmt yuv420p clip01.mp4
# 产物验证
ffprobe -v error -show_entries format=duration,size \
        -show_entries stream=codec_name,width,height final-1.mp4
ffmpeg -ss 8 -i final-1.mp4 -frames:v 1 frame.png   # 抽帧证明字幕/画面真烧进去了
```

失败也是素材：`failed_stage`、错误原文、根因（安全设计 / 枚举严格 / 参数格式）都写进「踩坑表」。

### Step 6 Key 问题单（需要外部凭据时）

用户明确会提供 Key 时，整理成分档问题单：

| 档 | 语义 |
|---|---|
| T0 | 已跑通，零 Key |
| T1 | 最高优先（解锁核心体验） |
| T2 | 次优先 |
| T3/T4 | 可选增强 |

每档必写：**需要哪些配置项**（`grep` 配置注释里的真实字段名）、**官方获取地址**（从 `config.example.toml` 注释提取）、**填在哪个文件哪一行**、**不填的后果**。附安全提示：Key 只落本地配置文件（确认在 `.gitignore` 内），不进文章、不进截图，建议用可吊销的测试 Key。

### Step 7 产出单文件 HTML

```bash
python scripts/build_article.py \
  --main article.html --fragment section.html \
  --anchor "  <section>|<h2>5. 三专题</h2>" \
  --image IMG_A=shots/panel-a.png --image IMG_B=shots/panel-b.png
```

脚本做四件事：插入章节 → 图片量化压缩（PNG 256 色，体积降约 60%）→ base64 内嵌 → 结构自检。
章节模板见 `references/article-template.md`。

### Step 8 交付前自检

必须实测，不能目测：

```python
# 结构断言
doctype / ends_html / section 数 / table 数 / data-uri 数 / 无占位符
# 渲染断言（playwright）
document.images 全部 ok === true
```

## HTML 交付规范（硬性）

### 样式：PPT 卡片化

每章节一张卡片，像幻灯片一样逐页滚动：

- 卡片：白底、20px 圆角、双层阴影、**顶部 6px 渐变色条**（按章节主题分色）
- 页码：右上角大号淡色 `01`/`02`…，用 CSS `counter` 自动生成，加章节不跳号
- 标题：h2 加粗放大 + 下分隔线；h3 左侧彩色竖条
- 导航：顶部 sticky 目录锚点直达；`section{scroll-margin-top:96px}` 防止标题被吸顶导航压住
- 卡片间距 30px、内边距 40px

### 内容：面向最终读者

**删掉一切写作过程痕迹**，读者只关心结论与方法：

| 删 | 替代 |
|---|---|
| 本地路径 / commit hash / 学习步骤 / 骨架说明 | 「项目速览」只留仓库、版本、实测环境 |
| 「本次实测」「本机」「我」等自述 | 中性化为读者视角 |
| 首次启动引导截图与说明 | 整节删除 |
| 「给我的方式」「拿到 Key 后我会补齐什么」 | 删除，问题单只留清单与获取地址 |
| 自测结论 note、footer 流水账 | 删除 / 改版本说明 |
| 踩坑流水账 | 改「环境要求与安装提示」，只留读者能用的（镜像、依赖版本） |

### 数字实测纪律

**数量类数字一律从模块导入或接口取，禁止 grep 手数。**（踩过的坑：手数 Provider 39 个，实测 `len(REGISTRY)` 是 37；手数端点 16 个，openapi 去重是 13 条路径 / 18 个方法级端点——`download`/`stream` 各含 HEAD+GET。）

```bash
# 正确姿势
.venv/Scripts/python -c "from app.models import llm_provider as m; print(len(m.LLM_PROVIDER_REGISTRY))"
curl -s /openapi.json | jq '[.paths | to_entries[] | .value | keys[]] | length'
```

计数口径与直觉不一致时（方法数 > 路径数），在文章里写明口径。

## 硬性要求

- 图片必须**真实截图**，不画示意图；确实没跑通就明确写"未获取"，不伪造
- 图注写清来源（哪个 URL / 哪条命令 / 哪个 commit）
- 数字（尺寸、时长、大小、进度百分比、耗时、数量）全部来自实测输出
- 踩坑表必含：现象 / 根因 / 处置，并区分「项目设计如此」与「环境问题」
- 中文输出；代码标识保留原文并附中文解释
- **改样式时勿整体覆盖 CSS**：曾因覆盖样式段冲掉导图放大规则，导致 checkbox 裸露、交互失效。用增量插入，改完渲染验证交互仍工作
- **沙箱批量 `rm` 有阈值**（约 50 文件，9 个也曾触发 SIGTERM），删文件 3–5 个一批
- **最终回复前必须加载 `delivery-no-pseudoblock` 技能并逐项跑 D1–D12**，在回复末尾贴闸门快照（每项写实际核对内容，禁只写「未命中」）；加载必须是发送前最后一步，不能在回合开头当盖章

## 自带例子（约 30 秒跑完，不依赖外网）

先跑例子确认脚本可用，再上真实项目：

```bash
python scripts/enum_features.py examples/demo-repo --depth 3 --out examples/expected-enum.md
python scripts/gen_mindmap.py --data examples/mindmap.sample.json --out examples/mindmap.sample.svg
cp examples/article.main.html examples/article.out.html
python scripts/build_article.py --main examples/article.out.html \
  --fragment examples/article.section.html \
  --anchor '  <section id="s6">' --image IMG_A=examples/assets/demo-shot.png
```

期望：枚举出 2 组注册表（各 3 项）与 6 条方法级路由；导图 1800×862、8 域；自检 `RESULT: PASS`。
逐步说明、真实输出与所有失败断言对照表见 `examples/walkthrough.md`。

## References

- `references/pitfalls.md` — 环境与截图踩坑清单（含具体命令）
- `references/article-template.md` — 文章章节骨架模板（可直接复制填空）
- `references/html-style-spec.md` — PPT 卡片化 HTML 样式规范与内容清理清单
