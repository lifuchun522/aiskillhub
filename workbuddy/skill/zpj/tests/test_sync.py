# -*- coding: utf-8 -*-
"""zpj · 资产一致性单测

「表单里内联的模板 / 示例数据」与「命令行用的 assets/template.html /
examples/demo-content.json」是同一份东西的两处存放 —— 这个文件守着它们不许漂移。
"""
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
FORM = os.path.join(SKILL, "assets", "form.html")
TPL = os.path.join(SKILL, "assets", "template.html")
DEMO = os.path.join(SKILL, "examples", "demo-content.json")


def grab(doc, start, end):
    m = re.search(re.escape(start) + r"\s*(.*?)\s*" + re.escape(end), doc, re.S)
    return m.group(1) if m else None


class TestSync(unittest.TestCase):

    def setUp(self):
        with open(FORM, encoding="utf-8") as fh:
            self.form = fh.read()
        with open(TPL, encoding="utf-8") as fh:
            self.tpl = fh.read()

    def test_template_markers_exist(self):
        for m in ("/*@TPL-START@*/", "/*@TPL-END@*/", "/*@DEMO-START@*/", "/*@DEMO-END@*/"):
            self.assertIn(m, self.form, "缺少标记 " + m)

    def test_embedded_template_equals_file(self):
        body = grab(self.form, "/*@TPL-START@*/", "/*@TPL-END@*/")
        self.assertIsNotNone(body, "找不到 TPL 标记区")
        self.assertEqual("const TPL = " in body, True)
        got = json.loads(body[len("const TPL = "):].rstrip(";"))
        self.assertEqual(got, self.tpl, "form.html 里的模板与 assets/template.html 不一致")

    def test_embedded_demo_equals_file(self):
        body = grab(self.form, "/*@DEMO-START@*/", "/*@DEMO-END@*/")
        self.assertIsNotNone(body, "找不到 DEMO 标记区")
        got = json.loads(body[len("const DEMO = "):].rstrip(";"))
        with open(DEMO, encoding="utf-8") as fh:
            want = json.load(fh)
        self.assertEqual(got, want, "form.html 里的示例数据与 examples/demo-content.json 不一致")

    def test_script_end_tag_escaped(self):
        """模板里的 </script> 必须被转义 —— 否则会提前闭合表单自身的 script 元素。"""
        body = grab(self.form, "/*@TPL-START@*/", "/*@TPL-END@*/")
        self.assertNotIn("</script", body)

    def test_no_bare_script_close_inside_literals(self):
        # 表单里其他字面量也不要出现裸 </script
        self.assertEqual(self.form.count("</script>"), 1, "form.html 只能有一个 </script>")

    def test_check_mode_passes(self):
        r = subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "sync_assets.py"),
                            "--check", "--skill-dir", SKILL],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_form_has_no_external_resource(self):
        """离线可用：不允许出现任何 http(s) 外链资源 / CDN。"""
        bad = re.findall(r'(?:src|href)\s*=\s*["\'](https?:)?//[^"\']+', self.form)
        self.assertEqual(bad, [], "表单引用了外部资源：" + str(bad[:5]))


class TestExamples(unittest.TestCase):

    def test_example_and_demo_share_content(self):
        """examples/content.json（命令行用）与 demo-content.json（表单用）内容必须一致，
        只允许图片表示方式不同（磁盘路径 vs 内联 data URI）。"""
        with open(os.path.join(SKILL, "examples", "content.json"), encoding="utf-8") as fh:
            full = json.load(fh)
        with open(DEMO, encoding="utf-8") as fh:
            demo = json.load(fh)
        self.assertEqual(full["texts"], demo["texts"])
        self.assertEqual(full["metrics"], demo["metrics"])
        self.assertEqual(full["content"], demo["content"])
        self.assertEqual(sorted(full["images"]), sorted(demo["images"]))
        for k, v in demo["images"].items():
            self.assertTrue(v["src"].startswith("data:image/"), k)

    def test_demo_size_is_reasonable(self):
        """示例是内联进表单的，体积失控会拖慢表单加载。"""
        self.assertLess(os.path.getsize(DEMO), 900 * 1024,
                        "demo-content.json 过大，考虑调小 make_demo.py 的演示尺寸")


if __name__ == "__main__":
    unittest.main()
