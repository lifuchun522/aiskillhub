#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zw-check 离线单测：全部纯函数，不触网、不依赖第三方库。

跑法：
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import zwcheck as Z  # noqa: E402


class TestVisibleText(unittest.TestCase):
    def test_html_visible_drops_script_style_img_figure(self):
        html = """<html><head><style>p{color:red}</style></head><body>
        <h1>标题</h1>
        <script>var a=1;</script>
        <p>正文一</p>
        <figure><img src="img/a.png" alt="这是图注"><figcaption>图注文字</figcaption></figure>
        <p>正文二 &amp; 结尾</p></body></html>"""
        text = Z.html_visible(html)
        self.assertIn("标题", text)
        self.assertIn("正文一", text)
        self.assertIn("正文二 & 结尾", text)
        for gone in ("color:red", "var a=1", "img/a.png", "这是图注", "图注文字"):
            self.assertNotIn(gone, text)

    def test_html_visible_normalizes_whitespace_and_keeps_spaces(self):
        text = Z.html_visible("<p>a   b\n\n c</p>")
        self.assertEqual(text, "a b c")

    def test_html_visible_markers(self):
        html = "<p>导航</p><h1>标题</h1><p>正文</p><script>x</script>"
        text = Z.html_visible(html, start="<h1", end="<script>")
        self.assertEqual(text, "标题正文")

    def test_md_visible_removes_images_and_code_fence(self):
        md = "开头 ![图](img/a.png) 结尾\n\n```bash\nrm -rf /tmp/x\n```\n"
        text = Z.md_visible(md)
        self.assertIn("开头", text)
        self.assertIn("结尾", text)
        self.assertNotIn("img/a.png", text)
        self.assertNotIn("rm -rf", text)

    def test_md_visible_keep_code(self):
        md = "```bash\nrm -rf /tmp/x\n```"
        self.assertIn("rm -rf", Z.md_visible(md, keep_code=True))


class TestCountChars(unittest.TestCase):
    def test_three_gauges(self):
        r = Z.count_chars("中文 abc 123")
        self.assertEqual(r["with_space"], 10)
        self.assertEqual(r["no_space"], 8)
        self.assertEqual(r["spaces"], 2)
        self.assertEqual(r["cjk"], 2)

    def test_empty(self):
        self.assertEqual(Z.count_chars(""), {"with_space": 0, "no_space": 0, "spaces": 0, "cjk": 0})


class TestTraces(unittest.TestCase):
    def test_block_level_hit(self):
        hits = Z.scan_traces("本次实测还产出三类可复核文件：operation-order.md。")
        self.assertTrue(any(h["category"] == "交付清单" and h["level"] == "block" for h in hits))

    def test_file_path_leak_hit(self):
        hits = Z.scan_traces("对照结果页面在 report/baseline-report.html。")
        self.assertTrue(any(h["category"] == "文件路径外泄" for h in hits))

    def test_url_is_not_path_leak(self):
        hits = Z.scan_traces("见 https://help.aliyun.com/zh/oss/user-guide/access-oss-by-https-protocol")
        self.assertFalse([h for h in hits if h["category"] == "文件路径外泄"])

    def test_warn_level_hit(self):
        hits = Z.scan_traces("在支持 Skill 的宿主里触发。")
        self.assertTrue(any(h["category"] == "宿主术语" and h["level"] == "warn" for h in hits))

    def test_clean_text_has_no_hits(self):
        clean = "那晚十点多，朋友发来一张截图。刷新、清缓存、换浏览器都正常，最后才在证书详情里看到：有效期已过。"
        self.assertEqual(Z.scan_traces(clean), [])

    def test_allow_list_passes_through(self):
        text = "本次实测还产出三类可复核文件"
        self.assertTrue(Z.scan_traces(text))
        hit = Z.scan_traces(text)[0]["match"]
        self.assertFalse([h for h in Z.scan_traces(text, allow=(hit,)) if h["match"] == hit])

    def test_context_carries_neighbour_text(self):
        hits = Z.scan_traces("前文甲乙丙丁戊己庚辛壬癸" * 3 + "本次实测还产出" + "后文" * 5)
        self.assertTrue(hits[0]["context"])
        self.assertIn("本次实测还产出", hits[0]["context"])


class TestAnalyzeText(unittest.TestCase):
    def test_max_chars_boundary(self):
        text = "一二三四五"
        self.assertEqual(Z.analyze_text(text, max_chars=5)["checks"][0]["status"], Z.PASS)
        self.assertEqual(Z.analyze_text(text, max_chars=4)["checks"][0]["status"], Z.FAIL)

    def test_no_max_chars_is_na(self):
        self.assertEqual(Z.analyze_text("abc")["checks"][0]["status"], Z.NA)

    def test_block_vs_warn_severity(self):
        r = Z.analyze_text("可供二次开发", max_chars=100)
        self.assertEqual(r["checks"][1]["status"], Z.FAIL)   # block 级 → FAIL
        r2 = Z.analyze_text("支持 Skill 的宿主", max_chars=100)
        self.assertEqual(r2["checks"][1]["status"], Z.PASS)  # 无 block 级
        self.assertEqual(r2["checks"][2]["status"], Z.WARN)  # warn 级 → WARN


class TestCheckHtml(unittest.TestCase):
    def _ck(self, html, min_images=None, max_images=None):
        return {c["id"]: c["status"] for c in Z.check_html(html, min_images, max_images)["checks"]}

    def test_clean_html_all_pass(self):
        html = '<div><h1>t</h1><p>a</p><p><img src="img/1.png" style="x"></p></div>'
        s = self._ck(html)
        self.assertEqual([v for v in s.values()], [Z.PASS] * len(s))

    def test_table_fails(self):
        self.assertEqual(self._ck("<div><h1>t</h1><table><tr><td>x</td></tr></table></div>")["H1"], Z.FAIL)

    def test_figcaption_fails(self):
        self.assertEqual(self._ck("<div><h1>t</h1><figure><figcaption>备注</figcaption></figure></div>")["H2"],
                         Z.FAIL)

    def test_h1_count(self):
        self.assertEqual(self._ck("<div><h1>a</h1><h1>b</h1></div>")["H3"], Z.FAIL)
        self.assertEqual(self._ck("<div><h1>a</h1></div>")["H3"], Z.PASS)

    def test_tag_balance(self):
        self.assertEqual(self._ck("<div><h1>t</h1><p>a</p></div>")["H4"], Z.PASS)
        self.assertEqual(self._ck("<div><h1>t</h1><p>a</p>")["H4"], Z.FAIL)

    def test_external_image_fails_relative_and_data_pass(self):
        self.assertEqual(self._ck('<div><h1>t</h1><p><img src="https://x.com/a.png"></p></div>')["H5"], Z.FAIL)
        r = Z.check_html('<div><h1>t</h1><p><img src="img/a.png"></p><p><img src="data:image/png;base64,AAA"></p></div>')
        self.assertEqual({c["id"]: c["status"] for c in r["checks"]}["H5"], Z.PASS)
        self.assertEqual(r["report"]["relative_imgs"], 1)
        self.assertEqual(r["report"]["embedded_imgs"], 1)

    def test_min_max_images(self):
        html = '<div><h1>t</h1><p><img src="img/a.png"></p><p><img src="img/b.png"></p></div>'
        s = self._ck(html, min_images=3, max_images=2)
        self.assertEqual(s["H6"], Z.FAIL)
        self.assertEqual(s["H7"], Z.PASS)

    def test_copy_button_detection(self):
        self.assertTrue(Z.check_html('<div><h1>t</h1></div><script>x</script><button>复制正文</button>')["report"]["has_copy_button"])
        self.assertFalse(Z.check_html('<div><h1>t</h1></div>')["report"]["has_copy_button"])


class TestFrontmatter(unittest.TestCase):
    def test_parses_two_fields(self):
        md = "---\nname: zw-check\ndescription: 检查稿件\n---\n\n# body\n"
        self.assertEqual(Z.parse_frontmatter(md), {"name": "zw-check", "description": "检查稿件"})

    def test_folded_multiline_value(self):
        md = "---\nname: x\ndescription: 第一段\n  第二段\n---\n"
        self.assertEqual(Z.parse_frontmatter(md)["description"], "第一段 第二段")

    def test_none_when_absent(self):
        self.assertIsNone(Z.parse_frontmatter("# 无 frontmatter\n"))


class TestRules(unittest.TestCase):
    def _status(self, rep, i):
        return {c["id"]: c["status"] for c in rep["checks"]}[i]

    def test_workbuddy_title_prefix(self):
        ok = Z.check_rules("【征文】网站弹出“不安全”那晚\n正文", "workbuddy")
        bad = Z.check_rules("网站弹出“不安全”那晚\n正文", "workbuddy")
        self.assertEqual(self._status(ok, "W1"), Z.PASS)
        self.assertEqual(self._status(bad, "W1"), Z.FAIL)

    def test_workbuddy_na_without_html(self):
        rep = Z.check_rules("【征文】x 正文 WorkBuddy WorkBuddy", "workbuddy")
        self.assertEqual(self._status(rep, "W3"), Z.NA)

    def test_workbuddy_image_gate_with_html_report(self):
        rep = Z.check_rules("【征文】x WorkBuddy WorkBuddy", "workbuddy",
                            html_report={"img_count": 2})
        self.assertEqual(self._status(rep, "W3"), Z.FAIL)

    def test_cloudq_six_dimensions_missing(self):
        rep = Z.check_rules("功能性、安全性、可靠性", "cloudq")
        self.assertEqual(self._status(rep, "C1"), Z.FAIL)
        self.assertEqual(self._status(rep, "C2"), Z.FAIL)

    def test_cloudq_all_dimensions_and_tiers(self):
        doc = ("功能性、安全性、可靠性、成本效益、用户体验、性能效率；"
               "红线维度、核心维度、评价维度。")
        rep = Z.check_rules(doc, "cloudq")
        self.assertEqual(self._status(rep, "C1"), Z.PASS)
        self.assertEqual(self._status(rep, "C2"), Z.PASS)

    def test_cloudq_single_tag_rule(self):
        one = Z.check_rules("> #Skill资产共创\n正文", "cloudq")
        three = Z.check_rules("> #AIOps最佳实践 #CloudQ共创征文 #Skill资产共创\n正文", "cloudq")
        self.assertEqual(self._status(one, "C3"), Z.PASS)
        self.assertEqual(self._status(three, "C3"), Z.FAIL)

    def test_cloudq_tag_outside_whitelist(self):
        rep = Z.check_rules("> #随便打的标签\n正文", "cloudq")
        self.assertEqual(self._status(rep, "C4"), Z.FAIL)

    def test_skill_md_metadata_fields_and_sections(self):
        good = "---\nname: s\ndescription: d\n---\n\n## 工具\n## 执行步骤\n## 安全边界\n## 铁律\n"
        bad = "---\nname: s\ndescription: d\nversion: 1\n---\n\n## 工具\n"
        g = Z.check_rules("x", "none", skill_md_text=good)
        b = Z.check_rules("x", "none", skill_md_text=bad)
        self.assertEqual(self._status(g, "S1"), Z.PASS)
        self.assertEqual(self._status(g, "S2"), Z.PASS)
        self.assertEqual(self._status(b, "S1"), Z.FAIL)
        self.assertEqual(self._status(b, "S2"), Z.FAIL)

    def test_track_none_is_na(self):
        self.assertEqual(self._status(Z.check_rules("x", "none"), "R0"), Z.NA)

    def test_char_limit_item(self):
        rep = Z.check_rules("x", "none", max_chars=10, chars=11)
        self.assertEqual(self._status(rep, "N1"), Z.FAIL)
        rep2 = Z.check_rules("x", "none", max_chars=10, chars=10)
        self.assertEqual(self._status(rep2, "N1"), Z.PASS)


class TestConsistency(unittest.TestCase):
    TREE = """正文说明…

```text
zw-check/
├── SKILL.md
├── README.md
├── scripts/
│   └── zwcheck.py
└── tests/
    └── test_zwcheck.py
```
"""

    def test_parse_tree_block(self):
        t = Z.parse_tree_block(self.TREE)
        self.assertEqual(t["root"], "zw-check/")
        self.assertEqual(sorted(t["files"]), ["README.md", "SKILL.md", "test_zwcheck.py", "zwcheck.py"])
        self.assertEqual(sorted(t["dirs"]), ["scripts", "tests"])

    def test_parse_tree_block_absent(self):
        self.assertIsNone(Z.parse_tree_block("```bash\nls -l\n```"))

    def test_parse_tree_block_strips_alignment_and_trailing_comments(self):
        tree = """```text
zw-check/
├── SKILL.md                      # 技能规范（元数据仅 name + description）
├── scripts/
│   ├── zwcheck.py                # 四类检查（text / html / rules / consist / all）
│   └── check_images.py           # 浏览器实测图片加载（可选依赖）
└── USAGE.html                    # 使用步骤手册
```
"""
        t = Z.parse_tree_block(tree)
        self.assertEqual(sorted(t["files"]),
                         ["SKILL.md", "USAGE.html", "check_images.py", "zwcheck.py"])
        self.assertEqual(t["dirs"], ["scripts"])
        for name in t["files"]:
            self.assertNotIn(" ", name)
            self.assertNotIn("#", name)

    def test_compare_tree_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in ("SKILL.md", "README.md"):
                (p / name).write_text("x", encoding="utf-8")
            (p / "scripts").mkdir()
            (p / "scripts" / "zwcheck.py").write_text("x", encoding="utf-8")
            (p / "tests").mkdir()
            (p / "tests" / "test_zwcheck.py").write_text("x", encoding="utf-8")
            self.assertEqual(Z.compare_tree(self.TREE, p)["status"], Z.PASS)

    def test_compare_tree_reports_missing_and_extra(self):
        tree = self.TREE.replace("│   └── zwcheck.py", "│   └── old_name.py")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "SKILL.md").write_text("x", encoding="utf-8")
            (p / "scripts").mkdir()
            (p / "scripts" / "zwcheck.py").write_text("x", encoding="utf-8")
            (p / "tests").mkdir()
            (p / "tests" / "test_zwcheck.py").write_text("x", encoding="utf-8")
            r = Z.compare_tree(tree, p)
            self.assertEqual(r["status"], Z.FAIL)
            self.assertIn("zwcheck.py", r["missing_in_doc"])

    def test_compare_tree_ignores_pycache(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "SKILL.md").write_text("x", encoding="utf-8")
            (p / "scripts").mkdir()
            (p / "scripts" / "zwcheck.py").write_text("x", encoding="utf-8")
            (p / "tests").mkdir()
            (p / "tests" / "test_zwcheck.py").write_text("x", encoding="utf-8")
            (p / "scripts" / "__pycache__").mkdir()
            (p / "scripts" / "__pycache__" / "zwcheck.cpython-313.pyc").write_bytes(b"x")
            self.assertNotIn("zwcheck.cpython-313.pyc", Z.compare_tree(self.TREE, p)["missing_in_doc"])

    def test_compare_tree_na_without_block(self):
        self.assertEqual(Z.compare_tree("没有目录树", Path("."))["status"], Z.NA)

    def test_compare_description(self):
        skill = '---\nname: s\ndescription: 同一段描述\n---\n'
        same = '正文\n\n```yaml\nname: s\ndescription: 同一段描述\n```\n'
        diff = '正文\n\n```yaml\nname: s\ndescription: 旧描述\n```\n'
        self.assertEqual(Z.compare_description(same, skill)["status"], Z.PASS)
        self.assertEqual(Z.compare_description(diff, skill)["status"], Z.FAIL)
        self.assertEqual(Z.compare_description("正文无元数据", skill)["status"], Z.NA)

    def test_claimed_and_actual_test_count(self):
        self.assertEqual(Z.extract_claimed_test_count("36 项离线单测全部通过"), 36)
        self.assertEqual(Z.extract_claimed_test_count("单测 47 个"), 47)
        self.assertEqual(Z.extract_claimed_test_count("Ran 12 tests in 0.1s"), 12)
        self.assertIsNone(Z.extract_claimed_test_count("没有提到测试数量"))
        self.assertEqual(Z.parse_unittest_count("\nRan 9 tests in 0.002s\n\nOK\n"), 9)
        self.assertIsNone(Z.parse_unittest_count("ModuleNotFoundError"))


class TestCli(unittest.TestCase):
    def _write(self, d: Path, name: str, text: str) -> Path:
        p = d / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_exit_zero_on_clean_doc(self):
        with tempfile.TemporaryDirectory() as d:
            doc = self._write(Path(d), "a.html",
                              '<div style="max-width:860px"><h1>【征文】标题</h1>'
                              '<p style="x">正文 WorkBuddy 干净内容。</p></div>')
            self.assertEqual(Z.main(["text", str(doc), "--max-chars", "200"]), 0)
            self.assertEqual(Z.main(["html", str(doc)]), 0)

    def test_exit_one_on_table_and_trace(self):
        with tempfile.TemporaryDirectory() as d:
            doc = self._write(Path(d), "b.html",
                              '<div><h1>t</h1><table><tr><td>x</td></tr></table>'
                              '<p>本次实测还产出三类可复核文件</p></div>')
            self.assertEqual(Z.main(["all", str(doc)]), 1)

    def test_json_output_and_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            doc = self._write(Path(d), "c.html",
                              '<div><h1>t</h1><p>干净正文</p></div>')
            self.assertEqual(Z.main(["text", str(doc), "--json"]), 0)

    def test_missing_file_returns_2(self):
        self.assertEqual(Z.main(["text", "definitely-missing-file.md"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
