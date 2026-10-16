#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""浏览器端实跑：中风险阈值过滤 → 点清理 → 确认清理（真删）→ 实时日志。
仅针对 targets.json 中 authorized=true 且 risk=low 的项，用于验证链路。"""
import sys
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "8848"
TARGET_ID = sys.argv[2] if len(sys.argv) > 2 else "cursor-logs"
URL = f"http://127.0.0.1:{PORT}/"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1460, "height": 940}, device_scale_factor=2)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_function("() => !document.querySelector('#meta .spin')", timeout=180000)
    pg.wait_for_timeout(500)
    print("概览:", pg.inner_text("#s-free"), "|", pg.inner_text("#s-low"), "|",
          pg.inner_text("#s-mid"), "|", pg.inner_text("#s-admin"))

    # --- 中风险阈值过滤 ---
    def mid_rows():
        return pg.eval_on_selector_all("#tb-mid tr", "els => els.map(e => parseFloat(e.children[2]?.innerText||'0'))")
    pg.fill("#midMin", "500")
    pg.wait_for_timeout(300)
    rows500 = mid_rows()
    print(f"阈值 500MB  -> {len(rows500)} 项, 最小 {min(rows500) if rows500 else 0} MB | {pg.inner_text('#n-mid')}")
    pg.fill("#midMin", "5000")
    pg.wait_for_timeout(300)
    rows5000 = mid_rows()
    print(f"阈值 5000MB -> {len(rows5000)} 项, 最小 {min(rows5000) if rows5000 else 0} MB | {pg.inner_text('#n-mid')}")
    assert rows500 and min(rows500) > 500, "阈值 500 过滤失效"
    assert rows5000 and min(rows5000) > 5000, "阈值 5000 过滤失效"
    print("  [OK] 中风险阈值过滤生效")
    pg.fill("#midMin", "500")
    pg.wait_for_timeout(300)
    pg.locator("#tb-mid").screenshot(path="page_mid_filtered.png")

    # --- 点击清理 ---
    btn = pg.locator(f'#tb-low button[data-id="{TARGET_ID}"]')
    print(f"低风险行数: {pg.locator('#tb-low button[data-act=one]').count()}，目标 {TARGET_ID} 存在: {btn.count()}")
    before = pg.eval_on_selector(f'#tb-low button[data-id="{TARGET_ID}"]', "e => e.dataset.path")
    btn.first.click()
    pg.wait_for_timeout(400)
    pg.locator(".modal").screenshot(path="page_modal2.png")
    print("弹窗标题:", pg.inner_text("#m-title"))

    t0 = __import__("time").time()
    pg.click("#m-go")
    pg.wait_for_selector("#logBadge", state="visible", timeout=5000)
    print(f"  [OK] 点击后 {( __import__('time').time()-t0):.2f}s 内出现「{pg.inner_text('#logBadge')}」标记，弹窗已关闭: {not pg.locator('.modal').is_visible()}")
    pg.wait_for_function("() => document.querySelector('#logBadge').textContent === '已完成'", timeout=300000)
    print(f"  [OK] 任务完成，总耗时 {__import__('time').time()-t0:.1f}s")
    pg.wait_for_timeout(1200)
    pg.locator("#log").screenshot(path="page_log_live.png")
    pg.screenshot(path="page_after.png")
    print("\n===== 页面实时日志 =====")
    print(pg.inner_text("#log"))
    print("\n===== 清理后该行体积 =====")
    print(pg.inner_text(f"#tb-low tr:has(button[data-id='{TARGET_ID}'])")[:200] if pg.locator(
        f"#tb-low button[data-id='{TARGET_ID}']").count() else "(该行已从表格移除 = 体积已为 0)")
    print("页面 JS 错误:", errs or "无")
    print("目标路径:", before)
    b.close()
