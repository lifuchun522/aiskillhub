#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanc —— Windows 磁盘可清理目录：扫描 + 授权清理 + 本地管理页

仅支持 Windows。清理动作使用 Python 实现，同时记录等价的 PowerShell / cmd 指令，
以便用户在内置接口失败时（占用、权限不足）可复制命令自行处理。

安全边界（硬编码，不可由请求绕过）
  1. 只有 targets.json 中 authorized=true 且 risk=low 的条目可被清理；
  2. 请求传入的路径必须落在"本次扫描解析出的授权路径集合"内，否则拒绝；
  3. NO_GO 前缀（盘根 / Windows / Program Files / ProgramData / Users 根 /
     System Volume Information / Recovery / $RECYCLE.BIN）一律拒绝；
  4. 默认 dry-run；--apply 才真删；只清空目录内容，保留目录本身；
  5. 清理前先写 manifest（文件清单+体积）到 logs/，便于事后追溯。

清理流程通过异步任务执行，前端用 /api/job 轮询实时日志：
  每个目录记录 —— 路径 / 执行指令 / 清理前 MB / 清理后 MB / 状态 / 失败处置命令

CLI
  python server.py scan  [--root C:/] [--top 20] [--json out.json]
  python server.py serve [--port 8848]
  python server.py clean --ids a,b,c [--apply] [--yes]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS_FILE = os.path.join(HERE, "targets.json")
HTML_FILE = os.path.join(HERE, "index.html")
LOG_DIR = os.path.join(HERE, "logs")

# ----------------------------------------------------------------- Windows 前置
if os.name != "nt":
    sys.stderr.write("[cleanc] 本工具仅支持 Windows（路径规则与清理指令均为 Windows 专有）。\n")
    sys.exit(3)

IS_ADMIN = False
try:
    import ctypes
    IS_ADMIN = bool(ctypes.windll.shell32.IsUserAnAdmin())
except Exception:                                                     # noqa: BLE001
    IS_ADMIN = False

# ----------------------------------------------------------------- 安全常量
NO_GO_EXACT = {
    "c:", "c:/", "c:/users", "c:/program files", "c:/program files (x86)",
    "c:/programdata", "c:/windows", "c:/system volume information",
    "c:/recovery", "c:/$recycle.bin",
}
NO_GO_PREFIX = (
    "c:/windows/", "c:/program files/", "c:/program files (x86)/",
    "c:/programdata/", "c:/system volume information/", "c:/recovery/",
    "c:/$recycle.bin/", "c:/boot/", "c:/perflogs/",
)

HOME = os.path.expanduser("~")
LOCAL = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
ROAM = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")


def norm(p: str) -> str:
    """统一为小写正斜杠、无尾斜杠的绝对路径形式，用于比较与拦截。"""
    p = (p or "").replace("\\", "/").strip()
    if len(p) >= 2 and p[1] == ":" and not p[2:3]:
        p = p + "/"
    while len(p) > 1 and p.endswith("/") and not p.endswith(":/"):
        p = p[:-1]
    return p.lower()


def expand(pattern: str) -> list[str]:
    """展开 %HOME%/%LOCAL%/%ROAM% 占位符与 * 通配，返回真实存在的路径。"""
    p = pattern
    for k, v in (("%HOME%", HOME), ("%LOCAL%", LOCAL), ("%ROAM%", ROAM)):
        p = p.replace(k, v.replace("\\", "/"))
    if "*" in p:
        return [os.path.normpath(x) for x in sorted(glob.glob(p))]
    return [os.path.normpath(p)] if os.path.exists(p) else []


def is_no_go(path: str) -> bool:
    n = norm(path)
    if n in NO_GO_EXACT:
        return True
    return any(n.startswith(x) for x in NO_GO_PREFIX)


# ----------------------------------------------------------------- 等价指令
def cmd_clear(path: str) -> str:
    """清空目录内容、保留目录本身 —— 等价 PowerShell 指令。"""
    if os.path.isfile(path):
        return f'Remove-Item -LiteralPath "{path}" -Force'
    return (f'Get-ChildItem -LiteralPath "{path}" -Force '
            f'| Remove-Item -Recurse -Force -ErrorAction SilentlyContinue')


def cmd_clear_cmd(path: str) -> str:
    return f'rmdir /s /q "{path}" && mkdir "{path}"'


def cmd_force_delete(path: str) -> str:
    return f'Remove-Item -LiteralPath "{path}" -Recurse -Force'


def cmd_elevate(path: str) -> list[str]:
    user = os.environ.get("USERNAME") or "%USERNAME%"
    return [
        f'takeown /f "{path}" /r /d y',
        f'icacls "{path}" /grant "{user}":F /t',
    ]


# ----------------------------------------------------------------- 体积统计
def path_size(path: str) -> tuple[int, int]:
    """返回 (字节数, 文件数)。逐项容错，不因单个文件失败而中断。"""
    if os.path.isfile(path):
        try:
            return os.path.getsize(path), 1
        except OSError:
            return 0, 0
    total = files = 0
    stack = [path]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            total += e.stat(follow_symlinks=False).st_size
                            files += 1
                    except OSError:
                        continue
        except OSError:
            continue
    return total, files


def mb(nbytes: int) -> float:
    return round(nbytes / 1048576.0, 1)


def disk_free_mb(path: str) -> float:
    try:
        drive = os.path.splitdrive(os.path.abspath(path))[0] or "C:"
        return mb(shutil.disk_usage(drive + os.sep).free)
    except OSError:
        return -1.0


# ----------------------------------------------------------------- 清单加载
def load_entries() -> list[dict]:
    with open(TARGETS_FILE, encoding="utf-8") as f:
        return json.load(f)["entries"]


def resolve_entry(entry: dict) -> list[str]:
    return expand(entry["pattern"])


_SCAN_CACHE: dict = {"at": 0.0, "data": None}
SCAN_TTL = 300.0          # 秒；期间复用扫描结果，避免每次点清理都重扫全盘


def scan(force: bool = False) -> dict:
    """扫描授权清单，返回带体积/风险/影响的条目。只读，不删任何东西。"""
    age = time.time() - _SCAN_CACHE["at"]
    if not force and _SCAN_CACHE["data"] is not None and age < SCAN_TTL:
        return _SCAN_CACHE["data"]

    entries = load_entries()

    jobs: list[tuple[dict, str]] = []
    for e in entries:
        for p in resolve_entry(e):
            jobs.append((e, p))

    def work(job):
        e, p = job
        size, cnt = path_size(p)
        return {
            "id": e["id"],
            "path": p,
            "risk": e["risk"],
            "category": e["category"],
            "desc": e["desc"],
            "impact": e.get("impact", ""),
            "hint": e.get("hint", ""),
            "cmd": cmd_clear(p),
            "mode": e.get("mode", "clear"),
            "authorized": bool(e.get("authorized")) and e["risk"] == "low",
            "size_mb": mb(size),
            "files": cnt,
            "no_go": is_no_go(p),
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(work, jobs))

    items = [i for i in items if i["size_mb"] > 0]
    items.sort(key=lambda x: -x["size_mb"])

    low_auth = [i for i in items if i["risk"] == "low" and i["authorized"]]
    data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "host": HOME,
        "is_admin": IS_ADMIN,
        "disk_free_mb": disk_free_mb(HOME),
        "summary": {
            "total": len(items),
            "low_authorized": len(low_auth),
            "low_authorized_mb": round(sum(i["size_mb"] for i in low_auth), 1),
            "mid_mb": round(sum(i["size_mb"] for i in items if i["risk"] == "mid"), 1),
            "locked": len([i for i in items if i["risk"] == "low" and not i["authorized"]]),
        },
        "items": items,
    }
    _SCAN_CACHE["at"] = time.time()
    _SCAN_CACHE["data"] = data
    return data


def _patch_cache(finished: list[dict]) -> None:
    """清理后就地更新扫描缓存，避免前端再等一次 51 秒全盘重扫。"""
    data = _SCAN_CACHE["data"]
    if not data:
        _SCAN_CACHE["at"] = 0.0
        return
    after = {norm(r["after_path"]): r for r in finished}
    kept = []
    for it in data["items"]:
        r = after.get(norm(it["path"]))
        if r is None:
            kept.append(it)
        elif r["after_mb"] > 0:
            it["size_mb"] = r["after_mb"]
            kept.append(it)
    data["items"] = kept
    data["disk_free_mb"] = disk_free_mb(HOME)
    low = [i for i in kept if i["risk"] == "low" and i["authorized"]]
    data["summary"].update({
        "total": len(kept),
        "low_authorized": len(low),
        "low_authorized_mb": round(sum(i["size_mb"] for i in low), 1),
    })
    _SCAN_CACHE["at"] = time.time()


# ----------------------------------------------------------------- 异步清理任务
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
JOB_KEEP = 20

# 宿主安全策略（如 WorkBuddy 的 safe-delete）会对批量删除（默认 >50 个文件）做拦截，
# 表现为删除调用长时间不返回。这里用看门狗让任务始终有终态，并把可复制的手工指令交给用户。
BULK_FILE_THRESHOLD = int(os.environ.get("CLEANC_BULK_THRESHOLD", "50"))
DEL_TIMEOUT_BASE = 20.0
DEL_TIMEOUT_PER_FILE = 0.2
DEL_TIMEOUT_MAX = 120.0


def _del_timeout(nfiles: int) -> float:
    return min(DEL_TIMEOUT_MAX, DEL_TIMEOUT_BASE + nfiles * DEL_TIMEOUT_PER_FILE)


def _delete_path(path: str, is_file: bool) -> tuple[str, list[str], str, bool, int]:
    """
    删除目标内容（保留目录本身），带看门狗。
    返回 (status, failed_list, err_text, timed_out, files_considered)。
    status: OK / PARTIAL / FAIL / TIMEOUT(批量删除被拦截)
    """
    holder: dict = {"failed": [], "err": ""}

    def work() -> None:
        try:
            if is_file:
                os.remove(path)
                return
            for name in os.listdir(path):
                fp = os.path.join(path, name)
                try:
                    shutil.rmtree(fp) if os.path.isdir(fp) else os.remove(fp)
                except OSError as exc:
                    holder["failed"].append(fp)
                    holder["err"] = f"[WinError {getattr(exc, 'winerror', '-')}] {exc.strerror}"
        except OSError as exc:
            holder["err"] = f"[WinError {getattr(exc, 'winerror', '-')}] {exc.strerror}"

    n = 1 if is_file else sum(len(f) for _r, _d, f in os.walk(path)) or 1
    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(_del_timeout(n))
    if th.is_alive():
        return "TIMEOUT(批量删除被拦截)", [], holder["err"], True, n
    if holder["failed"]:
        return "PARTIAL", holder["failed"], holder["err"], False, n
    if holder["err"]:
        return "FAIL", [], holder["err"], False, n
    return "OK", [], "", False, n


def _new_job(apply: bool) -> dict:
    job_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    os.makedirs(LOG_DIR, exist_ok=True)
    job = {
        "id": job_id,
        "apply": apply,
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        "_t0": time.time(),
        "done": False,
        "lines": [],
        "result": None,
        "log_file": os.path.join(LOG_DIR, ("clean_" if apply else "dryrun_") + job_id + ".log"),
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
        if len(JOBS) > JOB_KEEP:
            for k in sorted(JOBS)[:len(JOBS) - JOB_KEEP]:
                JOBS.pop(k, None)
    return job


def start_clean(ids: list[str], apply: bool) -> dict:
    job = _new_job(apply)
    threading.Thread(target=_clean_worker, args=(job, ids), daemon=True).start()
    return job


def _clean_worker(job: dict, ids: list[str]) -> None:
    apply = job["apply"]
    data = scan()
    by_id: dict[str, list[dict]] = {}
    for i in data["items"]:
        by_id.setdefault(i["id"], []).append(i)
    authorized_paths = {norm(i["path"]) for i in data["items"] if i["authorized"]}

    targets: list[dict] = []
    rejected: list[dict] = []
    for tid in ids:
        if tid == "__all_low__":
            targets += [i for i in data["items"] if i["authorized"]]
            continue
        for i in by_id.get(tid, []):
            if not i["authorized"]:
                rejected.append({"path": i["path"], "reason": "非授权目录(risk=mid 或 authorized=false)"})
            elif i["no_go"]:
                rejected.append({"path": i["path"], "reason": "命中 NO_GO 拦截"})
            elif norm(i["path"]) not in authorized_paths:
                rejected.append({"path": i["path"], "reason": "路径不在本次授权的解析集合内"})
            else:
                targets.append(i)

    seen: set[str] = set()
    targets = [t for t in targets if not (norm(t["path"]) in seen or seen.add(norm(t["path"])))]

    finished: list[dict] = []
    total_before = sum(t["size_mb"] for t in targets) or 0.0
    df_before = disk_free_mb(HOME)

    with open(job["log_file"], "w", encoding="utf-8") as log:
        def w(line: str = "") -> None:
            log.write(line + "\n")
            log.flush()
            job["lines"].append(line)
            print(line, flush=True)

        w("=" * 88)
        w(f" cleanc {'APPLY（实际清理）' if apply else 'DRY-RUN（只统计不删除）'}"
          f"   任务 {job['id']}   开始 {job['started']}")
        w(f" 主机 {HOME}")
        w(f" 执行权限：{'管理员（可删除受保护文件）' if IS_ADMIN else '普通用户（ProgramData/受保护目录会失败，需提权）'}")
        w(f" 待处理 {len(targets)} 个目录，清理前合计 {total_before:.1f} MB")
        w(f" C 盘可用（清理前）{df_before:.1f} MB")
        w("=" * 88)

        for t in targets:
            p = t["path"]
            b = t["size_mb"]
            is_file = os.path.isfile(p)
            w("")
            w(f"▶ 目录：{p}")
            w(f"  执行指令：{cmd_clear(p)}")
            w(f"  清理前：{b:.1f} MB（{t['files']} 个文件）")

            if not apply:
                w(f"  清理后：0.0 MB    释放：{b:.1f} MB    状态：DRY-RUN（未删除）")
                finished.append({"after_path": p, "before_mb": b, "after_mb": 0.0,
                                 "freed_mb": b, "status": "DRY-RUN", "cmd": cmd_clear(p)})
                continue

            if is_no_go(p) or norm(p) not in authorized_paths:
                w(f"  清理后：{b:.1f} MB    释放：0.0 MB    状态：SKIP（安全拦截，未删除）")
                finished.append({"after_path": p, "before_mb": b, "after_mb": b,
                                 "freed_mb": 0.0, "status": "SKIP(安全拦截)", "cmd": cmd_clear(p)})
                continue

            if t["files"] > BULK_FILE_THRESHOLD:
                w(f"  预检：{t['files']} 个文件 > 本机批量删除阈值 {BULK_FILE_THRESHOLD}，"
                  f"宿主安全策略可能拦截批量删除（表现为长时间无进展）。"
                  f"若本次失败，请用下方给出的指令自行清理。")

            # manifest：删之前先记录将消失的文件
            try:
                with open(job["log_file"] + ".manifest.txt", "a", encoding="utf-8") as mf:
                    for root, _dirs, files in os.walk(p):
                        for fn in files:
                            fp = os.path.join(root, fn)
                            try:
                                mf.write(f"{os.path.getsize(fp)}\t{fp}\n")
                            except OSError:
                                pass
            except OSError:
                pass

            status, failed, err_text, timed_out, nfiles = _delete_path(p, is_file)

            # 复核：删除调用可能被宿主策略静默忽略（正常返回但文件仍在），
            # 必须先复查再判定状态，否则界面会报假绿的 OK。
            abytes, afiles = path_size(p)
            a = mb(abytes)
            if status == "OK":
                if is_file and os.path.exists(p):
                    status = "BLOCKED(删除未生效)"
                elif not is_file and afiles > 0 and (b - a) < 1.0:
                    status = "BLOCKED(删除未生效)"

            w(f"  清理后：{a:.1f} MB    释放：{b - a:.1f} MB    状态：{status}")

            if status in ("PARTIAL", "FAIL", "TIMEOUT(批量删除被拦截)", "BLOCKED(删除未生效)"):
                if timed_out:
                    w(f"  未完成：扫描到 {nfiles} 个文件，删除调用超过 "
                      f"{_del_timeout(nfiles):.0f} 秒仍未返回，判定为本机安全策略拦截批量删除。")
                    w("  处置方式 —— 用你自己的终端执行（不受本进程策略限制）：")
                    w(f"        PowerShell: {cmd_force_delete(p)}")
                    w(f"        cmd:        {cmd_clear_cmd(p)}")
                    w(f"  分批替代：每次删除不超过 {BULK_FILE_THRESHOLD} 个文件后重试，"
                      f"或在资源管理器中手动清空该目录。")
                elif status == "BLOCKED(删除未生效)":
                    w(f"  未生效：删除调用正常返回，但复核发现仍有 {afiles} 个文件、"
                      f"{a:.1f} MB 未下降 —— 操作被本机批量删除保护静默忽略。")
                    w("  处置方式 —— 二选一：")
                    w("   A. 用你自己的终端执行（推荐，一定可行）：")
                    w(f"        PowerShell: {cmd_force_delete(p)}")
                    w(f"        cmd:        {cmd_clear_cmd(p)}")
                    w(f"   B. 双击运行 启动cleanc服务.bat，让服务在你自己的会话中启动，"
                      f"再回到页面点击清理。")
                else:
                    w(f"  未能删除 {len(failed) if failed else 1} 项，示例：{failed[0] if failed else p}")
                    w(f"  原因：{err_text or '文件被其他进程占用，或当前账户无删除权限'}")
                    w("  处置方式（自行选择其一，复制到 【管理员 PowerShell】 执行）：")
                    w("   A. 先提权接管再重试本页清理：")
                    for c in cmd_elevate(p):
                        w(f"        {c}")
                    w("   B. 直接强制删除等价指令：")
                    w(f"        PowerShell: {cmd_force_delete(p)}")
                    w(f"        cmd:        {cmd_clear_cmd(p)}")
                    w("   C. 若为进程占用：先关闭对应程序（浏览器 / IDE / 钉钉 / 飞书 / Docker），再重试。")

            finished.append({"after_path": p, "before_mb": b, "after_mb": a,
                             "freed_mb": round(b - a, 1), "status": status, "cmd": cmd_clear(p)})

        total_after = sum(r["after_mb"] for r in finished)
        saved = round(total_before - total_after, 1)
        df_after = disk_free_mb(HOME)
        w("")
        w("-" * 88)
        w(f" 汇总：清理前 {total_before:.1f} MB → 清理后 {total_after:.1f} MB，"
          f"节约 {saved:.1f} MB（{saved / 1024:.2f} GB）")
        w(f" C 盘可用：{df_before:.1f} MB → {df_after:.1f} MB（增加 {df_after - df_before:.1f} MB）")
        bad = [r for r in finished if r["status"] not in ("OK", "DRY-RUN")]
        if bad:
            w(f" 需人工处理 {len(bad)} 项，见上方各项的处置命令。")
        for r in rejected:
            w(f" [拒绝] {r['path']} —— {r['reason']}")
        w("=" * 88)

    if apply:
        _patch_cache(finished)

    with JOBS_LOCK:
        job["done"] = True
        job["result"] = {
            "ok": True,
            "mode": "apply" if apply else "dry-run",
            "log_file": job["log_file"],
            "total_before_mb": round(total_before, 1),
            "total_after_mb": round(total_after, 1),
            "saved_mb": saved,
            "saved_gb": round(saved / 1024, 2),
            "disk_free_before_mb": df_before,
            "disk_free_after_mb": df_after,
            "is_admin": IS_ADMIN,
            "items": [{"id": "", "path": r["after_path"], "before_mb": r["before_mb"],
                       "after_mb": r["after_mb"], "freed_mb": r["freed_mb"],
                       "status": r["status"], "cmd": r["cmd"]} for r in finished],
            "rejected": rejected,
        }


def clean_sync(ids: list[str], apply: bool = False, echo: bool = True) -> dict:
    """CLI / 自检用：同步跑完一个清理任务。"""
    job = start_clean(ids, apply)
    while not job["done"]:
        time.sleep(0.2)
    if not echo:
        job["lines"] = []
    return job["result"]


# ----------------------------------------------------------------- 发现式扫描
def top_dirs(root: str, top: int = 20) -> list[dict]:
    """只读统计 root 下一级目录体积，用于发现新的可清理目标。"""
    root = os.path.abspath(root)
    try:
        subs = [os.path.join(root, e.name) for e in os.scandir(root) if e.is_dir(follow_symlinks=False)]
    except OSError as exc:
        return [{"path": root, "error": str(exc)}]
    with ThreadPoolExecutor(max_workers=6) as pool:
        sizes = list(pool.map(lambda p: path_size(p)[0], subs))
    rows = [{"path": p, "size_mb": mb(s)} for p, s in zip(subs, sizes)]
    rows.sort(key=lambda r: -r["size_mb"])
    return rows[:top]


# ----------------------------------------------------------------- Web
class Handler(BaseHTTPRequestHandler):
    server_version = "cleanc/1.1"

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError):
            pass

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            try:
                with open(HTML_FILE, encoding="utf-8") as f:
                    self._send(200, f.read().encode("utf-8"), "text/html; charset=utf-8")
            except OSError:
                self._send(500, b"index.html missing", "text/plain; charset=utf-8")
            return
        if u.path == "/api/targets":
            refresh = (parse_qs(u.query).get("refresh") or [""])[0] in ("1", "true")
            try:
                self._json(scan(force=refresh))
            except Exception as exc:                                   # noqa: BLE001
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if u.path == "/api/job":
            jid = (parse_qs(u.query).get("id") or [""])[0]
            job = JOBS.get(jid)
            if not job:
                self._json({"ok": False, "error": "job not found"}, 404)
                return
            with JOBS_LOCK:
                self._json({"ok": True, "id": job["id"], "apply": job["apply"],
                            "started": job["started"], "done": job["done"],
                            "elapsed": round(time.time() - job["_t0"], 1),
                            "lines": list(job["lines"]), "result": job["result"]})
            return
        if u.path == "/api/log":
            name = (parse_qs(u.query).get("name") or [""])[0]
            safe = os.path.basename(name)
            p = os.path.join(LOG_DIR, safe)
            if not safe or not os.path.isfile(p):
                self._json({"ok": False, "error": "log not found"}, 404)
                return
            with open(p, encoding="utf-8", errors="replace") as f:
                self._send(200, f.read().encode("utf-8"), "text/plain; charset=utf-8")
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._json({"ok": False, "error": "invalid json"}, 400)
            return

        if u.path == "/api/clean":
            ids = body.get("ids") or []
            if not isinstance(ids, list) or not ids:
                self._json({"ok": False, "error": "ids 不能为空"}, 400)
                return
            apply = bool(body.get("apply"))
            try:
                job = start_clean(ids, apply)
            except Exception as exc:                                   # noqa: BLE001
                self._json({"ok": False, "error": str(exc)}, 500)
                return
            print(f"[cleanc] 任务 {job['id']} 已启动："
                  f"{'实际清理' if apply else '预演'} ids={ids}", flush=True)
            self._json({"ok": True, "job_id": job["id"], "apply": job["apply"],
                        "log_file": job["log_file"]})
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):                                # noqa: A003
        if os.environ.get("CLEANC_HTTP_DEBUG"):
            sys.stderr.write("[web] %s\n" % (fmt % args))


class _Server(ThreadingHTTPServer):
    # Windows 下 SO_REUSEADDR 会允许第二个进程重复绑定同一端口，
    # 造成新旧实例同时监听、请求随机落到旧代码上。禁用后重复启动会直接报端口占用。
    allow_reuse_address = False


def serve(port: int) -> None:
    if IS_ADMIN:
        print("[cleanc] 当前以管理员权限运行 —— 受保护目录也可清理。", flush=True)
    else:
        print("[cleanc] 当前为普通用户权限 —— ProgramData / 受保护目录会清理失败，"
              "日志中会给出提权命令。", flush=True)
    try:
        httpd = _Server(("127.0.0.1", port), Handler)
    except OSError as exc:
        sys.stderr.write(f"[cleanc] 端口 {port} 无法监听：{exc}\n"
                         f"         可能已有 cleanc 服务在跑。先结束它：\n"
                         f"         Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" "
                         f"| Where-Object {{$_.CommandLine -match 'server\\.py\\s+serve'}} "
                         f"| ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}\n"
                         f"         或换端口：python server.py serve --port 8899\n")
        return
    print(f"[cleanc] 管理页: http://127.0.0.1:{port}/   (Ctrl+C 退出)", flush=True)
    print(f"[cleanc] 授权清单: {TARGETS_FILE}", flush=True)
    print(f"[cleanc] 日志目录: {LOG_DIR}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[cleanc] 已退出")
    finally:
        httpd.server_close()


# ----------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(prog="cleanc", description="Windows 磁盘可清理目录扫描与授权清理")
    sub = ap.add_subparsers(dest="cmd")

    s1 = sub.add_parser("scan", help="只读扫描授权清单")
    s1.add_argument("--root", help="额外统计该目录下的一级子目录体积（发现用，只读）")
    s1.add_argument("--top", type=int, default=20)
    s1.add_argument("--json", dest="json_out")

    s2 = sub.add_parser("serve", help="启动本地管理页")
    s2.add_argument("--port", type=int, default=8848)

    s3 = sub.add_parser("clean", help="清理授权低风险目录")
    s3.add_argument("--ids", required=True, help="逗号分隔的 id，或 __all_low__")
    s3.add_argument("--apply", action="store_true", help="真正删除；缺省为 dry-run")
    s3.add_argument("--yes", action="store_true", help="跳过交互确认")

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 2

    if args.cmd == "serve":
        serve(args.port)
        return 0

    if args.cmd == "scan":
        data = scan()
        print(f"C盘可用 {data['disk_free_mb']:.1f} MB | 权限 "
              f"{'管理员' if data['is_admin'] else '普通用户'} | 候选 {data['summary']['total']} 项 | "
              f"低风险授权 {data['summary']['low_authorized']} 项 "
              f"{data['summary']['low_authorized_mb']:.1f} MB")
        print(f"{'风险':<7}{'清理前MB':>10}  {'授权':<6}{'类别':<12}路径")
        for i in data["items"]:
            print(f"{i['risk']:<9}{i['size_mb']:>10.1f}  {'Y' if i['authorized'] else '-':<8}"
                  f"{i['category']:<14}{i['path']}")
        if args.root:
            print(f"\n[发现] {args.root} 下体积 TOP{args.top}（只读）")
            for r in top_dirs(args.root, args.top):
                print(f"  {r['size_mb']:>10.1f} MB  {r['path']}")
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\nJSON 已写入 {args.json_out}")
        return 0

    if args.cmd == "clean":
        ids = [x.strip() for x in args.ids.split(",") if x.strip()]
        if args.apply and not args.yes:
            print("** 此操作非常危险，可能导致不可逆的数据丢失！**")
            print("即将清空下列授权目录的全部内容（目录本身保留）：")
            for i in scan()["items"]:
                if i["authorized"] and (i["id"] in ids or "__all_low__" in ids):
                    print(f"  - {i['path']}  ({i['size_mb']:.1f} MB)")
            if input("确认执行请输入 yes: ").strip() != "yes":
                print("[ABORT] 已取消，未做任何修改。")
                return 1
        res = clean_sync(ids, apply=args.apply)
        print(f"\n{'[APPLY]' if args.apply else '[DRY-RUN]'} 处理 {len(res['items'])} 项")
        print(f"清理前 {res['total_before_mb']:.1f} MB -> 清理后 {res['total_after_mb']:.1f} MB")
        print(f"节约空间 {res['saved_mb']:.1f} MB ({res['saved_gb']} GB)")
        print(f"C盘可用 {res['disk_free_before_mb']:.1f} MB -> {res['disk_free_after_mb']:.1f} MB")
        print(f"日志 {res['log_file']}")
        for r in res["rejected"]:
            print(f"  [拒绝] {r['path']} — {r['reason']}")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
