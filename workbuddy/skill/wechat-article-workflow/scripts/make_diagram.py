# -*- coding: utf-8 -*-
"""通用结构图生成器：按 JSON 描述画出分层结构图，中文 Pillow 直排。

用法:
    python make_diagram.py --spec <spec.json> --out <out.png>

spec.json 格式:
{
  "title": "图标题",
  "width": 1080,
  "layers": [
    {"label": "层名", "color": [r,g,b], "items": ["项1", "项2"]},
    ...
  ],
  "footer": "底部一句话"
}
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

FONT_CANDS = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]


def font(size, bold=False):
    cands = (["C:/Windows/Fonts/msyhbd.ttc"] if bold else []) + FONT_CANDS
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap(draw, text, fnt, max_w):
    out, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=fnt) <= max_w:
            cur += ch
        else:
            if cur:
                out.append(cur)
            cur = ch
    if cur:
        out.append(cur)
    return out


def build(spec, out_path):
    W = spec.get("width", 1080)
    title = spec.get("title", "")
    layers = spec.get("layers", [])
    footer = spec.get("footer", "")

    pad = 40
    inner = W - pad * 2

    f_title = font(40, True)
    f_layer = font(28, True)
    f_item = font(23)

    # 预先测量高度
    im0 = Image.new("RGB", (W, 10), "white")
    d0 = ImageDraw.Draw(im0)

    measure = []
    total_h = pad
    total_h += 56 + 30                       # 标题
    for L in layers:
        items = L.get("items", [])
        rows = []
        for it in items:
            lines = wrap(d0, it, f_item, inner - 130)
            rows.append(lines)
        h = 46 + 20                              # 层标题
        for lines in rows:
            h += len(lines) * 34 + 10
        h += 22
        measure.append(h)
        total_h += h + 18
    if footer:
        total_h += 30 + len(wrap(d0, footer, f_item, inner)) * 32 + 20
    total_h += pad

    H = total_h
    im = Image.new("RGB", (W, H), (250, 249, 246))
    d = ImageDraw.Draw(im)

    y = pad

    # 标题
    d.text((pad, y), title, font=f_title, fill=(24, 28, 38))
    y += 56 + 10
    d.line((pad, y, W - pad, y), fill=(200, 196, 188), width=2)
    y += 20

    for idx, L in enumerate(layers):
        h = measure[idx]
        color = tuple(L.get("color", [230, 232, 236]))
        x0, y0 = pad, y
        x1, y1 = W - pad, y + h
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=color,
                            outline=(150, 148, 144), width=2)

        # 层标签（左侧色块）
        d.rounded_rectangle((x0 + 16, y0 + 16, x0 + 26, y1 - 16),
                            radius=5, fill=(70, 78, 92))
        d.text((x0 + 40, y0 + 16), L.get("label", ""), font=f_layer,
               fill=(24, 28, 38))

        iy = y0 + 16 + 46
        for it in L.get("items", []):
            lines = wrap(d, it, f_item, inner - 130)
            d.ellipse((x0 + 46, iy + 11, x0 + 54, iy + 19), fill=(70, 78, 92))
            for k, ln in enumerate(lines):
                d.text((x0 + 66, iy + k * 34 - 6), ln, font=f_item,
                       fill=(40, 46, 58))
            iy += len(lines) * 34 + 10

        y += h + 18

    if footer:
        y += 6
        d.line((pad, y, W - pad, y), fill=(200, 196, 188), width=2)
        y += 16
        for ln in wrap(d, footer, f_item, inner):
            d.text((pad, y), ln, font=f_item, fill=(90, 92, 98))
            y += 32

    bottom = min(y + pad, H)
    im = im.crop((0, 0, W, bottom))
    im.save(out_path, quality=95)
    return im.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    size = build(spec, args.out)
    print("saved", args.out, size)


if __name__ == "__main__":
    main()
