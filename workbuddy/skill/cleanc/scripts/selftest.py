#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanc 自检：对运行中的 cleanc 服务做端到端断言。
除最后一组外全部为只读 / dry-run —— 不产生任何删除。

用法:
    python selftest.py [--port 8848]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:{port}"
passed = 0
failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}  {detail}")


def get(path: str, timeout: int = 300):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def post(path: str, payload: dict, timeout: int = 60):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "replace"))


def run_job(payload: dict, timeout: int = 600) -> dict:
    """/api/clean 起任务 → 轮询 /api/job 直到 done，返回 job 快照。"""
    st, r = post("/api/clean", payload)
    if st != 200 or r.get("ok") is False:
        return {"_submit_error": f"status={st} body={r}"}
    jid = r["job_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        _st, body = get(f"/api/job?id={jid}")
        j = json.loads(body)
        if j.get("done"):
            return j
        time.sleep(0.3)
    return {"_timeout": jid}


def main() -> int:
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8848)
    args = ap.parse_args()
    BASE = BASE.format(port=args.port)

    print("[1] GET / — 管理页")
    try:
        st, html = get("/")
        check("管理页返回 200", st == 200, f"status={st}")
        check("含清理按钮与实时日志容器", 'btn-all' in html and 'id="log"' in html and 'data-act="one"' in html)
        check("含中风险阈值控件", 'midMin' in html)
        check("含静态打开时的报错提示", 'serve --port' in html)
    except Exception as exc:                                          # noqa: BLE001
        check("管理页可访问", False, str(exc))
        return 1

    print("[2] GET /api/targets — 扫描")
    st, body = get("/api/targets?refresh=1")
    data = json.loads(body)
    check("扫描返回 200", st == 200, f"status={st}")
    s = data["summary"]
    print(f"       候选 {s['total']} 项 | 低风险授权 {s['low_authorized']} 项 "
          f"{s['low_authorized_mb']} MB | 中风险 {s['mid_mb']} MB | "
          f"C盘可用 {data['disk_free_mb']} MB | 权限 {'管理员' if data['is_admin'] else '普通用户'}")
    check("存在低风险授权项", s["low_authorized"] >= 1)
    check("每项字段完整",
          all({"id", "path", "risk", "size_mb", "authorized", "impact", "cmd"} <= set(i)
              for i in data["items"]))
    check("授权项 cmd 非空", all(i["cmd"] for i in data["items"] if i["authorized"]))
    check("授权项必为 low", all(i["risk"] == "low" for i in data["items"] if i["authorized"]))
    check("无 NO_GO 目录被授权",
          not any(i["no_go"] for i in data["items"] if i["authorized"]),
          str([i["path"] for i in data["items"] if i["no_go"] and i["authorized"]]))
    auth = [i for i in data["items"] if i["authorized"]]
    mid_ids = [i["id"] for i in data["items"] if i["risk"] == "mid"]

    print("[3] POST /api/clean 空 ids — 应 400")
    st, r = post("/api/clean", {"ids": []})
    check("空 ids 被拒", st == 400 and r.get("ok") is False, f"status={st} body={r}")

    print("[4] POST /api/clean 非法 job id")
    st, r = get("/api/job?id=not-exist", timeout=20)
    check("未知 job 返回 404", st == 404, f"status={st}")

    print("[5] dry-run 单项授权目录 → 轮询 job")
    j = run_job({"ids": [auth[0]["id"]], "apply": False})
    check("任务完成", j.get("done") is True, str(j)[:200])
    check("轮询到实时日志行", len(j.get("lines") or []) >= 8, f"lines={len(j.get('lines') or [])}")
    res = j.get("result") or {}
    check("结果 mode=dry-run", res.get("mode") == "dry-run", str(res)[:160])
    check("结果含释放量", res.get("saved_mb", 0) > 0, f"saved={res.get('saved_mb')}")
    check("dry-run 未产生删除残留", all(i["after_mb"] == 0 for i in res.get("items", [])),
          str(res.get("items"))[:200])

    print("[6] 日志四项字段齐全")
    txt = "\n".join(j["lines"])
    for field in ("目录：", "执行指令：", "清理前：", "清理后："):
        check(f"日志含「{field}」", field in txt)
    check("日志含权限状态", "执行权限" in txt)
    check("日志含状态标记", "状态：DRY-RUN" in txt or "状态：OK" in txt)

    print("[7] 中风险 id — 应被拒绝")
    if mid_ids:
        j = run_job({"ids": [mid_ids[0]], "apply": False})
        res = j.get("result") or {}
        check("中风险项进入 rejected", len(res.get("rejected", [])) >= 1 and res["items"] == [],
              str(res)[:200])
    else:
        print("        (无中风险项，跳过)")

    print("[8] 未授权低风险 id — 应被拒绝")
    j = run_job({"ids": ["win-logs", "recycle-bin"], "apply": False})
    res = j.get("result") or {}
    check("未授权项被拒绝", len(res.get("rejected", [])) == 2 and res["items"] == [], str(res)[:200])

    print("[9] 伪造 id 路径注入 — 不得产生任何删除")
    j = run_job({"ids": ["C:/Windows/System32", "../.."], "apply": True})
    res = j.get("result") or {}
    check("伪造 id 未被处理", res.get("items") == [], str(res)[:200])

    print("[10] dry-run 全部低风险")
    j = run_job({"ids": ["__all_low__"], "apply": False})
    res = j.get("result") or {}
    check("全量 dry-run 成功", res.get("ok") is True)
    check("全量项数 = 授权项数", len(res.get("items", [])) == len(auth),
          f"{len(res.get('items', []))} vs {len(auth)}")
    print(f"       清理前合计 {res.get('total_before_mb')} MB → 预计释放 "
          f"{res.get('saved_mb')} MB（{res.get('saved_gb')} GB）")

    print("[11] 服务端日志可回读")
    name = (res.get("log_file") or "").replace("\\", "/").split("/")[-1]
    st, txt = get(f"/api/log?name={name}", timeout=30)
    check("日志返回 200 且含四字段",
          st == 200 and "执行指令：" in txt and "清理前：" in txt and "清理后：" in txt,
          f"status={st}")
    check("日志含目录行", "▶ 目录：" in txt)

    print("[12] 失败处置命令与安全拦截（直接调函数验证）")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import server as S                                              # noqa: E402
    elev = S.cmd_elevate(r"C:\test")
    check("提权命令含 takeown / icacls",
          len(elev) == 2 and "takeown" in elev[0] and "icacls" in elev[1], str(elev))
    check("目录清理指令为 PowerShell", "Remove-Item" in S.cmd_clear(r"C:\test"))
    check("cmd 版清空指令", "rmdir /s /q" in S.cmd_clear_cmd(r"C:\test"))
    check("强制删除指令", S.cmd_force_delete(r"C:\test").startswith("Remove-Item -LiteralPath"))
    check("NO_GO 拦截系统目录",
          all(S.is_no_go(p) for p in (
              r"C:\Windows", r"C:\Windows\System32", r"C:\Program Files",
              r"C:\$RECYCLE.BIN", r"C:\Users")), "系统目录未被拦截")
    check("NO_GO 不误伤用户缓存",
          not any(S.is_no_go(p) for p in (
              r"C:\Users\Carter.li\AppData\Local\Temp",
              r"C:\Users\Carter.li\AppData\Local\Microsoft\Windows\WebCache")),
          "用户缓存被误拦")
    check("norm 归一化一致",
          S.norm("C:\\Users\\x\\") == S.norm("c:/users/x") == "c:/users/x",
          S.norm("C:\\Users\\x\\"))

    print(f"\n结果: {passed} 通过 / {failed} 失败")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
