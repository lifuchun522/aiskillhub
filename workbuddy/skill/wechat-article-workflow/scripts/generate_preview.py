#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""generate_preview.py —— 生成两个本地预览产物

用法:
    python generate_preview.py --dir <篇目录>

输出:
    index.html    轻量版（图片相对路径 images/xxx.png，约 20 KB）——
                  双击即看，但必须与 images/ 同级；预览面板/单独分享时子目录不可达
    preview.html  自包含版（图片 base64 内嵌）——
                  单文件即可渲染，供预览面板、分享、归档用；图片先缩到 750px 宽
                  再编 JPEG（质量 82），体积比原图直嵌小一个量级

规则（来自 skill S9）:
  - 占位符 {imgN} 整体替换为完整 <img> 标签。只替换成裸路径/裸 base64 字符串
    会得到一段文本节点，浏览器不渲染 -> 图片不显示。
  - 缺图时跳过该位并告警。
  - 支持非数字占位符（如 {img_arch}，由 Pillow 脚本生成的结构图）
"""
import argparse
import base64
import io
import os
import re
import sys

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

IMG_STYLE = "width:100%;display:block;margin:26px 0;border-radius:6px;"
BASE64_MAXW = 750       # 预览版图片最大宽度（正文显示宽 750，再宽无意义）
BASE64_QUALITY = 82     # JPEG 质量

HTML_HEAD = ('<!DOCTYPE html>\n<meta charset="UTF-8">\n'
             '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
             '<body style="margin:0;padding:16px;max-width:750px;margin:0 auto;'
             'font-family:-apple-system,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;">\n')


def candidate_paths(key, img_dir):
    """按占位符 key 找图（篇目录/images/ 下）。

    约定（占位符 {imgX}，key = X 去掉前导下划线）：
      - 数字 X="0"~"N"   -> imgN.png / imgN.jpg；X="0" 可退回 cover_final.png
      - 文本 X="_arch"   -> img_arch.png
    注意：正则捕获组会带上分隔用的下划线（{img_arch} -> "_arch"），
    这里统一去前导下划线，再按 数字/文本 两路拼真实文件名。
    """
    key = key.lstrip("_")
    cands = []
    if key.isdigit():
        n = int(key)
        cands += [os.path.join(img_dir, "img%d.png" % n), os.path.join(img_dir, "img%d.jpg" % n)]
        if n == 0:
            cands.append(os.path.join(img_dir, "cover_final.png"))
    else:
        cands.append(os.path.join(img_dir, "img_%s.png" % key))
        cands.append(os.path.join(img_dir, "img_%s.jpg" % key))
    return cands


def to_data_uri(path):
    """缩到 BASE64_MAXW 宽后编 JPEG，返回 data URI（体积可控）。"""
    im = Image.open(path).convert("RGB")
    if im.width > BASE64_MAXW:
        im = im.resize((BASE64_MAXW, int(im.height * BASE64_MAXW / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=BASE64_QUALITY, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def replace_slots(html, keys, tag_for):
    """把占位符整体替换为指定标签。返回 (新 html, 缺图 key 列表)。"""
    missing = []
    for key in keys:
        token = "{img%s}" % key
        tag = tag_for(key)
        if tag is None:
            missing.append(key)
            continue
        # 情形1：占位符被包在 <p ...>...</p> 里 -> 整段替换
        html, _ = re.subn(r"<p[^>]*>\s*" + re.escape(token) + r"\s*</p>", tag, html)
        # 情形2：裸占位符 -> 直接替换
        html = html.replace(token, tag)
    return html, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None, help="篇目录（含 images/ 与 article_body.html）")
    ap.add_argument("--no-base64", action="store_true", help="只生成轻量版 index.html")
    args = ap.parse_args()

    base_dir = os.path.abspath(args.dir) if args.dir else os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(base_dir, "images")

    body_path = os.path.join(base_dir, "article_body.html")
    if not os.path.exists(body_path):
        print("[ERR] 缺少 article_body.html:", base_dir)
        sys.exit(1)
    with open(body_path, "r", encoding="utf-8") as f:
        body = f.read()

    keys = []
    for m in re.findall(r"\{img(\w+)\}", body):
        if m not in keys:
            keys.append(m)
    if not keys:
        print("[WARN] 未找到任何 {img*} 占位符")

    def find(key):
        for c in candidate_paths(key, img_dir):
            if os.path.exists(c):
                return c
        return None

    # ---------- 1. 轻量版 index.html（相对路径）----------
    def rel_tag(key):
        p = find(key)
        if p is None:
            return None
        return '<img src="images/%s" style="%s">' % (os.path.basename(p), IMG_STYLE)

    light, miss1 = replace_slots(body, keys, rel_tag)
    _write(base_dir, "index.html", light)

    # ---------- 2. 自包含版 preview.html（base64，供预览面板/分享）----------
    if not args.no_base64:
        cache = {}

        def b64_tag(key):
            p = find(key)
            if p is None:
                return None
            if key not in cache:
                cache[key] = to_data_uri(p)
            return '<img src="%s" style="%s">' % (cache[key], IMG_STYLE)

        full, miss2 = replace_slots(body, keys, b64_tag)
        _write(base_dir, "preview.html", full)
        pk = os.path.getsize(os.path.join(base_dir, "preview.html")) / 1024
        n2 = full.count("<img ")
        print("[OK] preview.html（自包含） %.0f KB · <img> %d" % (pk, n2))

    if miss1:
        print("     缺图: %s" % ", ".join("{img%s}" % m for m in miss1))

    # ---------- 3. 断言 ----------
    for name in ("index.html", "preview.html"):
        p = os.path.join(base_dir, name)
        if not os.path.exists(p):
            continue
        h = open(p, encoding="utf-8").read()
        if h.count("<img ") == 0:
            print("[ERR] %s 无 <img> 标签，请检查 article_body.html 占位符格式" % name)
            sys.exit(1)
        if "{img" in h:
            print("[ERR] %s 有占位符未替换" % name)
            sys.exit(1)


def _write(base_dir, name, html):
    p = os.path.join(base_dir, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(HTML_HEAD + html + "\n</body>\n")
    kb = os.path.getsize(p) / 1024
    n = html.count("<img ")
    print("[OK] %-13s %.0f KB · <img> %d" % (name, kb, n))


if __name__ == "__main__":
    main()
