# -*- coding: utf-8 -*-
"""zpj · 把 content.json 渲染成自包含单页作品集 index.html

用法：
    python build_portfolio.py <content.json> [--skill-dir <zpj 根目录>] [--stats]

与 jl-zpj 的关系：同一套版式与编码策略，但把「区块是否渲染」交给显式标记，
不再依赖改版时人工数着删。三个约定：

  1. 内容与代码分离 —— 所有文案 / 图片映射写在 content.json，脚本零个人信息。
  2. 区块标记：<!--SEC:key-->…<!--/SEC:key-->  数据为空则整块（含它前后的留白）消失；
     <!--NAV:id-->…<!--/NAV:id-->  对应区块消失则导航项一起消失（不会留死链）；
     <!--HR-->  区块之间的分隔线，渲染后统一归一 —— 首尾与相邻重复的分隔线自动去掉；
     <!--N-->   章节序号，按 DOM 顺序自动编号（挪区块不再需要手动改编号）。
  3. 一次构建 = 一次校验 —— token 双向一致、资源键可解析、占位符零残留，
     任一不满足即 sys.exit(1)，不产出半成品。

图片 src 支持两种来源：
  * 磁盘路径（"assets/cert/xx.jpg"）—— 传统流水线；
  * data URI（"data:image/jpeg;base64,…"）—— 表单（assets/form.html）导出格式，
    浏览器里选完图直接内联，不需要先把文件落盘。
"""
import argparse
import base64
import io
import json
import os
import re
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install pillow")


# ----------------------------------------------------------------- 图像编码
DATA_URI_RE = re.compile(r"^data:image/([a-z+]+);base64,(.*)$", re.S)


def _decode_data_uri(s):
    """data URI -> (bytes, mime 子类型)；不是 data URI 返回 (None, None)。"""
    m = DATA_URI_RE.match(s.strip())
    if not m:
        return None, None
    return base64.b64decode(m.group(2)), m.group(1)


def to_data_uri(src, max_w=None, quality=82, as_png=None, passthrough=True, png8=False):
    """图片（路径或 data URI）-> (data URI, 归档字节)。

    as_png=None 时按扩展名推断目标格式。
    passthrough=True（默认）：当「无需缩放」且「源格式 == 目标格式」时，
    直接复用源字节，避免 JPEG 二次压缩的画质累积损失。
    png8=True：PNG 量化为 256 色调色板 —— 架构图这类线条 + 大色块素材配色有限，
    量化后肉眼基本无损，体积可省 50%+（手机 / 微信 / 企业 IM 对单文件体积更敏感）。
    """
    raw_src, src_ext = _decode_data_uri(src)
    if raw_src is not None:                       # 表单导出的内联图
        if as_png is None:
            as_png = src_ext in ("png", "webp")
        im = Image.open(io.BytesIO(raw_src))
        path = None
    else:
        if not os.path.exists(src):
            raise FileNotFoundError(src)
        if as_png is None:
            as_png = src.lower().endswith(".png")
        im = Image.open(src)
        path = src

    src_png = (im.format or "").upper() == "PNG"
    need_resize = bool(max_w and im.width > max_w)
    if passthrough and not need_resize and src_png == as_png and not png8:
        if raw_src is not None:
            raw = raw_src
        else:
            with open(path, "rb") as fh:
                raw = fh.read()
        mime = "image/png" if as_png else "image/jpeg"
        return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode()), raw
    if need_resize:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    if as_png:
        if png8:
            # 有 alpha 走 FASTOCTREE（保留透明），否则 MEDIANCUT + 关闭抖动
            # （抖动会在深色底上产生噪点，纯色块图不需要）
            if im.mode in ("RGBA", "LA", "P"):
                im.convert("RGBA").quantize(colors=256, method=Image.FASTOCTREE).save(
                    buf, "PNG", optimize=True)
            else:
                im.convert("RGB").quantize(colors=256, method=Image.MEDIANCUT,
                                           dither=Image.NONE).save(buf, "PNG", optimize=True)
        else:
            im.convert("RGB").save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        mime = "image/jpeg"
    raw = buf.getvalue()
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode()), raw


# ----------------------------------------------------------------- 工具
def esc(s):
    return (str(s).replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def split_tags(s):
    """标签串 / 标签数组 -> 标签列表。

    优先按 " / "（带空格）切分，避免把 CI/CD、ASR/TTS 这类本身含斜杠的词
    拆成两个标签；数据里若只写了裸 "/" 再退回按 "/" 切。
    已经是数组的直接用（手写 JSON 常写成数组，表单导出的是字符串）。
    """
    if isinstance(s, (list, tuple)):
        return [str(x).strip() for x in s if str(x).strip()]
    s = str(s or "")
    raw = s.split(" / ") if " / " in s else s.split("/")
    return [t.strip() for t in raw if t.strip()]


def truthy(v):
    """区块是否该渲染：空字符串 / 空列表 / 空字典 / 全空白 都算空。"""
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, tuple, dict)):
        return any(truthy(x) for x in (v.values() if isinstance(v, dict) else v))
    return bool(v)


def lines(v):
    """多行文本 / 列表 -> 非空行列表。表单导出的是 "一行一条" 的字符串，
    手写 JSON 的常是数组 —— 两种输入都要能吃。"""
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or "").splitlines() if x.strip()]


def pairs(v):
    """多行文本 / [[a,b],...] -> [[a, b], ...]（"数值 | 说明" 一行一条）。"""
    if isinstance(v, (list, tuple)):
        return [[str(x[0]), str(x[1]) if len(x) > 1 else ""] for x in v if len(x)]
    out = []
    for l in lines(v):
        a, _, b = l.partition("|")
        out.append([a.strip(), b.strip()])
    return out


# ----------------------------------------------------------------- 图标库
# 能力支柱图标库：content.pillars[].icon 引用这里的键，未知键回落 arch。
ICON_PATHS = {
    "arch":   ('#4ea8ff', '<rect x="3" y="3" width="7" height="7" rx="1.5"/>'
                          '<rect x="14" y="3" width="7" height="7" rx="1.5"/>'
                          '<rect x="3" y="14" width="7" height="7" rx="1.5"/>'
                          '<rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
    "ai":     ('#8b5cff', '<path d="M12 3v3M12 18v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M3 12h3M18 12h3'
                          'M4.9 19.1L7 17M17 7l2.1-2.1"/><circle cx="12" cy="12" r="3.4"/>'),
    "lead":   ('#2fd07f', '<path d="M17 20v-2a3 3 0 0 0-3-3H6a3 3 0 0 0-3 3v2"/>'
                          '<circle cx="10" cy="8" r="3.4"/>'
                          '<path d="M21 20v-2a3 3 0 0 0-2.3-2.9M16.5 5.1a3.4 3.4 0 0 1 0 5.8"/>'),
    "code":   ('#4ea8ff', '<path d="M8 6 3 12l5 6M16 6l5 6-5 6"/><path d="M13.5 4.5 10.5 19.5"/>'),
    "data":   ('#8b5cff', '<ellipse cx="12" cy="6" rx="7" ry="3"/>'
                          '<path d="M5 6v6c0 1.66 3.13 3 7 3s7-1.34 7-3V6M5 12v6c0 1.66 3.13 3 7 3s7-1.34 7-3v-6"/>'),
    "cloud":  ('#2fd07f', '<path d="M6.5 19h11a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.4 9.2 4.5 4.5 0 0 0 6.5 19Z"/>'),
    "shield": ('#4ea8ff', '<path d="M12 3l7 3v6c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z"/>'),
    "rocket": ('#2fd07f', '<path d="M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2M14.5 4.5C17 4 20 5 20 5s1 3-.5 5.5'
                          'c-1.4 2.3-3.6 4-6 5.2L9 12c1.2-2.4 2.9-4.6 5.5-7.5Z"/>'
                          '<circle cx="15" cy="8.5" r="1.6"/>'),
}


def svg_icon(kind):
    stroke, body = ICON_PATHS.get(kind, ICON_PATHS["arch"])
    return ('<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="%s" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">%s</svg>'
            % (stroke, body))


# ----------------------------------------------------------------- 渲染片段
def render_metrics(rows):
    """首屏数据条。rows: [[数值, 单位, 说明], ...]；单位可为空串。"""
    out = []
    for v, unit, label in rows:
        u = '<span style="font-size:15px">%s</span>' % esc(unit) if unit else ""
        out.append("<div><b>%s%s</b><span>%s</span></div>" % (esc(v), u, esc(label)))
    return ('<div class="metrics rv" style="--mc:%d">%s</div>'
            % (max(1, len(rows)), "".join(out)))


def render_namecard(card):
    """首屏名片（Hero 主体）。card 缺省 / 为空 -> 返回空串（Hero 只剩一行 tagline）。

    名片就是首屏本身 —— 不再有「大标题 + 信条 + 徽章 + 按钮」的文案块：
    名片已含姓名 / 头衔 / 教育背景 / 核心方向 / 代表项目 / 联系方式，而原文案块
    的信息与证书图、ABOUT ME 自述重复。名片必须铺满内容宽度，否则卡面文字不可读。
    """
    if not card:
        return ""
    t = card.get("title") or "名片"
    return ('<div class="hero-card" data-zoom="namecard" data-title="%s" data-sub="%s">'
            '<img data-asset="namecard" alt="%s">'
            '<div class="hc-hint">%s</div></div>'
            % (esc(t), esc(card.get("sub", "")), esc(t),
               esc(card.get("hint") or "点击名片可放大 ↗")))


def render_intro(intro):
    """第一人称自述。intro 缺省 / 为空 -> 返回空串（整块不渲染）。

    字段：label 侧栏小标 / who 姓名 / where 头衔·城市 /
          lead 首句重音（可含 <b>） / paras 正文段落列表 / facts [[数值, 说明], ...]
    """
    if not intro:
        return ""
    side = ('<div class="side"><div class="lb">%s</div><div class="who">%s</div>'
            '<div class="where">%s</div></div>'
            % (esc(intro.get("label") or "ABOUT ME"), intro.get("who", ""),
               intro.get("where", "")))
    txt = ['<div class="txt">']
    if intro.get("lead"):
        txt.append('<p class="lead">%s</p>' % intro["lead"])
    for p in lines(intro.get("paras")):
        txt.append("<p>%s</p>" % p)
    facts = pairs(intro.get("facts"))
    if facts:
        txt.append('<div class="facts">%s</div>' % "".join(
            "<div><b>%s</b><span>%s</span></div>" % (f[0], f[1]) for f in facts))
    txt.append("</div>")
    return '<div class="intro rv">%s%s</div>' % (side, "".join(txt))


def render_pillars(rows):
    """核心能力支柱。rows: [{icon, title, desc, tags[]|"a / b"}, ...]"""
    out = []
    for p in rows:
        tags = "".join("<li>%s</li>" % esc(t) for t in split_tags(p.get("tags")))
        out.append('<div class="pillar rv"><div class="ic">%s</div><h3>%s</h3>'
                   '<p>%s</p><ul>%s</ul></div>'
                   % (svg_icon(p.get("icon", "arch")), esc(p["title"]), p["desc"], tags))
    return "\n".join(out)


def render_project(p, no):
    chips = "".join('<span class="chip">%s</span>' % esc(c) for c in split_tags(p["chips"]))
    steps = "".join("<li>%s</li>" % s for s in lines(p["steps"]))
    o = ['<article class="p-card rv">', '<div class="p-body">']
    o.append('<div class="p-top"><div><div class="p-title"><span class="no">%s</span>%s</div>'
             '<div class="p-sub">%s</div></div><div class="p-meta">%s</div></div>'
             % (no, p["title"], p["sub"], p["period"]))
    o.append('<div class="blk"><div class="lb">PROJECT INTRO</div><p>%s</p></div>' % p["desc"])
    o.append('<div class="hl"><span class="lb">MY RESULT</span>%s</div>' % p["result"])
    o.append('<div class="blk"><div class="lb">KEY ACTIONS</div><ul class="ach">%s</ul></div>' % steps)
    o.append('<div class="chips">%s</div>' % chips)
    o.append("</div>")
    # fig 可以为空：早期项目没有留存架构图，就只出文字卡，不留空图占位
    if p.get("fig"):
        o.append('<div class="figure" data-zoom="%s" data-title="%s" data-sub="%s">'
                 '<div class="hint"><span>架构图 · %s</span><em>点击放大 ↗</em></div>'
                 '<img data-asset="%s" alt="%s" decoding="async"></div>'
                 % (p["fig"], esc(p["fig_title"]), esc(p["fig_sub"]),
                    p["fig_title"], p["fig"], esc(p["fig_title"])))
    if p.get("extra"):
        cells = "".join(
            '<div class="gitem" data-zoom="%s" data-title="%s" data-sub="%s">'
            '<img data-asset="%s" alt="%s" decoding="async"><div class="gl">%s</div></div>'
            % (k, esc(t), esc(s), k, esc(t), t) for k, t, s in p["extra"] if k)
        o.append('<div class="figure" style="cursor:default">'
                 '<div class="hint"><span>补充架构图 · 技术分层版</span><em>点击放大 ↗</em></div>'
                 '<div class="gal">%s</div></div>' % cells)
    o.append("</article>")
    return "\n".join(o)


def render_projects(rows):
    return "\n".join(render_project(p, "%02d" % (i + 1)) for i, p in enumerate(rows))


def render_stack(stack):
    """技术栈分组卡。每行 [分组名, "标签 / 标签", 实践说明?] —— 第三项可选，可含 <b>。"""
    out = []
    for row in stack:
        name, items = row[0], row[1]
        note = row[2] if len(row) > 2 else ""
        note_html = '<div class="note">%s</div>' % note if note else ""
        tags = "".join("<span>%s</span>" % esc(t) for t in split_tags(items))
        out.append('<div class="st rv"><h4>%s</h4>%s<div class="tags">%s</div></div>'
                   % (esc(name), note_html, tags))
    return "\n".join(out)


def render_timeline(timeline):
    out = []
    for when, role, org, now, bullets in timeline:
        lis = "".join("<li>%s</li>" % b for b in lines(bullets))
        out.append('<div class="tl-item%s"><div class="tl-when">%s</div>'
                   '<div class="tl-role">%s%s</div><div class="tl-org">%s</div>'
                   '<ul>%s</ul></div>'
                   % (" now" if now else "", esc(when), esc(role),
                      '<em>· 现职</em>' if now else "", esc(org), lis))
    return "\n".join(out)


def render_edu(edu):
    """教育背景行。edu: {label, tags[] | "a / b"}；缺省则整行不渲染。"""
    if not edu or not truthy(edu.get("tags")):
        return ""
    tags = "".join("<span>%s</span>" % esc(t) for t in split_tags(edu["tags"]))
    return ('<div class="st rv" style="margin-bottom:26px;display:flex;align-items:center;'
            'gap:20px;flex-wrap:wrap"><h4 style="margin:0">%s</h4>'
            '<div class="tags">%s</div></div>'
            % (esc(edu.get("label") or "教育背景"), tags))


def render_certs(cert_label):
    """cert_label: [[资源键, 名称, 说明], ...]；键为空表示还没选图 —— 整项跳过，不留空卡。"""
    return "\n".join(
        '<div class="cert" data-zoom="%s" data-title="%s" data-sub="%s">'
        '<img data-asset="%s" alt="%s"><div class="cl">%s</div></div>'
        % (k, esc(lb), esc(sub), k, esc(lb), lb)
        for k, lb, sub in cert_label if k)


def render_qrs(qrs):
    """qrs: [[资源键, 名称, 链接], ...]；缺图或缺链接的整项跳过（不可点击的二维码没有意义）。"""
    return "\n".join(
        '<a class="qr" href="%s" target="_blank" rel="noopener">'
        '<img data-asset="%s" alt="%s"><div class="ql">%s</div>'
        '<div class="qu">%s</div></a>'
        % (url, k, esc(lb), lb, url.replace("https://", "").replace("http://", ""))
        for k, lb, url in qrs if k and url)


def col_class(n, cap=4):
    """证书 / 二维码网格列数：数据条数 <= 3 时收窄，避免大块留空。"""
    if not n:
        return ""
    return " c%d" % n if n in (2, 3) else ""


# ----------------------------------------------------------------- 结构后处理
SEC_RE = re.compile(r"<!--SEC:([a-z_]+)-->(.*?)<!--/SEC:\1-->", re.S)
NAV_RE = re.compile(r"<!--NAV:([a-z_]+)-->(.*?)<!--/NAV:\1-->", re.S)
HR_MARK = "<!--HR-->"
HR_HTML = '<div class="wrap"><div class="hr"></div></div>'


def strip_blocks(html, pattern, dropped):
    """按标记名移除整块（含标记自身）。dropped 为空集时只做解包，保留内容。"""
    def rep(m):
        return "" if m.group(1) in dropped else m.group(2)
    return pattern.sub(rep, html)


def normalize_separators(html):
    """分隔线归一：只在 <main> 内部处理，首尾与相邻重复的 <!--HR--> 一律去掉。

    区块裁减后最容易留下的两类坏状态 —— 尾部「什么都没有的分隔线」、
    「第一个区块前就分一条线」—— 在这里被一次性消除，不靠人工数着删。
    注意处理范围必须限定在 <main> 之内：否则页面前缀（nav / hero）会被当成
    第一个「非空片段」，删掉首个区块后就会凭空多出一条分隔线。
    """
    def fix(m):
        parts = [p.strip() for p in m.group(2).split(HR_MARK)]
        parts = [p for p in parts if p]
        return m.group(1) + ("\n\n" + HR_HTML + "\n\n").join(parts) + m.group(3)

    return re.sub(r"(?s)(<main>)(.*?)(</main>)", fix, html, count=1)


def number_sections(html):
    """章节序号：按 DOM 顺序自动编号（<!--N--> → 01/02/…）。

    挪区块位置后不必再手改编号，序号与顺序不可能脱钩。
    """
    counter = [0]

    def rep(_m):
        counter[0] += 1
        return "%02d" % counter[0]

    return re.sub(r"<!--N-->", rep, html)


# ----------------------------------------------------------------- 主流程
PLACEHOLDERS = ["<!--METRICS-->", "<!--NAMECARD-->", "<!--INTRO-->", "<!--PILLARS-->",
                "<!--PROJECTS-->", "<!--STACK-->", "<!--TIMELINE-->", "<!--EDU-->",
                "<!--CERTS-->", "<!--QRS-->", "<!--CERT_COLS-->", "<!--QR_COLS-->",
                "<!--N-->", HR_MARK, "/*ASSETS*/{}/*END*/"]

KNOWN_TOP_KEYS = {"paths", "texts", "card", "metrics", "images", "content"}
KNOWN_CONTENT_KEYS = {"intro", "pillars", "projects", "stack", "timeline",
                      "edu", "cert_label", "qrs"}
TOP_ONLY_KEYS = {"card", "metrics"}
TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
SEC_KEYS = ("tagline", "metrics", "intro", "capability", "stack", "career",
            "credential", "projects")
NAV_TO_SEC = {"about": "intro", "capability": "capability", "stack": "stack",
              "career": "career", "credential": "credential", "projects": "projects"}


def build(cfg, skill_dir):
    """content.json 字典 -> 最终 HTML 字符串（不落盘，便于测试与表单复用）。"""
    C = cfg.get("content") or {}
    images = cfg.get("images") or {}
    P = cfg.get("paths") or {}
    # 名片只有配了图才算「有」—— 配置里留着一个没有 src 的 card 不会渲染出空图
    card = cfg.get("card") if (cfg.get("card") and "namecard" in images) else None
    certs = [c for c in (C.get("cert_label") or []) if c and c[0]]
    qrs = [q for q in (C.get("qrs") or []) if q and q[0] and len(q) > 2 and q[2]]
    projects = C.get("projects") or []

    keep = {
        "tagline": truthy((cfg.get("texts") or {}).get("TAGLINE")),
        "metrics": truthy(cfg.get("metrics")),
        "intro": truthy(C.get("intro")),
        "capability": truthy(C.get("pillars")),
        "stack": truthy(C.get("stack")),
        "career": truthy(C.get("timeline")),
        "credential": bool(truthy(C.get("edu")) or certs or qrs),
        "projects": truthy(projects),
    }

    # ---- 资源：默认内嵌 data URI；paths.external 非空时改写文件到指定目录（相对路径引用）
    # 外置形态用于「页面要长期维护 / 图片要能单独替换」的场景，index.html 可降到几十 KB。
    ext_dir = P.get("external") or ""
    if isinstance(ext_dir, dict):
        ext_dir = ext_dir.get("dir") or "img"
    assets, archived, external, raw_bytes = {}, [], [], 0
    referenced = set()
    for p in projects:
        if p.get("fig"):
            referenced.add(p["fig"])
        for k, _t, _s in (p.get("extra") or []):
            if k:
                referenced.add(k)
    referenced |= {c[0] for c in certs}
    referenced |= {q[0] for q in qrs}
    if card:
        referenced.add("namecard")

    unknown = sorted(referenced - set(images))
    if unknown:
        sys.exit("[构建失败] 正文引用了 images 段里没有的资源键：%s\n"
                 "  这些键会在页面上留一张永远加载不出来的空图。" % unknown)

    for key, spec in images.items():
        kw = {}
        for f in ("max_w", "quality", "as_png", "png8", "passthrough"):
            if f in spec:
                kw[f] = spec[f]
        src = spec["src"]
        base = P.get("src_dir") or ""
        if base and not os.path.isabs(src) and not DATA_URI_RE.match(src.strip()):
            src = os.path.join(base, src)                    # 相对路径按 paths.src_dir 解析
        try:
            uri, raw = to_data_uri(src, **kw)
        except FileNotFoundError:
            sys.exit("[构建失败] 素材缺失：%s（资源键 %s）" % (src, key))
        raw_bytes += len(raw)
        if ext_dir:
            # 扩展名以「实际编码出的格式」为准 —— 源图可能是 png 但被压成 jpeg
            mime = uri[5:uri.index(";")] if uri.startswith("data:") else "image/png"
            suf = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp",
                   "image/gif": "gif"}.get(mime, "png")
            rel = spec.get("file") or "%s/%s/%s.%s" % (
                ext_dir, spec.get("group") or "misc", key, suf)
            rel = rel.replace("\\", "/")
            dest = os.path.join(P.get("out_dir") or ".", rel)
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(raw)
            assets[key] = rel
            external.append((key, rel, len(raw)))
            continue                       # 已外置，archive 不再重复落一份
        assets[key] = uri
        arc = spec.get("archive")
        if arc:
            pth = arc if (os.path.isabs(arc) or not P.get("out_dir")) \
                else os.path.join(P["out_dir"], arc)
            os.makedirs(os.path.dirname(pth) or ".", exist_ok=True)
            with open(pth, "wb") as fh:
                fh.write(raw)
            archived.append((key, arc, len(raw)))

    # ---- token：先合并派生默认值，再做双向一致门禁
    n_proj, n_tl = len(projects), len(C.get("timeline") or [])
    cred_parts = []
    if truthy(C.get("edu")):
        cred_parts.append("教育背景")
    if certs:
        cred_parts.append("专业认证")
    if qrs:
        cred_parts.append("个人主页")
    T = cfg.get("texts") or {}
    defaults = {
        # 这四项用户不填也允许为空（表单里可以留空）—— 空值有明确语义：
        # MARK 用 placeholder，TAGLINE 空则整行不渲染，NAME 空则由构建时告警提示。
        "NAME": "", "ROLE": "", "ROLE_SHORT": "", "TAGLINE": "",
        "MARK": (T.get("NAME") or "·")[0],
        "TITLE": "%s · %s | 作品集" % (T.get("NAME", ""), T.get("ROLE_SHORT", "")),
        "META_DESC": "%s · %s 个人作品集" % (T.get("NAME", ""), T.get("ROLE", "")),
        "CAP_LEAD": "从核心编码到架构决策，从能力工程化到团队与交付体系，全部亲自下场。",
        "STACK_LEAD": "按能力维度组织：主干技术栈 + 相邻能力 + 工程化配套。",
        "CRED_H2": " · ".join(cred_parts) or "资质与主页",
        "CAREER_LEAD": "共 %d 段履历，按时间由近及远排列。" % n_tl,
        "PROJ_LEAD": "共 %d 个项目，按时间由近及远排列，一个项目一节。每张架构图可点击放大。"
                     % n_proj,
    }
    texts = {k: v for k, v in T.items() if truthy(v)}   # 用户给了非空值就用用户的
    for k, v in defaults.items():                       # 其余（含派生的）回落默认
        if not truthy(texts.get(k)):
            texts[k] = v

    with open(os.path.join(skill_dir, "assets", "template.html"), encoding="utf-8") as fh:
        tpl = fh.read()

    tpl_tokens = set(TOKEN_RE.findall(tpl))
    missing = sorted(tpl_tokens - set(texts))
    # ROLE 作为 META_DESC 的输入被间接消费，模板里不再单独出现 —— 不算死键
    dead = sorted(set(T) - tpl_tokens - {"ROLE"})
    if missing:
        sys.exit("[构建失败] 模板占位符在 texts 段没有对应值：%s\n"
                 "  请补 texts.%s，或从 assets/template.html 删除该 {{...}}。"
                 % (missing, missing[0]))
    if dead:
        print("  注意：texts 段有模板未使用的键 %s（不影响构建）" % dead)
    if not truthy(texts.get("NAME")):
        print("  注意：texts.NAME 为空 —— 页面标题、浏览器标签页与文件名都会是空的")

    # ---- 配置层级门禁（拦「键写错层级 → 整块静默消失」）
    stray = sorted(set(cfg) - KNOWN_TOP_KEYS)
    if stray:
        sys.exit("[构建失败] content.json 顶层出现未知键：%s\n  合法顶层键：%s\n"
                 "  提示：%s 属于 content 段内。"
                 % (stray, ", ".join(sorted(KNOWN_TOP_KEYS)), " / ".join(sorted(KNOWN_CONTENT_KEYS))))
    misplaced = sorted(set(C) & TOP_ONLY_KEYS)
    if misplaced:
        sys.exit("[构建失败] %s 属于顶层键，不应写在 content 段内 —— 否则整块不会渲染" % misplaced)
    stray_c = sorted(set(C) - KNOWN_CONTENT_KEYS)
    if stray_c:
        sys.exit("[构建失败] content 段出现未知键：%s（合法：%s，拼错即静默丢数据）"
                 % (stray_c, ", ".join(sorted(KNOWN_CONTENT_KEYS))))

    for k, v in texts.items():
        tpl = tpl.replace("{{%s}}" % k, str(v))

    html = (tpl
            .replace("<!--METRICS-->", render_metrics(cfg.get("metrics") or []))
            .replace("<!--NAMECARD-->", render_namecard(card))
            .replace("<!--INTRO-->", render_intro(C.get("intro")))
            .replace("<!--PILLARS-->", render_pillars(C.get("pillars") or []))
            .replace("<!--PROJECTS-->", render_projects(projects))
            .replace("<!--STACK-->", render_stack(C.get("stack") or []))
            .replace("<!--TIMELINE-->", render_timeline(C.get("timeline") or []))
            .replace("<!--EDU-->", render_edu(C.get("edu")))
            .replace("<!--CERTS-->", render_certs(certs))
            .replace("<!--QRS-->", render_qrs(qrs))
            .replace("<!--CERT_COLS-->", col_class(len(certs)))
            .replace("<!--QR_COLS-->", col_class(len(qrs)))
            .replace("/*ASSETS*/{}/*END*/", json.dumps(assets, ensure_ascii=False)))

    # 区块裁减：数据为空 -> 整块消失；导航项跟随；分隔线归一；章节序号自动编号
    drop_sec = {k for k in SEC_KEYS if not keep[k]}
    html = strip_blocks(html, SEC_RE, drop_sec)
    drop_nav = {i for i, s in NAV_TO_SEC.items() if s in drop_sec}
    html = strip_blocks(html, NAV_RE, drop_nav)
    html = normalize_separators(html)
    html = number_sections(html)

    # 残留自检：任何一个没被替换的标记都说明模板与脚本脱钩了
    residue = [ph for ph in PLACEHOLDERS if ph in html] + \
              ["{{%s}}" % k for k in texts if "{{%s}}" % k in html]
    if residue:
        sys.exit("[构建失败] 占位符未替换：%s" % residue)
    if re.search(r"<!--(SEC|NAV):", html):
        sys.exit("[构建失败] 区块标记未处理完：%s"
                 % re.findall(r"<!--(?:SEC|NAV):[a-z_]+-->", html)[:5])

    stats = {
        "metrics": len(cfg.get("metrics") or []),
        "namecard": 1 if card else 0,
        "intro": 1 if keep["intro"] else 0,
        "pillars": len(C.get("pillars") or []),
        "projects": n_proj,
        "stack": len(C.get("stack") or []),
        "timeline": n_tl,
        "certs": len(certs),
        "qrs": len(qrs),
        "images": len(assets),
        "kept": [k for k in ("capability", "stack", "career", "credential", "projects")
                 if keep[k]],
        "bytes": len(html.encode("utf-8")),
        "assets_bytes": raw_bytes,
        "external": ext_dir,
        "external_files": [{"key": k, "file": f, "bytes": n} for k, f, n in external],
    }
    return html, stats, archived


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", help="content.json 路径")
    ap.add_argument("--skill-dir",
                    default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help="zpj 技能根目录（用于定位 assets/template.html）")
    ap.add_argument("--out", default="", help="输出 index.html 路径（默认 <paths.out_dir>/index.html）")
    ap.add_argument("--stats", action="store_true", help="把统计以 STATS:{...} 单行 JSON 打印")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    html, stats, archived = build(cfg, args.skill_dir)

    out = args.out or os.path.join((cfg.get("paths") or {}).get("out_dir", "."), "index.html")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    for key, arc, n in archived:
        print("归档 %-16s %7.1f KB -> %s" % (key, n / 1024, arc))
    if stats["external"]:
        for f in stats["external_files"]:
            print("外置 %-16s %7.1f KB -> %s" % (f["key"], f["bytes"] / 1024, f["file"]))
        print("\n外置资源 %.2f MB ｜ index.html %.2f MB ｜ 区块 %s"
              % (stats["assets_bytes"] / 1024 / 1024, stats["bytes"] / 1024 / 1024,
                 "+".join(stats["kept"])))
    else:
        print("\n内嵌资源 %.2f MB ｜ index.html %.2f MB ｜ 区块 %s"
              % (stats["assets_bytes"] / 1024 / 1024, stats["bytes"] / 1024 / 1024,
                 "+".join(stats["kept"])))
        if stats["assets_bytes"] > 5 * 1024 * 1024:
            print("  警告：内嵌资源超过 5MB，手机端打开会卡 —— 建议对架构图开 png8 / 降低 max_w")
    if args.stats:
        print("STATS:" + json.dumps(stats, ensure_ascii=False))
    print("\nOK ->", out)


if __name__ == "__main__":
    main()
