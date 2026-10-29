# cleanc 使用文档（Windows）

> 版本 1.0.0 ｜ 仓库：[`workbuddy/skill/cleanc`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/cleanc)
> 文中日志样例取自 2026-10-16 在某开发机（Windows）上的真实运行记录。

管理页 + 命令行，扫描 C 盘找出可清理目录，按授权清单清理低风险项、说明中风险项的清理后果。

- **仅支持 Windows**：路径规则（`%LOCALAPPDATA%` / `%APPDATA%`）与清理指令（PowerShell / cmd / takeown）都是 Windows 专有。非 Windows 启动会直接退出并提示。
- **依赖**：Python 3.9+，仅标准库，无需 `pip install`。
- **默认不删任何东西**：页面按钮与 CLI 的 `--apply` 是仅有的两个删除入口。

---

## 一、快速开始

### 1. 启动服务

**方式 A（推荐）**：双击 `启动cleanc服务.bat`，浏览器打开 `http://127.0.0.1:8848/`。
由你自己的 Windows 会话启动服务，清理动作不受代理沙箱的批量删除保护限制。

**方式 B**：命令行启动

```bat
cd /d "%USERPROFILE%"\.workbuddy\skills\cleanc\scripts"
python server.py serve --port 8848
```

看到以下输出即为就绪：

```
[cleanc] 当前为普通用户权限 —— ProgramData / 受保护目录会清理失败，日志中会给出提权命令。
[cleanc] 管理页: http://127.0.0.1:8848/   (Ctrl+C 退出)
[cleanc] 授权清单: ...\cleanc\targets.json
[cleanc] 日志目录: ...\cleanc\logs
```

> **必须通过 `http://127.0.0.1:8848/` 访问页面。** 直接双击 `index.html` 打开时没有后端，按钮不会生效——页面顶部会明确提示"无法连接 cleanc 服务"。

### 2. 若要以管理员身份清理受保护目录

用**管理员身份**打开终端再启动服务：

```powershell
# 管理员 PowerShell
cd "$env:USERPROFILE\.workbuddy\skills\cleanc\scripts"
python server.py serve --port 8848
```

启动时会打印 `当前以管理员权限运行`，页面顶部"执行权限"卡片同步显示。非管理员运行时受保护目录会失败，失败项日志中会给出提权命令（见第五节）。

---

## 二、页面操作

打开 `http://127.0.0.1:8848/`。

| 区块 | 用途 |
|---|---|
| 概览卡片 | C 盘可用 / 低风险可一键清理 / 中风险合计 / 系统目录项数 / **执行权限** |
| **低风险目录** | 目录 · 类别 · **清理前MB** · 占比 · 文件数 · **执行指令** · **清理按钮** |
| 低风险 · 需人工处理 | `C:\Windows\Logs`、`$RECYCLE.BIN`、`.workbuddy\logs`、`.workbuddy\traces` —— 无按钮，只给替代命令 |
| **中风险目录** | 目录 · 类别 · 清理前MB · 占比 · **清理后的影响后果 / 建议指令**，**默认只列大于 500MB 的项**，阈值可在标题右侧输入框调整 |
| 服务端执行日志 | 实时输出每个目录的处理过程（见下） |
| 工具条 · 仅删改于 N 小时前的文件 | 默认 `0`（不限）。填 `24` 后，本次清理只删 24 小时前的文件，正在被使用的文件自动跳过；`*.vhdx` 恒定不删 |

### 清理按钮的行为

1. 点「清理」→ 弹出确认框，列出**绝对路径 / 清理前 MB / 执行指令 / 清理后的影响**，并给出红色警告。
2. 选择：
   - **确认清理** → 真删（清空目录内容，保留目录本身）
   - **预演（不删除）** → 只统计清理前后体积，不删任何文件
3. 提交后确认框立即关闭，页面顶部出现「执行中」标记，**下方的服务端执行日志开始逐行刷新**：

```
=====================================================================================
 cleanc APPLY（实际清理）   任务 20261016_224512_a1b2c3   开始 2026-10-16 22:45:12
 主机 C:\Users\Carter.li
 执行权限：普通用户（ProgramData/受保护目录会失败，需提权）
 待处理 5 个目录，清理前合计 963.1 MB
 C 盘可用（清理前）25085.3 MB
=====================================================================================

▶ 目录：C:\Users\Carter.li\AppData\Local\Temp
  执行指令：Get-ChildItem -LiteralPath "C:\Users\Carter.li\AppData\Local\Temp" -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  清理前：887.2 MB（213 个文件）
  清理后：12.4 MB    释放：874.8 MB    状态：PARTIAL
  未能删除 7 项，示例：C:\Users\Carter.li\AppData\Local\Temp\some.lock
  原因：[WinError 32] 另一个程序正在使用此文件，进程无法访问。
  处置方式（自行选择其一，复制到 【管理员 PowerShell】 执行）：
   A. 先提权接管再重试本页清理：
        takeown /f "C:\Users\Carter.li\AppData\Local\Temp" /r /d y
        icacls "C:\Users\Carter.li\AppData\Local\Temp" /grant "Carter.li":F /t
   B. 直接强制删除等价指令：
        PowerShell: Remove-Item -LiteralPath "C:\Users\Carter.li\AppData\Local\Temp" -Recurse -Force
        cmd:        rmdir /s /q "C:\Users\Carter.li\AppData\Local\Temp" && mkdir "C:\Users\Carter.li\AppData\Local\Temp"
   C. 若为进程占用：先关闭对应程序（浏览器 / IDE / 钉钉 / 飞书 / Docker），再重试。

-------------------------------------------------------------------------------------
 汇总：清理前 963.1 MB → 清理后 12.4 MB，节约 950.7 MB（0.93 GB）
 C 盘可用：25085.3 MB → 26031.0 MB（增加 945.7 MB）
 需人工处理 1 项，见上方各项的处置命令。
=====================================================================================
```

**每个目录固定输出四项**：清理哪个目录（`▶ 目录：`）、执行的是什么指令（`执行指令：`，等价命令行）、清理前目录大小 MB（`清理前：`）、清理后目录大小 MB（`清理后：`），另附状态与失败处置命令。

同一份日志（含以上全部内容）同时写到 `logs\clean_<任务号>.log`，并在服务端控制台实时打印。

---

## 三、命令行用法

```bat
cd /d "%USERPROFILE%"\.workbuddy\skills\cleanc\scripts"
```

| 命令 | 说明 |
|---|---|
| `python server.py scan` | 只读扫描授权清单，打印体积表 |
| `python server.py scan --root "C:\" --top 25` | 额外统计 `C:\` 下一级目录体积 TOP25，用于**发现**清单外的新目标（仍只读） |
| `python server.py scan --json out.json` | 结果落 JSON，便于二次处理 |
| `python server.py serve --port 8848` | 启动管理页（默认端口 8848） |
| `python server.py clean --ids __all_low__` | **dry-run**：统计全部低风险授权目录的释放量，不删 |
| `python server.py clean --ids __all_low__ --apply` | 真删，执行前要求输入 `yes` |
| `python server.py clean --ids local-temp,cursor-logs --apply --yes` | 指定多个 id 真删，跳过交互确认 |
| `python server.py clean --ids local-temp --apply --yes --min-age-hours 24` | **只删修改时间早于 24 小时的文件**（定时任务用这个） |
| `python server.py growth` | 对比最近两次扫描快照，列出**谁在长大** |
| `autoclean.bat` | 双击即执行"清 Temp 中 24 小时前的文件"，日志写 `logs\autoclean.log` |
| `python selftest.py --port 8848` | 端到端自检（只读 / dry-run，不产生删除） |

`scan` 输出的**风险 / 清理前MB / 授权 / 类别 / 路径**五列中，`授权` 为 `Y` 的才是 `clean --ids` 可用的目标；id 取 `targets.json` 里的 `id` 字段（页面上的每个目录也对应一个）。

### 两条内置保护（不可关闭）

1. **`*.vhdx` / `*.vhd` 永不删除** —— WSL 的 `swap.vhdx`、Docker 的 `docker_data.vhdx` 属于虚拟机磁盘，删掉会丢发行版或容器数据。日志会标 `保留 N 个虚拟磁盘`。
2. **junction / 符号链接不跟随** —— 统计体积与删除时都会剪掉 reparse point。Docker Desktop 会用 junction 指向同一份 `docker_data.vhdx`，跟随会把 42 GB 数成 85 GB。

### 增长归因怎么用

```bat
python server.py scan            :: 第一次，落快照
:: …隔几小时或一两天…
python server.py scan            :: 第二次，落快照
python server.py growth          :: 输出增长 TOP N
```

```
[growth] 2026-10-29 12:36:47 → 2026-10-29 12:38:24
 C 盘可用：14073.4 MB → 14175.6 MB（增加 102.2 MB）
      增长MB       当时MB       现在MB  路径
       0.7      284.1      284.8  C:\Users\...\.workbuddy\logs
```

快照存 `logs\snapshots\*.json`，只保留最近 60 份；清理任务完成后会自动收敛旧条目。

### 每天自动清理（防复发）

```bat
schtasks /Create /TN "cleanc-Temp每日清理" /SC DAILY /ST 12:30 ^
  /TR "\"%USERPROFILE%\.workbuddy\skills\cleanc\scripts\autoclean.bat\""
```

删除任务：`schtasks /Delete /TN "cleanc-Temp每日清理" /F`

> 只清 `local-temp` 且限 24 小时以上，不碰 IDE 日志 / 包缓存，避免第二天编译全量重下。

---

## 四、授权清单 `targets.json`

```json
{
  "id": "local-temp",
  "pattern": "%LOCAL%/Temp",
  "risk": "low",
  "category": "临时文件",
  "desc": "用户临时目录",
  "impact": "清理后：占用中的临时文件会被跳过；未保存的临时工作可能丢失。",
  "authorized": true,
  "mode": "clear"
}
```

| 字段 | 说明 |
|---|---|
| `id` | 稳定标识，`clean --ids` 用它 |
| `pattern` | 路径。占位符 `%HOME%` `%LOCAL%` `%ROAM%`，支持 `*` 通配（如 `%LOCAL%/JetBrains/*/log`、`%LOCAL%/Packages/*/LocalCache`） |
| `risk` | `low` 可清理 / `mid` 只解释后果 |
| `authorized` | **只有 `true` 且 `risk=low` 才允许被删除** |
| `impact` | 清理后的影响后果，页面直接展示 |
| `hint` | 等效命令或更安全的替代做法（中风险项必填） |
| `mode` | `clear` 清空内容保留目录 / `manual` 人工处理 |

**放开一个新目录**：先跑 `scan --root` 看它体积，再把 `authorized` 从 `false` 改成 `true`，重启服务即可。
**收紧**：改回 `false`。清单以**运行时所在目录**的 `scripts\targets.json` 为准；若你同时保留了多份副本（仓库副本、安装副本 `~\.workbuddy\skills\cleanc\scripts\targets.json`、工作目录副本），改完记得逐份同步。

---

## 五、删除失败怎么办

页面日志与服务端日志会按失败类型给出可直接复制的命令。四类常见原因：

### 0. 删除被本机批量删除保护拦截 —— `BLOCKED(删除未生效)` / `TIMEOUT(批量删除被拦截)`（**最常见**）

宿主环境（代理沙箱）带有批量删除保护。当目录文件数超过阈值（默认 50）时，删除调用会出现两种表现：

| 表现 | 日志状态 | 说明 |
|---|---|---|
| **静默忽略** | `BLOCKED(删除未生效)` | 调用正常返回，但文件仍在——服务端删后复查体积发现没下降，如实标记为 BLOCKED，不会报假绿的 OK |
| **调用挂起** | `TIMEOUT(批量删除被拦截)` | 调用长时间不返回，看门狗 `min(120s, 20s + 文件数×0.2s)` 超时后判定 |

实测样例（2026-10-16，文件数超过阈值的目标）：

```
▶ 目录：C:\Users\Carter.li\AppData\Roaming\Cursor\logs
  执行指令：Get-ChildItem -LiteralPath "C:\Users\Carter.li\AppData\Roaming\Cursor\logs" -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  清理前：10.2 MB（84 个文件）
  预检：84 个文件 > 本机批量删除阈值 50，宿主安全策略可能拦截批量删除（表现为长时间无进展）。若本次失败，请用下方给出的指令自行清理。
  清理后：10.4 MB    释放：-0.2 MB    状态：BLOCKED(删除未生效)
  未生效：删除调用正常返回，但复核发现仍有 84 个文件、10.4 MB 未下降 —— 操作被本机批量删除保护静默忽略。
  处置方式 —— 二选一：
   A. 用你自己的终端执行（推荐，一定可行）：
        PowerShell: Remove-Item -LiteralPath "C:\Users\Carter.li\AppData\Roaming\Cursor\logs" -Recurse -Force
        cmd:        rmdir /s /q "C:\Users\Carter.li\AppData\Roaming\Cursor\logs" && mkdir "C:\Users\Carter.li\AppData\Roaming\Cursor\logs"
   B. 双击运行 启动cleanc服务.bat，让服务在你自己的会话中启动，再回到页面点击清理。
```

处置方式，按可靠性排序：

| 方式 | 说明 |
|---|---|
| **1. 复制日志给出的命令，在你自己的终端里执行**（最可靠） | 在你自己打开的 PowerShell / cmd 中运行 `Remove-Item` / `rmdir`，不受任何代理策略限制 |
| **2. 双击 `启动cleanc服务.bat` 启动服务** | 服务由你自己的 Windows 会话拉起，页面按钮即可正常删除。**这条是推荐做法**，用于让页面恢复"一键清理"能力 |
| 3. 分批删除 | 单次删除不超过 50 个文件后回页面重试 |
| 4. 在资源管理器里手动清空该目录 | 等效，适合 `Temp` 这类子目录多的目标 |

> 这是本机**故意设置的安全策略**，本工具不做绕过。拦截发生时，工具的正确行为是**停下、如实标记、交还命令**。已删除的部分不会回滚。

**实测结论（2026-10-16，本机）**：

| 情形 | 实测结果 |
|---|---|
| 文件数 ≤ 50 且文件未被占用 | **真删成功**（`DingTalk\log` 6 个文件中 1 个成功删除） |
| 文件数 ≤ 50 但文件被运行中的程序占用 | `PARTIAL`（`DingTalk\log` 剩 5 个文件被钉钉进程持有），日志给出提权与强制删除命令 |
| 文件数 > 50（如 `Cursor\logs` 84 个、`Temp` 256 个） | `BLOCKED(删除未生效)`，调用返回成功但文件仍在；日志给出可复制命令 |
| 服务由代理会话启动 | 上述 3 条均成立 |
| 服务由用户自己双击 `启动cleanc服务.bat` 启动 | 批量删除保护不生效，页面按钮可直接清理（**推荐用这种方式跑**） |

### 1. 权限不足（`[WinError 5] 拒绝访问`）

在**管理员 PowerShell** 中提权接管后重试页面清理：

```powershell
takeown /f "C:\Users\Carter.li\AppData\Local\Temp" /r /d y
icacls "C:\Users\Carter.li\AppData\Local\Temp" /grant "Carter.li":F /t
```

（把路径与用户名换成日志里给出的实际值。）

### 2. 进程占用（`[WinError 32] 另一个程序正在使用此文件`）

先关闭占用程序再重试：浏览器 / IDE（IntelliJ、PyCharm、GoLand、Cursor）/ 钉钉 / 飞书 / Docker Desktop。
或直接强制删除：

```powershell
Remove-Item -LiteralPath "C:\Users\Carter.li\AppData\Local\Temp" -Recurse -Force
```

```bat
rmdir /s /q "C:\Users\Carter.li\AppData\Local\Temp" && mkdir "C:\Users\Carter.li\AppData\Local\Temp"
```

> `rmdir` 会连目录一起删掉，后面的 `mkdir` 用于恢复空目录。

### 3. 系统级目标 —— 本工具不代跑，只给命令

| 目标 | 命令（管理员） | 影响 |
|---|---|---|
| `C:\Windows\Logs` | `cleanmgr /sageset:1`（勾"系统存档日志"）→ `cleanmgr /sagerun:1` | 无 |
| 回收站 | `Clear-RecycleBin -Force` | 永久删除回收站内容 |
| `hiberfil.sys`（约 13 GB） | `powercfg /h off` | 关闭休眠与快速启动，可逆（`powercfg /h on`） |
| `C:\Windows\WinSxS`（约 23 GB） | `DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase` | 已安装更新无法卸载/回滚；**切勿手动删该目录** |
| Docker vhdx（约 35 GB） | `docker system prune -a --volumes` 后 `wsl --shutdown`，再 `Optimize-VHD -Path <vhdx> -Mode Full` | 直接删目录会毁掉全部镜像且空间不释放 |

---

## 六、日志与 manifest

| 文件 | 内容 |
|---|---|
| `logs\clean_<任务号>.log` | 实际清理日志：目录 / 执行指令 / 清理前MB / 清理后MB / 状态 / 失败处置命令 / 汇总 |
| `logs\dryrun_<任务号>.log` | 预演日志，同格式，`状态：DRY-RUN` |
| `logs\clean_<任务号>.log.manifest.txt` | **删除前**记录将被删除的每个文件：`字节数<TAB>绝对路径`，便于事后追溯 |

任务号格式 `YYYYmmdd_HHMMSS_<6位十六进制>`。页面通过 `GET /api/log?name=<文件名>` 回读。

状态取值：

| 状态 | 含义 |
|---|---|
| `OK` | 全部删除成功 |
| `DRY-RUN` | 预演，未删除 |
| `PARTIAL` | 部分文件被占用/无权限，其余已删除 |
| `FAIL` | 整体失败（目录不可列出、单文件删除失败） |
| `TIMEOUT(批量删除被拦截)` | 删除调用超过看门狗时限未返回，判定本机策略拦截了批量删除；文件基本未删，日志给出可直接执行的清理指令 |
| `BLOCKED(删除未生效)` | 删除调用正常返回但**删后复查体积未下降**，判定被本机批量删除保护静默忽略；日志给出清理指令 |
| `SKIP(安全拦截)` | 命中 NO_GO 或不在本次授权集合内，未删除 |

看门狗时限：`min(120s, 20s + 文件数 × 0.2s)`。例如 84 个文件 ≈ 37 秒，256 个文件 ≈ 71 秒。可用环境变量 `CLEANC_BULK_THRESHOLD` 调整预检提示的阈值（默认 50，与宿主策略对齐，**仅用于提示，不改变拦截行为**）。

---

## 七、常见问题

**点了清理没有任何反应？**

三个检查点，按顺序：

1. **访问地址**：页面必须由 Python 服务提供（`http://127.0.0.1:8848/`）。若地址栏是本地文件路径或别的静态服务，`/api/*` 会 404，提交不会生效——页面顶部会显示红色提示。
2. **服务端是否收到任务**：看服务端控制台有没有 `[cleanc] 任务 ... 已启动：实际清理 ids=[...]`。有，说明请求通了。
3. **日志里有没有 `预检：N 个文件 > 本机批量删除阈值 50`**：有，就是第五节第 0 类——本机策略拦截了批量删除。任务会在看门狗超时后给出 `TIMEOUT(批量删除被拦截)` 与你可直接执行的手工清理指令；页面在 45 秒无新输出时也会出现「等待中」提示。**这类目标请用日志给出的命令自己清理。**

**清理完毕但体积没变？**

若状态是 `TIMEOUT` / `PARTIAL` / `FAIL`，说明文件没删掉（被策略拦截 / 被占用 / 无权限），体积自然不会变。状态为 `OK` 却体积没降，多半是目录已被其他程序立刻重建（`Temp`、浏览器缓存很常见），属正常现象。

**端口被占用？**

服务端会打印：

```
[cleanc] 端口 8848 无法监听：[WinError 10048] ...
         可能已有 cleanc 服务在跑。先结束它：
         Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object {$_.CommandLine -match 'server\.py\s+serve'} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
         或换端口：python server.py serve --port 8899
```

> 服务已关闭 `SO_REUSEADDR`：Windows 默认允许第二个进程绑定同一端口，会导致新旧实例同时监听、请求随机落到旧代码上——这正是排查此类"改完代码不生效"问题的常见坑。

**回收站和 Windows 日志为什么没有按钮？**
它们在 `targets.json` 里是 `authorized: false`。回收站由系统托管，脚本递归清空有风险；`C:\Windows\Logs` 属操作系统目录。两者都给了替代命令（见第五节）。

**`.workbuddy` 目录会被删吗？**
不会。目录本身不在清单里。其子目录 `logs` / `traces` 标为 `authorized: false` —— WorkBuddy 运行中清理可能中断当前会话日志写入，建议退出后人工清理。

**删除能恢复吗？**
不能，不进回收站。清单里的目标都是缓存 / 日志 / 临时文件，程序会按需重建，代价是首次启动或首次构建变慢；中风险项（对话历史、本地文件历史、Maven 仓库等）删了就没了，页面上逐条写明了后果。

---

## 八、安全边界

代码级硬拦截（`NO_GO` 常量，独立于清单，即使写进 `targets.json` 且 `authorized: true` 也删不掉）：

```
C:\  |  C:\Windows  |  C:\Program Files*  |  C:\ProgramData
C:\Users（裸根）  |  C:\System Volume Information  |  C:\Recovery  |  C:\Boot  |  C:\$RECYCLE.BIN
```

双闸门：① 只有 `authorized=true && risk=low` 可删；② 请求的路径必须落在本次扫描解析出的授权集合内。传入 `C:\Windows\System32` 之类的伪造 id 不会产生任何操作（`selftest.py` 第 9 组断言覆盖）。

**绝不纳入清单**：桌面 / 文档 / 下载 / 图片 / 视频、任何含 `.git` 的源码目录、`.ssh` `.aws` `.kube` 等凭据目录、浏览器 `Cookies`/`Login Data`、IDE 配置与 `settings.json`、`.workbuddy` 目录本身、`pagefile.sys` / `swapfile.sys` / `WinSxS` 等系统文件。

---

## 九、自检

```bat
python server.py serve --port 8848
python selftest.py --port 8848
```

覆盖：页面与阈值控件、扫描字段完整性、授权项必为 low、NO_GO 目录未被授权、空 ids 拒绝、未知 job 404、dry-run 全流程与实时日志、日志四项字段、中风险/未授权/伪造 id 三类越权拒绝、失败处置命令生成、NO_GO 拦截与不误伤用户缓存。
