#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""apply_brand_watermark.py —— 用个人品牌水印替换 ImageGen 强制水印

背景（2026-09-30）:
  WorkBuddy ImageGen（混元）出图右下角固定带 "AI生成 / WORKBUDDY" 水印，
  prompt 里写 no watermark 也去不掉。
  -> 裁掉水印区后，在右下角重新绘制「资深架构师 李福春」+ 圆形头像。

品牌素材（固化路径，见 ~/.workbuddy/assets/brand.json）:
  portrait : ~/.workbuddy/assets/author-lfc-portrait.png

用法:
  python apply_brand_watermark.py comics/img0.png [img1.png ...]
  python apply_brand_watermark.py --all          # 处理 comics/ 下全部 imgN.png
"""
import io
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMICS = os.path.join(BASE_DIR, "comics")

HOME = os.path.expanduser("~")
BRAND_JSON = os.path.join(HOME, ".workbuddy", "assets", "brand.json")
PORTRAIT = os.path.join(HOME, ".workbuddy", "assets", "author-lfc-portrait.png")

WATERMARK_TEXT = "资深架构师 李福春"
CROP_BOTTOM = 90        # ImageGen 原图水印区高度（1536x1024 实测）
TARGET_W = 1080
AVATAR_D = 62           # 头像直径
MARGIN = 26             # 右下角边距
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def circular_avatar(path, d):
    """裁成圆形头像，带白色描边圈。"""
    im = Image.open(path).convert("RGB")
    # 演讲照取上半部人脸区域
    w, h = im.size
    side = int(min(w, h * 0.62))
    left = (w - side) // 2
    top = int(h * 0.04)
    im = im.crop((left, top, left + side, top + side)).resize((d, d), Image.LANCZOS)

    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
    out = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)

    # 白色描边
    ring = Image.new("RGBA", (d + 4, d + 4), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((0, 0, d + 3, d + 3), outline=(255, 255, 255, 235), width=3)
    base = Image.new("RGBA", (d + 4, d + 4), (0, 0, 0, 0))
    base.paste(out, (2, 2), out)
    base.alpha_composite(ring)
    return base


def add_watermark(img, text, avatar_path):
    """在右下角绘制：圆形头像 + 文字（半透明深色胶囊底，保证任何底色可读）。"""
    w, h = img.size
    fs = max(22, int(w * 0.026))
    font = load_font(fs)
    tw = font.getlength(text)

    pad_x, gap = 16, 10
    box_w = int(pad_x * 2 + AVATAR_D + 4 + gap + tw)
    box_h = AVATAR_D + 18
    x1, y1 = w - MARGIN, h - MARGIN - box_h
    x0 = x1 - box_w

    # 半透明深色胶囊
    overlay = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle(
        (0, 0, box_w - 1, box_h - 1), radius=box_h // 2, fill=(18, 22, 32, 168))

    av = circular_avatar(avatar_path, AVATAR_D) if os.path.exists(avatar_path) else None
    if av:
        overlay.alpha_composite(av, (pad_x - 2, (box_h - AVATAR_D - 4) // 2))

    d = ImageDraw.Draw(overlay)
    tx = pad_x + AVATAR_D + 4 + gap
    d.text((tx, (box_h - fs) / 2 - fs * 0.16), text, font=font, fill=(255, 255, 255, 250))

    base = img.convert("RGBA")
    base.alpha_composite(overlay, (x0, y1))
    return base.convert("RGB")


def process(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if h > CROP_BOTTOM:
        im = im.crop((0, 0, w, h - CROP_BOTTOM))  # 先裁掉 ImageGen 强制水印
    if im.width != TARGET_W:
        im = im.resize((TARGET_W, int(im.height * TARGET_W / im.width)), Image.LANCZOS)
    im = add_watermark(im, WATERMARK_TEXT, PORTRAIT)
    im.save(path, "PNG", optimize=True)
    print("  %s  %dx%d  水印: %s" % (os.path.basename(path), im.width, im.height, WATERMARK_TEXT))


def main():
    args = sys.argv[1:]
    if args == ["--all"]:
        targets = sorted(
            os.path.join(COMICS, f) for f in os.listdir(COMICS)
            if f.startswith("img") and f.endswith(".png"))
    elif args:
        targets = [a if os.path.isabs(a) else os.path.join(BASE_DIR, a) for a in args]
    else:
        sys.exit("用法: python apply_brand_watermark.py [--all | imgN.png ...]")

    if not os.path.exists(PORTRAIT):
        print("[WARN] 未找到头像 %s，将只画文字水印" % PORTRAIT)
    print("=" * 52)
    for t in targets:
        if os.path.exists(t):
            process(t)
        else:
            print("  [MISS] %s" % t)
    print("=" * 52)
    print("[OK] 共 %d 张，水印已替换为「%s」" % (len(targets), WATERMARK_TEXT))


if __name__ == "__main__":
    main()
