# -*- coding: utf-8 -*-
"""gr-zpj · 从 examples/content.json 生成 examples/demo-content.json

表单里的「载入示例」要在**没有任何本机素材**的情况下也能跑通，所以示例数据必须把
图片一并带上（data URI 内联）。直接把生产级原图内联会让示例文件几 MB 大，
因此这里统一压到「演示尺寸」：看得清结构，但不占体积。

用法：
    python make_demo.py [--src examples/content.json] [--out examples/demo-content.json]
                        [--scale 1.0]

压完记得跑一次 sync_assets.py，把示例注入表单。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_portfolio import to_data_uri, DATA_URI_RE   # noqa: E402

# 演示尺寸：(最大宽度, JPEG 质量 1-95, 是否 PNG, 是否 PNG8 量化)
DEMO_RULES = {
    "namecard":      (560, 72, False, False),
    "hand":          (460, 70, False, False),
    "layer":         (520, 0,  True,  True),
    "cert":          (260, 78, False, False),
    "qr":            (150, 0,  True,  False),
}


def rule_of(key):
    if key == "namecard":
        return DEMO_RULES["namecard"]
    if key.startswith("qr_"):
        return DEMO_RULES["qr"]
    if key.startswith("cert_"):
        return DEMO_RULES["cert"]
    if key.startswith("nh_"):
        return DEMO_RULES["hand"]
    return DEMO_RULES["layer"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(HERE, "..", "examples", "content.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "examples", "demo-content.json"))
    ap.add_argument("--scale", type=float, default=1.0, help="整体再乘一个宽度系数")
    args = ap.parse_args()

    cfg = json.load(open(args.src, encoding="utf-8"))
    base = (cfg.get("paths") or {}).get("src_dir") or ""
    images, total = {}, [0]

    for key, spec in cfg["images"].items():
        src = spec["src"]
        if base and not os.path.isabs(src) and not DATA_URI_RE.match(src.strip()):
            src = os.path.join(base, src)
        max_w, q, png, png8 = rule_of(key)
        kw = {"max_w": int(max_w * args.scale), "as_png": png, "png8": png8}
        if not png:
            kw["quality"] = q
        uri, raw = to_data_uri(src, **kw)
        images[key] = {"src": uri}
        total[0] += len(raw)
        print("  %-16s %7.1f KB" % (key, len(raw) / 1024))

    demo = {
        "texts": cfg.get("texts", {}),
        "metrics": cfg.get("metrics", []),
        "card": cfg.get("card", {}),
        "images": images,
        "content": cfg["content"],
    }
    out = os.path.abspath(args.out)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(demo, fh, ensure_ascii=False, indent=1)

    print("\n图片合计 %.0f KB ｜ demo-content.json %.0f KB"
          % (total[0] / 1024, os.path.getsize(out) / 1024))
    print("OK ->", out)
    print("下一步：python scripts/sync_assets.py")


if __name__ == "__main__":
    main()
