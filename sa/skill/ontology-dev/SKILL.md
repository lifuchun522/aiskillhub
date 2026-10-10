---
name: ontology-driven-dev
description: 当用户要基于业务需求，通过「需求探索 → 本体建模 → 应用构建」三步法开发一套完整、可运行的本体驱动 BS(浏览器前后端) 业务系统时使用。基于七模型本体 YAML(M1/M2/M3/M5/M6/M7/MU) 与内置 code-paas 技术底座，强制每个需求探索阶段人工确认，产出严格对齐需求文档、本体模型与代码的系统。支持整体触发与单阶段入口(仅建模/仅构建)。触发词含：本体驱动、需求探索、本体建模、七模型、code-paas、AI原生应用、业务系统开发。
---

# 本体驱动系统开发技能（Ontology-Driven Dev）

将"业务需求 → 软件需求规格 → 七模型本体 YAML → 可运行 BS 系统"的完整方法论打包为可复用技能。
技术底座为内置的 `code-paas`（Flask + SQLite + React/TS 单体应用，含系统管理、流程引擎、工作台、本体注册表），
输出严格受四份规范约束。

> **路径约定（跨工具通用）**：本技能内所有相对路径（如 `references/`、`reference-example/`、`techbase/`）均以「**本 SKILL.md 所在文件夹**」为根目录。
> - WorkBuddy / Claude Code / Codex 等工具在加载技能时会自动解析该根目录；
> - 若某工具未自动解析，请将下文 `<本技能目录>` / `<技能根目录>` 占位符替换为本 SKILL.md 的**绝对路径**（例如 `C:\Users\hemin\.claude\skills\ontology-driven-dev` 或 `~/.workbuddy/skills/ontology-driven-dev`）后执行。

## 一、适用场景与触发

- 用户给出一段业务需求（一句话或一段描述），希望产出一套可运行业务系统。
- 用户明确要求"需求探索确认 / 本体建模 / 七模型 / 基于 code-paas 构建 / AI 原生应用"。
- 自然语言示例：「帮我开发一个 XX 管理系统」「把这段需求做成本体驱动开发」「基于这份需求规格说明书生成系统」。

## 二、三阶段管线 + 人工门禁（强顺序）

阶段一与阶段二、阶段三之间强顺序；阶段一内部八阶段也强顺序，且每一阶段都必须**人工确认**后才可推进。

### 阶段一：需求探索 → 软件需求规格说明书

- **唯一依据**：`references/AI需求探索与确认提示词V9.0.md`（其附录一即《软件需求编写规范 V9.0》全文，是本阶段格式 / 编号 / 图表 / 自检的唯一基准）。
- **严格按该提示词的"阶段零 ～ 阶段七"八阶段推进**：
  - 阶段零 总体理解确认 → 阶段一 业务对象 → 阶段二 业务功能与规则 → 阶段三 跨对象联动识别 →
    阶段四 端到端协同流与审批流 → 阶段五 查询统计与固定报表 → 阶段六 角色权限 → 阶段七 UI 原型（可选，须先确认是否需要）。
- **人工确认门禁（强制，不可跳过）**：每个阶段(stage0-7)结束、进入下一阶段前，必须按提示词统一的"问题 N + AI建议 + 建议理由 + 其他选项 + 快捷回复"格式提问，并**硬性暂停等待用户明确确认**（"按AI建议" / 选项字母 / 修改意见）后才可推进。
  - A 类（行业通用）内容：AI 自动补全，标注 `[AI自动补全]`。
  - B 类（企业专属、猜错会有真实业务风险）内容：必须带 AI 建议提问，标注 `[待确认]` / `[已确认]`。
  - 绝不在用户未确认时私自进入下一阶段；附录 B 存在 `[待确认]` 则文档不得标记"完整"。
- **终态**：对照规范第十二章 47 项自检全通过、且附录 B 无 `[待确认]` 后，文档标记为「完整（可进入本体建模阶段）」。
- **输出**：`<业务域>-需求规格说明书-V9.md`（置于当前工作项目根目录）。
- **对照范例**：`reference-example/合同管理需求规格说明书-V9.md`（销售合同执行管理跑通实物）。

### 阶段二：本体建模 → 七模型 YAML

- **唯一依据**：`references/ontology_modeling_framework_v9.md`（七模型元文件规范 + 各模型 YAML 模板）。
- **输入**：阶段一需求文档，尤其其**附录 C 七模型建模输入基线**（是后续 YAML 的确定性输入，不得再做大范围业务拆分）。
- **产物**：M1 对象 / M2 行为 / M3 规则 / M5 主体 / M6 流程 / M7 查询报表 / MU UI 共七个 YAML + `manifest.json`，输出到当前项目的 `yaml/` 目录。
- **建模顺序建议**（见指导书 §4 步骤 1）：M1 → M5 角色 → M3 规则 → M2 行为 → M7 查询 → M5 权限 → M6 流程 → MU 界面。
- **一致性门禁（强制）**：建模后核对——
  - 可追溯门禁：M2 `triggerType=USER_ACTION` 行为须被至少一个 MU 操作功能点引用；MU 引用行为须存在。
  - M7 `behaviorRef` ↔ M2 `queryReportRef` 严格一对一。
  - M6 的 `roleRef` / `behaviorRef` / `subFlowRef` / `ruleRef` 引用均须存在；`SUB_FLOW_CALL` 调用图无环。
  - 每个正式查询报表与唯一 M2 QUERY 行为双向一对一；联动描述中规则条件与结论不混写。
- **输出**：`yaml/m1-object-model.yaml` … `yaml/mu-ui-model.yaml` + `yaml/manifest.json`。
- **对照范例**：`reference-example/` 下 7 个 yaml（字段语义、命名、syncTriggers / node_graph / ASCII 布局的直接参考）。

### 阶段三：应用构建 → 可运行 BS 系统

- **依据（严格按序参考）**：
  1. `references/本体模型业务功能开发指导书.md`（核心：步骤 1-10、模型→实现映射总表、审批端到端、AI 对话、检查清单）
  2. `references/AI原生应用技术架构设计文档.md`（技术栈 / 分层 / 语义注册表 / AI 编排 / SSE / 只读 SQL 安全边界）
  3. `references/UI-UE界面设计规范.md`（配色 token / 9pt / 标签右对齐 / 三类界面布局 / 完整 CSS 库）
- **技术底座**：本技能内置 `techbase/`（即 code-paas 干净源码，已剔除 node_modules / __pycache__ / dist / 运行时 DB）。
  **第一步**：将 `techbase/` 整体复制为当前项目根目录下的 `code-app/`，随后安装依赖：
  ```bash
  # 复制底座（保留目录结构）
  cp -r <本技能目录>/techbase/. <当前项目>/code-app/
  # （<本技能目录> = 本 SKILL.md 所在文件夹；各工具会自动解析，否则请替换为绝对路径）
  cd <当前项目>/code-app/frontend && npm install      # 还原前端依赖
  cd <当前项目>/code-app/backend  && pip install -r requirements.txt
  ```
  > 底座是只读基线，扩展只在 `code-app/` 内进行；techbase 自带的"客户申请/查询"示例模型（models/ 下 m1/m2/m5/m6/mu）按指导书复制改造或删除，用阶段二 `yaml/` 七模型取而代之并登记 manifest.json。
- **开发顺序（指导书 §1.4 标准流水线 10 步）**：
  1. 写七模型 YAML 到 `code-app/models/` 并登记 `manifest.json`；
  2. M1 → 数据库表 DDL（聚合根主表 / 子实体从表，含 5 默认字段；编号"三位前缀+四位流水号"自动生成）；
  3. 数据字典由注册表自动注册；
  4. M2 行为 + M3 规则 → `services/*.py`（事务内；前置校验→规则校验→状态变更→`syncTriggers` 联动；规则引擎 `simpleeval`，违反给中文提示）；
  5. M5 → 系统管理种子（角色 / 权限 / 资源 / 用户；接口加 `@require_permission`）；
  6. M6 → 流程引擎（M6 activities+branches 转 `node_graph`；审批角色须配置且有用户绑定）；
  7. MU → 菜单 + 页面 + 路由（单表 2 列 / 主从 3 列+从表表格 / 查询 3 列+结果表格分页；`AggregateRootRef` 跳选框、`Enum`/`DictionaryRef` 下拉框；带审批功能"保存草稿/提交"双按钮）；
  8. **强制实现右侧 AI 对话框**（指导书第 7 章 + 架构文档第 9 章）：底座默认 `ai.enabled=false` 且 backend 无 `ai/`、`sse/` 模块，本步必须补齐——system prompt 注入本体注册表、工具注册（导航/查询/行为/只读 SQL）、SSE 流式（`message_start→delta→tool_call→tool_result→render_payload→message_end`）、`text/table/chart/action` 渲染协议、动态 SQL 严格只读白名单 + 审计；
  9. 联调：登录 → 录入 → 暂存/提交 → 多级审批（通过/驳回/退回/撤回）→ 查询，全链路跑通；
  10. 验收：对照指导书附录 A 检查清单；规则违反前端有中文提示；界面符合 UI-UE 规范。
- **输出**：`code-app/`（可运行系统）。默认账号见 `techbase/README.md`（admin/admin123 等）。

## 三、单阶段入口（用户可指定只跑某段）

- **仅建模**：用户已提供需求规格说明书 → 直接从阶段二开始，产出 `yaml/` 七模型。
- **仅构建**：用户已提供七模型 YAML → 直接从阶段三开始（复制 techbase → code-app 并实现）。
- **重确认需求**：已产出需求文档但有修订 → 回到对应阶段补确认。

## 四、固定输出约定（技能级，仅「业务域」为参数）

| 产物 | 路径 / 命名 |
|---|---|
| 需求文档 | `<业务域>-需求规格说明书-V9.md`（项目根） |
| 本体模型 | `yaml/`（7 yaml + manifest.json） |
| 业务系统 | `code-app/` |
| 技术底座来源 | 技能内置 `techbase/`（运行时复制到 code-app） |

> 若用户显式要求其他路径/命名，以用户指定为准；否则一律采用上表。

## 五、关键纪律（不可违反）

1. **人工确认不可替代**：阶段一每个阶段必须硬暂停等人确认；附录 B 有 `[待确认]` 则文档不得标记完整。
2. **模型是唯一语义来源**：代码 / 表 / 接口 / 菜单 / 权限 / 流程 / 规则全部可回溯到某个本体模型元素，禁止"模型一套、代码一套"。
3. **底座不动**：扩展只在 `code-app/` 内，techbase/code-paas 是只读基线，不就地改。
4. **严格对齐四份规范**：开发全程遵守《本体模型业务功能开发指导书》《AI 原生应用技术架构设计文档》《UI-UE 界面设计规范》《ontology_modeling_framework_v9》的强制条款（5 默认字段、跳选框、双按钮、AI 只读、逻辑删除 `flag=0`、状态机）。
5. **AI 对话强制**：阶段三必须实现右侧 AI 对话框（含只读安全边界）。
6. **事务与联动边界**：一个行为只改一个聚合（聚合内主从同事务）；跨聚合靠 `syncTriggers` 或流程编排。

## 六、参考资源索引

- 方法论文档（5 份）：`references/`
  - `AI需求探索与确认提示词V9.0.md`（含《软件需求编写规范 V9.0》全文）
  - `ontology_modeling_framework_v9.md`
  - `本体模型业务功能开发指导书.md`
  - `AI 原生应用技术架构设计文档.md`
  - `UI-UE界面设计规范.md`
- 黄金范例（仅文档 + yaml）：`reference-example/`（销售合同执行管理跑通实物，对照参考）
- 技术底座（code-paas 干净源码 + requirements.txt + README）：`techbase/`

## 七、运行说明（给用户）

- 后端：`cd code-app/backend && pip install -r requirements.txt && python app.py`（默认 http://localhost:5000，首次启动自动建库+种子）
- 前端开发：`cd code-app/frontend && npm install && npm run dev`（http://localhost:5173）
- 前端生产：`npm run build` 后由 Flask 统一托管，访问 http://localhost:5000
- 默认账号：admin/admin123（管理员，全部权限）；详见 `techbase/README.md`
