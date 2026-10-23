#!/usr/bin/env python3
"""截图取证：Swagger 接口页 + Streamlit/Gradio 界面大视口整页，可选按 y 区间裁切。

前置: pip install playwright pillow
用法:
    python shot_pages.py --api http://127.0.0.1:8080/docs \
                         --webui http://127.0.0.1:8501 -o shots/
    python shot_pages.py --webui http://127.0.0.1:8501 -o shots/ --cut "0-1100,1100-1900"
"""
import argparse
import asyncio
import os
import sys

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

OVERLAY_SELECTORS = [
    'button[aria-label="Close"]',
    '[data-testid="stModal"] button',
    'button:has-text("×")',
    '.modal-close',
]


def find_browser():
    for p in BROWSERS:
        if os.path.isfile(p):
            return p
    return None


def cut(path, ranges):
    from PIL import Image
    im = Image.open(path)
    W, H = im.size
    base = os.path.splitext(path)[0]
    made = []
    for r in ranges:
        try:
            y1, y2 = [int(x) for x in r.split("-")]
        except ValueError:
            print(f"[skip] 无法解析裁切区间: {r}", file=sys.stderr)
            continue
        box = (0, max(0, y1), W, min(H, y2))
        if box[3] - box[1] < 40:
            continue
        out = f"{base}-cut{len(made) + 1}.png"
        im.crop(box).save(out)
        made.append(out)
        print(f"[cut] {out} {im.crop(box).size}")
    return made


async def run(a):
    from playwright.async_api import async_playwright

    exe = find_browser()
    if not exe:
        print("未找到 Edge/Chrome，请装 playwright 浏览器：python -m playwright install chromium",
              file=sys.stderr)
        return 1
    print(f"[browser] {exe}")

    os.makedirs(a.out, exist_ok=True)
    made = []

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, executable_path=exe, args=["--no-sandbox"])

        if a.api:
            pg = await b.new_page(viewport={"width": a.width, "height": 1600}, device_scale_factor=1)
            await pg.goto(a.api, wait_until="networkidle")
            await pg.wait_for_timeout(3500)
            # Swagger UI：展开全部端点，让清单完整
            for _ in range(3):
                for el in await pg.query_selector_all("button.opblock-summary-control, .opblock-summary"):
                    try:
                        await el.click(timeout=400)
                    except Exception:
                        pass
                await pg.wait_for_timeout(400)
            f = os.path.join(a.out, "shot-api.png")
            await pg.screenshot(path=f, full_page=True)
            made.append(f)
            print(f"[ok] {f}  title={await pg.title()}")
            await pg.close()

        if a.webui:
            # 大视口一次装下长页面（Streamlit 内部滚动，full_page 拿不到全部）
            pg = await b.new_page(viewport={"width": a.width, "height": a.tall}, device_scale_factor=1)
            await pg.goto(a.webui, wait_until="networkidle")
            await pg.wait_for_timeout(a.wait)
            # 关引导浮层（它常挡住首屏）
            for sel in OVERLAY_SELECTORS:
                try:
                    el = await pg.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click(timeout=1500)
                        print(f"[overlay] closed via {sel}")
                        break
                except Exception:
                    pass
            await pg.wait_for_timeout(1200)
            f = os.path.join(a.out, "shot-webui.png")
            await pg.screenshot(path=f, full_page=True)
            made.append(f)
            print(f"[ok] {f}  title={await pg.title()}")

            # 报告主要区块纵坐标，便于手工确定裁切区间
            pos = await pg.evaluate("""() => {
                const out = {};
                document.querySelectorAll('h1,h2,h3,h4').forEach(e=>{
                    const t=(e.innerText||'').trim();
                    if(t && t.length<40) out[t]=Math.round(e.getBoundingClientRect().top+window.scrollY);
                });
                return out;
            }""")
            if pos:
                print("[blocks] 区块纵坐标（用于 --cut）:")
                for k, v in sorted(pos.items(), key=lambda x: x[1]):
                    print(f"          y={v:<6} {k}")
            await pg.close()

        await b.close()

    if a.cut:
        for f in list(made):
            cut(f, a.cut.split(","))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="", help="Swagger/OpenAPI 页面 URL")
    ap.add_argument("--webui", default="", help="Web UI 首页 URL")
    ap.add_argument("-o", "--out", default="shots")
    ap.add_argument("--width", type=int, default=1500)
    ap.add_argument("--tall", type=int, default=2800, help="WebUI 视口高度，够高才能整页截全")
    ap.add_argument("--wait", type=int, default=10000, help="WebUI 首屏等待毫秒（Streamlit 冷启动慢）")
    ap.add_argument("--cut", default="", help='按 y 区间裁切，如 "0-1100,1100-1900"')
    a = ap.parse_args()
    if not a.api and not a.webui:
        ap.error("至少给一个 --api 或 --webui")
    sys.exit(asyncio.run(run(a)))


if __name__ == "__main__":
    main()
