#!/usr/bin/env python3
"""从实测特性数据生成 SVG 思维导图（确定性布局，不手画）。

用法:
    python gen_mindmap.py --data examples/mindmap.sample.json --out mindmap.svg
    python gen_mindmap.py --data tree.json --theme light --cols 4 --width 1800

数据格式见 examples/mindmap.sample.json：
    {
      "title": "特性树 · 思维导图",
      "subtitle": "8 个域 · 全部条目由源码与运行时实测枚举",
      "center": {"title": "项目名", "sub": "特性树 · 8 域", "foot": "v1.0 · 实测"},
      "domains": [
        {"letter": "A", "name": "文案生成", "sub": "LLM · 37 Provider",
         "needkey": "需 Key", "color": "#60a5fa",
         "children": ["条目1", "条目2"]}
      ]
    }
needkey 取 "免 Key" / "部分免 Key" / "需 Key"，决定徽章颜色。
含「免费 / 免 Key / 本地」的子条目绿字高亮，一眼看出免费通道。
"""
import argparse
import json
import os
import sys

PALETTE = ["#60a5fa", "#f472b6", "#34d399", "#fbbf24",
           "#a78bfa", "#22d3ee", "#fb923c", "#94a3b8",
           "#f87171", "#4ade80"]
KEY_COLOR = {"免 Key": "#4ade80", "部分免 Key": "#fbbf24", "需 Key": "#f87171"}
FREE_HINTS = ("免费", "免 Key", "免 key", "本地", "内置", "原声")
THEMES = {
    "dark": dict(bg="#0d1220", card="#161d2e", card_b="#263048", ink="#e8eefc",
                 sub="#8fa0bf", chip="#1e2740", chip_b="#2f3a56", chip_ink="#c7d2e8",
                 center="#1b2742", center_b="#4f7fd4", badge_bg="#0f1626", accent="#7fb0ff"),
    "light": dict(bg="#f7f9fd", card="#ffffff", card_b="#dfe5f0", ink="#1a2233",
                  sub="#5b6776", chip="#eef2f8", chip_b="#d8e0ee", chip_ink="#2b3b52",
                  center="#eef4ff", center_b="#4f7fd4", badge_bg="#ffffff", accent="#2f6df6"),
}
FF = "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tw(s, fs):
    """估算文本宽度：CJK 按 1.06em（留字宽余量防溢出），其余按 0.58em。"""
    return sum(fs * (1.06 if ord(ch) > 0x2E80 else 0.58) for ch in s)


def rr(x, y, w, h, r, fill, stroke=None, sw=1.0):
    s = (f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
         f'rx="{r}" fill="{fill}"')
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{sw}"'
    return s + '/>\n'


def txt(x, y, s, fill, fs, weight=400, anchor="start", baseline="auto"):
    bl = f' dominant-baseline="{baseline}"' if baseline != "auto" else ""
    return (f'  <text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{fs}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{bl}>{esc(s)}</text>\n')


def wrap_chips(children, maxw, fs):
    rows, cur, curw = [], [], 0.0
    for c in children:
        cw = tw(c, fs) + 26          # 左右内边距 12+12，再留 2px 字宽容差
        add = cw if not cur else curw + CHIP_GAP + cw
        if cur and add > maxw:
            rows.append(cur)
            cur, curw = [(c, cw)], cw
        else:
            cur.append((c, cw))
            curw = add
    if cur:
        rows.append(cur)
    return rows


def build(cfg, theme_name, width, cols):
    t = THEMES[theme_name]
    global CHIP_FS, CHIP_H, CHIP_GAP, ROW_LINE, PADX, HEADER_H, CARD_GAP, TOP, BOTTOM
    CHIP_FS, CHIP_H, CHIP_GAP = 13.5, 23, 9
    ROW_LINE = CHIP_H + CHIP_GAP
    PADX, HEADER_H, CARD_GAP, TOP, BOTTOM = 26, 78, 14, 116, 40

    W = width
    cw, chh = 366, 96                # 中心节点尺寸
    gap, margin = 96, 40             # 中心留白 / 画布边距
    bw = int(W / 2 - cw / 2 - gap - margin)   # 单侧卡片宽
    bw = max(420, min(640, bw))
    domains = cfg["domains"]

    cards = []
    for i, d in enumerate(domains):
        rows = wrap_chips(d.get("children", []), bw - PADX * 2, CHIP_FS)
        cards.append(dict(
            letter=d.get("letter", chr(65 + i)), name=d["name"], sub=d.get("sub", ""),
            needkey=d.get("needkey", "免 Key"),
            color=d.get("color") or PALETTE[i % len(PALETTE)],
            rows=rows, h=HEADER_H + len(rows) * ROW_LINE + 16))

    half = (len(cards) + 1) // 2 if cols <= 4 else min(cols, len(cards))
    left, right = cards[:half], cards[half:]

    def col_h(c):
        return sum(x["h"] for x in c) + CARD_GAP * max(0, len(c) - 1)

    colh = max(col_h(left), col_h(right))
    H = TOP + colh + BOTTOM

    def place(col):
        y = TOP + (colh - col_h(col)) / 2
        for c in col:
            c["y"] = y
            y += c["h"] + CARD_GAP

    place(left)
    place(right)

    CX, CY = W // 2, TOP + colh / 2
    # 卡片朝中心一侧的边界必须让开中心节点，否则中心卡会被两侧卡片压住
    left_edge, right_edge = CX - cw / 2 - gap, CX + cw / 2 + gap

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="100%" '
         f'style="max-width:{W}px;height:auto;display:block;margin:0 auto" '
         f'font-family="{FF}">\n']
    o.append(f'  <rect width="{W}" height="{H:.0f}" fill="{t["bg"]}" rx="16"/>\n')
    o.append(txt(CX, 54, cfg.get("title", "特性树 · 思维导图"), t["ink"], 30, 700, "middle"))
    if cfg.get("subtitle"):
        o.append(txt(CX, 84, cfg["subtitle"], t["sub"], 15.5, 400, "middle"))

    center = cfg.get("center", {})
    cx0, cy0 = CX - cw / 2, CY - chh / 2
    o.append(rr(cx0, cy0, cw, chh, 18, t["center"], t["center_b"], 2.0))
    o.append(txt(CX, CY - 13, center.get("title", ""), t["ink"], 23.5, 700, "middle"))
    o.append(txt(CX, CY + 19, center.get("sub", ""), t["accent"], 15.5, 400, "middle"))
    if center.get("foot"):
        o.append(txt(CX, cy0 + chh + 22, center["foot"], t["sub"], 12.5, 400, "middle"))

    for idx, c in enumerate(cards):
        side = -1 if idx < half else 1
        y, h, color = c["y"], c["h"], c["color"]
        x = (left_edge - bw) if side < 0 else right_edge

        sx = cx0 if side < 0 else cx0 + cw
        ex = left_edge if side < 0 else right_edge
        ey = y + HEADER_H / 2 - 2
        mx = (sx + ex) / 2
        o.append(f'  <path d="M {sx:.1f} {CY:.1f} C {mx:.1f} {CY:.1f} {mx:.1f} {ey:.1f} '
                 f'{ex:.1f} {ey:.1f}" fill="none" stroke="{color}" stroke-width="2.5" '
                 f'stroke-opacity="0.62"/>\n')

        o.append(rr(x, y, bw, h, 14, t["card"], t["card_b"], 1.2))
        bar_x = x + 8 if side < 0 else x + bw - 14
        o.append(rr(bar_x, y + 14, 6, max(0, h - 28), 3, color))

        lx = x + 26
        o.append(rr(lx, y + 22, 34, 34, 17, color))
        o.append(txt(lx + 17, y + 40, c["letter"], t["bg"], 19, 700, "middle", "central"))

        tx = lx + 48
        o.append(txt(tx, y + 36, c["name"], t["ink"], 19.5, 700, "start", "central"))
        if c["sub"]:
            o.append(txt(tx + tw(c["name"], 19.5) + 12, y + 37, c["sub"], t["sub"],
                         13.5, 400, "start", "central"))

        kc = KEY_COLOR.get(c["needkey"], t["sub"])
        kb = tw(c["needkey"], 12.5) + 20
        kbx = x + bw - 24 - kb
        o.append(rr(kbx, y + 26, kb, 24, 12, t["badge_bg"], kc, 1.2))
        o.append(txt(kbx + kb / 2, y + 38, c["needkey"], kc, 12.5, 400, "middle", "central"))

        ry = y + HEADER_H - 2
        for row in c["rows"]:
            rx = x + PADX
            for text, cwid in row:
                free = any(hint in text for hint in FREE_HINTS)
                o.append(rr(rx, ry, cwid, CHIP_H, CHIP_H // 2, t["chip"], t["chip_b"], 1.0))
                o.append(txt(rx + 12, ry + CHIP_H / 2, text,
                             "#4ade80" if free else t["chip_ink"],
                             CHIP_FS, 400, "start", "central"))
                rx += cwid + CHIP_GAP
            ry += ROW_LINE

    o.append('</svg>\n')
    return "".join(o), W, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="特性树 JSON 数据文件")
    ap.add_argument("--out", default="mindmap.svg")
    ap.add_argument("--theme", default="dark", choices=list(THEMES))
    ap.add_argument("--width", type=int, default=1800)
    ap.add_argument("--cols", type=int, default=4, help="单侧卡片数上限，域数 ≤ 8 时用 4")
    a = ap.parse_args()

    if not os.path.isfile(a.data):
        sys.exit(f"[error] 数据文件不存在: {a.data}")
    cfg = json.load(open(a.data, encoding="utf-8"))
    if not cfg.get("domains"):
        sys.exit("[error] domains 为空，导图没有内容")
    svg, w, h = build(cfg, a.theme, a.width, a.cols)
    open(a.out, "w", encoding="utf-8").write(svg)
    print(f"[ok] {a.out} | {w}x{h:.0f} | domains={len(cfg['domains'])} | "
          f"chars={len(svg)} | theme={a.theme}")


if __name__ == "__main__":
    main()
