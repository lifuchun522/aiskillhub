# -*- coding: utf-8 -*-
"""生成目录篇「架构精选图」：从各章 img_arch.png 中挑代表性架构图，单列大图拼合。

用法:
    python make_archs_00.py --series-dir <系列目录> --out-dir <输出篇目录>

默认（无参数）会尝试从当前目录向上推断系列根。

选图逻辑（覆盖不同结构类型，避免同质）——见 SELECTED：
  - 01 → 四层能力分工    （谁干什么）
  - 04 → MVP 优先级四象限（先干什么）
  - 07 → 能力编排五层分工 （怎么串起来）
  - 09 → OPC 经营闭环     （怎么转起来）

排版：单列，每张图独立白卡 + 左上式号徽标，宽度统一 CONTENT_W，等比缩放不拉伸。
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

W = 1200
PAD = 40
CONTENT_W = W - PAD * 2          # 卡片外宽
IMG_W = CONTENT_W - 32           # 卡内图可用宽
BAR_H = 78

BG = (250, 248, 244)
CARD = (255, 255, 255)
EDGE = (228, 222, 212)
INK = (43, 43, 43)
SUB = (124, 120, 112)
GOLD = (176, 137, 74)

# (篇目录名, 式号, 式名, 短定位, 一句话说明) —— 按需增删
SELECTED = [
    ("01", "01", "总诀式", "四层能力分工", "谁干什么：过去 8 个角色，现在哪些交给 AI、哪些必须自己留"),
    ("04", "04", "破枪式", "MVP 优先级四象限", "先干什么：一个人只有一双手，什么必须先做"),
    ("07", "07", "破掌式", "能力编排 · 五层分工", "怎么串起来：判断、编排、执行、校验、交付"),
    ("09", "09", "破气式", "OPC 经营闭环", "怎么转起来：九关过完，闭环自己转"),
]

TITLE = "九式架构精选：四张图，看清一个人怎么干活"
SUBTITLE = "从「谁干什么」到「怎么转起来」——九篇里画出来的四张核心结构"
FOOTER_L = "四张图连起来：分工 → 取舍 → 编排 → 闭环。"
FOOTER_R = "资深架构师 李福春"


def find_font(size, bold=False):
    """跨平台字体查找（Windows / macOS / Linux）。"""
    cands = (
        ["msyhbd.ttc", "msyh.ttc", "simhei.ttf"] if bold
        else ["msyh.ttc", "msyhbd.ttc", "simhei.ttf"]
    )
    dirs = ["C:/Windows/Fonts", "/System/Library/Fonts", "/usr/share/fonts/truetype"]
    for d in dirs:
        for c in cands:
            p = os.path.join(d, c)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    # 兜底：Pillow 自带字体
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description="生成目录篇架构精选拼图")
    ap.add_argument("--series-dir", required=True, help="系列根目录")
    ap.add_argument("--out-dir", default=None,
                    help="输出篇目录（默认 series-dir/00），图存到其 images/ 下")
    args = ap.parse_args()

    root = os.path.abspath(args.series_dir)
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(root, "00")
    out = os.path.join(out_dir, "images", "img_archs.png")

    f_title = find_font(40, True)
    f_sub = find_font(19)
    f_name = find_font(27, True)
    f_desc = find_font(17)
    f_badge = find_font(20, True)
    f_foot = find_font(18)

    items = []          # [(缩放后图, idx, name, short, desc)]，与跳过的图保持同步
    for dir_name, idx, name, short, desc in SELECTED:
        src = os.path.join(root, dir_name, "images", "img_arch.png")
        if not os.path.exists(src):
            print("[WARN] 跳过（缺图）:", src)
            continue
        im = Image.open(src).convert("RGB")
        h = int(im.height * IMG_W / im.width)
        items.append((im.resize((IMG_W, h), Image.LANCZOS), idx, name, short, desc))

    if not items:
        print("[ERR] 没有找到任何 img_arch.png")
        return

    card_hs = [BAR_H + im.height + 20 for im, *_ in items]
    top = 138
    GAP = 24
    H = top + sum(card_hs) + GAP * (len(items) - 1) + 100

    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)

    d.text((PAD, 40), TITLE, font=f_title, fill=INK)
    d.text((PAD, 96), SUBTITLE, font=f_sub, fill=SUB)

    y = top
    for i, (im, idx, name, short, desc) in enumerate(items):
        ch = card_hs[i]
        x0, x1 = PAD, PAD + CONTENT_W

        d.rounded_rectangle([x0, y, x1, y + ch], radius=16,
                            fill=CARD, outline=EDGE, width=2)
        # 标签条
        d.rounded_rectangle([x0, y, x1, y + BAR_H], radius=16, fill=(252, 246, 238))
        d.rectangle([x0, y + BAR_H - 16, x1, y + BAR_H], fill=CARD)
        d.line([x0 + 2, y + BAR_H, x1 - 2, y + BAR_H], fill=EDGE, width=2)

        # 式号徽标
        d.rounded_rectangle([x0 + 18, y + 21, x0 + 74, y + 57], radius=8,
                            fill=(255, 255, 255), outline=GOLD, width=2)
        d.text((x0 + 46, y + 39), idx, font=f_badge, fill=GOLD, anchor="mm")
        d.text((x0 + 90, y + 18), name, font=f_name, fill=INK)
        d.text((x0 + 90 + int(d.textlength(name, font=f_name)) + 14, y + 27),
               "· " + short, font=f_desc, fill=GOLD)
        d.text((x0 + 90, y + 50), desc, font=f_desc, fill=SUB)

        canvas.paste(im, (x0 + 16, y + BAR_H + 10))
        y += ch + GAP

    fy = H - 66
    d.line([PAD, fy - 18, W - PAD, fy - 18], fill=EDGE, width=2)
    d.text((PAD, fy), FOOTER_L, font=f_foot, fill=SUB)
    d.text((W - PAD, fy), FOOTER_R, font=f_foot, fill=(150, 150, 150), anchor="rs")

    os.makedirs(os.path.dirname(out), exist_ok=True)
    canvas.save(out, optimize=True)

    # 长条图用 JPG 更省体积（本例 PNG 1.4MB -> JPG 0.74MB），微信/b64 都受益
    jpg = os.path.splitext(out)[0] + ".jpg"
    canvas.convert("RGB").save(jpg, quality=88, optimize=True, subsampling=1)
    os.remove(out)
    print("[OK]", jpg, canvas.size)


if __name__ == "__main__":
    main()
