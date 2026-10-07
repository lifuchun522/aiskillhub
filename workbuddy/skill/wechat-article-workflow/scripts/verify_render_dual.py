# -*- coding: utf-8 -*-
"""生成 index.html + file:// 渲染验证。

只验证本地双击场景：images/ 与 index.html 同级可达，图片全部可见。
不再生成 / 校验 preview.html（base64 自包含版已移除）。
"""
import argparse
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

_ap = argparse.ArgumentParser(description="系列文章 index.html 生成 + file:// 渲染验证")
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

CHAPTERS = sorted(
    n for n in os.listdir(BASE)
    if n.isdigit() and os.path.isdir(os.path.join(BASE, n))
)
if not CHAPTERS:
    print("[ERR] %s 下没有找到两位数字命名的篇目录" % BASE)
    sys.exit(1)

print("== 生成 ==")
for name in CHAPTERS:
    d = os.path.join(BASE, name)
    r = subprocess.run([PY, os.path.join(T, "generate_preview.py"), "--dir", d],
                       capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout or r.stderr).strip().split("\n")
    kb = " | ".join(x.strip() for x in out if "[OK]" in x or "[ERR]" in x or "[WARN]" in x)
    print("[%s] %s" % (name, kb or ("exit=%d" % r.returncode)))
    if r.returncode != 0:
        print((r.stderr or r.stdout or "").strip())
        sys.exit(r.returncode)


def check_dir(root, page, name):
    """整目录映射（file://）：images/ 可达。"""
    page.goto("file:///%s/%s" % (root.replace("\\", "/"), name))
    page.wait_for_timeout(1200)
    return page.eval_on_selector_all("img", "els => els.map(e => e.naturalWidth)")


print()
print("== 验证 ==")
ok = True
with sync_playwright() as p:
    b = p.chromium.launch()
    for name in CHAPTERS:
        d = os.path.join(BASE, name)
        # 旧 preview.html 若残留则提示（不算失败，但应清理）
        pv = os.path.join(d, "preview.html")
        if os.path.exists(pv):
            print("[%s] [WARN] 残留 preview.html，可删" % name)

        pg = b.new_page(viewport={"width": 750, "height": 900})
        widths = check_dir(d, pg, "index.html")
        pg.close()

        visible = sum(1 for w in widths if w > 0)
        total = len(widths)
        if total == 0 or visible != total:
            ok = False
            print("[%s] index.html@file:// %d/%d 可见  FAIL" % (name, visible, total))
        else:
            print("[%s] index.html@file:// %d/%d 可见" % (name, visible, total))
    b.close()

print()
print("结论：", "全部通过" if ok else "存在待修项")
sys.exit(0 if ok else 1)
