# 提示词：基于七模型本体生成 UI 调用链追踪工作台

> 版本：V9  
> 用途：交给建模或前端 Agent 执行，产出可复用生成程序与自包含单文件 HTML。  
> 适用目录：本提示词所在目录，或具备相同七模型结构的其他 YAML 目录。

---

## 1. 你的角色

你是一名同时熟悉本体建模、业务分析、数据可视化和前端工程的高级开发者。

你的任务不是制作静态模型清单，而是构建一个可交互的“UI 调用链追踪工作台”：以界面和操作为入口，沿 YAML 中已经声明的引用逐级穿透，使使用者能够回答以下问题：

1. 一个界面有哪些元素和操作？
2. 执行某个操作会调用哪个行为？
3. 该行为属于哪个业务对象？
4. 行为应用了哪些规则，需要哪些权限？
5. 行为关联哪个查询报表，参与哪些业务流程？
6. 哪些角色拥有相关权限，哪些参与者承担这些角色？

整个工作台必须数据驱动。业务 ID、名称、数量和关系均从 YAML 读取，不把示例数据写死在 Python、HTML、CSS 或 JavaScript 中。

---

## 2. 目标产物

在 YAML 目录中生成以下文件：

1. `generate_ui_workbench.py`
   - Python 3 可执行程序；
   - 读取本节规定的 YAML；
   - 归一化数据后注入 HTML 模板；
   - 可对其他同结构模型目录复用。
2. `contract-management-ui-callchain.html`
   - UTF-8；
   - 单文件、自包含；
   - CSS、JavaScript 和归一化 JSON 全部内嵌；
   - 不发起外部网络请求；
   - 可直接双击打开。

命令行接口：

```bash
python generate_ui_workbench.py <yaml_dir> <output_html> [--pretty]
```

参数约定：

- `yaml_dir` 缺省为生成程序所在目录；
- `output_html` 缺省为同目录下的 `contract-management-ui-callchain.html`；
- `--pretty` 用于内嵌格式化 JSON，便于调试；
- 优先使用 PyYAML；依赖不可用时必须输出清晰提示，或使用能够完整解析本项目 YAML 语法的内置兼容解析器。

---

## 3. 唯一数据源与模型边界

先读取 `manifest.json`，以其中的 `model_files` 为模型范围。当前范围应包含且只处理以下七份模型：

| 模型 | 文件 | 权威顶层结构 |
|---|---|---|
| M1 对象模型 | `m1-object-model.yaml` | `aggregates[]`、`data_dictionaries[]`、`aggregate_associations[]` |
| M2 行为模型 | `m2-behavior-model.yaml` | `behaviors[]` |
| M3 规则模型 | `m3-rule-model.yaml` | `rules[]`；兼容存在时的 `ref_rules[]`、`inv_rules[]` |
| M5 主体模型 | `m5-actor-model.yaml` | `actors[]`、`roles[]`、`permissions[]` |
| M6 流程模型 | `m6-flow-model.yaml` | `flows[]` |
| M7 查询报表模型 | `m7-report-model.yaml` | `query_reports[]` |
| MU 界面模型 | `mu-ui-model.yaml` | `application`、`screens[]` |

执行纪律：

- YAML 是业务事实源，提示词中的示意名称不是事实源。
- 只展示 YAML 能够证明的节点和关系。
- 对缺失字段显示 `—` 或跳过对应区块。
- 对不存在的引用标记为“悬空引用”，使用灰色弱化样式，不中断生成。
- 不依据字段名、英文别名或常识补造 YAML 未声明的业务资源。
- 换用另一套同结构 YAML 时，无需修改程序代码。

---

## 4. 当前 YAML 契约

实现前必须先探查实际 YAML 键名。以下契约用于统一读取和归一化，不得用旧示例结构覆盖当前文件。

### 4.1 MU 界面模型

`screens[]` 中重点读取：

- `screenId`、`name`、`screenType`、`layout`；
- `elements[]`：`id`、`type`、`label`、`io`、`required`、`dataBinding`、`dataSource`；
- `actions[]`：`actionId`、`name`、`actionType`、`behaviorRef`、`permissionRef`。

`application.menus[]` 用于展示菜单层次及菜单到界面的入口关系。

界面元素 ID 和操作 ID 只保证在所属界面内有效。内部节点键必须包含父界面，例如：

```text
element:<screenId>:<elementId>
action:<screenId>:<actionId>
```

不得把多个界面中同名的 `btnLogout`、`actSubmit` 等局部节点覆盖为一个节点。

### 4.2 M1 对象模型

`aggregates[]` 中重点读取：

- `id`、`name`、`alias`、`aggregateType`、`description`；
- `lifecycle[]`、`tags[]`；
- `attributes[]` 及属性中的字典引用、聚合引用、枚举值和约束。

`data_dictionaries[]` 展示字典定义和字典项。  
`aggregate_associations[]` 展示来源聚合、目标聚合、关系类型、关联字段和说明。

### 4.3 M2 行为模型

`behaviors[]` 中重点读取：

- `id`、`name`、`ownerEntity`；
- `behaviorType`、`triggerType`；
- `preconditions[]`、`postconditions[]`；
- `appliedRules[]`、`requiredPermissions[]`；
- `syncTriggers[]`、`queryReportRef`。

### 4.4 M3 规则模型

规则节点重点读取：

- `id`、`name`、`ruleType`、`description`；
- `inputParams[]`、`outputType`、`expression`；
- `reusedBy[]`、`version`。

不同规则集合归一化到一个 `rules[]`，同时保留来源集合标识 `ruleFamily`。

### 4.5 M5 主体模型

- `actors[]`：`actorId`、`name`、`actorType`、`roles[]`；
- `roles[]`：`roleId`、`name`、`permissions[]`；
- `permissions[]`：`permissionId`、`targetType`、`targetRef`、`dataScope`、`abacCondition`。

角色与权限必须支持双向追踪：角色可查看其权限，权限可查看持有该权限的角色。

### 4.6 M6 流程模型

`flows[]` 中重点读取：

- `id`、`name`、`flowType`、`description`；
- `businessObjectRefs[]`、`roleRefs[]`；
- `startActivity`、`endActivities[]`；
- `activities[]`。

流程活动重点读取：

- `activityId`、`name`、`activityType`；
- `behaviorRef`、`roleRef`、`screenRef`；
- `subFlowRef`、`ruleRef`、`nextActivities[]`；
- 分支中的名称、条件和目标活动。

### 4.7 M7 查询报表模型

`query_reports[]` 中重点读取：

- `id`、`name`、`alias`、`objectType`、`description`；
- `behaviorRef`、`sourceObjects[]`；
- `parameters[]`、`resultColumns[]`、`joins[]`；
- `referenceSql`、`uiScreenRefs[]`、导出配置。

SQL 仅作为只读代码块展示，不在浏览器中执行。

---

## 5. 归一化数据

Python 先把七份模型归一化为一个 JSON，再注入 HTML。推荐结构：

```json
{
  "meta": {
    "domain": "...",
    "application": "...",
    "modelFiles": [],
    "missingFiles": []
  },
  "screens": [],
  "menus": [],
  "aggregates": [],
  "dictionaries": [],
  "associations": [],
  "behaviors": [],
  "rules": [],
  "actors": [],
  "roles": [],
  "permissions": [],
  "flows": [],
  "reports": []
}
```

注入 JSON 时使用 `ensure_ascii=False`，并转义可能提前结束 `<script>` 的文本片段。任何 YAML 内容都必须经过 HTML 转义后再进入 DOM。

建立两个索引：

1. `nodeKey -> { type, object, parentKey }`：负责树定位和详情渲染；
2. `businessId -> nodeKey[]`：负责跨模型引用穿透，并允许一个业务 ID 对应多个界面局部节点。

---

## 6. 真实调用链

工作台的主链路必须来自以下引用：

```text
界面 screen
  → 操作 action.behaviorRef
  → 行为 behavior.ownerEntity
  → 业务对象 aggregate
  → 行为 behavior.appliedRules
  → 规则 rule
  → 行为 behavior.requiredPermissions
  → 权限 permission
  → 角色 role.permissions
  → 参与者 actor.roles
  → 查询报表 behavior.queryReportRef / report.behaviorRef
  → 业务流程 flow.activities[].behaviorRef
```

同时生成反向关系：

- 对象 → 归属该对象的行为；
- 对象 → 以该对象为来源的报表；
- 行为 → 引用该行为的界面操作；
- 行为 → 包含该行为的流程活动；
- 规则 → 应用或复用该规则的行为；
- 权限 → 持有该权限的角色；
- 角色 → 承担该角色的参与者；
- 报表 → 绑定行为、来源对象和界面入口；
- 对象关联 → 来源对象与目标对象。

所有反向关系都在加载时从正向引用计算，不修改 YAML。

---

## 7. 页面布局

采用左右分栏的现代暗色工作台：

```text
┌────────────────────────────────────────────────────────────────────┐
│ 标题 │ 全局搜索 Ctrl+K │ 统计徽标 │ 展开全部 │ 折叠全部             │
├────────────────────────┬───────────────────────────────────────────┤
│ 左侧模型树             │ 右侧详情                                 │
│                        │                                           │
│ MU 界面模型            │ 面包屑 / 类型徽标 / 名称 / ID / 复制      │
│ M1 对象模型            │ 基本信息卡片                              │
│ M2 行为模型            │ 引用链路                                  │
│ M3 规则模型            │ 字段表、活动表、结果列表                  │
│ M5 主体与权限          │ 现代界面原型 / 原始 ASCII                 │
│ M6 流程模型            │                                           │
│ M7 查询报表模型        │                                           │
│ 字典 / 对象关联索引    │                                           │
└────────────────────────┴───────────────────────────────────────────┘
```

桌面端左栏建议宽度为 340～380px。右栏独立滚动。窄屏允许缩小左栏，但不得隐藏核心树和详情。

---

## 8. 左侧模型树

树节点采用懒展开或按需构建，至少提供以下层次。

### 8.1 MU 界面模型

```text
界面
├─ 界面详情与原型
├─ 界面元素
│  └─ 元素 → dataBinding 所属对象 / dataSource 报表
└─ 操作
   └─ 操作 → 行为 → 对象 / 规则 / 权限 / 报表 / 流程
```

### 8.2 M1 对象模型

```text
业务对象
├─ 属性
├─ 生命周期
├─ 行为
├─ 来源报表
└─ 对象关联
```

### 8.3 M2、M3、M5、M6、M7

- 行为：按所属对象分组，并提供扁平索引；
- 规则：展示规则类型、表达式和复用方；
- 主体：角色、参与者、权限分别可直接定位；
- 流程：流程下展开活动，活动可跳转到行为、角色、界面、子流程和规则；
- 查询报表：可跳转到绑定行为、来源对象和界面入口。

每个节点显示类型徽标、中文名称和英文 ID。树展开必须有防环集合，防环键使用稳定 `nodeKey`。

---

## 9. 右侧详情

| 节点类型 | 必须展示的内容 |
|---|---|
| screen | 类型、现代原型、原始 ASCII、元素表、操作表 |
| element | 控件类型、标签、I/O、必填、数据绑定、数据源 |
| action | 所属界面、操作类型、行为、权限、横向调用链 |
| aggregate | 基本信息、生命周期、属性、行为、报表、对象关联 |
| behavior | 所属对象、类型、前后置条件、规则、权限、报表、界面入口、参与流程 |
| rule | 类型、说明、输入参数、输出类型、表达式、复用方、版本 |
| actor | 类型、承担角色 |
| role | 权限、关联参与者、参与流程 |
| permission | 授权目标、数据范围、ABAC 条件、持有角色 |
| flow | 类型、对象、角色、起止活动、活动链和分支明细 |
| report | 类型、绑定行为、来源对象、参数、结果列、只读 SQL、界面入口 |
| dictionary | 字典编码、名称、字典项 |
| association | 来源对象、目标对象、关系类型、关联字段、说明 |

详情中的业务 ID 必须可点击。点击后展开左树中的对应路径、选中目标节点、滚动到可见位置并更新面包屑。

---

## 10. ASCII 原型现代化渲染

点击界面节点时，优先读取 `screen.layout`。不要只把 ASCII 文本平铺为 `<pre>`；实现解析层和渲染层，同时保留原文切换。

### 10.1 解析层

实现 `parseAsciiRows(screen)`：

1. 按行读取 `layout`；
2. 清理边框字符和多余空白；
3. 识别 `[]`、`()`、`{}` 中的控件标记及 `@控件ID`；
4. 用 `screen.elements[]` 补全控件类型、标签和绑定；
5. 将内容归类为标题、分区、表单行、按钮行、表格或说明文本；
6. 未识别标记降级为通用只读输入框；
7. 无 `layout` 时根据 `elements[]` 生成通用界面。

### 10.2 渲染层

实现 `renderModernUI(screen)`，至少覆盖：

- 窗体标题栏、窗口控制点、用户 Chip；
- TEXTBOX / TEXTAREA：圆角输入框；
- COMBO / POPUP_SELECT：带下拉提示的选择框；
- DATEPICKER：日期输入；
- CHECKBOX / RADIO：现代选择控件；
- BUTTON：主次按钮，提交、保存、查询、批准等主要操作高亮；
- GRID / TABLE：带表头的样例表格；
- REPORT_VIEWER：白底报表预览容器；
- 分区标题和间隔；
- 未知控件的安全降级。

原型区提供：

- “现代渲染 / 原始 ASCII”切换；
- 字号放大和缩小；
- 原始内容完整保留；
- 单个界面渲染失败时显示局部错误，不影响整个工作台。

---

## 11. 必做交互

1. 全局搜索：
   - 支持 `Ctrl+K` 聚焦；
   - 匹配中文名称、英文 ID、节点类型和节点内容；
   - 最多显示合理数量的结果；
   - 点击结果后定位树节点并渲染详情。
2. 树控制：
   - 根节点独立展开和折叠；
   - 提供“展开全部”和“折叠全部”；
   - 当前节点高亮。
3. 引用穿透：
   - 详情内所有有效引用均可点击；
   - 悬空引用显示灰色且不可点击；
   - 重复局部 ID 不串位。
4. 面包屑：
   - 至少显示领域、节点类型和当前节点；
   - 可选支持历史回跳。
5. ID 复制：
   - 优先使用 Clipboard API；
   - API 不可用时提供安全降级。
6. 统计徽标：
   - 屏幕、聚合、行为、规则、角色、权限、流程、报表数量；
   - 数值从归一化数据实时计算。
7. 横向链路：
   - 操作、行为和流程详情中用卡片加箭头展示关系；
   - 每个有效步骤均可点击穿透。

---

## 12. 视觉规范

采用现代深色 SaaS 仪表盘风格：

- 主背景：深灰蓝；
- 面板：分层深色卡片；
- 主操作色：蓝色；
- 行为：绿色；
- 规则：琥珀色；
- 流程：青色；
- 对象：紫色；
- 权限与角色：粉紫色；
- 查询报表：蓝色；
- 文本：高对比白色，次要信息使用灰蓝色；
- 卡片使用适度圆角、细边框和轻阴影；
- 中文为主，保留英文 ID；
- 不使用 emoji，类型标识使用文字徽标或简单几何符号。

必须保证长 ID、长表达式、SQL 和表格不会撑破布局。所有动态内容先 HTML 转义。

---

## 13. 容错与安全

- 单个 YAML 文件缺失：记录在 `meta.missingFiles`，其对应区域显示空状态；
- YAML 语法错误：报告文件名和可定位的错误信息，停止写出错误 HTML；
- 字段缺失：显示 `—` 或省略无意义的空区块；
- 引用不存在：标记悬空引用，页面继续工作；
- 引用环：使用 visited set 防止递归无限展开；
- 重复业务 ID：索引保存为数组，不静默覆盖；
- 重复界面局部 ID：使用父界面限定键；
- 动态文本：统一经过转义函数；
- SQL：只读显示；
- HTML：不加载 CDN、远程字体、远程脚本或统计代码。

---

## 14. 执行步骤

严格按以下顺序执行：

1. 读取 `manifest.json` 和七份 YAML，记录实际顶层键与数量。
2. 检查模型间引用字段，建立正向引用表。
3. 计算反向引用，识别悬空引用与重复局部 ID。
4. 实现归一化函数，输出可序列化 JSON。
5. 实现单文件 HTML 模板和统一节点索引。
6. 实现左侧树、右侧分类详情和引用穿透。
7. 实现 ASCII 解析与现代原型渲染。
8. 实现搜索、面包屑、复制、统计和展开折叠。
9. 生成 HTML。
10. 执行语法、数据、浏览器和交互验收；发现问题后修复并重新生成。

每一步完成标准都是“产物可被下一步直接消费且没有未解释的错误”，不能以只创建空壳函数或静态占位页面视为完成。

---

## 15. 验收标准

### 15.1 生成验收

在生成程序所在目录执行：

```bash
python generate_ui_workbench.py --pretty
```

完成条件：

- 命令退出码为 0；
- 生成 UTF-8 HTML；
- HTML 中没有外部资源 URL；
- 重新指定输入目录和输出文件时无需修改代码。

### 15.2 当前参考数据基线

使用本目录当前 YAML 时，归一化数量应为：

| 类型 | 数量 |
|---|---:|
| 屏幕 | 15 |
| 聚合 | 8 |
| 数据字典 | 7 |
| 对象关联 | 8 |
| 行为 | 25 |
| 规则 | 13 |
| 参与者 | 6 |
| 角色 | 6 |
| 权限 | 27 |
| 流程 | 4 |
| 查询报表 | 5 |

数量不一致时，先判断是 YAML 已更新还是解析丢失。不得为了通过基线把数量写死。

### 15.3 静态验收

- 用 JavaScript 语法检查器验证内嵌脚本；
- 检查 JSON 注入未破坏 `<script>`；
- 检查旧项目名称、示例 ID 和硬编码数量没有进入通用逻辑；
- 检查所有动态文本均经过转义。

### 15.4 浏览器验收

在真实 Chromium 浏览器中打开 HTML，至少验证：

1. 欢迎页和统计徽标正常；
2. 七个模型区域均可展开；
3. 任取一个界面，可看到现代原型、原始 ASCII、元素和操作；
4. 任取一个操作，可穿透到行为、对象、规则和权限；
5. 任取一个查询行为，可穿透到查询报表；
6. 任取一个流程，可查看活动并跳转到行为或角色；
7. 搜索中文名称和英文 ID 均有结果；
8. 展开全部、折叠全部、复制 ID 和原型切换正常；
9. 浏览器控制台没有未处理异常；
10. 断网状态下页面功能不受影响。

### 15.5 数据完整性验收

完成以下一致性检查并输出摘要：

- 树中可定位叶节点数等于节点索引中的可视节点数；
- 每个 `behaviorRef`、`ownerEntity`、规则引用、权限引用和报表引用都有解析结果或悬空标记；
- 每个角色权限都能反向找到角色；
- 每个流程活动引用都能定位或明确标记悬空；
- 同名界面局部节点拥有不同稳定键；
- 详情点击不会跳到错误界面下的同名节点。

---

## 16. 最终回复格式

完成后只报告可验证结果：

```text
已生成：
- <generate_ui_workbench.py 的路径>
- <HTML 的路径>

模型统计：屏幕 N / 聚合 N / 行为 N / 规则 N / 角色 N / 权限 N / 流程 N / 查询报表 N
验收：生成通过 / JavaScript 语法通过 / 浏览器加载通过 / 核心交互通过
说明：<缺失文件、悬空引用或兼容处理；没有则写“无”>
```

不要只说“已完成”。必须给出文件路径、真实统计和实际执行过的验收结果。
