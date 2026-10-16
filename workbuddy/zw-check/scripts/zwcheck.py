#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zw-check · 征文 / 投稿稿件发布前检查（离线优先，仅标准库）。

四类检查：
  text     字数口径（含空格 / 不含空格）与「加工痕迹」扫描
  html     结构完整性（表格 / 图注 / 标题层级 / 标签配平）与图片引用方式
  rules    征文硬性要求符合性（标题前缀、赛道标签、六维三层、Skill 目录约定…）
  consist  稿件与技能源码包的一致性（目录树 / 元数据 / 单测计数）

设计原则：
- 纯函数 + 显式规则：所有判定可离线复算，不依赖运行时推断；
- 判不了就报 NA 并写明原因，绝不猜测；
- 命中即给出原文上下文，便于定位；
- 退出码：0 全部通过；1 存在 FAIL；2 参数或文件错误。
"""

from __future__ import annotations

import argparse
import html as _html
import json
import re
import subprocess
import sys
from pathlib import Path

PASS, FAIL, WARN, NA = "PASS", "FAIL", "WARN", "NA"

# ------------------------------------------------------------------ 文本提取

_SCRIPT = re.compile(r"<script\b.*?</script>", re.I | re.S)
_STYLE = re.compile(r"<style\b.*?</style>", re.I | re.S)
_FIGURE = re.compile(r"<figure\b.*?</figure>", re.I | re.S)
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
_ANY_TAG = re.compile(r"<[^>]+>")
_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def html_visible(html_text: str, start: str | None = None, end: str | None = None) -> str:
    """取 HTML 的可见正文。

    去掉 script / style / figure / img 与全部标签，实体反转义，空白归一为单空格。
    图片既不计算文字，也不计算其 alt 文本。
    """
    frag = html_text
    if start:
        i = frag.find(start)
        if i >= 0:
            frag = frag[i:]
    if end:
        j = frag.find(end)
        if j >= 0:
            frag = frag[:j]
    frag = _SCRIPT.sub("", frag)
    frag = _STYLE.sub("", frag)
    frag = _FIGURE.sub("", frag)
    frag = _IMG_TAG.sub("", frag)
    return re.sub(r"\s+", " ", _html.unescape(_ANY_TAG.sub("", frag))).strip()


def md_visible(md_text: str, keep_code: bool = False) -> str:
    """取 Markdown 的可见正文：去图片语法，默认整段去掉围栏代码块。"""
    text = md_text
    if not keep_code:
        text = _FENCE.sub("", text)
    return re.sub(r"\s+", " ", _MD_IMAGE.sub("", text)).strip()


def count_chars(text: str) -> dict:
    """按「含空格 / 不含空格 / 中文汉字」三种口径计数。"""
    no_space = re.sub(r"\s", "", text)
    return {
        "with_space": len(text),
        "no_space": len(no_space),
        "spaces": len(text) - len(no_space),
        "cjk": len(re.findall(r"[\u4e00-\u9fff]", text)),
    }


# -------------------------------------------------------------- 加工痕迹扫描

# (类别, 级别, 正则, 说明)  级别 block = 必改；warn = 视文体斟酌
TRACE_RULES: list[tuple[str, str, str, str]] = [
    ("交付清单", "block",
     r"可供二次开发|可复核文件|本次实测还产出|以下(?:文件|产物)(?:一并|随(?:稿|包))|随包(?:一并)?附带",
     "把「交付了哪些文件」写进正文，读者视角读起来是交付说明，不是文章"),
    ("附件指向", "block",
     r"见文末附件|附件详见|详见附件|完整文件和检查脚本|放在文末附件",
     "正文指向附件/文件清单，属于写作过程残留"),
    ("文件路径外泄", "block",
     r"(?<![\w/.])（?`?(?:report|references|scripts|tests)/[\w./-]+\.(?:md|html|json|py)`?",
     "正文直出工程文件相对路径，应改为叙述性表述"),
    ("敏感串", "block",
     r"atomdemo\.[a-z0-9.-]+|([\w-]+\.){2,}[\w-]+\.(?:local|internal|corp)",
     "疑似未脱敏的内部域名/主机名"),
    ("自证腔", "warn",
     r"不拿关键词当成绩|文章里也不会|本例(?:没有|未)|每一条我都不写|我只写状态",
     "向读者自证「没造假」，是评审视角的行文残留"),
    ("写作元信息", "warn",
     r"本文工程设计|征文要求用|按要点评分|资料与附件|如上(?:表|述)所示，?本文",
     "暴露写作/评审过程的元信息"),
    ("宿主术语", "warn",
     r"支持 Skill 的宿主|运行宿主|宿主机|宿主环境",
     "用内部术语指代读者不认识的宿主，应落到具体工具名"),
    ("过程口吻", "warn",
     r"本次实测|本次验证|本轮(?:实测|检查)|经实测(?:发现|验证)",
     "以「过程汇报」口吻叙述，正文宜改成结果陈述"),
]

_TREE_GLYPHS = re.compile(r"^[\s│├└─|+`\\-]+")


def scan_traces(text: str, allow: tuple[str, ...] = ()) -> list[dict]:
    """扫描加工痕迹。allow 中的字面串（命中的整段 match）会被放行。"""
    hits: list[dict] = []
    for category, level, pattern, message in TRACE_RULES:
        for m in re.finditer(pattern, text):
            token = m.group(0)
            if token in allow:
                continue
            s = max(0, m.start() - 24)
            hits.append({
                "category": category,
                "level": level,
                "match": token,
                "context": text[s:m.end() + 24].replace("\n", " "),
                "message": message,
            })
    return hits


def analyze_text(text: str, max_chars: int | None = None, allow: tuple[str, ...] = ()) -> dict:
    chars = count_chars(text)
    traces = scan_traces(text, allow)
    blocks = [h for h in traces if h["level"] == "block"]
    warns = [h for h in traces if h["level"] == "warn"]
    checks = [{
        "id": "T1",
        "item": f"字数（含空格）≤ {max_chars}" if max_chars else "字数统计（含空格）",
        "status": (PASS if chars["with_space"] <= max_chars else FAIL) if max_chars else NA,
        "detail": f"含空格 {chars['with_space']}，不含空格 {chars['no_space']}，中文 {chars['cjk']}"
                  + (f"，余量 {max_chars - chars['with_space']}" if max_chars else ""),
    }, {
        "id": "T2",
        "item": "加工痕迹（block 级）为 0",
        "status": PASS if not blocks else FAIL,
        "detail": f"命中 {len(blocks)} 处" if blocks else "未命中",
    }, {
        "id": "T3",
        "item": "加工痕迹（warn 级）提示",
        "status": PASS if not warns else WARN,
        "detail": f"命中 {len(warns)} 处，按文体斟酌" if warns else "未命中",
    }]
    return {"chars": chars, "traces": traces, "checks": checks}


# ---------------------------------------------------------------- HTML 结构

_SRC = re.compile(r"<img\b[^>]*?\bsrc=\"([^\"]*)\"", re.I)


def check_html(html_text: str, min_images: int | None = None,
               max_images: int | None = None) -> dict:
    srcs = _SRC.findall(html_text)
    relative = [s for s in srcs if s.startswith(("img/", "./img/"))]
    embedded = [s for s in srcs if s.startswith("data:")]
    external = [s for s in srcs if s not in relative and s not in embedded]
    r = {
        "img_count": len(srcs),
        "relative_imgs": len(relative),
        "embedded_imgs": len(embedded),
        "external_imgs": external,
        "tables": len(re.findall(r"<table\b", html_text, re.I)),
        "figcaptions": len(re.findall(r"<figcaption\b", html_text, re.I)),
        "figures": len(re.findall(r"<figure\b", html_text, re.I)),
        "h1": len(re.findall(r"<h1\b", html_text, re.I)),
        "h2": len(re.findall(r"<h2\b", html_text, re.I)),
        "inline_styles": len(re.findall(r"style=\"", html_text)),
        "style_blocks": len(re.findall(r"<style\b", html_text, re.I)),
        "div_open": len(re.findall(r"<div\b", html_text, re.I)),
        "div_close": len(re.findall(r"</div>", html_text, re.I)),
        "p_open": len(re.findall(r"<p\b", html_text, re.I)),
        "p_close": len(re.findall(r"</p>", html_text, re.I)),
        "has_copy_button": ("复制" in html_text) and ("<script" in html_text.lower()),
    }
    checks = [
        {"id": "H1", "item": "无 <table>（编辑器易错乱样式）",
         "status": PASS if r["tables"] == 0 else FAIL, "detail": f"<table> {r['tables']} 处"},
        {"id": "H2", "item": "无 <figcaption>（截图备注已去掉）",
         "status": PASS if r["figcaptions"] == 0 else FAIL, "detail": f"<figcaption> {r['figcaptions']} 处"},
        {"id": "H3", "item": "恰有 1 个 <h1>",
         "status": PASS if r["h1"] == 1 else FAIL, "detail": f"<h1> {r['h1']} 个，<h2> {r['h2']} 个"},
        {"id": "H4", "item": "div / p 标签配平",
         "status": PASS if r["div_open"] == r["div_close"] and r["p_open"] == r["p_close"] else FAIL,
         "detail": f"div {r['div_open']}/{r['div_close']}，p {r['p_open']}/{r['p_close']}"},
        {"id": "H5", "item": "图片全部为相对路径或内嵌",
         "status": PASS if not external else FAIL,
         "detail": f"相对 {r['relative_imgs']}，内嵌 {r['embedded_imgs']}，外链 {len(external)}"
                   + (f"：{external[:3]}" if external else "")},
    ]
    if min_images is not None:
        checks.append({
            "id": "H6", "item": f"配图 ≥ {min_images} 张",
            "status": PASS if r["img_count"] >= min_images else FAIL,
            "detail": f"当前 {r['img_count']} 张",
        })
    if max_images is not None:
        checks.append({
            "id": "H7", "item": f"配图 ≤ {max_images} 张",
            "status": PASS if r["img_count"] <= max_images else FAIL,
            "detail": f"当前 {r['img_count']} 张",
        })
    return {"report": r, "checks": checks}


# ------------------------------------------------------------------ 征文规则

DIMENSIONS = {
    "红线维度": ("功能性", "安全性"),
    "核心维度": ("可靠性", "成本效益"),
    "评价维度": ("用户体验", "性能效率"),
}
CLOUDQ_TAGS = ("#AIOps最佳实践", "#CloudQ共创征文", "#Skill资产共创")
CONTEST = {
    "cloudq": {
        "name": "AIOps 最佳实践 · CloudQ 共创计划征文",
        "where": "同盟交流圈 https://cloud.tencent.com/developer/zone/tm",
        "deadline": "截稿 10/25；评选 10/25–11/15；公布 11/20",
     },
    "workbuddy": {
        "name": "WorkBuddy 频道首届征文",
        "where": "「实用文章」板块",
        "deadline": "投稿 10/12–11/02；评审 11/02–11/08；公布 11/09–11/15",
    },
}


def parse_frontmatter(text: str) -> dict | None:
    """解析 YAML frontmatter 的顶层标量字段（不引第三方 yaml）。"""
    m = re.search(r"^---\s*\n(.*?)\n---\s*$", text, re.M | re.S)
    if not m:
        return None
    body = m.group(1)
    data: dict[str, str] = {}
    key = None
    for line in body.splitlines():
        if re.match(r"^\s+\S", line) and key:            # 续行，拼到上一个字段
            data[key] += " " + line.strip()
            continue
        km = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not km:
            continue
        key, val = km.group(1), km.group(2).strip()
        data[key] = re.sub(r"\s+", " ", val)
    return data


def _tag_tokens(text: str) -> tuple[list[str], list[str]]:
    """返回（标签行原文, 标签 token 列表）。

    规则是「每篇仅一个标签」，所以按 **token 数**判定，不按行数——
    一行里写三个标签同样是违规。
    """
    lines, tokens = [], []
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^>\s*#", s):
            lines.append(s)
            tokens += re.findall(r"#[\w\u4e00-\u9fff]+", s)
    return lines, tokens


def check_rules(doc_text: str, track: str = "none", *, skill_md_text: str | None = None,
                html_report: dict | None = None, max_chars: int | None = None,
                chars: int | None = None) -> dict:
    """征文硬性要求符合性检查。判不了的项标 NA 并写明原因，不猜。"""
    ck: list[dict] = []

    def add(i, item, ok, detail, na=False):
        ck.append({"id": i, "item": item, "status": NA if na else (PASS if ok else FAIL), "detail": detail})

    first_line = next((l for l in doc_text.splitlines() if l.strip()), "")
    if track == "workbuddy":
        add("W1", "标题以「【征文】」开头（标题自拟）", first_line.startswith("【征文】"),
            f"H1：{first_line[:46]}")
        add("W2", "正文与 WorkBuddy 强相关", doc_text.count("WorkBuddy") >= 2,
            f"提及 WorkBuddy {doc_text.count('WorkBuddy')} 次")
        add("W3", "配图 ≥ 3 张", bool(html_report) and html_report["img_count"] >= 3,
            f"HTML 配图 {html_report['img_count']} 张" if html_report else "未提供 HTML，无法判定",
            na=not html_report)
        add("W4", "发布板块 =「实用文章」", False, "平台侧动作，稿件无法自证", na=True)
    elif track == "cloudq":
        missing = [d for tier, ds in DIMENSIONS.items() for d in ds if d not in doc_text]
        add("C1", "六维度提及齐全（功能性/安全性/可靠性/成本效益/用户体验/性能效率）",
            not missing, "缺：" + "、".join(missing) if missing else "六项齐")
        tiers = [t for t in DIMENSIONS if t in doc_text]
        add("C2", "三层维度口径齐全（红线/核心/评价）", len(tiers) == 3,
            "齐" if len(tiers) == 3 else "缺：" + "、".join(t for t in DIMENSIONS if t not in tiers))
        tags, tokens = _tag_tokens(doc_text)
        add("C3", "赛道标签「每篇仅一个」（正文标签 token ≤ 1）", len(tokens) <= 1,
            f"标签 {len(tokens)} 个 / {len(tags)} 行：{tokens}" if tokens else "正文无标签行（走页面字段，合规）")
        bad = [t for t in tokens if t not in CLOUDQ_TAGS]
        add("C4", "标签落在官方候选集合内", not bad, "、".join(bad) if bad else "无越界标签")
        add("C5", "发布位置 = 同盟交流圈 zone/tm", False,
            f"{CONTEST['cloudq']['where']}（平台侧动作）", na=True)
    else:
        add("R0", "征文赛道", False, "未指定 --track，跳过赛道专属项", na=True)

    if skill_md_text is not None:
        fm = parse_frontmatter(skill_md_text) or {}
        fields = sorted(fm.keys())
        add("S1", "SKILL.md 元数据仅 name + description", fields == ["description", "name"],
            f"实际字段：{fields or '未解析到 frontmatter'}")
        need = {"工具": "工具", "步骤": "执行步骤", "边界": "安全边界", "铁律": "铁律"}
        miss = [k for k, kw in need.items() if kw not in skill_md_text]
        add("S2", "SKILL.md 正文含工具 / 步骤 / 边界 / 铁律", not miss,
            "缺：" + "、".join(miss) if miss else "四项齐")

    if max_chars is not None and chars is not None:
        add("N1", f"字数（含空格）≤ {max_chars}", chars <= max_chars,
            f"当前 {chars}，余量 {max_chars - chars}")

    cfg = CONTEST.get(track)
    if cfg:
        add("P1", "截稿/发布时间线自行确认", False,
            f"{cfg['name']}：{cfg['deadline']}", na=True)
    return {"track": track, "checks": ck}


# ------------------------------------------------------------------ 一致性

def parse_tree_block(doc_text: str) -> dict | None:
    """从正文里抓「ASCII 目录树」代码块，返回文件名/目录名集合。

    注意：只比对 basename 集合，不还原层级路径（树里只写了名字）。
    """
    for block in _FENCE.findall(doc_text):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2 or not any(("├──" in l or "└──" in l) for l in lines):
            continue
        files, dirs = set(), set()
        for line in lines[1:]:
            name = _TREE_GLYPHS.sub("", line).strip()
            if not name:
                continue
            name = re.split(r"\s+#", name)[0].strip()      # 去掉行尾注释（├── a.py  # 说明）
            if not name:
                continue
            name = name.split()[0]                          # 去掉对齐空白，只取文件名本身
            if name.endswith("/"):
                dirs.add(name.rstrip("/"))
            else:
                files.add(name.split("/")[-1].strip())
        if files or dirs:
            return {"root": lines[0].strip(), "files": sorted(files), "dirs": sorted(dirs)}
    return None


def compare_tree(doc_text: str, skill_dir: Path) -> dict:
    tree = parse_tree_block(doc_text)
    if not tree:
        return {"status": NA, "reason": "正文未内嵌目录树代码块"}
    actual_files = sorted(p.name for p in skill_dir.rglob("*")
                          if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    actual_dirs = sorted(p.name for p in skill_dir.rglob("*") if p.is_dir() and "__pycache__" not in p.parts)
    doc_files, doc_dirs = set(tree["files"]), set(tree["dirs"])
    missing = sorted(set(actual_files) - doc_files)
    extra = sorted(doc_files - set(actual_files))
    missing_dirs = sorted(set(actual_dirs) - doc_dirs)
    return {
        "status": PASS if not (missing or extra) else FAIL,
        "root": tree["root"],
        "doc_files": len(doc_files), "actual_files": len(actual_files),
        "missing_in_doc": missing, "extra_in_doc": extra,
        "missing_dirs": missing_dirs,
    }


def compare_description(doc_text: str, skill_md_text: str) -> dict:
    fm_doc = None
    for block in _FENCE.findall(doc_text):
        if "name:" in block and "description:" in block:
            fm_doc = parse_frontmatter("---\n" + block.strip().strip("-").strip() + "\n---")
            if fm_doc:
                break
    if not fm_doc:
        return {"status": NA, "reason": "正文未内嵌 SKILL.md 元数据"}
    fm_skill = parse_frontmatter(skill_md_text) or {}
    same = fm_doc.get("description", "") == fm_skill.get("description", "")
    return {
        "status": PASS if same else FAIL,
        "doc_description": fm_doc.get("description", ""),
        "skill_description": fm_skill.get("description", ""),
    }


_CLAIMED = (r"(\d+)\s*(?:项|个)(?:离线)?(?:单测|测试)",
            r"(?:单测|测试)\s*(\d+)\s*(?:项|个)",
            r"Ran\s+(\d+)\s+tests")


def extract_claimed_test_count(doc_text: str) -> int | None:
    for pat in _CLAIMED:
        m = re.search(pat, doc_text)
        if m:
            return int(next(g for g in m.groups() if g))
    return None


def parse_unittest_count(stderr: str) -> int | None:
    m = re.search(r"Ran\s+(\d+)\s+tests", stderr)
    return int(m.group(1)) if m else None


def run_unit_tests(python_exe: str, skill_dir: Path) -> dict:
    proc = subprocess.run([python_exe, "-m", "unittest", "discover", "-s", "tests"],
                          cwd=str(skill_dir), capture_output=True, text=True)
    count = parse_unittest_count(proc.stderr or "")
    return {"returncode": proc.returncode, "count": count,
            "tail": (proc.stderr or "").strip().splitlines()[-1:] , "ok": proc.returncode == 0}


def check_consistency(doc_text: str, skill_dir: Path, *, python_exe: str | None = None,
                      run_tests: bool = False) -> dict:
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_text = skill_md_path.read_text(encoding="utf-8") if skill_md_path.exists() else ""
    checks: list[dict] = []

    t = compare_tree(doc_text, skill_dir)
    checks.append({
        "id": "K1", "item": "正文目录树与实际文件一致",
        "status": t["status"] if t["status"] != NA else NA,
        "detail": (f"树内 {t['doc_files']} 个文件 / 实际 {t['actual_files']} 个"
                   + (f"；正文缺：{t['missing_in_doc']}" if t.get("missing_in_doc") else "")
                   + (f"；正文多：{t['extra_in_doc']}" if t.get("extra_in_doc") else "")
                   + (f"；目录差：{t['missing_dirs']}" if t.get("missing_dirs") else "")
                   ) if t["status"] != NA else t["reason"],
    })

    d = compare_description(doc_text, skill_md_text) if skill_md_text else {"status": NA, "reason": "未找到 SKILL.md"}
    checks.append({
        "id": "K2", "item": "正文内嵌元数据与 SKILL.md 逐字一致",
        "status": d["status"],
        "detail": "一致" if d["status"] == PASS else (
            d.get("reason") or f"正文：{d.get('doc_description')} / 实际：{d.get('skill_description')}"),
    })

    claimed = extract_claimed_test_count(doc_text)
    if run_tests and python_exe and (skill_dir / "tests").exists():
        res = run_unit_tests(python_exe, skill_dir)
        actual = res["count"]
        checks.append({
            "id": "K3", "item": "正文所述单测数与实跑一致",
            "status": PASS if (claimed is not None and claimed == actual and res["ok"]) else FAIL,
            "detail": f"正文 {claimed} 项 / 实跑 {actual} 项 / 退出码 {res['returncode']}",
        })
    else:
        checks.append({
            "id": "K3", "item": "正文所述单测数与实跑一致",
            "status": NA, "detail": f"正文声明 {claimed} 项；未加 --run-tests，未实跑",
        })
    return {"checks": checks}


# ---------------------------------------------------------------------- CLI

def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _print(checks: list[dict], title: str) -> int:
    width = max((len(c["item"]) for c in checks), default=10)
    print(f"\n== {title} ==")
    for c in checks:
        print(f"  [{c['status']:4}] {c['item']:<{width}}  {c['detail']}")
    fails = [c for c in checks if c["status"] == FAIL]
    print(f"  → {len(checks)} 项检查，FAIL {len(fails)}，WARN "
          f"{sum(1 for c in checks if c['status'] == WARN)}，NA {sum(1 for c in checks if c['status'] == NA)}")
    return len(fails)


def _dump(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _count_fails(checks: list[dict]) -> int:
    return sum(1 for c in checks if c["status"] == FAIL)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zwcheck", description="征文/投稿稿件发布前检查")
    ap.add_argument("mode", choices=["text", "html", "rules", "consist", "all"])
    ap.add_argument("doc", help="稿件文件（.html 或 .md）")
    ap.add_argument("--html", dest="html_path", help="发布版 HTML（校验结构/配图）")
    ap.add_argument("--skill-dir", help="技能源码目录（一致性比对）")
    ap.add_argument("--skill-md", help="外部 SKILL.md（规则校验用）")
    ap.add_argument("--track", choices=["cloudq", "workbuddy", "none"], default="none")
    ap.add_argument("--max-chars", type=int, default=None)
    ap.add_argument("--min-images", type=int, default=None)
    ap.add_argument("--max-images", type=int, default=None)
    ap.add_argument("--allow", action="append", default=[], help="放行的痕迹命中串，可重复")
    ap.add_argument("--from", dest="from_marker",
                    help="只统计从该标记开始的区域（如 '<h1'），用于排除工具栏等页面外壳")
    ap.add_argument("--to", dest="to_marker", help="只统计到该标记为止（如 '<script>'）")
    ap.add_argument("--run-tests", action="store_true", help="实跑技能单测并比对正文声明")
    ap.add_argument("--python", default=sys.executable, help="跑单测用的解释器")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    doc_path = Path(args.doc)
    if not doc_path.exists():
        print(f"文件不存在：{doc_path}", file=sys.stderr)
        return 2
    raw = _load(doc_path)
    is_html = doc_path.suffix.lower() in (".html", ".htm")
    visible = (html_visible(raw, args.from_marker, args.to_marker) if is_html
               else md_visible(raw))
    out: dict = {"doc": str(doc_path), "is_html": is_html,
                 "count_region": [args.from_marker or "文档开头", args.to_marker or "文档结尾"]}
    fails = 0
    chars_ws = count_chars(visible)["with_space"]

    if args.mode in ("text", "all"):
        t = analyze_text(visible, args.max_chars, tuple(args.allow))
        out["text"] = t
        fails += _count_fails(t["checks"])
        if not args.json:
            _print(t["checks"], "字数与加工痕迹")
            if t["traces"]:
                print("  -- 痕迹明细 --")
                for h in t["traces"]:
                    print(f"     [{h['level']}] {h['category']}｜{h['match']}｜…{h['context']}…")

    if args.mode in ("html", "all"):
        target = Path(args.html_path) if args.html_path else (doc_path if is_html else None)
        if target is None:
            print("\n== HTML 结构 ==\n  [NA  ] 未提供 --html，跳过")
            out["html"] = {"skipped": "未提供 --html"}
        else:
            hr = check_html(_load(target), args.min_images, args.max_images)
            out["html"] = hr
            fails += _count_fails(hr["checks"])
            if not args.json:
                _print(hr["checks"], f"HTML 结构（{target.name}）")

    if args.mode in ("rules", "all"):
        html_report = out.get("html", {}).get("report") if isinstance(out.get("html"), dict) else None
        smd = _load(Path(args.skill_md)) if args.skill_md else (
            _load(Path(args.skill_dir) / "SKILL.md")
            if args.skill_dir and (Path(args.skill_dir) / "SKILL.md").exists() else None)
        rr = check_rules(visible, args.track, skill_md_text=smd, html_report=html_report,
                         max_chars=args.max_chars,
                         chars=chars_ws if args.max_chars is not None else None)
        out["rules"] = rr
        fails += _count_fails(rr["checks"])
        if not args.json:
            _print(rr["checks"], f"征文规则（track={args.track}）")

    if args.mode in ("consist", "all"):
        if not args.skill_dir:
            print("\n== 一致性 ==\n  [NA  ] 未提供 --skill-dir，跳过")
            out["consist"] = {"skipped": "未提供 --skill-dir"}
        else:
            # 一致性比对必须用**原始文本**：目录树与 SKILL.md 元数据都在围栏代码块内，
            # 用去掉代码块的可见正文会直接漏检。
            cr = check_consistency(raw, Path(args.skill_dir),
                                   python_exe=args.python, run_tests=args.run_tests)
            out["consist"] = cr
            fails += _count_fails(cr["checks"])
            if not args.json:
                _print(cr["checks"], "稿件 ↔ 技能源码一致性")

    if args.json:
        _dump(out)
    print(f"\n结论：FAIL {fails} 项" + ("，可以发布" if fails == 0 else "，需先修正"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
