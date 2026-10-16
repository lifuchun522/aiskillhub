# cleanc｜Windows 磁盘可清理目录扫描与安全清理（v1.0.0）

> 本页对应 **WorkBuddy 版 v1.0.0**：把「C 盘满了，帮我清一下」从一次提心吊胆的手工删除，变成 **只读扫描 → 授权清单 → 网页逐条确认 → 全字段日志** 的一条闭环。低风险项一键清，中风险项只解释后果。

仓库路径：[`workbuddy/skill/cleanc/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/cleanc)

完整使用文档（含失败处置与 FAQ）：[`references/usage-windows.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/cleanc/references/usage-windows.md)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/cleanc/SKILL.md) ｜ 概览：[`README.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/cleanc/README.md)

## 一句话

输入一句话，先只读量出每个候选目录的实测体积，按授权清单分级；再用一个本地网页逐条确认——低风险给清理按钮，中风险写清清理后果；每条目录的「执行了哪条指令、清理前后各多少 MB、状态是什么、没删成该怎么办」全部落日志。

## 它解决什么问题

C 盘红了之后，难的不是「删哪个」，而是三件事：**删之前不知道能回收多少**、**不知道删了会怎样**、**删不掉时不知道该做什么**。

| 痛点 | 本技能的做法 |
|---|---|
| 猜着删，删完只多几百 MB | `os.scandir` 8 线程并行遍历，按体积排序，回收量可预期 |
| 清 `Temp` 和清 IDEA 索引代价天差地别 | 清单每条带 `impact` 字段，写**后果**（丢什么 / 多久恢复 / 能否回滚），页面直接展示 |
| 权限不足 / 进程占用 / 策略拦截混成一个「失败」 | 三种处置分开，日志给出可复制的 `takeown`+`icacls` 提权、`Remove-Item`/`rmdir` 强删命令 |

## 能力边界与铁律

| 铁律 | 说明 |
|---|---|
| **只读优先** | 扫描阶段绝不删。删除只发生在这两处：网页点「确认清理」，或 CLI 显式 `clean --apply` |
| **不碰操作系统文件** | `C:\Windows`、`C:\Program Files*`、`C:\ProgramData`、`C:\Users` 裸根、盘根、`System Volume Information`、`Recovery`、`$RECYCLE.BIN` 在**代码级 `NO_GO` 黑名单**里，独立于清单硬拦截——即使写进 `targets.json` 且 `authorized: true` 也删不动 |
| **双闸门** | ① 只有 `risk=low && authorized=true` 可删；② 请求路径必须落在**本次扫描解析出的授权集合**内。伪造 id 传 `C:\Windows\System32` 不产生任何操作 |
| **不报假绿** | 删除后**必须重新测量体积**才判 `OK`。只凭「调用没抛异常」就报成功，会在删除被宿主策略静默忽略时撒谎 |
| **只清空内容，保留目录本身** | 避免程序因缺目录而报错 |
| **删前写 manifest** | 记录每个将被删除的文件（字节数 + 绝对路径）到 `scripts/logs/`，便于追溯 |
| **删不掉就交还命令** | 不绕过宿主安全策略；停下、如实标记、给出用户可自行执行的命令 |
| **系统级目标只给命令不代跑** | `hiberfil.sys`（`powercfg /h off`）、`WinSxS`（`DISM`）、回收站（`Clear-RecycleBin`）由用户在管理员终端确认 |
| **绝不纳入清单** | 桌面 / 文档 / 下载 / 图片 / 视频、含 `.git` 的源码目录、`.ssh`/`.aws`/`.kube` 凭据目录、浏览器 `Cookies`/`Login Data`、IDE 配置、`.workbuddy` 目录本身、`pagefile.sys`/`swapfile.sys`/`WinSxS` |

## 安装与环境

```bash
git clone https://github.com/lifuchun522/aiskillhub.git
cp -r aiskillhub/workbuddy/skill/cleanc ~/.workbuddy/skills/cleanc
```

- **仅支持 Windows**：路径占位符（`%LOCALAPPDATA%` / `%APPDATA%`）与清理指令（PowerShell / cmd / takeown）都是 Windows 专有。非 Windows 启动即退出并提示。
- **依赖**：Python 3.9+，**仅标准库**，无需 `pip install`。
- 可选：`tests/verify_browser.py` 需要 `playwright`（仅用于浏览器实跑验证，工具本身不依赖）。

## 使用步骤

### 第 1 步：启动管理页（**推荐双击 `.bat`**）

```bat
:: 双击 scripts\启动cleanc服务.bat，或命令行：
cd /d "%USERPROFILE%\.workbuddy\skills\cleanc\scripts"
python server.py serve --port 8848
```

浏览器打开 **`http://127.0.0.1:8848/`**。

> **为什么推荐双击 `.bat`**：若服务由带批量删除保护的宿主 / 沙箱会话启动，文件数超过阈值（默认 50）的目录会被静默拦截。由你自己的 Windows 会话启动则不继承该策略，页面按钮才能真正一键清理。详见「重要警告」第 1 条。

> **必须走 `http://127.0.0.1:8848/`。** 直接双击 `index.html` 打开时没有后端，`/api/*` 会 404，按钮不生效——页面顶部会报红并给出启动命令。

需要清理受保护目录（`ProgramData` 等）时，用**管理员身份**开终端再启动服务，启动时会打印「当前以管理员权限运行」，页面「执行权限」卡片同步显示。

### 第 2 步：在页面上逐条确认

| 区块 | 内容 |
|---|---|
| 概览卡片 | C 盘可用 / 低风险可一键清理 / 中风险合计 / 系统目录项数 / **执行权限** |
| **低风险目录** | 目录 · 类别 · **清理前 MB** · 占比 · 文件数 · **执行指令** · **清理按钮** |
| 低风险 · 需人工处理 | `C:\Windows\Logs`、`$RECYCLE.BIN`、`.workbuddy\logs` —— 无按钮，只给替代命令 |
| **中风险目录** | 目录 · 类别 · 清理前 MB · 占比 · **清理后的影响后果 / 建议指令**；**默认只列 > 500MB**，阈值可调 |
| 服务端执行日志 | 实时轮询 `POST /api/clean` 返回的 `job_id`，逐行追加 |

点「清理」→ 弹确认框（绝对路径 / 清理前 MB / 执行指令 / 影响 / 红色警告）→ 选：

- **确认清理** → 真删（清空目录内容，保留目录本身）
- **预演（不删除）** → 只统计清理前后体积，不删任何文件

提交后弹窗立即关闭、出现「执行中」标记，日志逐行刷新；45 秒无新输出会给出「等待中」提示，而不是静默卡住。

### 第 3 步：读日志（每个目录固定四行）

```
▶ 目录：C:\Users\<你>\AppData\Local\JetBrains\IntelliJIdea2025.3\log
  执行指令：Get-ChildItem -LiteralPath "..." -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  清理前：4.7 MB（12 个文件）
  清理后：0.0 MB    释放：4.7 MB    状态：OK
```

清理哪个目录 / 执行的是什么指令 / 清理前 MB / 清理后 MB —— 四项齐全，同时写进 `scripts\logs\clean_<任务号>.log` 并在服务端控制台实时打印。

### 第 4 步（可选）：命令行替代网页

```bat
python server.py scan                              :: 只读扫描，打印体积表
python server.py scan --root "C:\" --top 25         :: 只读统计一级目录体积，用于发现清单外的新目标
python server.py scan --json out.json               :: 结果落 JSON
python server.py clean --ids __all_low__            :: dry-run：只统计释放量，不删
python server.py clean --ids __all_low__ --apply    :: 真删，执行前需输入 yes
python server.py clean --ids local-temp,cursor-logs --apply --yes
python selftest.py --port 8848                      :: 端到端自检（只读 / dry-run）
```

### 第 5 步（可选）：按自己的机器调整清单

先看真实体积，再决定放开什么：

```bat
python server.py scan --root "C:\Users\%USERNAME%" --top 30
```

然后编辑 `scripts\targets.json`：新增条目一律先 `authorized: false`，把 `impact`（后果）和 `hint`（更安全的替代做法）写清楚，看了体积之后再决定是否改成 `true`，重启服务生效。

## 状态取值

| 状态 | 含义 |
|---|---|
| `OK` | 删除调用成功**且删后复查体积确实下降** |
| `DRY-RUN` | 预演，未删除 |
| `PARTIAL` | 部分文件被占用 / 无权限，其余已删除 |
| `FAIL` | 整体失败（目录不可列出、单文件删除失败） |
| `BLOCKED(删除未生效)` | 调用成功返回但复查体积未降 —— 被宿主批量删除保护静默忽略 |
| `TIMEOUT(批量删除被拦截)` | 删除调用超过看门狗时限未返回 |
| `SKIP(安全拦截)` | 命中 `NO_GO` 或不在本次授权集合内 |

看门狗时限：`min(120s, 20s + 文件数 × 0.2s)`（84 个文件 ≈ 37 秒，256 个文件 ≈ 71 秒）。环境变量 `CLEANC_BULK_THRESHOLD`（默认 50）只调整预检提示的阈值，**不改变拦截行为**。

## 重要警告

- **宿主批量删除保护是本项目最坑的一条**：文件数超过阈值（默认 50）时，删除要么被**静默忽略**（调用正常返回但文件仍在），要么**挂起不返回**。前者的危险在于「没抛异常」被当成成功，界面会撒谎——所以本工具做了删后体积复核（`BLOCKED`）与每目标看门狗（`TIMEOUT`）。拦截发生时**不做绕过**，如实标记并交出 `Remove-Item` / `rmdir` 命令；推荐双击 `.bat` 让服务跑在你自己的会话里。
- **删除不进回收站**，不可恢复。清单里的缓存 / 日志 / 临时文件程序会按需重建，代价是首次启动或首次构建变慢；中风险项（对话历史、本地文件历史、Maven 仓库等）删了就没了。
- **默认清单来自一台真实开发机**（C 盘 298 GB 已用 / 剩余 1.8 GB），不代表你的机器。**先 `scan --root` 看你自己的体积再调清单。**
- **Docker vhdx 删了也不释放空间**：`ext4.vhdx` 是稀疏文件，必须先 `docker system prune -a --volumes`，再 `wsl --shutdown` + `Optimize-VHD`。直接删目录会毁掉全部镜像且空间不释放。

## 验证

```bat
python server.py serve --port 8848
python selftest.py --port 8848
```

`selftest.py` 共 **37 项断言，全 dry-run，实测 37 通过 / 0 失败**，覆盖：管理页与阈值控件、扫描字段完整性、授权项必为 low、`NO_GO` 目录未被授权、空 ids 拒绝、未知 job 404、dry-run 全流程与实时日志、日志四项字段、中风险 / 未授权 / 伪造 id 三类越权拒绝、失败处置命令生成、`NO_GO` 拦截且不误伤用户缓存。

浏览器实跑（`tests/verify_browser.py`，需 playwright）：中风险阈值过滤（500MB / 5000MB 两档）、点清理 → 弹窗 → 确认 → 实时日志 → 表格自动刷新，并断言页面 JS 错误为 0。

## 相关文件

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 技能规范：触发条件、四步工作流、安全红线九条、常见坑六类 |
| `README.md` | 概览：定位、快速开始、状态取值、目录结构、验证、踩坑、边界声明 |
| `references/usage-windows.md` | 完整使用文档：页面 / CLI / 清单结构 / 失败处置 / FAQ / 安全边界 |
| `references/safety.md` | 安全边界与逐条允许 / 禁止清单 |
| `scripts/server.py` | 扫描 + 清理 + HTTP API + 内置管理页（纯标准库） |
| `scripts/targets.json` | 授权清单（风险等级 / 影响说明 / `authorized` 开关） |
| `scripts/selftest.py` | 端到端自检 37 断言，全 dry-run |
| `scripts/启动cleanc服务.bat` | 推荐启动方式（CRLF 换行） |
| `tests/verify_browser.py` | 可选：真实浏览器实跑验证（需 playwright） |

更多细节以仓库内 `SKILL.md` 与 `references/usage-windows.md` 为准。
