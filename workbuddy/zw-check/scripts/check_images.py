#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zw-check / check_images.py —— 用真实浏览器校验 HTML 配图是否真的能打开。

为什么需要它：静态检查只能说「引用了 img/xx.png」，说不了「这张图真的加载出来了」。
路径拼错、大小写不符、文件漏打包，静态检查全都看不出来，浏览器一看就现形。

依赖（可选用）：
    pip install playwright && python -m playwright install chromium

用法：
    python scripts/check_images.py article.html
    python scripts/check_images.py article.html --json
退出码：0 全部加载成功；1 有图片加载失败或存在失败请求；2 依赖缺失/文件不存在。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="check_images", description="浏览器实测 HTML 配图加载")
    ap.add_argument("html", help="本地 HTML 文件")
    ap.add_argument("--wait", type=int, default=1500, help="等待加载的毫秒数")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.html)
    if not path.exists():
        print(f"文件不存在：{path}", file=sys.stderr)
        return 2
    try:
        import asyncio
        from playwright.async_api import async_playwright
    except ImportError:
        print("缺少依赖：pip install playwright && python -m playwright install chromium", file=sys.stderr)
        return 2

    async def run() -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1000, "height": 900})
            failed_req: list[str] = []
            page.on("requestfailed", lambda r: failed_req.append(r.url))
            await page.goto("file:///" + str(path.resolve()).replace("\\", "/"))
            await page.wait_for_timeout(args.wait)
            imgs = await page.eval_on_selector_all(
                "img", "els => els.map(e => ({src: e.getAttribute('src'), w: e.naturalWidth, h: e.naturalHeight}))")
            await browser.close()
        return {"images": imgs, "failed_requests": failed_req}

    result = asyncio.run(run())
    imgs = result["images"]
    ok = [i for i in imgs if i["w"] > 0]
    bad = [i for i in imgs if i["w"] == 0]
    report = {
        "file": str(path),
        "total": len(imgs),
        "loaded": len(ok),
        "broken": bad,
        "failed_requests": result["failed_requests"],
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"== 图片实测（{path.name}）==")
        print(f"  加载成功 {len(ok)}/{len(imgs)}")
        for i in imgs:
            flag = "OK " if i["w"] > 0 else "BAD"
            print(f"    [{flag}] {i['src']}  {i['w']}x{i['h']}")
        print(f"  失败请求：{result['failed_requests'] or '无'}")
        print(f"  结论：{'全部加载成功' if not bad and not result['failed_requests'] else '存在未加载成功的图或失败请求'}")
    return 0 if not bad and not result["failed_requests"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
