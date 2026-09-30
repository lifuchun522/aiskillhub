# -*- coding: utf-8 -*-
"""9 篇生成双产物 + 双模式渲染验证。

验证模型：
  A) 单文件映射（预览面板）—— 只能拿到 html 本身，子目录不可达
     -> index.html 图片必挂；preview.html 必须全部加载成功
  B) 整目录映射（本地双击 file://）—— images/ 可达
     -> index.html 与 preview.html 都应加载成功
"""
import argparse
import http.server
import os
import socketserver
import subprocess
import sys
import threading

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

_ap = argparse.ArgumentParser(description="系列文章双产物生成 + 双模式渲染验证")
_ap.add_argument("--series-dir", required=True,
                 help="系列根目录（内含 01/ 02/ ... 各篇目录）")
_ap.add_argument("--templates", default=None,
                 help="脚本所在目录（默认取本脚本所在目录）")
_ap.add_argument("--python", default=sys.executable,
                 help="运行 generate_preview.py 的 python（默认当前解释器）")
_args = _ap.parse_args()

BASE = os.path.abspath(_args.series_dir)
T = os.path.abspath(_args.templates) if _args.templates else os.path.dirname(os.path.abspath(__file__))
PY = _args.python

# 自动探测篇目录（两位数字命名的子目录，升序）
CHAPTERS = sorted(
    n for n in os.listdir(BASE)
    if n.isdigit() and os.path.isdir(os.path.join(BASE, n))
)
if not CHAPTERS:
    print("[ERR] %s 下没有找到两位数字命名的篇目录" % BASE)
    sys.exit(1)

# ---------- 1. 批量生成 ----------
print("== 生成 ==")
for name in CHAPTERS:
    d = os.path.join(BASE, name)
    r = subprocess.run([PY, os.path.join(T, "generate_preview.py"), "--dir", d],
                       capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout or r.stderr).strip().split("\n")
    kb = " | ".join(x.strip() for x in out if "[OK]" in x)
    print("[%s] %s" % (name, kb))

# ---------- 2. 单文件映射服务器（模拟预览面板）----------
class SingleFile(http.server.BaseHTTPRequestHandler):
    root = None

    def do_GET(self):
        name = self.path.lstrip("/") or "index.html"
        p = os.path.join(self.root, name)
        if os.path.isfile(p):
            data = open(p, "rb").read()
            ct = "text/html; charset=utf-8" if name.endswith(".html") else "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


def check_single(root, page, url_path):
    """单文件映射：html 可达，子目录一律 404。"""
    h = type("H", (SingleFile,), {"root": root})
    srv = socketserver.TCPServer(("127.0.0.1", 0), h)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    page.goto("http://127.0.0.1:%d/%s" % (port, url_path))
    page.wait_for_timeout(1200)
    info = page.eval_on_selector_all("img", "els => els.map(e => e.naturalWidth)")
    srv.shutdown()
    srv.server_close()
    return info


def check_dir(root, page, name):
    """整目录映射（file://）：images/ 可达。"""
    page.goto("file:///%s/%s" % (root, name))
    page.wait_for_timeout(1200)
    return page.eval_on_selector_all("img", "els => els.map(e => e.naturalWidth)")


# ---------- 3. 验证 ----------
print()
print("== 验证 ==")
ok = True
with sync_playwright() as p:
    b = p.chromium.launch()
    for name in CHAPTERS:
        d = os.path.join(BASE, name)
        pg = b.new_page(viewport={"width": 750, "height": 900})

        # A) 单文件映射 —— preview.html
        a_full = check_single(d, pg, "preview.html")
        # A2) 单文件映射 —— index.html（预期挂掉，证明假设成立）
        a_light = check_single(d, pg, "index.html")
        # B) file:// 整目录 —— index.html
        b_light = check_dir(d, pg, "index.html")

        pg.close()

        full_ok = all(w > 0 for w in a_full)
        light_local_ok = all(w > 0 for w in b_light)
        if not (full_ok and light_local_ok):
            ok = False

        print("[%s] preview.html@单文件 %d/%d 可见 | index.html@file:// %d/%d 可见 | index.html@单文件 %d/%d（预期 0）"
              % (name, sum(1 for w in a_full if w > 0), len(a_full),
                 sum(1 for w in b_light if w > 0), len(b_light),
                 sum(1 for w in a_light if w > 0), len(a_light)))
    b.close()

print()
print("结论：", "全部通过" if ok else "存在待修项")
