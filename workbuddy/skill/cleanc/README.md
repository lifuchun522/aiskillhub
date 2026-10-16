# cleanc

Windows 磁盘可清理目录的**只读扫描 → 授权清单 → 本地管理网页**技能（v1.0.0）。

喊一句「C 盘满了 / 帮我清一下 C 盘」，它不急着删：先只读扫出每个候选目录的实测体积，再按授权清单分级——**低风险**的给出清理按钮，**中风险**的逐条写清清理后果——最后在一个本地网页上让你逐条确认。清理到哪一步、释放了多少、哪一条没删成、该怎么手工补，全部有日志。

- **只读优先**：扫描阶段绝不删。删除只发生在这两处：网页上点「确认清理」，或 CLI 显式 `clean --apply`。
- **不碰操作系统文件**：`C:\Windows`、`C:\Program Files*`、`C:\ProgramData`、`C:\Users` 裸根、盘根、`System Volume Information`、`Recovery`、`$RECYCLE.BIN` 在**代码级黑名单**里，独立于清单硬拦截——即使写进 `targets.json` 且 `authorized: true` 也删不动。
- **双闸门**：① 只有 `risk=low && authorized=true` 可删；② 请求路径必须落在**本次扫描解析出的授权集合**内。伪造 id 传 `C:\Windows\System32` 不会产生任何操作。
- **不报假绿**：删除后**必须重新测量体积**才判 `OK`。只凭「调用没抛异常」就报成功，会在删除被宿主策略静默忽略时给用户一个假结果——这是本项目踩过的真实坑，见「踩坑」第 1 条。
- **删不掉就交还命令**：命中权限不足 / 进程占用 / 批量删除拦截时，日志输出可直接复制执行的 `takeown` + `icacls` 提权命令与 `Remove-Item` / `rmdir` 强删命令，不静默失败也不硬扛。

## 快速开始

**仅支持 Windows**（路径占位符 `%LOCALAPPDATA%` / `%APPDATA%`、清理指令 PowerShell / cmd / takeown 都是 Windows 专有；非 Windows 启动即退出）。依赖 **Python 3.9+，仅标准库**，不需要 `pip install`。

```bash
# 1) 安装：整目录拷贝到本地 skills 目录
git clone https://github.com/lifuchun522/aiskillhub.git
cp -r aiskillhub/workbuddy/skill/cleanc ~/.workbuddy/skills/cleanc
# 其他宿主按各自约定放置（Claude Code / Codex / Cursor 均可直接用 SKILL.md）
```

```bat
:: 2) 启动管理页 —— 双击 scripts\启动cleanc服务.bat，或：
cd /d "%USERPROFILE%\.workbuddy\skills\cleanc\scripts"
python server.py serve --port 8848
:: 浏览器打开 http://127.0.0.1:8848/
```

```bat
:: 3) 命令行用法（可选，替代网页）
python server.py scan                                   :: 只读扫描，打印体积表
python server.py scan --root "C:\" --top 25              :: 只读统计一级目录体积，用于发现清单外的新目标
python server.py clean --ids __all_low__                 :: dry-run：只统计释放量，不删
python server.py clean --ids __all_low__ --apply         :: 真删，执行前需输入 yes
python selftest.py --port 8848                           :: 端到端自检（只读 / dry-run）
```

> **用 `启动cleanc服务.bat` 启动**（而不是在带批量删除保护的宿主会话里启动）时，页面按钮才能真正一键删除。原因见「踩坑」第 1 条。

## 它解决什么问题

C 盘红了之后，真正难的不是「删哪个」，而是三件事：

1. **删之前不知道能回收多少。** 猜着删，删完发现只多了几百 MB。本工具先把候选目录逐个体积量出来（`os.scandir` 8 线程并行遍历），按体积排序，回收量是可预期的。
2. **不知道删了会怎样。** 清 `Temp` 和清 IDEA 索引、清 Maven 仓库，代价完全不同。清单里每条都带 `impact` 字段，写的是**后果**（会丢什么、多久恢复、能不能回滚），页面上直接展示，不写「建议清理」这种废话。
3. **删不掉时不知道该做什么。** 权限不足、被进程占用、被宿主策略拦截是三种完全不同的处置。工具会区分它们并给出对应的命令，而不是笼统报一个「失败」。

## 页面

启动后打开 `http://127.0.0.1:8848/`。

| 区块 | 内容 |
|---|---|
| 概览卡片 | C 盘可用 / 低风险可一键清理（项数 + MB）/ 中风险合计 / 系统目录项数 / **执行权限**（是否管理员） |
| **低风险目录** | 目录 · 类别 · **清理前 MB** · 占比 · 文件数 · **执行指令** · **清理按钮**（只对授权目录渲染） |
| 低风险 · 需人工处理 | `C:\Windows\Logs`、`$RECYCLE.BIN`、`.workbuddy\logs` —— 无按钮，只给替代命令 |
| **中风险目录** | 目录 · 类别 · 清理前 MB · 占比 · **清理后的影响后果 / 建议指令**；**默认只列 > 500MB 的项**，阈值在标题右侧输入框可调 |
| 服务端执行日志 | 实时轮询 `POST /api/clean` 返回的 `job_id`，逐行追加 |

点「清理」→ 弹确认框（绝对路径 / 清理前 MB / 执行指令 / 影响 / 红色警告）→「确认清理」真删 或「预演」只看数字。提交后弹窗立即关闭、出现「执行中」标记、日志逐行刷新；45 秒无新输出时给出「等待中」提示，而不是静默卡住。

**必须通过 `http://127.0.0.1:8848/` 访问。** 直接双击 `index.html` 打开时没有后端，`/api/*` 会 404，按钮不生效——页面顶部会明确报红并给出启动命令，不会静默失败。

### 每个目录的日志固定四行

```
▶ 目录：C:\Users\<你>\AppData\Roaming\Cursor\logs
  执行指令：Get-ChildItem -LiteralPath "..." -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  清理前：10.2 MB（84 个文件）
  清理后：10.4 MB    释放：-0.2 MB    状态：BLOCKED(删除未生效)
```

清理哪个目录 / 执行的是什么指令 / 清理前 MB / 清理后 MB —— 四项齐全，同时写进 `scripts\logs\clean_<任务号>.log` 并在服务端控制台实时打印。

## 状态取值（判定前必须复核）

| 状态 | 含义 |
|---|---|
| `OK` | 删除调用成功**且删后复查体积确实下降** |
| `DRY-RUN` | 预演，未删除 |
| `PARTIAL` | 部分文件被占用 / 无权限，其余已删除 |
| `FAIL` | 整体失败（目录不可列出、单文件删除失败） |
| `BLOCKED(删除未生效)` | 调用成功返回但复查体积未降 —— 被宿主的批量删除保护静默忽略 |
| `TIMEOUT(批量删除被拦截)` | 删除调用超过看门狗时限未返回 |
| `SKIP(安全拦截)` | 命中 NO_GO 或不在本次授权集合内 |

## 授权清单 `scripts/targets.json`

| 字段 | 含义 |
|---|---|
| `id` | 稳定标识，CLI 的 `--ids` 用它 |
| `pattern` | 路径，支持 `%HOME%` `%LOCAL%` `%ROAM%` 占位符与 `*` 通配（如 `%LOCAL%/JetBrains/*/log`） |
| `risk` | `low` 可清理 / `mid` 只解释后果 |
| `authorized` | **只有 `true` 且 `risk=low` 才允许被删除** |
| `category` / `desc` | 页面用的分类与说明 |
| `impact` | 清理后的影响后果（写后果，不写建议） |
| `hint` | 等效命令或更安全的替代做法（中风险项必填） |
| `mode` | `clear` 清空内容保留目录 / `manual` 人工处理 |

新增条目一律先 `authorized: false`，写清 `impact` / `hint`，跑过 `scan --root` 看过真实体积后，再决定是否放开。

## 目录结构

```
cleanc/
├── SKILL.md                    # 技能规范：何时触发、工作流、安全红线、踩坑
├── README.md                   # 本文件
├── scripts/
│   ├── server.py               # 扫描 + 清理 + HTTP API + 内置管理页（纯标准库，736 行）
│   ├── targets.json            # 授权清单
│   ├── index.html              # 管理网页
│   ├── selftest.py             # 端到端自检 37 断言，全 dry-run
│   ├── 启动cleanc服务.bat       # 推荐启动方式（CRLF 换行）
│   └── logs/                   # 运行期日志与 manifest（已 gitignore）
├── tests/
│   └── verify_browser.py       # 可选：真实浏览器走一遍阈值过滤 + 清理链路（需 playwright）
└── references/
    ├── safety.md               # 安全边界与逐条允许/禁止清单
    └── usage-windows.md        # 完整使用文档：页面 / CLI / 失败处置 / FAQ
```

## 验证

```bat
python server.py serve --port 8848
python selftest.py --port 8848
```

自检覆盖：页面与阈值控件、扫描字段完整性、授权项必为 low、NO_GO 目录未被授权、空 ids 拒绝、未知 job 404、dry-run 全流程与实时日志、日志四项字段、中风险 / 未授权 / 伪造 id 三类越权拒绝、失败处置命令生成、NO_GO 拦截且不误伤用户缓存。

外加浏览器实跑（`tests/verify_browser.py`）：中风险阈值过滤（500MB / 5000MB 两档）、点清理 → 弹窗 → 确认 → 实时日志 → 表格自动刷新，并断言页面 JS 错误为 0。

## 踩坑

### 1. 宿主的批量删除保护会让删除**静默失效**（最坑）

若服务由某个带批量删除保护的宿主 / 沙箱会话启动，单个目标文件数超过阈值（默认 50）时，删除有两种表现：

| 表现 | 日志状态 |
|---|---|
| 调用正常返回，但文件仍在（被静默忽略） | `BLOCKED(删除未生效)` |
| 调用长时间不返回（被挂起） | `TIMEOUT(批量删除被拦截)` |

前者最危险：只凭「没抛异常」就报 OK，界面会撒谎。本工具的对策是**删除后重新 `path_size` 复核**：`删除后仍有文件 且 (清理前 - 清理后) < 1MB` → 判 `BLOCKED`。后者则靠每个目标的看门狗 `min(120s, 20s + 文件数 × 0.2s)` 兜底（84 个文件 ≈ 37 秒，256 个文件 ≈ 71 秒），超时判定后给出手工命令，而不是让任务永远不返回、页面永远停在「执行中」。

**拦截发生时不要试图绕过。** 正确做法是如实标记 + 交还可直接执行的命令：

```powershell
Remove-Item -LiteralPath "<path>" -Recurse -Force
```
```bat
rmdir /s /q "<path>" && mkdir "<path>"
```

**推荐用法**是把 `启动cleanc服务.bat` 交给用户双击，由用户自己的 Windows 会话拉起服务，不继承宿主策略，页面按钮即可正常一键清理。这是本工具**推荐**的运行方式，不是变通。

实测结论（2026-10-16，某开发机）：

| 情形 | 结果 |
|---|---|
| 文件数 ≤ 50 且未被占用 | 真删成功 |
| 文件数 ≤ 50 但被运行中的程序占用 | `PARTIAL`，日志给出提权与强删命令 |
| 文件数 > 50（`Cursor\logs` 84 个、`Temp` 256 个） | `BLOCKED(删除未生效)` |
| 服务由宿主会话启动 | 上述三条均成立 |
| 服务由用户双击 `.bat` 启动 | 批量删除保护不生效，按钮可直接清理 |

### 2. Windows 下 `SO_REUSEADDR` 会导致双实例抢端口

`HTTPServer.allow_reuse_address` 默认 1，Windows 语义允许第二个进程绑定同一端口，于是新旧实例同时监听、请求随机落到旧代码上（表现是「改了代码不生效」）。本项目显式设 `allow_reuse_address = False`，并在启动失败时打印结束旧进程的命令。

### 3. 只给 URL，不要同时把 `index.html` 当文件交付

同时交付会生成一份静态副本页，那份副本的 `/api/*` 返回 404，用户点按钮毫无反应。**只交付 URL。**

### 4. 不要用 `du` 判断 Windows 目录体积

Git Bash 的 `du` 在大量小文件下极慢。用 `server.py` 内置的 `os.scandir` 遍历（`follow_symlinks=False` 避免循环），或 PowerShell。

### 5. `.bat` 必须保持 CRLF

cmd.exe 解析 `if errorlevel 1 (...)` 这类块依赖 CRLF；被统一成 LF 后双击会报「此时不应有 xxx」。仓库 `.gitattributes` 已显式声明 `*.bat text eol=crlf`。

### 6. 其他

- **并行测体积**：Docker vhdx、JetBrains index 这类大目录串行会拖很久，用 8 线程池，别改成单线程。
- **一个路径被多个 id 命中**（如 `%LOCAL%/JetBrains/*/log` 展开多个），清理前去重。
- **Docker vhdx 删了也不释放空间**：`ext4.vhdx` 是稀疏文件，必须先 `docker system prune -a --volumes`，再 `wsl --shutdown` + `Optimize-VHD`。直接删目录会毁掉全部镜像且空间不释放——这一点写在页面的影响说明里。
- **系统级目标只给命令、不代跑**：`hiberfil.sys`（`powercfg /h off`）、`WinSxS`（`DISM /Online /Cleanup-Image /StartComponentCleanup`）、回收站（`Clear-RecycleBin`）由用户在管理员终端确认执行。

## 边界声明

- Windows 专有；Linux / macOS 未适配（`os.name != "nt"` 时直接退出）。
- 删除**不进回收站**，清单里的缓存 / 日志 / 临时文件不可恢复但程序会按需重建，代价是首次启动或首次构建变慢；中风险项（对话历史、本地文件历史、Maven 仓库等）删了就没了。
- **绝不纳入清单**：桌面 / 文档 / 下载 / 图片 / 视频、任何含 `.git` 的源码目录、`.ssh` `.aws` `.kube` 等凭据目录、浏览器 `Cookies` / `Login Data`、IDE 配置与 `settings.json`、`.workbuddy` 目录本身、`pagefile.sys` / `swapfile.sys` / `WinSxS` 等系统文件。
- 本工具**不做宿主安全策略的绕过**。策略拦截时它的职责是停下、如实标记、交还命令。
- 默认清单基于一台真实开发机（C 盘 298 GB 已用 / 剩余 1.8 GB）的实际占用情况整理，不代表你的机器。**先 `scan --root` 看你自己的体积再调清单。**
