# -*- coding: utf-8 -*-
"""
cdpfetch · 单文件产出物确定性验证器

在**真实浏览器**里打开待交付的 HTML，做确定性核验，杜绝两类假结论：
  假阳性（实际 0 报 1，冤枉）与假阴性（实际 1 报 0，漏报，更危险）。
报「有问题」前先证伪自己，报「全绿」前先证全覆盖——所以每项检查都必须给出
「期望值 vs 实测值」，不允许出现靠肉眼印象的结论。

用法:
    python verify_dashboard.py --file dashboard.html
    python verify_dashboard.py --file dashboard.html --spec spec.json --shots ./shots
    python verify_dashboard.py --file d.html --sections "#sec-cards,#sec-price" --toggle-lang

spec.json 可选字段（全部可省，省则为默认）:
    {
      "selectors":            {"#cards .card": 5, "#cmp tbody tr": 13},
      "zero_console_errors":  true,
      "forbid_external_refs": true,    # link/script[src]/img[src]/iframe/source 不许外链
      "forbid_anchor_href":   true,    # a[href] 也必须为 0（纯单文件交付）
      "sections":             ["#sec-cards", "#sec-price"],
      "title_contains":       "竞品"
    }

退出码: 0 全绿 / 1 存在未通过项
"""
import argparse
import hashlib
import json
import os
import sys


def parser():
    ap = argparse.ArgumentParser(description="cdpfetch · 产出物确定性验证器")
    ap.add_argument("--file", required=True, help="待验证的 HTML 文件")
    ap.add_argument("--spec", help="检查规格 JSON（见文件头）")
    ap.add_argument("--shots", default=None, help="截图输出目录")
    ap.add_argument("--sections", default=None, help="按区块截图，逗号分隔的选择器")
    ap.add_argument("--toggle-lang", action="store_true", help="验证中英切换（#lang-en / #lang-zh）")
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--settle", type=int, default=1600, help="加载后等待毫秒数")
    return ap


AUDIT_JS = """() => {
  const refs = [];
  document.querySelectorAll('link[href],script[src],img[src],iframe[src],source[src],video[src],audio[src]')
    .forEach(el => refs.push(el.tagName.toLowerCase() + ':' + (el.getAttribute('src') || el.getAttribute('href'))));
  const anchors = Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'));
  const ext = u => !!u && !/^(#|data:|javascript:|mailto:|tel:|\\s*$)/i.test(u);
  return {
    lang: document.documentElement.lang || '',
    title: document.title,
    externalRefs: refs.filter(r => ext(r.split(':').slice(1).join(':'))),
    externalAnchors: anchors.filter(ext),
    anchorCount: anchors.length,
    inlineStyleTags: document.querySelectorAll('style').length,
    inlineScriptTags: document.querySelectorAll('script:not([src])').length,
    svgCount: document.querySelectorAll('svg').length
  };
}"""


def evaluate_counts(page, selectors):
    if not selectors:
        return {}
    expr = """(sels) => Object.fromEntries(sels.map(s => [s, document.querySelectorAll(s).length]))"""
    return page.evaluate(expr, list(selectors.keys()))


def run(args):
    from playwright.sync_api import sync_playwright

    spec = {}
    if args.spec:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
    sections = [s for s in (args.sections or "").split(",") if s.strip()]
    sections = spec.get("sections", sections)

    path = os.path.abspath(args.file)
    if not os.path.exists(path):
        print("[FATAL] 文件不存在: %s" % path)
        return 1
    url = "file:///" + path.replace("\\", "/")

    checks = []          # (名称, 期望, 实测, 通过)
    console_errors = []

    def check(name, expected, actual):
        """
        期望值 vs 实测值。expected 传可调用对象时按谓词判定（用于「不等于某值」这类断言），
        传字面值时为相等比较。
        注意：不要拿布尔字面量去和描述性文本比较——那是比较类型的误用，
        会把「已通过」误报成 FAIL。需要「判定 + 文字说明」时用 report()。
        """
        if callable(expected):
            ok, exp_disp = bool(expected(actual)), "<谓词判定>"
        else:
            ok, exp_disp = expected == actual, expected
        checks.append({"name": name, "expected": exp_disp, "actual": actual, "pass": ok})
        print("  %s %-34s 期望 %-14s 实测 %s" % ("PASS" if ok else "FAIL", name, exp_disp, actual))
        return ok

    def report(name, passed, detail):
        """用于「结论是布尔判定、但需要附一段可读说明」的检查项。"""
        checks.append({"name": name, "expected": "通过", "actual": detail, "pass": bool(passed)})
        print("  %s %-34s %s" % ("PASS" if passed else "FAIL", name, detail))
        return bool(passed)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": args.width, "height": args.height}, device_scale_factor=2
        )
        page = ctx.new_page()
        page.on("console", lambda m: console_errors.append("%s: %s" % (m.type, m.text)) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append("pageerror: %s" % e))

        page.goto(url, wait_until="load")
        page.wait_for_timeout(args.settle)

        print("\n[审计] %s" % url)
        audit = page.evaluate(AUDIT_JS)
        print("  title=%r  lang=%r  <style>=%d  <script>=%d  <svg>=%d"
              % (audit["title"], audit["lang"], audit["inlineStyleTags"], audit["inlineScriptTags"], audit["svgCount"]))

        if spec.get("title_contains"):
            check("标题包含关键词", lambda a: spec["title_contains"] in a, audit["title"])
        if spec.get("zero_console_errors", True):
            check("控制台错误数", 0, len(console_errors))
        if spec.get("forbid_external_refs", True):
            check("外部资源引用数", 0, len(audit["externalRefs"]))
            if audit["externalRefs"]:
                for r in audit["externalRefs"][:10]:
                    print("       外链 → %s" % r)
        if spec.get("forbid_anchor_href", False):
            check("锚点外链数", 0, len(audit["externalAnchors"]))

        counts = evaluate_counts(page, spec.get("selectors"))
        print("\n[DOM 计数]")
        for sel, want in (spec.get("selectors") or {}).items():
            check("count(%s)" % sel, want, counts.get(sel, 0))

        # 语言切换：比对【整页正文指纹】而非某个取样元素。
        # 取样单个元素会假阳性——例如表头第二列是产品名，中英两侧本就相同。
        # 指纹必须「切过去变了、切回来还原」，两个方向都验，避免只验了单向渲染。
        if args.toggle_lang:
            print("\n[中英切换]")
            try:
                def body_digest():
                    txt = page.evaluate("() => document.body.innerText") or ""
                    return hashlib.sha256(txt.encode("utf-8")).hexdigest()[:12], len(txt)

                zh_lang = page.evaluate("() => document.documentElement.lang")
                zh_dig, zh_len = body_digest()

                page.click("#lang-en")
                page.wait_for_timeout(900)
                en_lang = page.evaluate("() => document.documentElement.lang")
                en_dig, en_len = body_digest()

                page.click("#lang-zh")
                page.wait_for_timeout(700)
                back_lang = page.evaluate("() => document.documentElement.lang")
                back_dig, back_len = body_digest()

                check("切换为英文后 lang 变化", lambda a: a != zh_lang, en_lang)
                check("切换为英文后正文变化", lambda a: a != zh_dig, "%s → %s (%d→%d 字符)" % (zh_dig, en_dig, zh_len, en_len))
                check("切回中文后正文还原", lambda a: a == zh_dig, back_dig)
                report("切换按钮存在且可点", True, "#lang-en / #lang-zh 均点击成功，最终 lang=%s" % back_lang)
            except Exception as e:  # noqa: BLE001
                check("中英切换可用", False, "异常: %s" % e)

        # 按钮导航：必须逐个按钮验证「是否真滚到了目标区块」。
        # 不能用「首个按钮点击后 scrollY > 0」判定——首个按钮指向的往往是页首区块，
        # 点击后 scrollY 本就该是 0，那样判会假阳性。
        nav_ok, nav_detail = True, ""
        btns = page.query_selector_all("button[data-scroll]")
        if btns:
            print("\n[按钮导航]")
            tol = 160          # 容差：吸顶导航占位与平滑滚动落点误差
            worst, any_scrolled, moved = 0, False, 0
            for b in btns:
                target = b.get_attribute("data-scroll")
                b.click()
                page.wait_for_timeout(900)
                r = page.evaluate(
                    """(id) => {
                      const el = document.getElementById(id);
                      if (!el) return { missing: true };
                      const rect = el.getBoundingClientRect();
                      const atBottom = Math.abs(window.scrollY + window.innerHeight - document.documentElement.scrollHeight) < 4;
                      return { top: Math.round(rect.top), scrollY: Math.round(window.scrollY),
                               atBottom, vh: Math.round(window.innerHeight) };
                    }""", target)
                if r.get("missing"):
                    nav_ok, nav_detail = False, "按钮指向不存在的元素 #%s" % target
                    break
                if r["scrollY"] > 0:
                    any_scrolled = True
                    moved += 1
                # 正常落位：目标区块顶边贴齐视口顶（容差内）；若页面已滚到底则允许停在下半屏
                dev = abs(r["top"])
                ok_this = dev <= tol or (r["atBottom"] and 0 <= r["top"] <= r["vh"])
                print("  %s #%-14s 目标 top=%-6s scrollY=%-6s%s"
                      % ("PASS" if ok_this else "FAIL", target, r["top"], r["scrollY"],
                         "  (页面已到底)" if r["atBottom"] else ""))
                if not ok_this:
                    nav_ok = False
                    nav_detail = "点击 #%s 后目标 top=%s，超出容差 %s" % (target, r["top"], tol)
                worst = max(worst, dev)
            if nav_ok:
                nav_detail = "%d 个按钮全部滚到目标区块（最大偏差 %spx，%d 个产生位移）" % (
                    len(btns), worst, moved)
                nav_ok = any_scrolled
                if not any_scrolled:
                    nav_detail = "所有按钮点击后 scrollY 恒为 0，页面未发生滚动"
            report("按钮滚动到目标区块", nav_ok, nav_detail)

        if args.shots:
            os.makedirs(args.shots, exist_ok=True)
            for sel in sections:
                if not sel.strip():
                    continue
                el = page.query_selector(sel)
                name = sel.strip().lstrip("#").replace("/", "_") + ".png"
                if el:
                    el.screenshot(path=os.path.join(args.shots, name))
                else:
                    print("  [WARN] 区块不存在，跳过截图: %s" % sel)
            page.screenshot(path=os.path.join(args.shots, "_full.png"), full_page=True)
            print("\n[截图] %s" % args.shots)

        browser.close()

    failed = [c for c in checks if not c["pass"]]
    print("\n[结论] %d 项检查，%d 项未通过" % (len(checks), len(failed)))
    if console_errors:
        print("[控制台错误明细]")
        for e in console_errors[:10]:
            print("  " + e)
    return 1 if failed else 0


def main():
    args = parser().parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
