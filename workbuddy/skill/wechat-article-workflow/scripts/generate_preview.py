#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""generate_preview.py —— 生成本地预览 index.html（相对路径）

用法:
    python generate_preview.py --dir <篇目录>

输出:
    index.html  图片走相对路径 images/xxx.png，本地双击即可看版式。
                须与 images/ 同级；不要粘贴进公众号编辑器（推送走 article_body.html）。

规则:
  - 占位符 {imgN} 整体替换为完整 <img> 标签（勿只塞路径字符串）
  - 缺图时跳过该位并告警
  - 支持非数字占位符（如 {img_arch}）
"""
import argparse
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

IMG_STYLE = "width:100%;display:block;margin:26px 0;border-radius:6px;"

HTML_HEAD = ('<!DOCTYPE html>\n<meta charset="UTF-8">\n'
             '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
             '<body style="margin:0;padding:16px;max-width:750px;margin:0 auto;'
             'font-family:-apple-system,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;">\n')


def candidate_paths(key, img_dir):
    """按占位符 key 找图（篇目录/images/ 下）。

    约定（占位符 {imgX}，key = X 去掉前导下划线）：
      - 数字 X="0"~"N"   -> imgN.png / imgN.jpg；X="0" 可退回 cover_final.png
      - 文本 X="_arch"   -> img_arch.png
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


def replace_slots(html, keys, tag_for):
    """把占位符整体替换为指定标签。返回 (新 html, 缺图 key 列表)。"""
    missing = []
    for key in keys:
        token = "{img%s}" % key
        tag = tag_for(key)
        if tag is None:
            missing.append(key)
            continue
        html, _ = re.subn(r"<p[^>]*>\s*" + re.escape(token) + r"\s*</p>", tag, html)
        html = html.replace(token, tag)
    return html, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None, help="篇目录（含 images/ 与 article_body.html）")
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

    def rel_tag(key):
        p = find(key)
        if p is None:
            return None
        return '<img src="images/%s" style="%s">' % (os.path.basename(p), IMG_STYLE)

    light, miss = replace_slots(body, keys, rel_tag)
    out_path = os.path.join(base_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(HTML_HEAD + light + "\n</body>\n")

    kb = os.path.getsize(out_path) / 1024
    n_img = light.count("<img ")
    print("[OK] index.html %.0f KB · <img> %d" % (kb, n_img))
    if miss:
        print("     缺图: %s" % ", ".join("{img%s}" % m for m in miss))

    if n_img == 0 and keys:
        print("[ERR] index.html 无 <img> 标签，请检查 article_body.html 占位符格式")
        sys.exit(1)
    if "{img" in light:
        print("[ERR] index.html 有占位符未替换")
        sys.exit(1)


if __name__ == "__main__":
    main()
