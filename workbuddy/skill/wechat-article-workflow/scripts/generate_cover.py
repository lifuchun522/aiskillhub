# -*- coding: utf-8 -*-
"""generate_cover.py —— 生成公众号封面（HTML模板 + playwright 截图，Pillow 兜底）

用法:
  python generate_cover.py "封面标题" "副标题" --tag "AI转型" [--template cover_template_1.html] [--out covers/cover_final.png] [--fallback]

铁律（007篇踩坑）:
  - 封面标题必须单独设，≤10个中文字符，超出必溢出
  - 主标题每行 <=14 字自动换行；副标题每行 <=18 字
  - 截图前等 2 秒，等字体渲染完成

依赖:
  首选 playwright（pip install playwright && playwright install chromium）
  失败自动走 Pillow 纯色方案
"""
import os
import re
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SKILL_DIR, "assets")
DEFAULT_TEMPLATE = os.path.join(ASSETS, "cover_template_1.html")
W, H = 900, 500
BRAND = "架构师手记"


def wrap(text, per_line):
    """按中文字符数换行；英文单词尽量不拆。"""
    lines, cur, cur_w = [], "", 0.0
    for ch in text:
        w = 1.0 if ord(ch) > 0x2E80 else 0.55
        if cur_w + w > per_line and cur:
            lines.append(cur)
            cur, cur_w = ch, w
        else:
            cur += ch
            cur_w += w
    if cur:
        lines.append(cur)
    return lines


def render_pillow(title, subtitle, tag, out):
    from PIL import Image, ImageDraw, ImageFont
    font_path = next((p for p in [
        r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf"] if os.path.exists(p)), None)

    def F(sz):
        return ImageFont.truetype(font_path, sz) if font_path else ImageFont.load_default()

    im = Image.new("RGB", (W, H), (26, 26, 46))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=(int(26 + 12 * t), int(26 + 22 * t), int(46 + 44 * t)))
    d.rectangle([60, 96, 116, 100], fill=(227, 93, 40))

    tf = F(52)
    y = 150
    for ln in wrap(title, 9)[:3]:
        d.text((60, y), ln, font=tf, fill=(255, 255, 255))
        y += 68
    # 副标题固定位置，避免随主标题行数浮动后与标题挤在一起
    sf = F(24)
    y = max(y + 24, 336)
    for ln in wrap(subtitle, 20)[:2]:
        d.text((62, y), ln, font=sf, fill=(178, 190, 210))
        y += 36
    d.text((62, H - 58), "%s · OPC时代的独孤九剑" % BRAND, font=F(20), fill=(120, 132, 152))
    if tag:
        d.text((W - 62 - F(18).getlength(tag), H - 58), tag, font=F(18), fill=(227, 93, 40))
    im.save(out, "PNG")
    print("[cover/Pillow] %s (%dx%d)" % (out, W, H))


def render_playwright(title, subtitle, tag, template, out):
    from playwright.sync_api import sync_playwright
    with open(template, "r", encoding="utf-8") as f:
        html = f.read()
    html = (html.replace("{{TITLE}}", "<br>".join(wrap(title, 9)))
                .replace("{{SUBTITLE}}", "<br>".join(wrap(subtitle, 20)))
                .replace("{{TAG}}", tag or "")
                .replace("{{BRAND}}", BRAND))
    tmp = os.path.join(os.path.dirname(out), "_cover_render.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg.goto("file:///" + tmp.replace("\\", "/"))
        pg.wait_for_timeout(2000)  # 等字体渲染
        pg.screenshot(path=out, clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    os.remove(tmp)
    print("[cover/playwright] %s (%dx%d)" % (out, W, H))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) < 2:
        sys.exit('用法: python generate_cover.py "标题" "副标题" [--tag X] [--template f.html] [--out p.png] [--fallback]')

    title, subtitle = args[0], args[1]
    tag = ""
    template = DEFAULT_TEMPLATE
    out = os.path.join(os.getcwd(), "covers", "cover_final.png")
    for i, a in enumerate(sys.argv):
        if a == "--tag" and i + 1 < len(sys.argv):
            tag = sys.argv[i + 1]
        if a == "--template" and i + 1 < len(sys.argv):
            template = sys.argv[i + 1] if os.path.isabs(sys.argv[i + 1]) else os.path.join(ASSETS, sys.argv[i + 1])
        if a == "--out" and i + 1 < len(sys.argv):
            out = os.path.abspath(sys.argv[i + 1])

    os.makedirs(os.path.dirname(out), exist_ok=True)
    if len(title) > 10:
        print("[WARN] 封面标题 %d 字，建议 <=10 字，否则可能溢出" % len(title))

    if "--fallback" not in flags:
        try:
            render_playwright(title, subtitle, tag, template, out)
            return
        except Exception as e:
            print("[WARN] playwright 失败（%s），改用 Pillow 兜底" % type(e).__name__)
    render_pillow(title, subtitle, tag, out)


if __name__ == "__main__":
    main()
