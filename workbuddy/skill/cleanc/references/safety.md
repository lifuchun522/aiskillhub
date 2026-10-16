# cleanc 安全边界

本文是 `SKILL.md` 红线的完整版，也是代码里 `NO_GO_*` 常量的依据。
改 `targets.json` 之前先读这里。

## 一、绝对禁止（代码级硬拦截）

`server.py` 的 `is_no_go()` 对以下路径直接返回 True，清理请求一律拒绝并记入 `rejected`：

| 类别 | 路径 |
|---|---|
| 盘根 | `C:/` |
| 系统目录 | `C:/Windows` 及其全部子目录 |
| 程序目录 | `C:/Program Files`、`C:/Program Files (x86)` |
| 程序数据 | `C:/ProgramData` 及其子目录 |
| 用户根 | `C:/Users`（裸根，不含具体用户目录） |
| 系统保留 | `C:/System Volume Information`、`C:/Recovery`、`C:/Boot`、`C:/PerfLogs` |
| 回收站 | `C:/$RECYCLE.BIN` |

这些路径即使写进 `targets.json` 且 `authorized: true`，也依然删不掉——两道闸门独立生效。

## 二、绝不纳入清单的目录

即使用户主动要求，也不加入可清理项：

- **个人文件区**：Desktop、Documents、Downloads、Pictures、Videos、Music、OneDrive 同步目录
- **源码与仓库**：任何含 `.git` 的目录、项目工作区
- **凭据与密钥**：`.ssh`、`.aws`、`.kube`、`.gnupg`、`.npmrc`、`.gitconfig`、浏览器 `Login Data` / `Cookies`
- **应用配置**：`settings.json`、IDE 配置目录（`JetBrains/*/options`）、`Roaming/<App>` 下的非缓存子目录
- **`.workbuddy` 目录本身**（存项目数据与记忆，不是缓存）
- **系统文件**：`hiberfil.sys`、`pagefile.sys`、`swapfile.sys`、`WinSxS`、`WinRE`

## 三、只输出命令、不代跑的操作

以下必须由用户在管理员终端自行确认执行：

| 操作 | 命令 | 影响 |
|---|---|---|
| 关闭休眠 | `powercfg /h off` | 禁用休眠与快速启动，可逆 |
| 组件清理 | `DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase` | 已安装更新无法卸载/回滚 |
| 清空回收站 | `Clear-RecycleBin -Force` | 永久删除，不可恢复 |
| 磁盘清理向导 | `cleanmgr /sagerun:1` | 按勾选项执行，可控 |
| Docker 瘦身 | `docker system prune -a --volumes` | 删除未使用镜像/容器/卷 |
| WSL 磁盘压缩 | `wsl --shutdown; Optimize-VHD -Path <vhdx> -Mode Full` | 需 Hyper-V 模块与管理员 |

## 四、删除行为规范

1. **只清空内容，保留目录本身**（`mode: "clear"`）。
   直接删目录会让程序启动时报错或重建慢。
2. **写 manifest 再删**：`clean_<ts>.log.manifest.txt` 逐行记录
   `字节数<TAB>绝对路径`，事后可查"到底删了什么"。
3. **单文件目标**（如 `state.vscdb`）用 `os.remove`；
   目录目标用 `shutil.rmtree` 逐子项处理。
4. **占用/权限失败不中断**：标 `PARTIAL(部分被占用)` 继续下一项，最后汇总。
5. **不进回收站**。这一点在交付说明与网页确认框里都必须出现。
6. **批量上限**：一次清理不超过一个 `--ids` 请求的范围；网页全量按钮只覆盖
   `authorized=true && risk=low` 的集合，不含 mid。

## 五、交付时必须告知用户的三件事

1. **删了什么**：路径清单 + 每项释放量。
2. **怎么恢复**：缓存类由程序按需重建；日志/历史类不可恢复；给出首次变慢的预期。
3. **没删什么**：mid 项与 locked 项的完整列表及原因——用户需要知道"剩下的空间从哪来"。

## 六、被拒绝时的正确姿势

`rejected` 里出现条目，说明请求越权或命中黑名单。**不要改代码放宽校验**，
而应：把原因原样告知用户 → 若是路径写错则修正 `targets.json` 的 `pattern` →
若是系统目录则给替代命令 → 重新扫描复验。
