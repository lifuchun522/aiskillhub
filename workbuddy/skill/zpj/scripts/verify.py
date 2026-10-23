# -*- coding: utf-8 -*-
"""zpj · 端到端自检（Playwright）

对构建产物做**程序化**校验，不靠人眼看截图：

  [0] 产物文本：模板残留（{{TOKEN}} / <!--SEC:…--> / <!--NAV:…--> / <!--HR--> / <!--N-->）必须为 0
  [1] 运行时：0 个 JS 错误
  [2] 资源：0 张破图；图片数 > 0
  [3] 结构：导航 / 名片 / 数据条 / 自述 / 支柱 / 项目卡 / 技术栈 / 时间线 / 证书 / 二维码
      + 导航无死链 + 收尾整洁（无空壳页脚、无孤立分隔线、body 无游离区块）
      + 区块位置（--last-section）+ 章节序号与 DOM 顺序连续
      + 首屏主体：名片占内容宽度比例达标
  [4] 内容断言：--must 必须出现、--absent 必须不出现
  [5] 数据映射：项目主图资源键顺序 == --expect；项目周期时间降序；编号连续
  [6] 交互：灯箱打开 / ESC 关闭、名片可放大、二维码链接协议正确
  [7] 多端渲染：桌面 Chrome / 平板 / iPhone 微信 / Android 微信 / iPhone 企业微信
      五个 profile 逐一校验无横向溢出、关键区块未溢出、触摸端正文字号达标、名片在首屏

用法：
    python verify.py <index.html> [--expect fig1,fig2,…] [--shots <目录>]
                     [--must "必须出现的词"] [--absent "必须消失的旧文案"]
                     [--last-section projects] [--skip-multi]

退出码非 0 表示有 FAIL，可直接用作门禁。
"""
import argparse
import os
import re
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("需要 playwright：pip install playwright && python -m playwright install chromium")


# --------------------------------------------------------------- 多端 profile
UA_WECHAT_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
                 "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003132) "
                 "NetType/WIFI Language/zh_CN")
UA_WECHAT_ANDROID = ("Mozilla/5.0 (Linux; Android 13; PGT-AN00 Build/TP1A.220905.001; wv) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.0.0 "
                     "Mobile Safari/537.36 XWEB/1160065 MMWEBSDK/20231202 MMWEBID/1234 "
                     "MicroMessenger/8.0.47.2560(0x28002F35) WeChat/arm64 Weixin "
                     "NetType/WIFI Language/zh_CN ABI/arm64")
UA_WECOM_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003132) "
                "NetType/WIFI Language/zh_CN wxwork/4.1.26 MicroMessenger/7.0.1")
UA_CHROME_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

PROFILES = [
    ("桌面 Chrome 1440", 1440, 900, UA_CHROME_DESKTOP, False),
    ("平板 820", 820, 1100, UA_WECHAT_IOS, True),
    ("iPhone 微信 390", 390, 844, UA_WECHAT_IOS, True),
    ("Android 微信 360", 360, 780, UA_WECHAT_ANDROID, True),
    ("iPhone 企业微信 320", 320, 568, UA_WECOM_IOS, True),
]

# (标签, 子元素选择器, 容器选择器)。第三个非空 = 可选区块：容器里一个子项都没有时，
# 这块本来就不该出现（没配证书 / 二维码），跳过而非判缺。
KEY_BLOCKS = [
    ("导航", ".nav", None), ("名片", ".hero-card img", None), ("数据指标", ".metrics div", None),
    ("自述", ".intro", None), ("能力支柱", ".pillar", None), ("项目卡", ".p-card", None),
    ("技术栈", "#stack .st", None), ("时间线", ".tl-item", None),
    ("证书", ".cert", ".certs"), ("二维码", ".qr", ".qrs"),
]

# 这两个计数允许为 0：没配证书 / 二维码时，对应网格整块不渲染
OPTIONAL_STATS = ("certs", "qrs")

RESIDUE = [
    ("模板 token", re.compile(r"\{\{[A-Z0-9_]+\}\}")),
    ("区块标记", re.compile(r"<!--(?:SEC|NAV):[a-z_]+-->")),
    ("分隔线标记", re.compile(r"<!--HR-->")),
    ("序号标记", re.compile(r"<!--N-->")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--expect", default="", help="期望的项目主图资源键，逗号分隔（顺序敏感；无主图的项目不占位）")
    ap.add_argument("--must", default="", help="页面文本里必须出现的关键词，逗号分隔")
    ap.add_argument("--absent", default="", help="页面文本里必须不出现的关键词，逗号分隔")
    ap.add_argument("--last-section", default="", help="要求排在最末的区块 id")
    ap.add_argument("--shots", default="", help="截图输出目录（可选）")
    ap.add_argument("--viewport", default="1440x1000")
    ap.add_argument("--skip-multi", action="store_true", help="跳过五端渲染（快速迭代用）")
    args = ap.parse_args()

    url = "file:///" + os.path.abspath(args.html).replace("\\", "/")
    W, H = (int(x) for x in args.viewport.lower().split("x"))
    fails = []

    def check(name, ok, detail=""):
        print("  %-30s %s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    print("[0] 产物文本")
    raw = open(args.html, encoding="utf-8", errors="replace").read()
    for label, rex in RESIDUE:
        hit = rex.findall(raw)
        check("无残留 " + label, not hit, str(sorted(set(hit))[:4]))

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url, wait_until="load")
        pg.wait_for_timeout(1500)

        print("[1] 运行时")
        check("JS 错误", not errs, str(errs[:3]))

        print("[2] 资源")
        broken = pg.evaluate("""()=>Array.from(document.images)
            .filter(i => i.getAttribute('data-asset') && (!i.complete || i.naturalWidth === 0))
            .map(i => i.getAttribute('data-asset'))""")
        check("破图", not broken, str(broken))
        n_img = pg.evaluate("document.images.length")
        check("图片总数>0", n_img > 0, "imgs=%d" % n_img)

        print("[3] 结构")
        stats = pg.evaluate("""()=>({
            pillars:document.querySelectorAll('.pillar').length,
            herocard:document.querySelectorAll('.hero-card img').length,
            metrics:document.querySelectorAll('.metrics div').length,
            cards:  document.querySelectorAll('.p-card').length,
            zoom:   document.querySelectorAll('[data-zoom]').length,
            certs:  document.querySelectorAll('.cert').length,
            qrs:    document.querySelectorAll('.qr').length,
            tl:     document.querySelectorAll('.tl-item').length,
            stack:  document.querySelectorAll('#stack .st').length,
            navlinks:document.querySelectorAll('.nav ul a').length,
            anchors:document.querySelectorAll('main section[id], header [id]').length
        })""")
        for k, v in stats.items():
            if k in OPTIONAL_STATS and not v:
                print("  %-34s SKIP 0（未配，区块整块不出现）" % ("计数 " + k))
                continue
            check("计数 " + k, v > 0, str(v))
        # 数据条列数必须等于条数，否则末尾会留空列
        mc = pg.evaluate("""()=>{const m=document.querySelector('.metrics');
            return m ? [getComputedStyle(m).getPropertyValue('--mc').trim(),
                        m.children.length] : ['',''];}""")
        if mc[0]:
            check("数据条列数=条数", mc[0] == str(mc[1]), "--mc=%s 条数=%s" % tuple(mc))
        # 导航锚点必须能落到真实区块（删区块忘删导航 = 死链）
        dead = pg.evaluate("""()=>Array.from(document.querySelectorAll('.nav ul a'))
            .map(a=>a.getAttribute('href'))
            .filter(h=>!h || !document.querySelector(h))""")
        check("导航无死链", not dead, str(dead))
        # 收尾整洁：区块裁减后最容易留下「没有内容的页脚」「后面什么都没有的孤立分隔线」
        tail = pg.evaluate("""()=>{
            const ok = {MAIN:1,NAV:1,HEADER:1,SCRIPT:1,STYLE:1,LINK:1};
            const stray = Array.from(document.body.children)
                .filter(e => !ok[e.tagName] &&
                             !(e.tagName === 'DIV' && e.classList.contains('modal')))
                .map(e => e.tagName.toLowerCase() + '.' + String(e.className));
            const main = document.querySelector('main');
            const kids = main ? Array.from(main.children) : [];
            let last = kids.length ? kids[kids.length-1] : null;
            while (last && !last.getBoundingClientRect().height) last = last.previousElementSibling;
            return {stray, footers: document.querySelectorAll('footer').length,
                    orphanHr: !!(last && last.classList.contains('hr')),
                    lastCls: last ? String(last.className) : ''};
        }""")
        check("无遗留页脚", tail["footers"] == 0, "footer=%d" % tail["footers"])
        check("body 无游离区块", not tail["stray"], str(tail["stray"]))
        check("末尾非孤立分隔线", not tail["orphanHr"], "last=.%s" % tail["lastCls"])
        if args.last_section:
            seq = pg.evaluate("""()=>Array.from(document.querySelectorAll('main > section')).map(s=>({
                id: s.id,
                idx: (s.querySelector('.idx')||{}).textContent || '',
                h2:  (s.querySelector('h2')||{}).textContent || ''
            }))""")
            ids = [x["id"] for x in seq]
            check("末区块为 %s" % args.last_section,
                  bool(ids) and ids[-1] == args.last_section, "->".join(ids))
            nums = [x["idx"].split("/")[0].strip() for x in seq]
            check("章节序号按 DOM 顺序连续",
                  nums == ["%02d" % (i + 1) for i in range(len(nums))], str(nums))
            check("章节序号与标题对应", all(x["idx"] and x["h2"] for x in seq),
                  str([(x["idx"], x["h2"]) for x in seq]))
            for x in seq:
                print("      %-8s %-14s %s" % (x["idx"], x["id"], x["h2"]))

        print("[3c] 首屏主体（名片）")
        hero = pg.evaluate("""()=>{
            const n = document.querySelector('.hero-card img');
            const t = document.querySelector('.tagline');
            if (!n) return null;
            const r = n.getBoundingClientRect();
            return {ratio: r.width / document.documentElement.clientWidth,
                    w: Math.round(r.width), h: Math.round(r.height),
                    tagline: t ? t.innerText.trim().slice(0, 40) : ''};
        }""")
        if hero:
            check("名片占屏宽比", hero["ratio"] >= 0.55,
                  "%.0f%% (%dx%d)" % (hero["ratio"] * 100, hero["w"], hero["h"]))
        else:
            check("名片占屏宽比", False, "未渲染名片（card 未配或未给图）")

        print("[3d] 内容断言")
        txt = pg.evaluate("document.body.innerText")
        for kw in [x.strip() for x in args.must.split(",") if x.strip()]:
            check("必须出现 " + kw, kw in txt)
        for kw in [x.strip() for x in args.absent.split(",") if x.strip()]:
            check("必须消失 " + kw, kw not in txt)

        print("[3b] 自述与名片（可选区块）")
        opt = pg.evaluate("""()=>{
            const i = document.querySelector('.intro');
            const n = document.querySelector('.hero-card img');
            return {intro: !!i, introChars: i ? i.innerText.replace(/\\s+/g,'').length : 0,
                    namecard: !!n,
                    namecardW: n ? n.naturalWidth : 0,
                    namecardH: n ? n.naturalHeight : 0,
                    namecardInline: n ? (n.getAttribute('src') || '').startsWith('data:') : false};
        }""")
        if not opt["intro"] and not opt["namecard"]:
            print("      未配置自述 / 名片区块，跳过")
        if opt["intro"]:
            check("自述文本非空", opt["introChars"] > 60, "%d 字" % opt["introChars"])
        if opt["namecard"]:
            # 名片可能是内嵌 data URI，也可能是外置 img/ 相对路径 —— 判据统一为「解码出了像素」
            check("名片已加载", opt["namecardW"] > 200,
                  "%dx%d（%s）" % (opt["namecardW"], opt["namecardH"],
                                  "内嵌" if opt["namecardInline"] else "外置"))
            pg.click(".hero-card img")
            pg.wait_for_timeout(600)
            # 图可能是内嵌 data URI，也可能是外置 img/ 相对路径 —— 判据是「真的解码出了像素」
            check("名片可放大",
                  pg.evaluate("(()=>{const i=document.getElementById('mImg');"
                              "return !!i.getAttribute('src') && i.naturalWidth>0})()"))
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(250)

        print("[5] 数据映射")
        rows = pg.evaluate("""()=>Array.from(document.querySelectorAll('.p-card')).map(c=>{
            const f = c.querySelector('.figure[data-zoom]');
            return {
              no:    (c.querySelector('.p-title .no')||{}).textContent || '',
              title: c.querySelector('.p-title').innerText.replace(/\\s+/g,' ').trim(),
              meta:  (c.querySelector('.p-meta')||{}).textContent || '',
              fig:   f ? f.getAttribute('data-zoom') : '(无)'
            };
        })""")
        for r in rows:
            print("      %-46s %-24s -> %s" % (r["no"] + " " + r["title"][:42], r["meta"], r["fig"]))
        if args.expect:
            exp = [x.strip() for x in args.expect.split(",") if x.strip()]
            # 只比「有主图的项目」—— 没配 fig 的项目渲染成纯文字卡，不占位
            got = [r["fig"] for r in rows if r["fig"] != "(无)"]
            check("主图映射顺序", got == exp, "期望%s 实际%s" % (exp, got))
        periods = [r["meta"].split("—")[0].strip() for r in rows if "—" in r["meta"]]
        if periods:
            check("项目按时间降序", periods == sorted(periods, reverse=True), str(periods))
        nums = [r["no"].strip() for r in rows]
        check("项目编号连续", nums == ["%02d" % (i + 1) for i in range(len(rows))], str(nums))

        print("[6] 交互")
        if rows and rows[0]["fig"] != "(无)":
            pg.click("[data-zoom='%s']" % rows[0]["fig"])
            pg.wait_for_timeout(700)
            check("灯箱打开", pg.evaluate("document.getElementById('modal').classList.contains('open')"))
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
            check("灯箱 ESC 关闭",
                  not pg.evaluate("document.getElementById('modal').classList.contains('open')"))
        links = pg.evaluate("Array.from(document.querySelectorAll('a.qr')).map(a=>a.href)")
        check("二维码链接", all(l.startswith("http") for l in links) if links else True,
              "%d 个" % len(links))

        if args.skip_multi:
            if args.shots:
                os.makedirs(args.shots, exist_ok=True)
                pg.add_style_tag(content="html{scroll-behavior:auto !important}")
                pg.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
                pg.wait_for_timeout(400)
                pg.screenshot(path=os.path.join(args.shots, "desktop-full.png"), full_page=True)
                print("  截图 -> %s" % args.shots)
        else:
            print("[7] 多端渲染（手机 / 微信 / 企业 IM）")
            for name, vw, vh, ua, touch in PROFILES:
                ctx = b.new_context(viewport={"width": vw, "height": vh}, user_agent=ua,
                                    is_mobile=touch, has_touch=touch,
                                    device_scale_factor=2 if touch else 1)
                mp = ctx.new_page()
                merrs = []
                mp.on("pageerror", lambda e, L=merrs: L.append(str(e)))
                mp.goto(url, wait_until="load")
                mp.wait_for_timeout(1100)
                tag = "%dpx" % vw
                sw, cw = mp.evaluate(
                    "[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                check("%s 无横向溢出" % tag, sw <= cw + 1 and not merrs,
                      "scrollW=%d clientW=%d%s" % (sw, cw, (" err=" + str(merrs[:1])) if merrs else ""))
                probe = mp.evaluate("""(blocks)=>{
                    const bad = [];
                    for (const [label, sel, box] of blocks){
                        const el = document.querySelector(sel);
                        if (!el){
                            // 可选区块：容器在但没有任何子项 —— 没配数据，本就该没有
                            if (box && !(document.querySelector(box + ' > *'))) continue;
                            bad.push(label + ':缺'); continue;
                        }
                        const r = el.getBoundingClientRect();
                        if (r.width > document.documentElement.clientWidth + 1)
                            bad.push(label + ':溢出' + Math.round(r.width));
                    }
                    return bad;
                }""", KEY_BLOCKS)
                check("%s 关键区块" % tag, not probe, str(probe))
                fs = mp.evaluate("parseFloat(getComputedStyle(document.body).fontSize)")
                if touch:
                    check("%s 正文字号" % tag, fs >= 12, "%.1fpx" % fs)
                nb = mp.evaluate("""()=>{
                    const n = document.querySelector('.hero-card img');
                    if (!n) return null;
                    const r = n.getBoundingClientRect();
                    return {top: r.top + window.scrollY, h: r.height, vh: window.innerHeight};
                }""")
                if nb:
                    check("%s 名片在首屏" % tag, nb["top"] < nb["vh"] * 1.6,
                          "top=%.0f vh=%d" % (nb["top"], nb["vh"]))
                if args.shots:
                    os.makedirs(args.shots, exist_ok=True)
                    mp.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
                    mp.wait_for_timeout(350)
                    mp.screenshot(path=os.path.join(args.shots, "viewport-%d-top.png" % vw))
                    mp.screenshot(path=os.path.join(args.shots, "viewport-%d-full.png" % vw),
                                  full_page=True)
                ctx.close()

            if args.shots:
                os.makedirs(args.shots, exist_ok=True)
                pg.add_style_tag(content="html{scroll-behavior:auto !important}")
                pg.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
                pg.wait_for_timeout(400)
                pg.screenshot(path=os.path.join(args.shots, "desktop-full.png"), full_page=True)
                print("  截图 -> %s" % args.shots)

        b.close()

    print("\n" + "=" * 60)
    if fails:
        print("FAIL: %d 项 -> %s" % (len(fails), fails))
        sys.exit(1)
    print("PASS: 全部检查通过")


if __name__ == "__main__":
    main()
