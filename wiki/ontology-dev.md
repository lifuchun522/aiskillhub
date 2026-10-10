# ontology-dev｜本体驱动业务系统开发技能（v9）

> 把「业务需求 → 软件需求规格 → 七模型本体 YAML → 可运行 BS 系统」整条链路打包成一个技能。需求可追溯、模型即语义来源、每个探索阶段人工门禁、内置 `code-paas` 技术底座。

仓库路径：[`sa/skill/ontology-dev/`](https://github.com/lifuchun522/aiskillhub/tree/main/sa/skill/ontology-dev)

完整使用说明：[`README.md`](https://github.com/lifuchun522/aiskillhub/blob/main/sa/skill/ontology-dev/README.md)　·　英文版 [`README_EN.md`](https://github.com/lifuchun522/aiskillhub/blob/main/sa/skill/ontology-dev/README_EN.md)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/sa/skill/ontology-dev/SKILL.md)

来源：上游 [`sharptoolbox/ontology-driven-dev`](https://github.com/sharptoolbox/ontology-driven-dev)（MIT License）。本仓快照对应上游 commit [`49a9eff`](https://github.com/sharptoolbox/ontology-driven-dev/commit/49a9eff8b17349adaa860b355e82e6154c35dc82)（2026-10-09），2026-10-10 同步入仓。

---

## 一句话

输入一段业务需求（一句话或一段描述），输出一套**可运行的管理系统**，且数据库表、接口、菜单、权限、流程、规则全部可回溯到七模型本体 YAML——不是「让 AI 直接写代码」，而是「让模型驱动代码」。

## 它解决什么问题

三件事，普通「帮我写个管理系统」做不好：

1. **需求可追溯** —— 每个功能点都能回溯到需求规格说明书的某一条，而不是 AI 自由发挥；
2. **模型即语义来源** —— M1 对象 / M2 行为 / M3 规则 / M5 主体 / M6 流程 / M7 查询报表 / MU 界面七份 YAML 是唯一事实源，杜绝「模型一套、代码一套」；
3. **门禁不可跳过** —— 需求探索的 8 个阶段（阶段零～阶段七）每一阶段都必须**硬暂停等人确认**，企业专属内容未确认不得推进。

## 包含内容

```
sa/skill/ontology-dev/
├── SKILL.md                      # 技能核心指令（三阶段管线 + 门禁纪律）
├── references/                   # 5 份强制规范（288 KB）
│   ├── AI需求探索与确认提示词V9.0.md      # 含《软件需求编写规范 V9.0》全文
│   ├── ontology_modeling_framework_v9.md  # 七模型元规范 + YAML 模板（103 KB）
│   ├── 本体模型业务功能开发指导书.md        # 模型→实现映射、开发流水线 10 步
│   ├── AI 原生应用技术架构设计文档.md       # 语义注册表 / AI 编排 / SSE / 只读 SQL
│   └── UI-UE界面设计规范.md               # 配色 token / 布局 / 完整 CSS 库
├── reference-example/            # 黄金范例：销售合同执行管理（1.1 MB）
│   ├── 合同管理需求规格说明书-V9.md（91 KB）+ UI 原型 HTML
│   ├── m1…m7 + mu-ui 共 8 份 YAML + manifest.json
│   └── 界面调用链/
├── techbase/                     # code-paas 底座·Python 版（Flask + SQLite + React/TS）
├── go-techbase/                  # code-paas 底座·Go 版（Gin + PostgreSQL + goose + React 19）
└── code-app-example/             # 完整应用样例：合同/开票/收款/审批/报表/AI 助手
```

| 组件 | 作用 | 何时用 |
|---|---|---|
| `SKILL.md` | 三阶段流程 + 门禁 + 纪律 | Agent 每次加载 |
| `references/` | 5 份方法论文档，**分阶段按需读** | 阶段一/二/三各读对应那几份 |
| `reference-example/` | 黄金范例，字段语义与命名的对照物 | 建模期对照 |
| `techbase/` `go-techbase/` | 干净底座，复制成 `code-app/` 后再扩展 | 阶段三起点 |
| `code-app-example/` | 跑通的实物（含 SQLite 测试数据） | 学习/验证完整链路 |

## 安装

技能不依赖任何平台专有机制，整目录拷贝即可。唯一适配点：内部相对路径以「本 SKILL.md 所在文件夹」为根，各工具自动解析。

```bash
# WorkBuddy（用户级 / 项目级）
cp -r sa/skill/ontology-dev ~/.workbuddy/skills/ontology-dev
cp -r sa/skill/ontology-dev <项目>/.workbuddy/skills/ontology-dev

# Claude Code
cp -r sa/skill/ontology-dev ~/.claude/skills/ontology-dev

# Codex：放入仓库 .codex/skills/，再在 AGENTS.md / codex.md 里加一句
#   「提到本体驱动/需求探索/本体建模/七模型时，加载 .codex/skills/ontology-dev/SKILL.md 并按三阶段执行」

# Cursor / Cline / Aider：把 SKILL.md 作为方法论指令注入项目上下文
```

## 使用流程（强顺序三阶段）

| 阶段 | 依据 | 产物 |
|---|---|---|
| 一 · 需求探索 | `AI需求探索与确认提示词V9.0.md` | `<业务域>-需求规格说明书-V9.md`（含附录 C 建模基线） |
| 二 · 本体建模 | `ontology_modeling_framework_v9.md` | `yaml/` 七模型 + `manifest.json` |
| 三 · 应用构建 | 指导书 + 架构文档 + UI-UE 规范 | `code-app/`（可运行 BS 系统） |

- **阶段一门禁**：每阶段结束按「问题 N + AI 建议 + 理由 + 其他选项 + 快捷回复」提问并硬暂停；A 类（行业通用）AI 自动补全并标注 `[AI自动补全]`，B 类（企业专属）必须 `[待确认]`，附录 B 有 `[待确认]` 则文档不得标「完整」。
- **阶段二门禁**：可追溯性、M7 `behaviorRef` ↔ M2 `queryReportRef` 一对一、M6 引用无环等强制核对。
- **阶段三**：`cp -r <技能根>/techbase/. <项目>/code-app/` → 按指导书 10 步实现 → **必须补齐右侧 AI 对话框**（本体注册表注入 + 工具调用 + SSE 流式 + 只读 SQL 白名单）。
- 支持**单阶段入口**：只建模（已有需求文档）、只构建（已有七模型 YAML）、回到某阶段重确认。

## 触发语

| 意图 | 示例 |
|---|---|
| 整体开发 | 「帮我开发一个 XX 管理系统」「把这段需求做成本体驱动开发」 |
| 仅建模 | 「基于这份需求规格说明书，做本体建模」 |
| 仅构建 | 「基于这几份七模型 YAML，生成系统」 |
| 关键字 | 本体驱动、需求探索、本体建模、七模型、code-paas、AI 原生应用、业务系统开发 |

## 运行环境

- Python 3.10+（后端 Flask + SQLite）、Node.js 18+（前端 React + Vite）
- 首次运行需联网 `npm install` / `pip install`
- 默认账号：`admin / admin123`；样例另有 `sales / finance / finmgr / gm / emp`（详见各自 README）

---

## 测评（2026-10-10 · 本机实测）

### 结论

**可用，且是"重型但完整"的技能**——方法论、范例、底座、样例应用四件套合一，两套后端在真实环境跑通端到端链路。代价是体量大（391 文件 / 4.2 MB），需要按阶段按需加载 references，不适合自动常开触发。

### 实测记录

| 检查项 | 命令 / 方式 | 结果 |
|---|---|---|
| 快照完整性 | 上游 `git clone --depth 1`，去 `.git` 后入仓 | ✅ 391 文件 / 4.2 MB，无嵌套 `.git` |
| 语法编译 · 底座 | `python -m compileall techbase/backend` | ✅ 32 个 py 文件全部通过 |
| 语法编译 · 样例 | `python -m compileall code-app-example/backend` | ✅ 53 个 py 文件全部通过 |
| 端到端 · 底座 | `techbase/backend/smoke_test.py` | ✅ 通过（登录 → 申请暂存/提交 → 两级审批 → 驳回 → 撤回 → 系统数据核对） |
| 端到端 · 样例 | `code-app-example/backend/smoke_test.py` | ✅ **13 项全通过**（主数据 / 合同二级审批含 ≥100 万分支 / 驳回 / 开票审批联动 / 收款 + 冲销联动 / 审批记录 / 3 张报表 / 流程实例） |
| 结构一致性 | 5 refs + 8 YAML + manifest + 双底座 + 样例 | ✅ 与 `README.md` 目录树一致 |

实测环境：Windows / Python 3.13.14 / Flask 3.1.3 / PyYAML 6.0.3。

### 做得好的地方

- **闭环而非片段**：规范（5 份）→ 范例（需求文档 + 七模型）→ 底座（双栈）→ 样例（跑通实物）齐备，学习者与执行者拿到的是同一套闭环。
- **门禁是真门禁**：8 阶段硬暂停 + 建模期一致性核对 + 附录 `[待确认]` 阻断，把"AI 一路直出、事后返工"的风险前置为"逐步确认"。
- **双技术底座可选**：Python（Flask + SQLite）与 Go（Gin + PostgreSQL + goose + React 19）同一套本体语义，按项目栈选型。
- **真的跑得起来**：两套 `smoke_test.py` 均实测通过，样例覆盖跨对象状态联动（开票↔付款阶段、收款↔开票）与冲销回退，不是"骨架 + TODO"。
- **跨工具可移植**：frontmatter 仅 `name` / `description`，相对路径以 SKILL.md 为根，WorkBuddy / Claude Code / Codex / Cursor 通用。

### 风险与不足

| 级别 | 问题 | 影响 / 建议 |
|---|---|---|
| P1 | `requirements.txt` 钉 `PyYAML==6.0.1`，在 Python 3.13 上无 cp313 wheel（需本地编译，无编译器即失败） | 首次安装即报 `Failed building wheel for PyYAML`。按文档用 3.10–3.12，或把依赖放宽到 `PyYAML>=6.0.2` |
| P2 | `go-techbase/go.mod` 的 module 仍为 `github.com/opic-ai/ontology-driven-dev/go-techbase`（上游路径未中性化） | 落地 Go 版时须先改 module 名，否则私有仓库/内网 import 会失败 |
| P2 | `code-app-example` 的 AI API Key 已清空 | 使用右侧 AI 智能助理前，须在界面自行配置 OpenAI 兼容服务 |
| P2 | 体量大：单技能 391 文件 / 4.2 MB，`references/` 共 288 KB | 不宜用户级常开（会与无关会话争上下文）；建议项目级安装，且 references **按阶段按需读**，不要一次性全量加载 |
| P3 | `reference-example/合同管理需求规格说明书-V9-UI原型.html` 为 570 KB 单页 | 直接打开较慢，用于对照即可，不必进模型上下文 |

### 适用 / 不适用

- **适用**：从需求出发生成一套可运行管理系统；对"需求—模型—代码"强追溯有硬要求的交付；想把 `code-paas` 底座（Python/Go）当作二次开发起点。
- **不适用**：只写几个零散接口/页面；不需要本体建模的小需求；希望 AI 一口气直出、不想逐阶段人工确认的场景（门禁会成为阻力）。

## 相关文件

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 三阶段流程、门禁、固定输出约定、关键纪律 |
| `references/AI需求探索与确认提示词V9.0.md` | 需求探索 8 阶段提示词 + 《软件需求编写规范 V9.0》全文 |
| `references/ontology_modeling_framework_v9.md` | 七模型元规范 + 各模型 YAML 模板 |
| `references/本体模型业务功能开发指导书.md` | 模型→实现映射总表 + 开发流水线 10 步 + 检查清单 |
| `references/AI 原生应用技术架构设计文档.md` | 技术栈 / 语义注册表 / AI 编排 / SSE / 只读 SQL 边界 |
| `references/UI-UE界面设计规范.md` | 配色 token / 布局 / CSS 库 |
| `reference-example/` | 合同管理七模型 + 需求规格 + UI 原型（对照范例） |
| `techbase/backend/smoke_test.py` | 底座端到端自测 |
| `code-app-example/backend/smoke_test.py` | 样例端到端自测（13 项） |

更多细节以仓库内 `SKILL.md` 与 `README.md` 为准。
