# -*- coding: utf-8 -*-
"""verify_delivery.py —— 文章交付前自检

用法:
    python verify_delivery.py [--root <系列根目录>]

检查项（每篇）：
  1. index.html  < 60 KB、无内嵌 base64、<img src="images/..."> 数 == 图数、相对引用文件都存在
  2. preview.html 存在、自包含（data:image 数 == 图数）
  3. article_body.html 微信安全：div / h1-h3 / class= / display:flex / <style> 残留为 0
  4. 篇目录只保留 6 项（index.html / preview.html / 正文.md / article_body.html
                       / metadata.json / publish_config.json / images）
"""
import argparse
import os
import re
import sys

DEFAULT_ROOT = os.environ.get("WECHAT_SERIES_ROOT", "")
sys.stdout.reconfigure(encoding="utf-8")

ALLOW = {"index.html", "preview.html", "正文.md", "article_body.html",
         "metadata.json", "publish_config.json", "images"}
# 00 篇额外承担系列级素材（规划 / 风格指南 / 总图），不算违规
ALLOW_00 = {"series-plan.md", "style-guide.md",
            "series_overview.png", "series_overview_spec.json"}
WX_PATTERNS = {"div": r"<div", "h1-3": r"<h[1-3]", "class=": r"class=",
               "flex": r"display:flex", "<style": r"<style"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT or None,
                    help="系列根目录（含 01/ 02/ ... 各篇目录）")
    args = ap.parse_args()
    if not args.root:
        ap.error("必须指定 --root <系列根目录>（或设置环境变量 WECHAT_SERIES_ROOT）")
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("[ERR] 目录不存在:", root)
        sys.exit(1)

    ok = True
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d) or name.startswith("_"):
            continue
        # 只检查编号目录
        if not re.match(r"^\d{2}$", name):
            continue

        body_p = os.path.join(d, "article_body.html")
        if not os.path.exists(body_p):
            print("[%s] 非文章目录（无 article_body.html），跳过" % name)
            continue

        idx_p = os.path.join(d, "index.html")
        pv_p = os.path.join(d, "preview.html")
        body = open(body_p, encoding="utf-8").read()

        probs = []

        # -- index.html：轻量 + 相对路径 --
        if not os.path.exists(idx_p):
            probs.append("缺 index.html")
            kb = 0
            n_rel = 0
        else:
            ih = open(idx_p, encoding="utf-8").read()
            kb = os.path.getsize(idx_p) / 1024
            n_rel = len(re.findall(r'<img src="images/[^"]+"', ih))
            if kb > 60:
                probs.append("index.html %.0fKB 偏大" % kb)
            if "data:image" in ih:
                probs.append("index.html 含内嵌 base64")
            if "{img" in ih:
                probs.append("index.html 有未替换占位符")
            for ref in re.findall(r'<img src="(images/[^"]+)"', ih):
                if not os.path.exists(os.path.join(d, ref)):
                    probs.append("index.html 引用缺失: %s" % ref)

        # -- preview.html：自包含 --
        n_b64 = 0
        if not os.path.exists(pv_p):
            probs.append("缺 preview.html")
            pk = 0
        else:
            ph = open(pv_p, encoding="utf-8").read()
            pk = os.path.getsize(pv_p) / 1024
            n_b64 = ph.count("data:image")
            if n_b64 == 0:
                probs.append("preview.html 无内嵌图片")
            if "{img" in ph:
                probs.append("preview.html 有未替换占位符")
            if not all(f'<img src="images/{x}"' in ih for x in []) and False:
                pass

        # -- 微信安全 --
        wx = {k: len(re.findall(v, body)) for k, v in WX_PATTERNS.items()}
        wx = {k: v for k, v in wx.items() if v}
        if wx:
            probs.append("微信违规 %s" % wx)

        # -- 目录整洁 --
        allow = ALLOW | (ALLOW_00 if name == "00" else set())
        extra = sorted(set(os.listdir(d)) - allow)
        if extra:
            probs.append("多余文件 %s" % extra)

        # -- 图数一致 --
        n_img_dir = len([f for f in os.listdir(os.path.join(d, "images"))
                         if f.startswith("img") and f.endswith((".png", ".jpg"))])
        if n_rel and n_b64 and not (n_rel == n_b64 == n_img_dir):
            probs.append("图数不一致 rel=%d b64=%d 文件=%d" % (n_rel, n_b64, n_img_dir))

        if probs:
            ok = False
            print("[%s] <<< %s" % (name, "; ".join(probs)))
        else:
            print("[%s] index %5.0fKB/相对%2d · preview %5.0fKB/内嵌%2d · 微信OK · 目录OK"
                  % (name, kb, n_rel, pk, n_b64))

    print()
    print("结论：", "全部通过" if ok else "存在待修项")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
