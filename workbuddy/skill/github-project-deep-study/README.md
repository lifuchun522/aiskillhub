# github-project-deep-study

把一个 GitHub 开源项目做成 **一篇面向最终读者的深度学习文章** + **一套可复现的实战证据**。

产出是**单文件 HTML**（双击即开、图片全内嵌、PPT 卡片式翻页），写完后你自己能讲清"它是什么、怎么实现的、真能跑吗、到底能干什么"。

> 核心原则：每条结论都要有 **源码 / UI / 接口** 三源之一佐证，不转述 README；每个数字都要 **实测**，不靠 grep 手数。

---

## 能力边界

| 做 | 不做 |
|---|---|
| Web 服务、CLI 工具、桌面应用（WPF/WinForms/Avalonia） | 闭源 SaaS、无源码可读的项目 |
| 真实 clone → 装依赖 → 启动 → 截图 → 跑通 | 只读 README 写读后感 |
| 特性树八域枚举 + 思维导图（SVG 生成） | 手画示意图代替截图 |
| 零 Key 全流程验证（免付费凭据跑通核心链路） | 需要企业内网/私有凭据才能跑的场景 |
| 需要 Key 的能力整理成 T0–T4 分档问题单 | 伪造运行结果、编造数字 |
| 单文件 HTML（PPT 卡片化） | React/Vue 工程、需要构建的多文件站点 |

无头环境起不了 GUI 是常态：桌面项目如实标注"运行时截图未获取"，证据链改为 **构建输出 + 项目自带探测工具 + 纯逻辑类 harness 调用**。

---

## 产出长什么样

固定四段 + 三专题横切：

| 段 | 必须回答 | 合格判据 |
|---|---|---|
| **熟悉** | 它是什么 / 给谁用 / 为什么存在 | 一句话电梯演讲能说清问题与用户 |
| **学习** | 它怎么做到的 | C4 四层 + 核心抽象 + 关键路径（标函数名与行号）+ ADR 权衡 |
| **实战** | 真能跑吗 | 真实命令输出 + 界面实图 + 可复现踩坑表 |
| **特性探索** | 到底有哪些能力、哪些能白跑 | 特性树导图（八域）+ 特性矩阵 + 用户视角逐步操作 + 零 Key 验证 |

三专题：**应用场景**（5W1H）· **边界思考**（适用/不适用/性能/成本/运维/vs 同类 六维）· **内核架构**（一句话 + 链路图）。

完整章节骨架见 [`references/article-template.md`](references/article-template.md)。

---

## 安装

放到用户级技能目录（Windows / macOS / Linux 同构）：

```bash
# Windows
xcopy /E /I github-project-deep-study "%USERPROFILE%\.workbuddy\skills\github-project-deep-study"
# macOS / Linux
cp -r github-project-deep-study ~/.workbuddy/skills/
```

或者放进项目的 `.workbuddy/skills/` 作为项目级技能。

依赖：

| 项 | 必需 | 用途 |
|---|---|---|
| Python 3.10+ | ✔ | 三个脚本 |
| Pillow | 推荐 | 截图压缩（缺了退化为原图内嵌） |
| playwright + Edge/Chrome | 推荐 | 自动截图与渲染自检 |
| ffmpeg / ffprobe | 视项目 | 造素材、验产物 |

---

## 用法

直接对 Agent 说：

> 帮我写一篇 `owner/repo` 的学习文章，本地跑起来带截图，特性树用思维导图，最后给我 HTML

执行流程由 `SKILL.md` 定义，共 8 步：

1. **克隆 + 三源枚举** — 源码 / 接口 / UI 三源交叉，缺一容易漏项
2. **环境搭建与启动** — Web 与桌面两条分支（SDK / 运行时 / 探测工具）
3. **截图取证** — 静态面板 + 按真实操作顺序的使用流程实拍
4. **特性树八域 + 思维导图** — `gen_mindmap.py` 从数据生成 SVG，不手画
5. **零 Key 验证** — 证明"不付一分钱也能跑通"，同时暴露真实依赖边界
6. **Key 问题单** — T0–T4 分档，字段名从配置注释抄，附官方申请地址
7. **产出单文件 HTML** — `build_article.py` 插入章节 + 压图内嵌 + 结构自检
8. **交付前自检** — 结构断言 + 渲染断言 + 导图交互开合验证

---

## 脚本

| 脚本 | 作用 | 典型命令 |
|---|---|---|
| `scripts/enum_features.py` | 三源枚举：目录树、服务模块、注册表、路由、UI 入口、openapi | `python scripts/enum_features.py <repo> --api http://127.0.0.1:8080` |
| `scripts/shot_pages.py` | 自动截图：Edge 回退、关引导浮层、Streamlit 大视口、Swagger 展开、按 y 裁切 | `python scripts/shot_pages.py --api .../docs --webui ...:8501 -o shots/` |
| `scripts/gen_mindmap.py` | 由 JSON 数据生成特性树 SVG（深/浅两套主题） | `python scripts/gen_mindmap.py --data tree.json --out mindmap.svg` |
| `scripts/build_article.py` | 章节插入 + PNG 量化压缩 + base64 内嵌 + 结构自检 | `python scripts/build_article.py --main a.html --fragment s.html --anchor "<section id=\"s6\">" --image IMG_A=shots/a.png` |

全部脚本 `--help` 可查参；无第三方依赖也能跑（Pillow 缺失时自动降级）。

---

## 例子

[`examples/`](examples/) 里有一个自带夹具项目 `demo-repo`，一路跑到底约 30 秒：

```bash
python scripts/enum_features.py examples/demo-repo --depth 3 --out examples/expected-enum.md
python scripts/gen_mindmap.py --data examples/mindmap.sample.json --out examples/mindmap.sample.svg
cp examples/article.main.html examples/article.out.html
python scripts/build_article.py --main examples/article.out.html \
  --fragment examples/article.section.html \
  --anchor '  <section id="s6">' --image IMG_A=examples/assets/demo-shot.png
```

逐步说明与**真实输出**见 [`examples/walkthrough.md`](examples/walkthrough.md)。

| 文件 | 说明 |
|---|---|
| `examples/demo-repo/` | 夹具项目：两种路由声明、两组注册表、UI 入口、config 示例 |
| `examples/mindmap.sample.json` | 特性树数据格式（八域，含免 Key 徽章） |
| `examples/article.section.html` | PPT 卡片章节片段（含 `IMG_*` 占位符） |
| `examples/article.main.html` | 最小主 HTML 骨架 |
| `examples/article.out.html` | 构建产物（37 KB，图片已内嵌，可双击打开） |

---

## 文档

`wiki/` 下按主题拆开，可直接搬进 GitHub Wiki：

| 页面 | 内容 |
|---|---|
| [Home](wiki/Home.md) | 导航 + 五分钟上手 |
| [四阶段与三专题](wiki/01-四阶段与三专题.md) | 文章骨架为什么这么定 |
| [三源枚举](wiki/02-三源枚举.md) | 源码 / 接口 / UI 各能捞到什么 |
| [环境与启动](wiki/03-环境与启动.md) | Web 与桌面两条路径 |
| [截图取证](wiki/04-截图取证.md) | 静态面板 vs 使用流程实拍 |
| [特性树与思维导图](wiki/05-特性树与思维导图.md) | 八域划分与 SVG 生成 |
| [零 Key 验证](wiki/06-零Key验证.md) | 找免费通道的四步法 |
| [Key 问题单](wiki/07-Key问题单.md) | T0–T4 分档写法 |
| [HTML 交付规范](wiki/08-HTML交付规范.md) | PPT 卡片化与内容清理 |
| [踩坑总表](wiki/09-踩坑总表.md) | 环境/截图/构建 16 条实证 |
| [FAQ](wiki/10-FAQ.md) | 常见疑问与边界 |

---

## 实测验证

本仓库内的脚本在示例夹具上跑通（Windows 11 + Python 3.13 + Edge 内核）：

```
enum_features  → 2 组注册表（ProviderSpec 3 / TTSSpec 3）、6 条方法级路由、1 个 UI 入口
gen_mindmap    → 1800x862 SVG，8 域，22 KB
build_article  → 结构自检 PASS（sections 4 / tables 2 / data_uris 1 / 无占位符残留）
render check   → images 1 broken 0；导图放大 position=fixed 宽 1280，收起 position=relative
```

---

## 硬性规则

1. 图片必须真实截图，跑不通就写"未获取"，不画示意图冒充
2. 图注写清来源（哪个 URL / 哪条命令）
3. 数量类数字从模块导入或接口取，禁止 grep 手数；口径不一致时写明口径
4. 踩坑表必含「现象 / 根因 / 处置」，并区分「项目设计如此」与「环境问题」
5. 改样式只做增量追加，不整体替换 CSS 段（会冲掉导图交互规则）
6. 交付前跑结构断言 + 渲染断言，导图交互点开再点合各验一次
