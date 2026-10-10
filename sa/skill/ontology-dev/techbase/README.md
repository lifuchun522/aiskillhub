# 客户管理技术底座（code-paas）

基于《系统管理 + 流程引擎需求规格说明书》实现的可运行技术空框架，严格遵循《AI 原生应用技术架构设计文档》与《UI-UE 界面设计规范》。

本项目用两个完整示例功能验证技术底座能力：

- **客户申请**：带「暂存 / 提交」双按钮的单表录入，提交后启动客户审批流；
- **客户查询**：查询列表（查询条件 + 结果表格 + 分页）。

客户审批流包含两个严格串行的审批节点（两个独立角色）：

```
开始 → 客户经理审批（CUSTOMER_MANAGER）→ 部门总经理审批（DEPT_GENERAL_MANAGER）→ 通过结束
                                    └（任一节点驳回）→ 驳回结束
```

> 说明：右侧 AI 对话区本期不实现（无实际业务功能），仅保留布局占位。

---

## 1. 技术栈

| 层 | 选型 |
|---|---|
| 数据库 | SQLite 3（WAL 模式） |
| 后端 | Python 3.10+ + Flask（单体分层，`sqlite3` 直连，不用 ORM） |
| 认证 | PyJWT（自定义装饰器） |
| 配置 | PyYAML + python-dotenv |
| 前端 | React 18 + TypeScript + Vite |
| 样式 | Vanilla CSS（9pt 基准、标签右对齐控件左对齐） |
| 图标/图表 | Lucide React / ECharts |
| 流程设计器 | react-flow |

## 2. 目录结构

```
code-paas/
├── models/                     # 客户示例域本体模型 YAML（M1/M2/M5/M6/MU + manifest）
├── backend/
│   ├── app.py                  # Flask 入口（含前端静态托管）
│   ├── config.yaml             # 应用配置（端口/数据库/JWT/默认账号/AI 占位）
│   ├── schema.sql              # 数据库结构（系统表 + 流程表 + 业务表）
│   ├── seed.py                 # 初始化种子数据（角色/权限/资源/用户/流程定义）
│   ├── db.py                   # sqlite3 数据访问（不使用 ORM）
│   ├── config/settings.py      # 配置加载
│   ├── ontology/registry.py    # 运行时语义注册表（加载 YAML）
│   ├── engine/flow_engine.py   # 工作流引擎（start/approve/reject/return）
│   ├── services/               # 业务服务层（auth/用户/角色/权限/资源/流程/工作台/客户）
│   ├── api/                    # REST 接口层
│   └── utils/                  # JWT / 密码 / 统一响应
└── frontend/
    └── src/
        ├── api/                # 接口封装
        ├── stores/             # 用户状态（token/权限/菜单）
        ├── layouts/            # 三栏布局（侧边栏 + 多标签工作区 + AI 占位）
        ├── pages/              # 客户 / 工作台 / 流程 / 系统管理
        ├── router/             # 路由 + 登录守卫
        ├── styles/             # 设计系统 CSS（UI-UE 规范）
        └── utils/              # 图标 / 状态标签
```

## 3. 快速启动

### 3.1 后端

```bash
cd backend
pip install -r requirements.txt
python app.py            # 默认 http://localhost:5000
```

首次启动自动建库并写入种子数据（角色、权限、资源、用户、客户审批流定义）。

### 3.2 前端

开发模式（独立启动，代理 `/api` 到后端）：

```bash
cd frontend
npm install
npm run dev              # http://localhost:5173
```

生产模式（构建后由 Flask 统一托管）：

```bash
cd frontend
npm run build            # 产物输出到 frontend/dist
```

构建后直接访问 `http://localhost:5000` 即可（后端自动托管前端静态资源，SPA 路由回退已处理）。

## 4. 默认账号

| 账号 | 密码 | 角色 | 说明 |
|---|---|---|---|
| `admin` | `admin123` | 系统管理员 | 全部功能权限 |
| `sales` | `123456` | 业务人员 | 客户申请 / 查询 |
| `cmanager` | `123456` | 客户经理 | 审批第一节点 |
| `gm` | `123456` | 部门总经理 | 审批第二节点 |

## 5. 验证示例流程（客户申请审批）

1. 用 `sales` 登录 → 客户管理 → 客户申请，填写后点「暂存」，再点「提交」；
2. 用 `cmanager` 登录 → 审批中心 → 我的待办 → 处理（通过/驳回）；
3. 通过后，用 `gm` 登录 → 我的待办 → 处理（通过）；
4. 用 `sales` 登录 → 我的申请 查看进度；客户查询 查看已通过的客户。

## 6. 功能清单

- **系统管理**：用户 / 角色（含继承）/ 权限（行为级 + 数据范围）/ 资源（菜单·按钮·接口），RBAC 权限校验。
- **流程管理**：流程定义（react-flow 拖拽设计器，8 种活动类型）、发布、流程实例、任务（转办/催办）。
- **工作台**：我的待办（通过/驳回/退回）、我的已办、我的申请（撤回）。
- **示例业务**：客户申请（暂存/提交）、客户查询（分页模糊查询）。

## 7. 配置说明

所有可变项集中在 `backend/config.yaml`（禁止硬编码）：

- `app.port` / `app.database`：服务端口与 SQLite 路径；
- `auth.jwt_secret` / `auth.jwt_expires_hours`：JWT 密钥与有效期；
- `auth.default_admin` / `auth.default_admin_password`：默认管理员；
- `ai.*`：AI 对话配置占位（本期不实现，`ai.enabled=false`）。

## 8. 说明

- 后端 `smoke_test.py` 为端到端自测脚本，可运行 `python smoke_test.py` 验证登录、客户申请提交、两级审批、驳回、撤回等链路。
