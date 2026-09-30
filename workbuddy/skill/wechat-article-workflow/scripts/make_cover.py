# -*- coding: utf-8 -*-
"""生成系列文章封面：优先 playwright 截 HTML 模板，失败则 Pillow 兜底。

用法:
    python make_cover.py --dir <篇目录> --title "独孤九剑·破剑式" \
        --sub "别等风来，先下水" --tag "AI转型" --idx "02"

输出: covers/cover_final.png (900x500)
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover_template_1.html")
W, H = 900, 500

FONT_CANDS = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]


def font(size, bold=True):
    cands = FONT_CANDS if bold else FONT_CANDS[1:]
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def try_playwright(title, sub, tag, brand, out):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    if not os.path.exists(TPL):
        return False
    try:
        with open(TPL, encoding="utf-8") as f:
            html = f.read()
        html = (html.replace("{{TITLE}}", title)
                    .replace("{{SUBTITLE}}", sub)
                    .replace("{{TAG}}", tag)
                    .replace("{{BRAND}}", brand))
        tmp = os.path.join(os.path.dirname(out), "_cover_tmp.html")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(html)
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.goto("file:///" + tmp.replace("\\", "/"))
            pg.wait_for_timeout(1500)
            pg.screenshot(path=out, clip={"x": 0, "y": 0, "width": W, "height": H})
            b.close()
        os.remove(tmp)
        return True
    except Exception as e:
        print("  [playwright failed]", e)
        return False


def pillow_cover(title, sub, tag, brand, out):
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    # 渐变
    for y in range(H):
        t = y / H
        r = int(26 + (35 - 26) * t)
        g = int(26 + (57 - 26) * t)
        b = int(46 + (93 - 46) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # 装饰
    d.rectangle([60, 92, 116, 97], fill=(227, 93, 40))
    d.ellipse([W - 130, 52, W - 56, 126], outline=(227, 93, 40), width=2)

    f_title = font(52)
    f_sub = font(24, False)
    f_brand = font(19, False)
    f_tag = font(18)

    # 标题自动换行
    max_w = W - 130
    lines, cur = [], ""
    for ch in title:
        if d.textlength(cur + ch, font=f_title) <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)

    y = 134
    for ln in lines[:3]:
        d.text((60, y), ln, font=f_title, fill=(255, 255, 255))
        y += 66

    # 副标题固定在安全位置
    y = max(y + 24, 336)
    for ln in _wrap(d, sub, f_sub, W - 130)[:2]:
        d.text((62, y), ln, font=f_sub, fill=(178, 190, 210))
        y += 36

    d.text((62, H - 58), "%s · OPC时代的独孤九剑" % brand, font=f_brand,
           fill=(120, 132, 152))
    tw = d.textlength(tag, font=f_tag)
    d.text((W - 60 - tw, H - 55), tag, font=f_tag, fill=(227, 93, 40))

    im.save(out, quality=95)
    return True


def _wrap(d, text, fnt, max_w):
    out, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=fnt) <= max_w:
            cur += ch
        else:
            out.append(cur)
            cur = ch
    if cur:
        out.append(cur)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--sub", default="")
    ap.add_argument("--tag", default="AI转型")
    ap.add_argument("--brand", default="李福春 资深架构师")
    args = ap.parse_args()

    d = os.path.abspath(args.dir)
    covers = os.path.join(d, "covers")
    os.makedirs(covers, exist_ok=True)
    out = os.path.join(covers, "cover_final.png")

    ok = try_playwright(args.title, args.sub, args.tag, args.brand, out)
    if not ok:
        print("  -> 使用 Pillow 兜底")
        pillow_cover(args.title, args.sub, args.tag, args.brand, out)
    im = Image.open(out)
    print("  cover:", out, im.size)


if __name__ == "__main__":
    main()
