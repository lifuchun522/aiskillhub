---
name: cleanc
description: 磁盘可清理空间分析（C 盘为主）。只读扫描体积 → 按授权清单给出可清理目录 → 生成/启动本地管理网页，一键清理低风险项、解释中风险项的清理后果。触发词：清理C盘、C盘满了、磁盘空间不足、磁盘瘦身、扫描可清理目录、clean disk、磁盘占用分析、清理缓存目录、释放C盘空间。
---

# cleanc — 磁盘可清理目录扫描与安全清理

> 版本 1.1.0。Windows 专有。只读扫描 → 授权清单 → 本地管理网页（低风险一键清 / 中风险只解释后果）。
> 1.1.0 新增：`*.vhdx` 保护、按文件年龄清理（`--min-age-hours`）、增长归因（`growth`）、junction 去重。
> 仓库地址：<https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/cleanc>

## 这个 skill 解决什么

用户喊"C 盘满了 / 帮我清一下 C 盘"时，走同一套流程：

1. **只读**找体积（绝不先删）
2. 按 **授权清单** 给出可清理目录，分级（low 可一键清 / mid 只解释后果）
3. 产出**本地管理网页**：目录 + 清理前 MB + 占比 + 清理按钮
4. 真正的删除只发生在两类时机：用户在网页上点"清理"，或用户显式执行 CLI 的 `clean --apply`

**硬约束：不碰操作系统文件。** Windows / Program Files / ProgramData / Users 根 / 盘根 /
System Volume Information / Recovery / $RECYCLE.BIN 全部在 `NO_GO` 黑名单里，代码层面拒绝，
不是靠"注意别删"的口头约定。

## 目录结构

```
cleanc/
├── SKILL.md
├── README.md                  # 仓库使用说明：安装 / 快速开始 / 踩坑 / 验证
├── scripts/
│   ├── server.py              # 扫描 + 清理 + HTTP API + 本地管理页（纯标准库）
│   ├── targets.json           # 授权清单：风险等级 / 影响说明 / authorized 开关
│   ├── index.html             # 管理网页（server.py 内置提供）
│   ├── selftest.py            # 端到端自检 43 断言，全 dry-run
│   ├── autoclean.bat          # 每日定时清理入口：只清 Temp 中 24h 前的文件
│   └── 启动cleanc服务.bat      # 推荐启动方式：由用户自己的会话拉起服务
├── tests/
│   └── verify_browser.py      # 可选：真实浏览器走一遍阈值过滤 + 清理链路（需 playwright）
└── references/
    ├── safety.md              # 安全边界与逐条允许/禁止清单
    └── usage-windows.md       # 完整使用文档（Windows）
```

无第三方依赖，直接用系统/托管 Python 3 运行。**仅支持 Windows**（非 Windows 启动即退出）。

## 工作流

### 第 1 步：只读盘点（必须）

```bash
python <skill>/scripts/server.py scan --json /tmp/cleanc_scan.json
```

输出：C 盘可用 MB、候选清单（体积 / 风险 / 是否授权 / 路径）。
这一步只读，不做任何修改。

需要发现**清单外**的新目标时，加 `--root` 统计某目录下的一级子目录体积（仍然只读）：

```bash
python <skill>/scripts/server.py scan --root "C:/" --top 25
```

读到的 TOP 目录用于判断"有没有新的缓存/日志目录值得加进 `targets.json`"。
**不要在没看体积的情况下凭猜测往清单里加路径。**

### 第 2 步：交付管理网页

**首选**：把 `scripts/启动cleanc服务.bat` 复制给用户，让他双击启动。
由用户自己的 Windows 会话拉起的服务，清理不受代理沙箱的批量删除保护限制，页面按钮才能真正删掉。

**代理内验证时**用命令行启动（此时沙箱策略生效，见"常见坑"第 1 条）：

```bash
python <skill>/scripts/server.py serve --port 8848
```

然后 `present_files` 打开 `http://127.0.0.1:8848/`。**只给 URL，不要再把 index.html 当文件一起 present** —— 那会生成一份静态副本，该副本没有后端，用户在那个页面上点清理不会有任何反应（`/api/*` 返回 404）。

页面内容：
- 顶部概览：C 盘可用 / 低风险可一键清理 / 中风险合计 / 系统目录项数 / **执行权限**
- **低风险表格**：目录、类别、清理前 MB、占比、文件数、**执行指令**、**清理按钮**（只对授权目录渲染）
- **低风险·需人工处理**：回收站、Windows 日志等，只给替代做法，不给按钮
- **中风险表格**：目录、清理前 MB、占比、**清理后的影响后果**，**默认只列 > 500MB 的项**，阈值可在标题右侧输入框调整
- **服务端执行日志**：实时轮询 `/api/job`，逐目录输出 目录 / 执行指令 / 清理前MB / 清理后MB / 状态 / 失败处置命令

按钮行为：点击 → 弹确认框（绝对路径、体积、指令、警告）→「确认清理」真删 / 「预演」只看数字。
确认后弹窗**立即关闭**并出现「执行中」标记，日志逐行刷新（含已用时计时）。服务端每次都会重新校验授权与 NO_GO，前端传什么路径都不越权。

### 第 3 步：CLI 清理（可选，替代网页）

```bash
python <skill>/scripts/server.py clean --ids __all_low__            # dry-run
python <skill>/scripts/server.py clean --ids __all_low__ --apply    # 真删，需输入 yes
python <skill>/scripts/server.py clean --ids pip-cache,local-temp --apply --yes
python <skill>/scripts/server.py clean --ids local-temp --apply --yes --min-age-hours 24
```

`--ids` 取 `scan` 输出里的 id，`__all_low__` 代表全部授权低风险项。
`--min-age-hours N` 只删修改时间早于 N 小时的文件，定时任务必须带上它。

### 第 3.5 步：治"清了又长"（**C 盘反复满的必做项**）

清理只能治标，回涨通常是四类固定源头，先定位再谈清理：

```bash
python <skill>/scripts/server.py scan     # 第一次，落体积快照
# …隔几小时/一两天…
python <skill>/scripts/server.py scan     # 第二次
python <skill>/scripts/server.py growth   # 谁在长、长了多少、可用空间怎么变
```

| 反复出现的增长源 | 判据 | 治本做法 |
|---|---|---|
| WSL2 `swap.vhdx`（常在 `%TEMP%\<GUID>\`，可达 8 GB） | Temp 体积里有个 8 GB 的 `*.vhdx` | `~/.wslconfig` 设 `swap=2GB`、`swapFile=D://wsl//swap.vhdx`、`[experimental] autoMemoryReclaim=gradual` + `sparseVhd=true`，然后 `wsl --shutdown` |
| Docker `docker_data.vhdx`（只增不减） | `%LOCAL%/Docker/wsl/disk/*.vhdx` 数十 GB | `docker system df` → `docker builder prune -af`；或把磁盘镜像位置改到非系统盘 |
| 自动化工具 Temp 残留（`playwright-java-*`、`wb-*` 等，每次会话 55–101 MB） | Temp 下成百个同前缀目录 | 每日 `autoclean.bat` + `--min-age-hours 24` |
| 编辑器状态库 / 版本目录（如 `state.vscdb` 数 GB、旧版本各 150 MB） | 单文件特大 + 同前缀多版本 | 关程序后 `VACUUM`；旧版本目录只留最新 1–2 个 |

**不要**把 8 GB 的 `swap.vhdx` 当垃圾直接删了报"释放 8 GB"——下次 WSL 起来会重写满，用户第二天又满，
而且删除运行中的 vhdx 会波及发行版。正确顺序：先改配置限制上限并把文件挪到非系统盘，再 `wsl --shutdown` 收尾。

### 第 4 步：汇报

至少给：清理前/后合计 MB、节约 MB（附 GB）、C 盘可用前后、被拒绝的项及原因、日志文件路径，
以及每个状态为 `BLOCKED` / `TIMEOUT` / `PARTIAL` / `FAIL` 的项该怎么处理（照抄日志里的命令）。

日志落在 `scripts/logs/`：
- `clean_<任务号>.log` / `dryrun_<任务号>.log` — 主日志，每目录四行：`▶ 目录：` / `执行指令：` / `清理前：` / `清理后：`
- `clean_<任务号>.log.manifest.txt` — 删除前记录每个将被删除的文件（`字节数<TAB>绝对路径`）

## 状态取值（判定前必须复核）

| 状态 | 含义 |
|---|---|
| `OK` | 删除调用成功**且删后复查体积确实下降** |
| `DRY-RUN` | 预演，未删除 |
| `PARTIAL` | 部分文件被占用/无权限，其余已删除 |
| `FAIL` | 整体失败（目录不可列出、单文件删除失败） |
| `BLOCKED(删除未生效)` | 调用成功返回但复查体积未降 —— 被批量删除保护静默忽略 |
| `TIMEOUT(批量删除被拦截)` | 调用超过看门狗时限未返回 |
| `SKIP(安全拦截)` | 命中 NO_GO 或不在本次授权集合内 |
| `OK(部分保留)` | 删了该删的，但有 `*.vhdx` 或未达 `--min-age-hours` 的文件被主动保留 |
| `SKIP(虚拟磁盘)` | 目标本身是 `*.vhdx` / `*.vhd`，代码级拒绝删除 |

**删除后必须重新测量体积（`path_size`）才能判 OK。** 只凭"调用没抛异常"就报 OK，
会在被策略静默忽略时给用户一个假绿的结果——这是本项目踩过的真实坑。

## 授权模型（改清单前必读）

`targets.json` 每条：

| 字段 | 含义 |
|---|---|
| `id` | 稳定标识，CLI 的 `--ids` 用它 |
| `pattern` | 路径，支持 `%HOME%` `%LOCAL%` `%ROAM%` 占位符与 `*` 通配 |
| `risk` | `low` 可清 / `mid` 只解释后果 |
| `authorized` | **只有 `true` 且 `risk=low` 才允许被删除** |
| `impact` | 清理后的影响后果（网页直接展示这行） |
| `hint` | 等效命令或更安全的替代做法 |
| `mode` | `clear` 清空内容保留目录 / `manual` 人工处理 |

新增条目一律先 `authorized: false`，把 `impact` / `hint` 写清楚，让用户点开确认后再改 `true`。
`impact` 必须写**后果**（会丢什么、多久恢复、能不能回滚），不写"建议清理"。

## 安全红线（完整版见 `references/safety.md`）

1. **先扫后删**，扫描阶段只读。没有扫描数据就不许动删除。
2. **只清空内容，保留目录本身**，避免程序因缺目录而报错。
3. **删除前写 manifest**（被删文件清单+体积）到 logs/，便于追溯。
4. **不碰**：盘根、Windows、Program Files*、ProgramData、Users 根、
   System Volume Information、Recovery、$RECYCLE.BIN、任何系统文件（`hiberfil.sys` / `WinSxS` 只给命令）。
5. **个人文件不删**：Desktop / Documents / Downloads / Pictures / Videos / 各项目源码目录
   一律不进清单。清磁盘 ≠ 清用户文件。
6. `.workbuddy` **目录本身不删**（项目数据）。其 `logs`/`traces` 子目录在清单中标记
   `authorized: false`，建议退出 WorkBuddy 后人工清理。
7. 正在运行的程序占用的文件自动跳过并计入 `PARTIAL`，不强行删除、不中断流程。
8. 删除**不进回收站**。缓存类目标不可恢复但可由程序重建——这一点必须在交付时告知用户。
9. 涉及注册表、系统服务、驱动、分区、`powercfg`、`DISM` 的操作**只输出命令，不代跑**，
   由用户在管理员终端确认执行。

## 常见坑

### 1. 宿主批量删除保护会让删除静默失效（**最坑，必读**）

代理沙箱带批量删除保护：单个目标文件数超过阈值（默认 50）时，删除的两种表现是——
调用被**静默忽略**（返回成功但文件还在），或调用**挂起**不返回。

- 只凭"没抛异常"就报 OK → 界面报假绿，用户以为清了其实没清。
  必须在删除后重新 `path_size` 复核：`afiles > 0 且 (before - after) < 1MB` → `BLOCKED(删除未生效)`。
- 每个目标都要有看门狗（`min(120s, 20s + 文件数×0.2s)`），否则任务永远不返回，
  页面停在「执行中」，用户感受就是"点了清理没反应"。
- 拦截发生时**不要试图绕过**。正确做法：如实标记状态 + 输出可直接执行的手工命令：
  `Remove-Item -LiteralPath "<path>" -Recurse -Force`（PowerShell）/ `rmdir /s /q "<path>" && mkdir "<path>"`（cmd），
  并提示用户双击 `启动cleanc服务.bat` 让服务在自己的会话中启动。
- 排查线索：服务端 stderr 会出现 `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED] {...}`。
- 实测（2026-10-16）：≤50 文件且未被占用 → 真删成功；≤50 但被运行中程序占用 → `PARTIAL`；
  >50 文件 → `BLOCKED`；由用户自己双击 `启动cleanc服务.bat` 启动的服务不受该策略限制。

### 2. Windows 下 SO_REUSEADDR 会导致双实例抢端口

`HTTPServer.allow_reuse_address` 默认 1，Windows 语义允许第二个进程绑定同一端口，
于是新旧实例同时监听、请求随机落到旧代码上（表现为"改了代码不生效"）。
本项目显式设 `allow_reuse_address = False`，并用在启动失败提示里给出结束旧进程的命令。

### 3. 只给 URL，不要同时 present index.html

同时 present 会生成静态副本页面，用户点那个页面上的按钮不会有任何反应。
页面在连接失败时也应显式报错（`/api/health` 或 `/api/targets` 失败 → 顶部红条 + 提示命令），
而不是静默卡在"扫描中"。

### 4. 不要用 `du` 判断 Windows 目录体积

Git Bash 的 `du` 在大量小文件下极慢。用 `server.py` 内置的 `os.scandir` 遍历，或 PowerShell。

### 5. PowerShell / 控制台中文乱码

写文件用 `-Encoding utf8`；子进程调用 Python 时设 `PYTHONIOENCODING=utf-8`。

### 6. junction / 符号链接会让体积虚高，也会把删除带到别处

Windows 的 reparse point（junction、目录符号链接）在 `os.walk` / `os.scandir` 里**看似普通目录**。
Docker Desktop 就用 junction 把 `DockerRecovery-*` 指向同一份 `docker_data.vhdx`：

- 老口径量 `%LOCAL%/Packages/OpenAI.Codex_*/LocalCache` 得 **85.5 GB**，去重后只有 **0.8 GB**；
- 删除时顺着 junction 走，会删到目标目录里去，属于越权删除。

本项目的处理：`is_reparse()` 用 `st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT` 判定，
统计时**不入栈**、删除时**从 `dirs` 里剪掉**。任何"磁盘/目录体积"结论都要在这个口径下复核一次。

### 7. 其他

- **并行测体积**：Docker vhdx、JetBrains index 这类大目录串行会拖很久，用 8 线程池，别改单线程。
- **符号链接**：`os.scandir` 用 `follow_symlinks=False`，避免循环。
- **一个路径被多个 id 命中**（如 `JetBrains/*/log` 展开多个），清理前去重。
- **占用中的文件**：浏览器/IDE 运行时其缓存目录会 `PARTIAL`，属正常，提示用户关闭程序后重跑。
- **Docker vhdx 删了也不释放空间**：ext4.vhdx 是稀疏文件，必须先 `docker system prune`
  再 `wsl --shutdown` + `Optimize-VHD`。这一点必须在网页影响说明里写清。

## 实测基线参考（2026-10-29 同一台开发机，C 盘 300 GB / 可用 0.48 GB）

| 体积 | 路径 | 处置 |
|---:|---|---|
| 42.4 GB | `%LOCAL%/Docker/wsl/disk/docker_data.vhdx` | mid，`docker builder prune` + 改磁盘镜像位置 |
| 23.8 GB | `C:/Windows/WinSxS` | mid，`DISM /StartComponentCleanup` |
| 12.6 GB | `C:/hiberfil.sys` | mid，`powercfg /h off` |
| 9.3 GB | `%LOCAL%/JetBrains/IntelliJIdea*/index` | mid，IDE 内 Invalidate Caches |
| 8.1 GB | `%TEMP%/<GUID>/swap.vhdx`（WSL swap） | **不是垃圾**：改 `.wslconfig` 限流 + 迁到非系统盘 |
| 7.2 GB | `%ROAM%/Cursor/User/globalStorage/state.vscdb` | mid，关程序后 `VACUUM` |
| 4.8 GB | Cursor `cursor-agent/versions/*`（25 份） | 只留最新 1–2 份 |
| 12.2 GB | `%LOCAL%/Temp`（其中 8.1 GB 是上面的 swap） | low，`--min-age-hours 24` 定时清 |

一次实测治理：Temp 清 11.7 GB + Cursor 旧版本 4.3 GB → 可用 **0.48 GB → 13.8 GB**。
