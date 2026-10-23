#!/usr/bin/env python3
"""把章节片段插入主 HTML，压缩并内嵌图片，最后做结构自检。

用法:
    python build_article.py --main article.html --fragment section.html \
        --anchor "<h2>5. 三专题</h2>" \
        --image IMG_A=shots/a.png --image IMG_B=shots/b.png

    # 锚点含换行时用字面 \\n
    --anchor "<section>\\n    <h2>5. 三专题</h2>"
"""
import argparse
import base64
import io
import os
import re
import sys


def optimize_bytes(path, colors=192):
    """PNG 量化压缩；无 Pillow 或非 PNG 时原样返回。"""
    try:
        from PIL import Image
    except ImportError:
        return open(path, "rb").read(), "raw(no pillow)"
    if not path.lower().endswith(".png"):
        return open(path, "rb").read(), "raw"
    im = Image.open(path).convert("RGB")
    q = im.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()
    raw = os.path.getsize(path)
    if len(data) >= raw:
        return open(path, "rb").read(), f"raw({raw // 1024}KB)"
    return data, f"{raw // 1024}KB -> {len(data) // 1024}KB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", required=True)
    ap.add_argument("--fragment", required=True)
    ap.add_argument("--anchor", default="", help="片段插入到此字符串之前；用字面 \\n 表示换行")
    ap.add_argument("--image", action="append", default=[], metavar="KEY=PATH",
                    help="占位符 KEY 替换为该图片的 base64 data-uri，可重复")
    ap.add_argument("--no-optimize", action="store_true")
    a = ap.parse_args()

    h = open(a.main, encoding="utf-8").read()
    before = len(h)

    # 1) 插入片段
    if a.anchor:
        anchor = a.anchor.replace("\\n", "\n")
        if anchor not in h:
            print(f"[error] 锚点未命中：{anchor!r}", file=sys.stderr)
            sys.exit(2)
        frag = open(a.fragment, encoding="utf-8").read()
        h = h.replace(anchor, frag.rstrip() + "\n\n" + anchor, 1)
        print(f"[insert] fragment 已插入（锚点前），+{len(frag)} 字符")

    # 2) 内嵌图片
    for item in a.image:
        if "=" not in item:
            print(f"[error] --image 需 KEY=PATH 格式：{item}", file=sys.stderr)
            sys.exit(2)
        key, path = item.split("=", 1)
        if key not in h:
            print(f"[warn] 占位符 {key} 不在文件中，跳过", file=sys.stderr)
            continue
        data, note = (open(path, "rb").read(), "raw") if a.no_optimize else optimize_bytes(path)
        uri = "data:image/png;base64," + base64.b64encode(data).decode()
        h = h.replace(key, uri)
        print(f"[image] {key} <- {os.path.basename(path)}  ({note})")

    open(a.main, "w", encoding="utf-8").write(h)

    # 3) 自检
    left = re.findall(r'\bIMG_[A-Z0-9_]+\b', h)
    checks = {
        "doctype": h.strip().startswith("<!DOCTYPE"),
        "ends_html": h.strip().endswith("</html>"),
        # 用正则而不是 h.count("<section>")：带 id 的 <section id="s1"> 会被漏数
        "sections": len(re.findall(r"<section[\s>]", h)),
        "h2": h.count("<h2>"),
        "h3": h.count("<h3>"),
        "tables": h.count("<table>"),
        "data_uris": h.count("data:image/png;base64,"),
        "no_placeholder": not left,
        "size_kb": round(os.path.getsize(a.main) / 1024),
        "delta_kb": round((os.path.getsize(a.main) - before) / 1024, 1),
    }
    print("\n=== 自检 ===")
    for k, v in checks.items():
        print(f"  {k:15} {v}")
    if left:
        print(f"  [warn] 残留占位符: {sorted(set(left))}")
    ok = checks["doctype"] and checks["ends_html"] and checks["no_placeholder"]
    print("\nRESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
