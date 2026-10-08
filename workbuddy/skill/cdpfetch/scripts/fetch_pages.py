# -*- coding: utf-8 -*-
"""
cdpfetch · 并发真实浏览器抓取器（Playwright 无头通道）

用真实 Chromium 渲染目标页，落盘「正文 / 链接 / DOM」三件套 + 存证清单。
适用于：反爬站点、动态渲染页、需要滚动触发懒加载的页面、批量来源取数。

用法:
    python fetch_pages.py --targets templates/targets.example.json --out ./raw
    python fetch_pages.py --targets t.json --out ./raw --concurrency 5 --scroll 3 --no-html
    python fetch_pages.py --targets t.json --out ./raw --headed      # 需要人工过验证码时

产出:
    <out>/<key>.txt         渲染后正文（document.body.innerText）
    <out>/<key>.links.txt   页面链接清单，格式 `可见文本 :: 绝对URL`
    <out>/<key>.html        渲染后 DOM 快照（--no-html 时跳过）
    <out>/_manifest.json    存证清单，见 references/evidence-schema.md

依赖:
    pip install playwright && playwright install chromium
"""
import argparse
import asyncio
import datetime
import hashlib
import json
import os
import sys

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

TEXT_JS = "() => document.body ? document.body.innerText : ''"

LINKS_JS = """() => {
  const out = [];
  for (const a of document.querySelectorAll('a[href]')) {
    const t = (a.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 60);
    if (t) out.push(t + ' :: ' + a.href);
  }
  return Array.from(new Set(out));
}"""


def now_iso():
    """带时区的本地时间戳，精确到秒。所有存证时间统一走这里，便于跨页比对。"""
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def load_targets(path):
    """目标清单：JSON 数组，元素为 {key, url} 或 [key, url] 两种写法都接受。"""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    targets, seen = [], set()
    for item in raw:
        if isinstance(item, dict):
            key, url = item.get("key"), item.get("url")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            key, url = item[0], item[1]
        else:
            raise SystemExit("[FATAL] 目标清单元素必须是 {key,url} 或 [key,url]：%r" % (item,))
        if not key or not url:
            raise SystemExit("[FATAL] 缺少 key 或 url：%r" % (item,))
        if key in seen:
            raise SystemExit("[FATAL] key 重复，会导致落盘互相覆盖：%s" % key)
        seen.add(key)
        targets.append((key, url))
    if not targets:
        raise SystemExit("[FATAL] 目标清单为空")
    return targets


async def grab(sem, browser, key, url, args, results):
    """抓单个目标。异常不抛出，转为一条 ok=false 的存证记录，不拖垮整批。"""
    async with sem:
        ctx = await browser.new_context(
            user_agent=args.user_agent,
            locale=args.locale,
            viewport={"width": args.width, "height": args.height},
        )
        page = await ctx.new_page()
        rec = {
            "key": key,
            "requested_url": url,
            "fetched_at": now_iso(),
            "channel": "playwright-headless" if not args.headed else "playwright-headed",
            "ok": False,
        }
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=args.timeout)
            rec["status"] = resp.status if resp else None
            # 基础等待：SPA 首屏水合、字体与接口回调都要时间，过短会抓到空壳
            await page.wait_for_timeout(args.settle)
            # 滚动触发懒加载：不滚到底，页面下半部分的图片/区块不会进 DOM
            for _ in range(args.scroll):
                await page.mouse.wheel(0, 2600)
                await page.wait_for_timeout(900)
            if args.scroll:
                await page.evaluate("() => window.scrollTo(0, 0)")
                await page.wait_for_timeout(300)

            rec["final_url"] = page.url
            rec["title"] = await page.title()
            text = await page.evaluate(TEXT_JS) or ""
            links = await page.evaluate(LINKS_JS) or []
            html = await page.content()

            rec["text_len"] = len(text)
            rec["link_count"] = len(links)
            rec["text_sha256"] = sha256(text)
            rec["html_sha256"] = sha256(html)
            rec["ok"] = True

            with open(os.path.join(args.out, key + ".txt"), "w", encoding="utf-8") as f:
                f.write(text)
            with open(os.path.join(args.out, key + ".links.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(links))
            if not args.no_html:
                with open(os.path.join(args.out, key + ".html"), "w", encoding="utf-8") as f:
                    f.write(html)
        except Exception as e:  # noqa: BLE001 —— 抓取失败必须是数据，不是崩溃
            rec["error"] = "%s: %s" % (type(e).__name__, e)
        finally:
            await ctx.close()

        results.append(rec)
        flag = "OK " if rec["ok"] else "ERR"
        print("[%s] %-24s %-5s %s" % (
            flag, key, rec.get("status"), rec.get("text_len", rec.get("error", ""))
        ))


async def run(args):
    from playwright.async_api import async_playwright  # 延迟导入，--help 不需要装依赖

    targets = load_targets(args.targets)
    os.makedirs(args.out, exist_ok=True)
    results = []
    sem = asyncio.Semaphore(args.concurrency)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not args.headed,
            args=["--disable-blink-features=AutomationControlled"],
        )
        await asyncio.gather(*[grab(sem, browser, k, u, args, results) for k, u in targets])
        await browser.close()

    results.sort(key=lambda r: r["key"])
    manifest = os.path.join(args.out, "_manifest.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["ok"])
    print("\n[MANIFEST] %s" % manifest)
    print("[SUMMARY ] %d/%d 成功，抓取窗口 %s → %s" % (
        ok, len(results),
        min(r["fetched_at"] for r in results),
        max(r["fetched_at"] for r in results),
    ))
    if ok != len(results):
        print("[WARN    ] 存在失败项，逐条见 _manifest.json 的 error 字段")
        return 1
    return 0


def build_parser():
    ap = argparse.ArgumentParser(description="cdpfetch · 并发真实浏览器抓取器（Playwright 通道）")
    ap.add_argument("--targets", required=True, help="目标清单 JSON，元素形如 {key,url}")
    ap.add_argument("--out", default="./raw", help="落盘目录（默认 ./raw）")
    ap.add_argument("--concurrency", type=int, default=5, help="并发上下文数，默认 5")
    ap.add_argument("--timeout", type=int, default=60000, help="单页导航超时（毫秒），默认 60000")
    ap.add_argument("--settle", type=int, default=3500, help="导航后基础等待（毫秒），默认 3500")
    ap.add_argument("--scroll", type=int, default=3, help="懒加载滚动次数，0 表示不滚动")
    ap.add_argument("--no-html", action="store_true", help="不落盘 DOM 快照（省磁盘）")
    ap.add_argument("--headed", action="store_true", help="显示浏览器窗口，便于人工过验证码")
    ap.add_argument("--locale", default="zh-CN", help="页面 locale，默认 zh-CN")
    ap.add_argument("--user-agent", default=DEFAULT_UA, help="覆盖 UA")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1000)
    return ap


def main():
    args = build_parser().parse_args()
    try:
        sys.exit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
