# cleanc CLI 菜谱（examples）

所有命令在 `cleanc/scripts/` 目录下执行。依赖 Python 3.9+ 仅标准库，无需 `pip install`。

> 路径占位符：`%LOCAL%` = `C:\Users\<你>\AppData\Local`，`%ROAM%` = `...\AppData\Roaming`，`%HOME%` = `C:\Users\<你>`。

---

## 1. 只读扫描：看清能回收多少

```bat
python server.py scan
```

预期输出（节选）：

```
C盘可用 1625.4 MB | 权限 普通用户 | 候选 67 项 | 低风险授权 15 项 20101.6 MB
风险      清理前MB   授权  类别            路径
low       17978.1   Y     临时文件          C:\Users\Carter.li\AppData\Local\Temp
low         891.1   Y     包缓存            C:\Users\Carter.li\AppData\Local\uv\cache
low         503.8   Y     包缓存            C:\Users\Carter.li\AppData\Local\npm-cache
mid       71535.6   -     应用缓存          C:\Users\Carter.li\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache
...
```

把结果落 JSON（交给脚本/看板用）：

```bat
python server.py scan --json scan.json
```

---

## 2. 发现式扫描：找出清单外的大目录

用于判断「有没有新的缓存/日志目录值得加进 `targets.json`」。**不靠猜**，先看真实体积：

```bat
python server.py scan --root "C:\" --top 25
```

```
[发现] C:\ 下体积 TOP25（只读）
   35453.0 MB  C:\Users\Carter.li\AppData\Local\Docker\wsl
   23731.6 MB  C:\Windows\WinSxS
   12911.3 MB  C:\hiberfil.sys
   ...
```

---

## 3. 预演（dry-run）：先算释放量，不删任何东西

```bat
python server.py clean --ids __all_low__
```

```
[DRY-RUN] 处理 15 项
清理前 20101.6 MB -> 清理后 0.0 MB
节约空间 20101.6 MB (19.63 GB)
C盘可用 1625.4 MB -> 1625.4 MB
```

`__all_low__` = 全部 `risk=low && authorized=true` 的项。也可只选几项：

```bat
python server.py clean --ids local-temp,uv-cache,pip-cache
```

---

## 4. 真删：显式 `--apply`

```bat
python server.py clean --ids __all_low__ --apply
```

执行前会要求输入 `yes` 确认：

```
** 此操作非常危险，可能导致不可逆的数据丢失！**
即将清空下列授权目录的全部内容（目录本身保留）：
  - C:\Users\Carter.li\AppData\Local\Temp  (17978.1 MB)
  - C:\Users\Carter.li\AppData\Local\uv\cache  (891.1 MB)
  ...
确认执行请输入 yes: yes

[APPLY] 处理 15 项
清理前 20101.6 MB -> 清理后 2118.8 MB
节约空间 17982.8 MB (17.56 GB)
C盘可用 1625.4 MB -> 19408.2 MB
日志 D:\...\cleanc\scripts\logs\clean_20261021_123447_ffe701.log
```

非交互（CI / 脚本）加 `--yes` 跳过确认：

```bat
python server.py clean --ids local-temp --apply --yes
```

---

## 5. 网页 / 自检（替代 CLI）

```bat
:: 启动管理页（推荐双击 scripts\启动cleanc服务.bat，由你自己的会话拉起）
python server.py serve --port 8848
:: 浏览器打开 http://127.0.0.1:8848/

:: 端到端自检（37 断言，全 dry-run，不删文件）
python selftest.py --port 8848
```

---

## 6. 中风险项：只给命令，不代跑

中风险项（`risk=mid`，如 Docker / WinSxS / hiberfil）**不会出现在清理按钮里**，页面只展示 `impact` 与 `hint`。按页面给的命令在**管理员终端**自行执行：

```bat
:: 关闭休眠并释放 hiberfil.sys（约 12 GB，可逆）
powercfg /h off
:: 清理 WinSxS 已卸载更新（不可逆回滚，但安全）
DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase
:: Docker：先 prune 内部空间，再压缩 vhdx（直接删目录不释放空间）
docker system prune -a --volumes
wsl --shutdown
Optimize-VHD -Path "$env:LOCALAPPDATA\Docker\wsl\disk\docker-desktop-data\ext4.vhdx" -Mode Full
```
