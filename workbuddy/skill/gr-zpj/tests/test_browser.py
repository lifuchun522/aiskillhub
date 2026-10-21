# -*- coding: utf-8 -*-
"""gr-zpj · 浏览器端单测（Playwright / Chromium）

两块：
  A. 表单本身 —— 九个采集块都在、增删行可用、示例可载入、导出 JSON 形状正确、
     空数据有告警、导入导出可往返、页面零 JS 错误
  B. 渲染一致性（parity）—— **表单里生成的页面** 与 **命令行构建的页面**
     必须是同一个页面：结构计数、章节序号、导航、缩放点、正文文本逐字对比。
     这是"一份模板两处渲染"这个设计的正确性证明。

无 Playwright 时整体 skip（不把可选依赖变成硬依赖）。

运行：
    python -m unittest discover -s tests -v
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import build_portfolio as B   # noqa: E402

try:
    from playwright.sync_api import sync_playwright
    HAS_PW = True
except ImportError:                                     # pragma: no cover
    HAS_PW = False

FORM = os.path.join(SKILL, "assets", "form.html")
DEMO = os.path.join(SKILL, "examples", "demo-content.json")
EXAMPLE = os.path.join(SKILL, "examples", "content.json")


def expected_counts():
    """示例数据的真实条数 —— 不写死数字，改 content.json 后测试自动跟上。"""
    with open(EXAMPLE, encoding="utf-8") as fh:
        cfg = json.load(fh)
    C = cfg["content"]
    return {
        "metrics": len(cfg.get("metrics") or []),
        "pillars": len(C.get("pillars") or []),
        "stack": len(C.get("stack") or []),
        "timeline": len(C.get("timeline") or []),
        "projects": len(C.get("projects") or []),
        "cert_label": len(C.get("cert_label") or []),
        "qrs": len(C.get("qrs") or []),
        "images": len(cfg.get("images") or {}),
    }

PROBE = """() => ({
  counts: {
    pillars:  document.querySelectorAll('.pillar').length,
    cards:    document.querySelectorAll('.p-card').length,
    metrics:  document.querySelectorAll('.metrics div').length,
    stack:    document.querySelectorAll('#stack .st').length,
    timeline: document.querySelectorAll('.tl-item').length,
    certs:    document.querySelectorAll('.cert').length,
    qrs:      document.querySelectorAll('.qr').length,
    zooms:    document.querySelectorAll('[data-zoom]').length,
    navlinks: document.querySelectorAll('.nav ul a').length,
    sections: document.querySelectorAll('main > section').length,
    hrs:      document.querySelectorAll('.hr').length,
    namecard: document.querySelectorAll('.hero-card img').length,
    edu:      document.querySelectorAll('#credential .st').length
  },
  idx:   Array.from(document.querySelectorAll('main > section')).map(
           s => (s.querySelector('.idx')||{}).textContent || ''),
  ids:   Array.from(document.querySelectorAll('main > section')).map(s => s.id),
  nav:   Array.from(document.querySelectorAll('.nav ul a')).map(a => a.getAttribute('href')),
  zoomShape: Array.from(document.querySelectorAll('[data-zoom]')).map(
           e => e.className.split(' ')[0]),
  broken: Array.from(document.images)
           .filter(i => i.getAttribute('src') && (!i.complete || i.naturalWidth === 0))
           .map(i => i.getAttribute('data-asset') || i.getAttribute('src').slice(0, 24)),
  imgs:   document.images.length,
  title: document.title,
  text:  (document.body.innerText || '').replace(/\\s+/g, ' ').trim()
})"""


@unittest.skipUnless(HAS_PW, "未安装 playwright，跳过浏览器端测试")
class BrowserBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.ctx = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.page = self.ctx.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.goto("file:///" + FORM.replace("\\", "/"), wait_until="load")
        self.page.wait_for_timeout(400)

    def tearDown(self):
        self.ctx.close()

    def probe(self, html):
        """把一段 HTML 灌进空白页并采集结构化快照（用于两处渲染的逐字对比）。"""
        p = self.ctx.new_page()
        p.set_content(html, wait_until="load")
        p.wait_for_timeout(250)
        return p.evaluate(PROBE)


# ============================================================ A. 表单本体
class TestFormUI(BrowserBase):

    def test_no_js_error_on_load(self):
        self.assertEqual(self.errors, [])

    def test_nine_blocks_present(self):
        heads = self.page.eval_on_selector_all(
            "main .blk > h2", "els => els.map(e => e.innerText.replace(/\\s+/g,' ').trim())")
        self.assertEqual(len(heads), 9)
        for kw in ("基础信息", "首屏数据条", "首屏名片", "第一人称自述", "核心能力支柱",
                   "技术栈分组", "工作经历", "教育背景", "我的项目"):
            self.assertTrue(any(kw in h for h in heads), kw)

    def test_template_and_demo_injected(self):
        ok = self.page.evaluate("() => ({tpl: TPL.length, demo: DEMO ? 1 : 0})")
        self.assertGreater(ok["tpl"], 10000, "模板未注入")
        self.assertEqual(ok["demo"], 1, "示例数据未注入")
        self.assertIn("<!--SEC:capability-->", self.page.evaluate("() => TPL"))

    def test_empty_state_warns_about_name(self):
        txt = self.page.inner_text("#sumBox")
        self.assertIn("必须处理", txt)
        self.assertIn("姓名", txt)

    def test_load_demo_fills_every_block(self):
        exp = expected_counts()
        self.page.click("#btnDemo")
        self.page.wait_for_timeout(300)
        pay = self.page.evaluate("() => __grzpj.payload()")
        self.assertEqual(len(pay["metrics"]), exp["metrics"])
        self.assertEqual(len(pay["content"]["pillars"]), exp["pillars"])
        self.assertEqual(len(pay["content"]["stack"]), exp["stack"])
        self.assertEqual(len(pay["content"]["timeline"]), exp["timeline"])
        self.assertEqual(len(pay["content"]["projects"]), exp["projects"])
        self.assertEqual(len(pay["content"]["cert_label"]), exp["cert_label"])
        self.assertEqual(len(pay["content"]["qrs"]), exp["qrs"])
        self.assertEqual(len(pay["images"]), exp["images"])
        # 图片必须是内联 data URI（浏览器里能直接显示）
        for k, v in pay["images"].items():
            self.assertTrue(v["src"].startswith("data:image/"), k)
        # 表单控件也要真的被填上（不是只有内存状态）
        self.assertEqual(self.page.input_value('[data-path="texts.NAME"][data-path]'), "李福春")

    def test_add_and_remove_rows(self):
        before = self.page.eval_on_selector_all("#list-projects .row", "e => e.length")
        self.page.click('[data-add="projects"]')
        self.page.wait_for_timeout(120)
        self.assertEqual(self.page.eval_on_selector_all("#list-projects .row", "e => e.length"),
                         before + 1)
        self.page.click('#list-projects .row:last-child .rm')
        self.page.wait_for_timeout(120)
        self.assertEqual(self.page.eval_on_selector_all("#list-projects .row", "e => e.length"),
                         before)

    def test_extra_images_subrow(self):
        self.page.click('[data-add="projects"]')
        self.page.wait_for_timeout(100)
        self.page.click('#list-projects .row:last-child [data-add="extra"]')
        self.page.wait_for_timeout(100)
        n = self.page.eval_on_selector_all(
            '#list-projects .row:last-child [data-del="extra"]', "e => e.length")
        self.assertEqual(n, 1)

    def test_project_numbering_is_positional(self):
        """编号由位置生成：删掉第一个项目后，剩下的仍然从 01 开始。"""
        self.page.click("#btnDemo")
        self.page.wait_for_timeout(250)
        self.page.click('#list-projects .row:first-child .rm')
        self.page.wait_for_timeout(150)
        html = self.page.evaluate("() => __grzpj.render(__grzpj.payload())")
        second = self.page.evaluate("() => __grzpj.payload().content.projects[0].title")
        self.assertIn('<span class="no">01</span>' + second, html)

    def test_export_shape_is_buildable(self):
        """表单导出的 JSON 必须能直接被命令行构建器吃下（离线互通）。"""
        self.page.click("#btnDemo")
        self.page.wait_for_timeout(300)
        pay = self.page.evaluate("() => __grzpj.payload()")
        pay["paths"] = {"out_dir": tempfile.mkdtemp(prefix="grzpj-x-")}
        try:
            html, stats, _a = B.build(pay, SKILL)
            exp = expected_counts()
            self.assertEqual(stats["projects"], exp["projects"])
            self.assertEqual(stats["images"], exp["images"])
            self.assertNotIn("{{", html)
        finally:
            shutil.rmtree(pay["paths"]["out_dir"], ignore_errors=True)

    def test_import_export_roundtrip(self):
        self.page.click("#btnDemo")
        self.page.wait_for_timeout(300)
        pay = self.page.evaluate("() => __grzpj.payload()")
        self.page.evaluate("() => document.getElementById('btnClear')")
        self.page.evaluate("p => __grzpj.load(p)", json.loads(json.dumps(pay)))
        self.page.wait_for_timeout(300)
        pay2 = self.page.evaluate("() => __grzpj.payload()")
        self.assertEqual(json.dumps(pay, sort_keys=True), json.dumps(pay2, sort_keys=True))

    def test_disk_paths_are_flagged_not_silently_dropped(self):
        """命令行格式的 content.json（磁盘路径图）导入后必须给出提示。"""
        cfg = json.load(open(os.path.join(SKILL, "examples", "content.json"), encoding="utf-8"))
        self.page.evaluate("p => __grzpj.load(p)", cfg)
        self.page.wait_for_timeout(300)
        txt = self.page.inner_text("#sumBox")
        self.assertIn("磁盘路径", txt)

    def test_generate_opens_preview(self):
        self.page.click("#btnDemo")
        self.page.wait_for_timeout(300)
        self.page.click("#btnGen")
        self.page.wait_for_timeout(600)
        self.assertTrue(self.page.evaluate(
            "() => document.getElementById('out').classList.contains('open')"))
        self.assertGreater(len(self.page.evaluate("() => __lastHTML")), 200000)
        self.assertEqual(self.errors, [])

    def test_summary_reflects_counts(self):
        exp = expected_counts()
        self.page.click("#btnDemo")
        self.page.wait_for_timeout(300)
        txt = self.page.inner_text("#sumBox")
        self.assertIn("我的项目 · %d 个" % exp["projects"], txt)
        self.assertIn("工作经历 · %d 段" % exp["timeline"], txt)
        self.assertIn("填写进度", txt)


# ============================================================ B. 两处渲染一致性
class TestRenderParity(BrowserBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cfg = json.load(open(DEMO, encoding="utf-8"))
        cls.tmp = tempfile.mkdtemp(prefix="grzpj-parity-")
        cfg["paths"] = {"out_dir": cls.tmp}
        cls.py_html, _, _ = B.build(cfg, SKILL)
        cls.path = os.path.join(cls.tmp, "index.html")
        with open(cls.path, "w", encoding="utf-8") as fh:
            fh.write(cls.py_html)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)
        super().tearDownClass()

    def form_html(self):
        self.page.evaluate("p => __grzpj.load(p)",
                           json.load(open(DEMO, encoding="utf-8")))
        self.page.wait_for_timeout(400)
        return self.page.evaluate("() => __grzpj.render(__grzpj.payload())")

    def test_structure_counts_identical(self):
        a = self.probe(self.py_html)
        b = self.probe(self.form_html())
        self.assertEqual(a["counts"], b["counts"], "结构计数不一致")

    def test_section_index_and_nav_identical(self):
        a = self.probe(self.py_html)
        b = self.probe(self.form_html())
        self.assertEqual(a["idx"], b["idx"])
        self.assertEqual(a["ids"], b["ids"])
        self.assertEqual(a["nav"], b["nav"])
        # 资源键名两处不同（表单用位置键 fig_1 / x_1_1，手写 JSON 用语义键），
        # 但「可缩放元素的类型序列」必须完全一致 —— 这才是页面结构等价
        self.assertEqual(a["zoomShape"], b["zoomShape"])

    def test_visible_text_identical(self):
        a = self.probe(self.py_html)
        b = self.probe(self.form_html())
        self.assertEqual(a["text"], b["text"], "正文文本不一致")
        self.assertIn("李福春", a["text"])

    def test_title_identical(self):
        a = self.probe(self.py_html)
        b = self.probe(self.form_html())
        self.assertEqual(a["title"], b["title"])

    def test_form_output_has_no_residue(self):
        html = self.form_html()
        for pat in (r"\{\{[A-Z0-9_]+\}\}", r"<!--(?:SEC|NAV):[a-z_]+-->",
                    r"<!--HR-->", r"<!--N-->"):
            self.assertFalse(re.search(pat, html), "残留：" + pat)

    def test_form_output_images_all_load(self):
        """两处渲染的图必须都能真的显示（资源字典形状写错时这一步会炸）。"""
        a = self.probe(self.py_html)
        b = self.probe(self.form_html())
        self.assertEqual(b["imgs"], a["imgs"], "图片数量不一致")
        self.assertEqual(b["broken"], [], "表单渲染的页面有破图")
        self.assertEqual(a["broken"], [], "命令行渲染的页面有破图")


if __name__ == "__main__":
    unittest.main()
