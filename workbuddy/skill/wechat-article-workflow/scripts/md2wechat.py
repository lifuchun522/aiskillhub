# -*- coding: utf-8 -*-
"""把初稿.md 转成微信安全 HTML（纯内联 style + <section>）+ 按规划插入图片占位符。

用法:
    python md2wechat.py --key 02_破剑式

从同目录的初稿.md 读入，输出 article_body.html。
"""
import argparse
import os
import re
import sys

C = {
    "body": "font-size:16px;line-height:1.9;color:#2b2b2b;letter-spacing:.3px;"
            "font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;",
    "h2": "font-size:19px;font-weight:bold;color:#1a1a1a;margin:34px 0 14px;line-height:1.5;",
    "p": "margin:0 0 18px;",
    "quote": "margin:0 0 26px;padding:14px 18px;border-left:3px solid #c9a86a;"
             "background:#faf8f3;color:#5a5648;font-size:16px;line-height:1.9;",
    "li": "margin:0 0 12px;padding-left:4px;",
    "strong": "color:#8a5a2b;",
    "sign": "margin:36px 0 0;padding-top:18px;border-top:1px solid #e8e4dc;"
            "font-size:14px;color:#8a8a8a;text-align:right;",
    "hr": "height:1px;background:#e8e4dc;margin:30px 0;",
}

# 卡片对比块：> [!card] 标题 / 描述 两行一组
CARD_HEAD = ("margin:0;padding:11px 14px 2px;font-size:16px;line-height:1.7;"
             "font-weight:bold;color:#2b2b2b;")
CARD_DESC = ("margin:0;padding:0 14px 12px;font-size:15px;line-height:1.75;color:#6b675e;")
CARD_BOX = ("margin:0 0 14px;background:#fbf9f5;border:1px solid #ece5d8;"
            "border-left:3px solid #c9a86a;border-radius:8px;")

# 篇 -> [(小节关键字, 占位符)]，占位符按此顺序插入到该小节标题之后
LAYOUTS = {
    "00": [
        ("四、写给四类人", "img1"),
        ("为什么用独孤九剑", "img2"),
        ("为什么又用七个习惯", "img3"),
        ("九式一览", "img_archs"),
        ("一张总图", "img_arch"),
        ("给自己写一首", "img4"),
    ],
    "01": [
        ("我问错了问题", "img1"),
        ("老周那句话", "img2"),
        ("换一个能验证的问题", "img3"),
        ("一张总图", "img_arch"),
        ("归去，也无风雨也无晴", "img4"),
    ],
    "02": [
        ("我给自己找的理由", "img1"),
        ("三十天，三件事", "img2"),
        ("第十八天，那个 Demo", "img3"),
        ("一张图：两个圈", "img_arch"),
        ("给自己留个三十天", "img4"),
    ],
    "03": [
        ("先想终局，再想当下", "img1"),
        ("给客户的话：不做清单", "img2"),
        ("一张终局图", "img_arch"),
        ("给自己留个终局", "img3"),
        ("砍不是减法，是定价", "img4"),
    ],
    "04": [
        ("我用了一把很钝的尺子", "img1"),
        ("第四十二天的那次崩溃", "img3"),
        ("一张图：优先级四象限", "img_arch"),
        ("放下的那个功能", "img2"),
        ("给自己留个最低限度", "img4"),
    ],
    "05": [
        ("把自己从", "img1"),
        ("那个设计师", "img3"),
        ("一张网", "img_arch"),
        ("跟客户也不做", "img2"),
        ("那个月的账", "img4"),
    ],
    "06": [
        ("我把访谈记录翻了出来", "img1"),
        ("六步问法", "img2"),
        ("重新约见林总", "img4"),
        ("一张表：表面需求", "img_arch"),
        ("给自己理顺那个结", "img3"),
    ],
    "07": [
        ("我把自己写的代码过了一遍", "img1"),
        ("能力编排：五类分法", "img2"),
        ("那次模型切换", "img3"),
        ("一张图：能力编排", "img_arch"),
        ("那个我没招的人", "img4"),
    ],
    "08": [
        ("那两周", "img1"),
        ("四个层级的更新机制", "img2"),
        ("此心安处", "img3"),
        ("一张图：更新飞轮", "img_arch"),
        ("第一次复盘，看到的数", "img4"),
    ],
    "09": [
        ("把它们摞起来看", "img1"),
        ("这套东西能换赛道吗", "img2"),
        ("那张完整的图", "img_arch"),
        ("最后给自己写首诗", "img3"),
        ("回头看那条路", "img4"),
    ],
}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def split_row(s):
    """GFM 表格行 -> 单元格列表。去掉首尾竖线后按未转义竖线切分。"""
    s = s.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def is_sep_row(s):
    """|---|---| 这类分隔行。"""
    if not re.match(r"^\|[\s:|-]+\|?\s*$", s.strip()):
        return False
    return "-" in s and set(s.replace("|", "").replace(" ", "")) <= set("-:")


def render_table(rows):
    """把 GFM 表格渲染成微信可用的 <section>。表头加底色，单元格 inline style。

    微信禁用真正的 <table> 之外还有样式限制，这里用 <section> + 逐行 <p> 模拟，
    保证公众号编辑器不吞样式。
    """
    head, body = rows[0], rows[1:]
    width = len(head)
    out = ['<section style="margin:0 0 26px;">']

    def cells_to_line(cells, bold, bg):
        cells = (cells + [""] * width)[:width]
        parts = []
        for c in cells:
            inner = inline_md(c)
            if bold:
                inner = '<strong style="color:#3d3d3d;">%s</strong>' % inner
            parts.append(
                '<span style="display:inline-block;width:%d%%;padding:9px 8px;'
                'box-sizing:border-box;vertical-align:top;font-size:14px;'
                'line-height:1.6;color:#3d3d3d;">%s</span>'
                % (int(100 / width), inner or "&nbsp;")
            )
        return ('<section style="background:%s;border-bottom:1px solid #eee;">%s</section>'
                % (bg, "".join(parts)))

    out.append(cells_to_line(head, True, "#f5f2ec"))
    for r in body:
        out.append(cells_to_line(r, False, "#ffffff"))
    out.append("</section>")
    return "\n".join(out)


def inline_md(t):
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*",
               r'<strong style="color:#8a5a2b;">\1</strong>', t)
    # markdown 链接 [文字](url) -> 公众号可点链接。
    # 微信正文外链只在「阅读原文」和少数白名单域名可点，其余渲染为普通文字；
    # 这里统一输出 <a>，发布时若无法跳转也不影响阅读。
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               r'<a href="\2" style="color:#576b95;text-decoration:none;'
               r'border-bottom:1px solid #d5dced;">\1</a>', t)
    return t


def convert(md_text, key):
    lines = md_text.split("\n")
    layout = LAYOUTS.get(key, [])
    pending = dict((kw, ph) for kw, ph in layout)

    out = ['<section style="%s">' % C["body"]]
    in_list = False
    lead_img = "img0"      # 篇首图固定为 img0（紧接诗引，与诗引匹配）
    header_done = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</section>")
            in_list = False

    def emit_lead():
        """篇首图：紧接诗引之后、第一个正文小节之前输出一次。"""
        nonlocal header_done
        if header_done:
            return
        header_done = True
        if lead_img:
            out.append("{%s}" % lead_img)

    tbl = []          # 正在收集的 GFM 表格行
    line_idx = -1

    def flush_table():
        """把收集到的表格行渲染出来。"""
        nonlocal tbl
        if tbl:
            out.append(render_table(tbl))
            tbl = []

    for raw in lines:
        line_idx += 1
        s = raw.strip()
        if not s:
            continue

        # ---- GFM 表格：连续的 "|...|" 行成块处理 ----
        if s.startswith("|") and s.count("|") >= 2:
            row = split_row(s)
            if is_sep_row(s):
                # 分隔行只是表头标记，不作为数据
                continue
            tbl.append(row)
            # 检查下一行是否仍是表格行；不是则收尾
            nxt = lines[line_idx + 1].strip() if line_idx + 1 < len(lines) else ""
            nxt_is_sep = nxt.startswith("|") and is_sep_row(nxt)
            nxt_is_row = nxt.startswith("|") and nxt.count("|") >= 2
            if not (nxt_is_row or nxt_is_sep):
                close_list()
                flush_table()
            continue
        flush_table()


        if s.startswith("# ") and not s.startswith("## "):
            continue

        if s.startswith("## "):
            close_list()
            if not header_done:
                # 还没输出过首图 -> 这是第一个正文小节，先补首图再写标题
                emit_lead()
            title = s[3:].strip()
            out.append('<p style="%s">%s</p>' % (C["h2"], inline_md(title)))
            # 匹配插图（模糊包含）。占位符单独成行，不能包在 <p> 里，
            # 否则 generate_preview / push_draft 替换后得到裸 base64 字符串，图片不显示。
            # 每个 key 只插一次：同篇里若两个小节标题都含同一关键字，会重复插同一张图。
            for kw in list(pending.keys()):
                if kw in title:
                    out.append("{%s}" % pending.pop(kw))
                    break
            continue

        # ---- 卡片对比块 ----
        # 语法：
        #   > [!card] 标题行
        #   > 描述行（可多行，合并为一段）
        if s.startswith("> [!card]"):
            flush_table()
            close_list()
            head = s[len("> [!card]"):].strip()
            desc = []
            j = line_idx + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if nxt.startswith("> ") and not nxt.startswith("> [!card]"):
                    desc.append(nxt[2:].strip())
                    j += 1
                else:
                    break
            line_idx = j - 1
            out.append('<section style="%s">' % CARD_BOX)
            out.append('<p style="%s">%s</p>' % (CARD_HEAD, inline_md(head)))
            if desc:
                out.append('<p style="%s">%s</p>'
                           % (CARD_DESC, inline_md(" ".join(desc))))
            out.append("</section>")
            continue

        if s.startswith("> "):
            out.append('<p style="%s">%s</p>' % (C["quote"], inline_md(s[2:].strip())))
            emit_lead()          # 诗引行之后立刻放首图
            continue

        if s == "---":
            out.append('<p style="%s"></p>' % C["hr"])
            continue

        m = re.match(r"^([-*]|\d+\.)\s+(.*)$", s)
        if m:
            if not in_list:
                out.append("<section>")
                in_list = True
            out.append('<p style="%s">%s</p>' % (C["li"], inline_md(m.group(2))))
            continue
        else:
            close_list()

        out.append('<p style="%s">%s</p>' % (C["p"], inline_md(s)))

    close_list()
    out.append("</section>")
    return "\n".join(out), len(pending), [kw for kw in pending]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="如 02_破剑式")
    ap.add_argument("--dir", default=None, help="篇目录（优先）")
    ap.add_argument("--root", default=None)
    args = ap.parse_args()

    if args.dir:
        d = os.path.abspath(args.dir)
    else:
        root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        d = os.path.join(root, args.key)
    md = None
    for cand in ("正文.md", "初稿.md"):
        p = os.path.join(d, cand)
        if os.path.exists(p):
            md = p
            break
    if md is None:
        print("[ERR] 缺少正文.md / 初稿.md:", d)
        sys.exit(1)
    out = os.path.join(d, "article_body.html")

    with open(md, encoding="utf-8") as f:
        md_text = f.read()

    html, left, left_kw = convert(md_text, args.key)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    phs = re.findall(r"\{img(\w+)\}", html)
    print("[%s] 占位符: %s" % (args.key, phs))
    if left:
        print("   [WARN] 未匹配的小节关键字:", left_kw)
    print("   -> %s (%d chars)" % (out, len(html)))


if __name__ == "__main__":
    main()
