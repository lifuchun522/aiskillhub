# -*- coding: utf-8 -*-
"""生成 00 篇结构图：九式 × 七习惯 × 三层 依赖关系总图。

布局（1760 x 1180）：
  左轴 3 层（上：剑式所破 / 中：七习惯代表七种权力 / 下：AI 接走的执行）
  横向 9 列 = 九式，列高随「阶段」递增，体现依赖递进
  顶部 4 个阶段分段标签：想清楚 / 收窄 / 借力 / 可持续
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1760, 1180


def find_font_name(bold=False):
    cands = (
        ["msyhbd.ttc", "msyh.ttc", "simhei.ttf"] if bold
        else ["msyh.ttc", "msyhbd.ttc", "simhei.ttf"]
    )
    for d in ("C:/Windows/Fonts", "/System/Library/Fonts",
              "/usr/share/fonts/truetype", "/usr/share/fonts"):
        for c in cands:
            p = os.path.join(d, c)
            if os.path.exists(p):
                return p
    return "DejaVuSans.ttf"


FONT_B = find_font_name(True)
FONT_R = find_font_name(False)
BG = (250, 248, 244)

INK = (43, 43, 43)
INK_L = (110, 110, 110)
GOLD = (176, 137, 74)
RED = (176, 74, 58)
BLUE = (74, 106, 148)
GREEN = (96, 132, 104)

STAGES = [
    ("想清楚", "第 1~2 式", 0, 1, (252, 240, 233), RED),
    ("收窄", "第 3~4 式", 2, 3, (248, 245, 240), GOLD),
    ("借力", "第 5~7 式", 4, 6, (240, 244, 246), BLUE),
    ("可持续", "第 8~9 式", 7, 8, (238, 242, 238), GREEN),
]

SWORDS = [
    ("总诀式", "价值论"),
    ("破剑式", "积极主动"),
    ("破刀式", "以终为始"),
    ("破枪式", "要事第一"),
    ("破鞭式", "双赢思维"),
    ("破索式", "知彼解己"),
    ("破掌式", "统合综效"),
    ("破箭式", "不断更新"),
    ("破气式", "OPC 心法"),
]

BREAKS = [
    "站哪的模糊",
    "五十多天没动",
    "什么都接",
    "功能越拉越长",
    "个人英雄主义",
    "我以为我懂客户",
    "什么都自己造",
    "被事务拖垮",
    "离不开赛道",
]

EXEC = [
    "收藏与信息",
    "焦虑与观望",
    "需求全揽",
    "功能堆叠",
    "单打独斗",
    "主观猜测",
    "重复造轮",
    "事务缠身",
    "赛道依赖",
]


def font(path, size):
    return ImageFont.truetype(path, size)


def ctext(d, box, txt, fnt, fill, anchor="mm"):
    x0, y0, x1, y1 = box
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), txt, font=fnt, fill=fill, anchor=anchor)


def main():
    ap = argparse.ArgumentParser(description="生成系列目录篇的九式总纲结构图")
    ap.add_argument("--out", required=True,
                    help="输出 png 路径，如 <系列>/00/images/img_arch.png")
    args = ap.parse_args()
    out = os.path.abspath(args.out)

    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    f_title = font(FONT_B, 40)
    f_stage = font(FONT_B, 24)
    f_sub = font(FONT_R, 19)
    f_sword = font(FONT_B, 25)
    f_habit = font(FONT_R, 21)
    f_cell = font(FONT_R, 19)
    f_layer = font(FONT_B, 23)
    f_note = font(FONT_R, 20)

    d.text((70, 46), "九式 × 七习惯：每一层解掉的，是下一层暴露出来的问题", font=f_title, fill=INK)
    d.text((70, 104), "横轴 = 独孤九剑九式（破什么）　纵轴 = 三层结构（AI 在执行层，人在权力层）", font=f_sub, fill=INK_L)

    # ---- 几何 ----
    LX = 150                 # 左侧层标签宽
    TX = 250                 # 表格起点
    CW = (W - TX - 70) / 9   # 列宽
    TOP = 250                # 阶段条顶部
    SH = 62                  # 阶段条高度
    Y0 = TOP + SH + 18       # 层区顶部

    LAYER_H = [148, 168, 168]        # 三层高：破 / 权力 / 执行
    GAP = 12
    ys = []
    y = Y0
    for h in LAYER_H:
        ys.append((y, y + h))
        y += h + GAP
    BOTTOM = ys[-1][1] + 92

    # ---- 阶段分段条 ----
    for name, rng, i0, i1, col, accent in STAGES:
        x0 = TX + i0 * CW
        x1 = TX + (i1 + 1) * CW
        d.rounded_rectangle([x0 + 4, TOP, x1 - 4, TOP + SH], radius=12,
                            fill=col, outline=accent, width=3)
        ctext(d, (x0, TOP + 4, x1, TOP + 34), name, f_stage, accent)
        ctext(d, (x0, TOP + 32, x1, TOP + SH - 2), rng, f_sub, INK_L)

    # ---- 三层 ----
    layer_names = ["剑式所破\n（认知障碍）", "七种权力\n（人必须拿着）", "AI 接走的执行\n（越来越便宜）"]
    layer_cols = [(252, 246, 242), (250, 248, 240), (244, 246, 248)]
    layer_edges = [RED, GOLD, BLUE]

    for li, (a, b) in enumerate(ys):
        d.rounded_rectangle([60, a, TX - 22, b], radius=14,
                            fill=layer_cols[li], outline=layer_edges[li], width=3)
        lines = layer_names[li].split("\n")
        cy = (a + b) / 2
        d.text((60 + 14, cy - 20), lines[0], font=f_layer, fill=layer_edges[li])
        d.text((60 + 14, cy + 8), lines[1], font=f_sub, fill=INK_L)

    # ---- 单元格 ----
    for i in range(9):
        x0 = TX + i * CW
        x1 = x0 + CW
        a, b = ys[0]
        d.rounded_rectangle([x0 + 6, a, x1 - 6, b], radius=12, fill=(255, 255, 255),
                            outline=(226, 220, 210), width=2)
        ctext(d, (x0, a + 14, x1, a + 66), SWORDS[i][0], f_sword, INK)
        ctext(d, (x0, a + 62, x1, a + 100), BREAKS[i], f_cell, RED)

        a, b = ys[1]
        d.rounded_rectangle([x0 + 6, a, x1 - 6, b], radius=12, fill=(255, 253, 249),
                            outline=(230, 218, 196), width=2)
        ctext(d, (x0, a + 30, x1, a + 78), SWORDS[i][1], f_habit, GOLD)
        d.line([x0 + CW * 0.3, a + 96, x1 - CW * 0.3, a + 96], fill=(232, 220, 200), width=2)

        a, b = ys[2]
        d.rounded_rectangle([x0 + 6, a, x1 - 6, b], radius=12, fill=(247, 249, 251),
                            outline=(214, 222, 232), width=2)
        ctext(d, (x0, a + 16, x1, b - 16), EXEC[i], f_cell, BLUE)

    # ---- 列间递进箭头 ----
    ay = TOP + SH + 6
    for i in range(8):
        cx = TX + (i + 1) * CW
        d.line([cx - 12, ay, cx + 8, ay], fill=(200, 194, 184), width=3)
        d.polygon([(cx + 8, ay - 7), (cx + 20, ay), (cx + 8, ay + 7)], fill=(200, 194, 184))

    # ---- 底部说明 ----
    by = BOTTOM - 74
    d.rounded_rectangle([60, by, W - 70, by + 62], radius=12,
                        fill=(255, 255, 255), outline=(230, 224, 214), width=2)
    d.text((84, by + 11), "读法：③ 砍完需求，才暴露「一个人扛不住全链路」→ 才有 ⑤ 破鞭式。",
           font=f_note, fill=INK)
    d.text((84, by + 35), "九式不是并列选题，是依赖关系；跳着读也行，按序读才能拿到完整推理链。",
           font=f_note, fill=INK_L)

    # ---- 顶部收尾线 ----
    d.line([60, H - 34, W - 70, H - 34], fill=(232, 226, 216), width=2)
    d.text((W - 70, H - 26), "资深架构师 李福春 · OPC时代的独孤九剑", font=f_sub,
           fill=(150, 150, 150), anchor="rs")

    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, optimize=True)
    print("[OK]", out, im.size)


if __name__ == "__main__":
    main()
