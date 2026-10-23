# -*- coding: utf-8 -*-
"""微信短图文构建：压缩 → 图内底部图注+品牌水印 → base64 内联 → 校验

用法:
  python build.py --src draft.html --out 成稿.html --img a.jpg b.jpg --cap "图注1" "图注2"
可选:
  --width 900        图片内嵌宽度
  --quality 82       JPEG 质量
  --band 84          底部信息条高度（图注+水印，画布需留 ≥100px 余量）
  --font PATH        中文字体路径（默认自动探测 simhei / PingFang / Noto CJK）
  --wm TEXT          品牌水印文字（默认「资深架构师 李福春」）
  --no-watermark     图片已带底带时跳过（防止叠两层）

图注规则（2026-10-18 改版）：
  图注不再作为页面里的 div 文字，而是画进图片底部深蓝条的【左侧】，
  品牌水印「资深架构师 李福春」在【右侧】，两者同一行、同一条底带。
  页面里禁止出现「图一 / 图二」这类编号。
"""
import argparse, base64, glob, io, os, re, sys
from PIL import Image, ImageDraw, ImageFont

WM = "资深架构师 李福春"

# 中文字体候选（Windows / macOS / Linux），图注与水印必须能渲染中文
FONT_CANDIDATES = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]
FONT_CANDIDATES += sorted(glob.glob("/usr/share/fonts/**/NotoSansCJK*.ttc", recursive=True))


def find_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("找不到中文字体，请用 --font 指定（图注与水印必须渲染中文）")


def add_watermark(im, caption="", band=84, font=None, wm=WM):
    """底部深蓝条：左=图注，右=品牌水印。图注过长自动缩字号。"""
    font = font or find_font()
    d = ImageDraw.Draw(im)
    w, h = im.size
    d.rectangle([0, h - band, w, h], fill=(11, 61, 99, 235))
    mid = h - band // 2

    f_wm = ImageFont.truetype(font, 22)
    wm_w = d.textlength(wm, font=f_wm)
    d.text((w - 18, mid), wm, font=f_wm, fill=(255, 255, 255), anchor="rm")

    if caption:
        size = 22
        f_cap = ImageFont.truetype(font, size)
        while d.textlength(caption, font=f_cap) + wm_w + 60 > w and size > 12:
            size -= 1
            f_cap = ImageFont.truetype(font, size)
        d.text((18, mid), caption, font=f_cap, fill=(255, 255, 255), anchor="lm")
    return im


def to_b64(im, width, q):
    im = im.convert("RGB")
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), len(buf.getvalue())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--img", nargs="+", required=True)
    ap.add_argument("--cap", nargs="*", default=[], help="图注，画进图片底部左侧，数量与 --img 对齐")
    ap.add_argument("--width", type=int, default=900)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--band", type=int, default=84)
    ap.add_argument("--font", default=None, help="中文字体路径，默认自动探测")
    ap.add_argument("--wm", default=WM, help="品牌水印文字")
    ap.add_argument("--no-watermark", action="store_true")
    a = ap.parse_args()

    html = open(a.src, encoding="utf-8").read()
    outdir = os.path.dirname(os.path.abspath(a.out)) or "."
    caps = list(a.cap) + [""] * (len(a.img) - len(a.cap))

    for i, (path, cap) in enumerate(zip(a.img, caps), 1):
        im = Image.open(path).convert("RGB")
        if not a.no_watermark:
            im = add_watermark(im, cap, a.band, a.font, a.wm)
        stem = os.path.splitext(os.path.basename(a.out))[0]
        jpg = os.path.join(outdir, "%s_img%d.jpg" % (stem, i))
        im.save(jpg, "JPEG", quality=88)
        uri, size = to_b64(im, a.width, a.quality)
        n = html.count("{{IMG%d}}" % i)
        html = html.replace("{{IMG%d}}" % i, uri)
        print("图%d %s → %s (%.0fKB, 替换%d处, 图注「%s」)" % (
            i, os.path.basename(path), jpg, size / 1024, n, cap))

    open(a.out, "w", encoding="utf-8").write(html)

    # ---- 校验 ----
    t = html
    left = re.findall(r"\{\{[^}]+\}\}", t)
    page_txt = re.sub(r"<[^>]+>", "", t)
    n_page = len(re.findall(r"[\u4e00-\u9fff]", page_txt))
    n_cap = sum(len(re.findall(r"[\u4e00-\u9fff]", c)) for c in caps)
    print("\n==== 校验 ====")
    print("页面CJK:", n_page, "| 图内图注CJK:", n_cap, "| 合计:", n_page + n_cap,
          "->", "达标(<=1000)" if n_page + n_cap <= 1000 else "超标")
    print("字数档位:", "优(<=600)" if n_page <= 600 else ("合格(<=1000)" if n_page <= 1000 else "超标"))
    print("img:", t.count("<img"), "| data:", t.count("data:image/jpeg"), "| 外链 http:", "http" in t)
    # 占位符如果漏掉 src=" 外壳（写成 {{IMG1}} 而非 src="{{IMG1}}"），图会被塞进标签里变成死链
    print("img 缺少 src 属性:", len(re.findall(r"<img\s+data:", t)))
    print("JS:", bool(re.search(r"\bon\w+=|<script", t)), "| style块:", t.count("<style"),
          "| class:", "class=" in t, "| id:", "id=" in t, "| input:", len(re.findall(r"<input", t)))
    print("HTML实体残留:", len(re.findall(r"&[a-zA-Z#0-9]+;", t)))
    print("「图一/图二」编号残留:", len(re.findall(r"图[一二三四五六七八]", t)))
    print("结尾口号行残留:", "把复杂系统，设计成简单可依赖的产品" in t)
    print("占位残留:", left if left else 0)
    print("<br> 换行残留:", t.count("<br"))
    for tag in ["div", "p", "h1", "section", "b", "span"]:
        o = len(re.findall(r"<%s[ >/]" % tag, t))
        c = len(re.findall(r"</%s>" % tag, t))
        print("%-8s open=%d close=%d %s" % (tag, o, c, "OK" if o == c else "MISMATCH"))
    print("文件大小: %.0fKB" % (len(t.encode()) / 1024))


if __name__ == "__main__":
    main()
