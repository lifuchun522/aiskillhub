# cleanc 例子（examples）

本目录放可直接对照运行的样例，方便你在不真删文件的情况下理解 cleanc 的输入输出。

| 文件 | 用途 |
|---|---|
| [`scan-sample.json`](./scan-sample.json) | 一份**真实结构**的扫描结果样例（取自真实扫描、裁剪 12 项）。对应 `scan --json out.json` 的产物，字段与线上一致。 |
| [`cleanup-log-sample.log`](./cleanup-log-sample.log) | 一份**真实格式**的清理任务日志样例，覆盖 `OK` / `DRY-RUN` / `PARTIAL` / `BLOCKED(删除未生效)` 等状态，以及命中批量删除保护、进程占用时的处置命令。 |
| [`cli-cookbook.md`](./cli-cookbook.md) | CLI 命令菜谱：扫描、发现新目录、dry-run、真删、网页/自检、中风险项命令。每条都带预期输出。 |

## 怎么复现

样例是静态文件，下面命令会生成**你机器**的真实数据：

```bat
cd cleanc/scripts

:: 1) 生成你自己的扫描 JSON（等价于 scan-sample.json 的真实版）
python server.py scan --json ../examples/my-scan.json

:: 2) 先看能回收多少，不删
python server.py clean --ids __all_low__

:: 3) 真删（会要求输入 yes；或加 --yes 跳过）
python server.py clean --ids __all_low__ --apply
```

## 字段速查（scan-sample.json）

```jsonc
{
  "disk_free_mb": 1625.4,          // C 盘可用 MB
  "is_admin": false,               // 是否管理员（影响受保护目录能否删）
  "summary": { "total": 67, "low_authorized": 15, "low_authorized_mb": 20101.6, "mid_mb": 178867.2, "locked": 4 },
  "items": [
    {
      "id": "local-temp",
      "path": "C:\\Users\\...\\AppData\\Local\\Temp",
      "risk": "low",               // low=可清 / mid=只解释后果
      "authorized": true,          // 只有 risk=low && authorized=true 才能删
      "size_mb": 17978.1,
      "files": 256,
      "impact": "清理后：占用中的临时文件会被跳过；...",
      "hint": "",
      "cmd": "Get-ChildItem -LiteralPath \"...\" -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue",
      "no_go": false               // true 表示命中 NO_GO 黑名单，绝不可删
    }
  ]
}
```

## 状态取值（cleanup-log-sample.log 里出现）

`OK` · `DRY-RUN` · `PARTIAL` · `FAIL` · `BLOCKED(删除未生效)` · `TIMEOUT(批量删除被拦截)` · `SKIP(安全拦截)`

判定前**必须删后重新量体积**：只凭「调用没抛异常」就报 OK，会在删除被宿主策略静默忽略时给出假绿结果。
