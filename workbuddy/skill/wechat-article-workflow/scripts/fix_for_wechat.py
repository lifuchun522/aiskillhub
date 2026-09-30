#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fix_for_wechat.py —— 微信兼容 HTML 自动修复

用法: python fix_for_wechat.py article_body.html
功能:
  1. 去除 BOM、零宽字符等不可见脏字符
  2. <div> -> <section>
  3. <h1>/<h2>/<h3> -> <p> (保留文字)
  4. 去除 display:flex / align-items / justify-content
  5. 去除 HTML 注释
  6. 压缩多余空行
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def fix(path):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    stats = {}

    before = html
    html = re.sub(r"[\ufeff\u200b\u200c\u200d\ufffe]", "", html)
    stats["脏字符"] = len(before) - len(html)

    n = len(re.findall(r"<div\b", html))
    html = re.sub(r"<div\b", "<section", html)
    html = re.sub(r"</div>", "</section>", html)
    stats["<div>"] = n

    n = len(re.findall(r"<h[123]\b", html))
    html = re.sub(r"<h[123]\b[^>]*>", '<p style="font-size:17px;font-weight:bold;color:#e35d28;line-height:1.6;">', html)
    html = re.sub(r"</h[123]>", "</p>", html)
    stats["<h1/h2/h3>"] = n

    n = len(re.findall(r"display\s*:\s*flex", html))
    html = re.sub(r"display\s*:\s*flex\s*;?", "", html)
    html = re.sub(r"(align-items|justify-content)\s*:\s*[^;\"']+;?", "", html)
    stats["display:flex"] = n

    n = len(re.findall(r"<!--.*?-->", html, re.S))
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    stats["HTML注释"] = n

    html = re.sub(r"\n\s*\n+", "\n\n", html).strip() + "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    print("=" * 50)
    print("OK WeChat-safe HTML 已写入:", path)
    for k, v in stats.items():
        print("  %s: %d 个（已修复）" % (k, v))
    # 复查
    left = []
    if re.search(r"<div\b", html):
        left.append("<div>")
    if re.search(r"<h[123]\b", html):
        left.append("<h1/h2>")
    if re.search(r"display\s*:\s*flex", html):
        left.append("display:flex")
    if re.search(r"[\ufeff\u200b]", html):
        left.append("脏字符")
    if left:
        print("  [WARN] 仍有残留:", ", ".join(left))
    else:
        print("  残留检查: 0，通过")
    phs = re.findall(r"\{img(\w+)\}", html)
    print("  图片占位符:", ["{img%s}" % p for p in phs])
    nums = sorted(int(p) for p in phs if p.isdigit())
    if nums and nums != list(range(0, len(nums))):
        print("  [WARN] 数字占位符不连续，检查是否跳号!")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fix_for_wechat.py article_body.html")
        sys.exit(1)
    fix(os.path.abspath(sys.argv[1]))
