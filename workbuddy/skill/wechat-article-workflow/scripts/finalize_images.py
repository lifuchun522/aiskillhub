# -*- coding: utf-8 -*-
"""按 MAPPING 把 ImageGen 原图归位为 imgN.png，并裁掉平台水印后打品牌水印。

用法:
    python finalize_images.py --dir <篇目录>
"""
import argparse
import os
import sys
import glob

from PIL import Image, ImageDraw, ImageFont

# ---------- 品牌水印参数 ----------
WATERMARK_TEXT = "资深架构师 李福春"
CROP_BOTTOM = 90          # 裁掉 ImageGen 平台水印高度
AVATAR_D = 62             # 头像直径
MARGIN = 26               # 距右下边距
PORTRAIT = os.environ.get(
    "BRAND_PORTRAIT",
    os.path.join(os.path.expanduser("~"), ".workbuddy/assets/author-lfc-portrait.png"),
)

PAD_X, PAD_Y = 12, 8
GAP = 10


def find_font(size):
    cands = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def circular_avatar(path, d):
    """裁圆形头像，取上半部（人脸区域），带白描边。"""
    av = Image.open(path).convert("RGBA")
    w, h = av.size
    # 取上半部正方形，人脸通常在上方
    side = min(w, h)
    top = int((h - side) * 0.08)
    av = av.crop(((w - side) // 2, top, (w - side) // 2 + side, top + side))
    av = av.resize((d, d), Image.LANCZOS)

    mask = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    mask = mask.resize((d, d), Image.LANCZOS)

    # 圆形裁剪（用 alpha 通道做遮罩）
    av.putalpha(mask)

    # 白色描边 + 合成画布
    ring = Image.new("RGBA", (d + 4, d + 4), (0, 0, 0, 0))
    ring.paste(av, (2, 2), av)
    rd = ImageDraw.Draw(ring)
    rd.ellipse((1, 1, d + 2, d + 2), outline=(255, 255, 255, 235), width=2)
    return ring


def add_watermark(img_path):
    im = Image.open(img_path).convert("RGBA")
    w, h = im.size

    # 裁掉底部平台水印
    if h > CROP_BOTTOM + 40:
        im = im.crop((0, 0, w, h - CROP_BOTTOM))

    w, h = im.size
    base = im.convert("RGBA")

    font = find_font(26)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    try:
        tb = tmp.textbbox((0, 0), WATERMARK_TEXT, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
    except Exception:
        tw, th = len(WATERMARK_TEXT) * 26, 26

    av_size = AVATAR_D + 4
    cap_w = PAD_X + av_size + GAP + tw + PAD_X
    cap_h = max(av_size, th) + PAD_Y * 2

    x0 = w - MARGIN - cap_w
    y0 = h - MARGIN - cap_h

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(
        (x0, y0, x0 + cap_w, y0 + cap_h),
        radius=cap_h // 2,
        fill=(18, 22, 32, 168),
    )

    if os.path.exists(PORTRAIT):
        try:
            av = circular_avatar(PORTRAIT, AVATAR_D)
            layer.paste(av, (x0 + PAD_X, y0 + (cap_h - av.size[1]) // 2), av)
        except Exception as e:
            print("  [warn] avatar failed:", e)

    tx = x0 + PAD_X + av_size + GAP
    ty = y0 + (cap_h - th) // 2 - 2
    d.text((tx, ty), WATERMARK_TEXT, font=font, fill=(255, 255, 255, 246))

    out = Image.alpha_composite(base, layer).convert("RGB")
    out.save(img_path, quality=95)
    return out.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="篇目录")
    args = ap.parse_args()

    root = os.path.abspath(args.dir)
    comics = os.path.join(root, "comics")

    mp = os.path.join(root, "image_mapping.txt")
    if not os.path.exists(mp):
        print("[ERR] 缺少 image_mapping.txt:", mp)
        sys.exit(1)

    pairs = []
    with open(mp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            target, prefix = line.split("|", 1)
            pairs.append((target.strip(), prefix.strip()))

    done = 0
    for target, prefix in pairs:
        matches = [p for p in glob.glob(os.path.join(comics, "*.png"))
                   if os.path.basename(p).startswith(prefix)]
        if not matches:
            print("  [MISS] %-12s prefix=%s" % (target, prefix))
            continue
        src = sorted(matches)[0]
        dst = os.path.join(comics, target)
        im = Image.open(src).convert("RGB")
        # 缩放至 1080 宽（若更宽）
        if im.width > 1080:
            im = im.resize((1080, int(im.height * 1080 / im.width)), Image.LANCZOS)
        im.save(dst, quality=95)
        add_watermark(dst)
        print("  [OK] %-12s <- %s" % (target, os.path.basename(src)))
        done += 1

    print("完成 %d/%d" % (done, len(pairs)))


if __name__ == "__main__":
    main()
