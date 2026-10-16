# -*- coding: utf-8 -*-
"""gr-zpj · 构建器单测（全部离线，不需要浏览器）

覆盖四类断言：
  A. 结构计数与产物整洁（残留标记 / 导航死链 / 孤立分隔线 / 章节序号）
  B. 区块裁减 —— 数据为空则整块消失，且不留下「空区块 + 死链 + 孤儿分隔线」三件套
  C. 配置门禁 —— 键写错层级 / 资源键打错 / 文件缺失 / token 不匹配，必须报错退出
  D. 输入容错 —— 同一份数据既能是「一行一条的字符串」（表单导出），也能是数组（手写 JSON）

运行：
    python -m unittest discover -s tests -v
"""
import base64
import io
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
    from PIL import Image
except ImportError:                                    # pragma: no cover
    raise SystemExit("需要 Pillow：pip install pillow")


def png(w, h, color=(90, 140, 220)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


def jpg(w, h, color=(200, 120, 90)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG", quality=80)
    return buf.getvalue()


def data_uri(raw, mime="image/png"):
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode())


class Base(unittest.TestCase):
    """每例一个临时目录，图片按需生成，避免依赖本机素材。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="grzpj-")
        self.img = os.path.join(self.tmp, "a.png")
        open(self.img, "wb").write(png(900, 500))
        self.img2 = os.path.join(self.tmp, "b.jpg")
        open(self.img2, "wb").write(jpg(700, 400))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- 最小可用配置，各用例按需覆盖
    def cfg(self, **over):
        c = {
            "paths": {"out_dir": self.tmp},
            "texts": {"NAME": "测试君", "ROLE": "架构师", "ROLE_SHORT": "架构师",
                      "TAGLINE": "Architect"},
            "metrics": [["10", "年", "经验"], ["3", "万 QPS", "峰值"]],
            "card": {"title": "名片", "sub": "副标题", "hint": "点击放大"},
            "images": {
                "namecard": {"src": self.img},
                "fig_1": {"src": self.img},
            },
            "content": {
                "intro": {"label": "ABOUT ME", "who": "测试君", "where": "深圳",
                          "lead": "一句话 <b>重音</b>。", "paras": ["第一段", "第二段"],
                          "facts": [["10 年", "经验"]]},
                "pillars": [{"icon": "arch", "title": "架构", "desc": "描述",
                             "tags": ["高并发", "分布式"]}],
                "stack": [["后端", "Java / Spring", "说明"]],
                "timeline": [["2024.01 — 2025.01", "架构师", "某公司", True, ["要点一"]]],
                "edu": {"label": "教育背景", "tags": ["某大学 · 本科"]},
                "cert_label": [["cert_1", "认证名", "颁发方"]],
                "qrs": [["qr_1", "公众号", "https://example.com/x"]],
                "projects": [{
                    "title": "项目一", "period": "2024.01 — 2025.01", "sub": "副标题",
                    "desc": "简介", "result": "成果 <b>P99 降 60%</b>",
                    "steps": ["动作一", "动作二"], "chips": "Java / CI/CD",
                    "fig": "fig_1", "fig_title": "项目一 · 架构图", "fig_sub": "图说明",
                    "extra": [["fig_1", "补充图", "说明"]],
                }],
            },
        }
        c["images"]["cert_1"] = {"src": self.img2}
        c["images"]["qr_1"] = {"src": self.img}
        for k, v in over.items():
            c[k] = v
        return c

    def build(self, cfg):
        return B.build(cfg, SKILL)


# =============================================================== A. 结构与整洁
class TestStructure(Base):

    def test_full_render(self):
        html, stats, arch = self.build(self.cfg())
        self.assertEqual(stats["pillars"], 1)
        self.assertEqual(stats["projects"], 1)
        self.assertEqual(stats["timeline"], 1)
        self.assertEqual(stats["certs"], 1)
        self.assertEqual(stats["qrs"], 1)
        self.assertEqual(stats["namecard"], 1)
        self.assertEqual(stats["kept"],
                         ["capability", "stack", "career", "credential", "projects"])

    def test_no_template_residue(self):
        html, _s, _a = self.build(self.cfg())
        for pat in (r"\{\{[A-Z0-9_]+\}\}", r"<!--(?:SEC|NAV):[a-z_]+-->",
                    r"<!--HR-->", r"<!--N-->"):
            self.assertFalse(re.search(pat, html), "残留标记：" + pat)

    def test_section_numbers_are_dom_ordered(self):
        html, _s, _a = self.build(self.cfg())
        nums = re.findall(r'class="idx">(\d\d) / ([\w ]+)', html)
        self.assertEqual([n[0] for n in nums], ["01", "02", "03", "04", "05"])
        self.assertEqual([n[1] for n in nums],
                         ["CAPABILITY", "TECH STACK", "CAREER", "CREDENTIAL", "MY PROJECTS"])

    def test_separators_between_sections_only(self):
        """分隔线数量 = 区块数 - 1；且不落在 main 的最前 / 最后。"""
        html, _s, _a = self.build(self.cfg())
        self.assertEqual(html.count('class="hr"'), 4)
        main = html.split("<main>")[1].split("</main>")[0]
        self.assertFalse(main.strip().startswith('<div class="wrap"><div class="hr">'))
        self.assertFalse(main.strip().endswith("</div></div>"))

    def test_nav_has_no_dead_link(self):
        html, _s, _a = self.build(self.cfg())
        links = re.findall(r'<a href="#([a-z]+)">', html)
        ids = re.findall(r'\sid="([a-z]+)"', html)
        for l in links:
            self.assertIn(l, ids, "导航指向不存在的锚点：#" + l)

    def test_token_defaults_are_derived(self):
        cfg = self.cfg(texts={"NAME": "张三", "ROLE": "架构师", "ROLE_SHORT": "架构师"})
        html, _s, _a = self.build(cfg)
        self.assertIn("<title>张三 · 架构师 | 作品集</title>", html)
        self.assertIn('<div class="mk">张</div>', html)
        self.assertIn("共 1 段履历", html)                 # CAREER_LEAD 自动生成
        self.assertIn("共 1 个项目", html)                 # PROJ_LEAD 自动生成

    def test_metrics_columns_match_rows(self):
        html, _s, _a = self.build(self.cfg())
        self.assertIn('style="--mc:2"', html)

    def test_data_uri_input_passthrough(self):
        """表单导出的内联图必须能直接被构建器吃下。"""
        cfg = self.cfg(images={"namecard": {"src": data_uri(png(40, 40))},
                               "fig_1": {"src": data_uri(jpg(40, 40), "image/jpeg")},
                               "cert_1": {"src": data_uri(png(40, 40))},
                               "qr_1": {"src": data_uri(png(40, 40))}})
        html, stats, _a = self.build(cfg)
        self.assertEqual(stats["images"], 4)
        self.assertEqual(html.count("data:image"), 4 + 0)   # 4 个资源键各出现一次

    def test_string_inputs_shorthand(self):
        """同一份内容：字符串形态（一行一条）与数组形态必须构建出**逐字相同**的页面。"""
        arr = self.cfg()
        arr["content"]["timeline"][0][4] = ["要点一", "要点二"]
        arr["content"]["projects"][0]["steps"] = ["动作一", "动作二"]
        arr["content"]["intro"]["paras"] = ["第一段", "第二段"]
        arr["content"]["intro"]["facts"] = [["10 年", "经验"]]
        arr["content"]["pillars"][0]["tags"] = ["高并发", "分布式"]
        arr["content"]["edu"]["tags"] = ["某大学 · 本科"]

        s = self.cfg()
        s["content"]["timeline"][0][4] = "要点一\n要点二"
        s["content"]["projects"][0]["steps"] = "动作一\n动作二"
        s["content"]["intro"]["paras"] = "第一段\n第二段"
        s["content"]["intro"]["facts"] = "10 年 | 经验"
        s["content"]["pillars"][0]["tags"] = "高并发 / 分布式"
        s["content"]["edu"]["tags"] = "某大学 · 本科"

        a = self.build(arr)[0]
        b = self.build(s)[0]
        self.assertEqual(re.sub(r"\s+", "", a), re.sub(r"\s+", "", b))
        # 6 个导航项 + 2 个支柱标签 + 2 条时间线要点 + 2 条项目动作
        self.assertEqual(b.count("<li>"), 12)
        self.assertEqual(b.count('<span class="chip">'), 2)   # CI/CD 不被拆开


# =============================================================== B. 区块裁减
class TestSectionPruning(Base):

    def test_drop_capability(self):
        cfg = self.cfg()
        cfg["content"]["pillars"] = []
        html, stats, _a = self.build(cfg)
        self.assertNotIn('id="capability"', html)
        self.assertNotIn('href="#capability"', html)
        self.assertEqual(html.count('class="hr"'), 3)
        self.assertEqual(stats["kept"], ["stack", "career", "credential", "projects"])
        self.assertEqual(re.findall(r'class="idx">(\d\d)', html), ["01", "02", "03", "04"])

    def test_drop_tail_credential(self):
        """删掉尾部区块不能留下「什么都没有的分隔线」。"""
        cfg = self.cfg()
        cfg["content"]["credential"] = None
        cfg["content"].pop("credential", None)
        cfg["content"]["cert_label"] = []
        cfg["content"]["qrs"] = []
        cfg["content"]["edu"] = {}
        html, _s, _a = self.build(cfg)
        self.assertEqual(html.count('class="hr"'), 3)
        main = html.split("<main>")[1].split("</main>")[0].strip()
        self.assertTrue(main.endswith("</section>"), "main 末尾不该是分隔线")
        self.assertNotIn('id="credential"', html)

    def test_only_projects_no_separator(self):
        cfg = self.cfg()
        for k in ("pillars", "stack", "timeline"):
            cfg["content"][k] = []
        cfg["content"]["intro"] = None
        cfg["content"]["cert_label"], cfg["content"]["qrs"] = [], []
        cfg["content"]["edu"] = {}
        cfg["card"] = None
        cfg["metrics"] = []
        html, stats, _a = self.build(cfg)
        self.assertEqual(html.count('class="hr"'), 0, "只剩一个区块时不该有分隔线")
        self.assertEqual(stats["kept"], ["projects"])
        self.assertEqual(re.findall(r'class="idx">(\d\d)', html), ["01"])

    def test_empty_content_still_valid_page(self):
        cfg = self.cfg()
        cfg["content"] = {}
        cfg["metrics"] = []
        cfg["card"] = None
        cfg["images"] = {"fig_1": {"src": self.img}}
        html, stats, _a = self.build(cfg)
        self.assertFalse(stats["kept"])
        self.assertIn("</html>", html)
        self.assertEqual(html.count('class="hr"'), 0)

    def test_card_without_image_is_dropped(self):
        """配置里留着 card 但没给图 -> 不渲染空图，也不报错。"""
        cfg = self.cfg()
        cfg["images"] = {"fig_1": {"src": self.img}, "cert_1": {"src": self.img},
                         "qr_1": {"src": self.img}}
        html, stats, _a = self.build(cfg)
        self.assertEqual(stats["namecard"], 0)
        self.assertNotIn('data-asset="namecard"', html)

    def test_cert_without_image_skipped(self):
        cfg = self.cfg()
        cfg["content"]["cert_label"] = [["", "只有名字没图"], ["cert_1", "有图", "方"]]
        html, stats, _a = self.build(cfg)
        self.assertEqual(stats["certs"], 1)
        self.assertNotIn("只有名字没图", html)

    def test_qr_without_url_skipped(self):
        cfg = self.cfg()
        cfg["content"]["qrs"] = [["qr_1", "没链接", ""], ["qr_1", "有链接", "https://a.b"]]
        html, stats, _a = self.build(cfg)
        self.assertEqual(stats["qrs"], 1)
        self.assertNotIn("没链接", html)


# =============================================================== C. 配置门禁
class TestGates(Base):

    def assert_exit(self, cfg, keyword):
        with self.assertRaises(SystemExit) as cm:
            B.build(cfg, SKILL)
        self.assertIn(keyword, str(cm.exception))

    def test_unknown_top_key(self):
        cfg = self.cfg()
        cfg["projectss"] = []
        self.assert_exit(cfg, "顶层出现未知键")

    def test_unknown_content_key(self):
        cfg = self.cfg()
        cfg["content"]["project"] = []
        self.assert_exit(cfg, "content 段出现未知键")

    def test_top_only_key_misplaced(self):
        cfg = self.cfg()
        cfg["content"]["card"] = cfg.pop("card")
        self.assert_exit(cfg, "属于顶层键")

    def test_unknown_asset_key(self):
        cfg = self.cfg()
        cfg["content"]["projects"][0]["fig"] = "nope"
        self.assert_exit(cfg, "没有的资源键")

    def test_missing_file(self):
        cfg = self.cfg()
        cfg["images"]["fig_1"]["src"] = os.path.join(self.tmp, "nope.png")
        self.assert_exit(cfg, "素材缺失")

    def test_token_mismatch(self):
        """模板里写了一个 texts 段没有的 token —— 必须报错而不是留脏 token。"""
        tpl = open(os.path.join(SKILL, "assets", "template.html"), encoding="utf-8").read()
        broken = os.path.join(self.tmp, "skill")
        os.makedirs(os.path.join(broken, "assets"))
        open(os.path.join(broken, "assets", "template.html"), "w", encoding="utf-8").write(
            tpl.replace("{{TAGLINE}}", "{{TAGLINE_X}}"))
        with self.assertRaises(SystemExit) as cm:
            B.build(self.cfg(), broken)
        self.assertIn("TAGLINE_X", str(cm.exception))


# =============================================================== D. 编码工具
class TestEncoding(Base):

    def test_split_tags_keeps_slash_words(self):
        self.assertEqual(B.split_tags("Java / CI/CD / ASR/TTS"),
                         ["Java", "CI/CD", "ASR/TTS"])
        self.assertEqual(B.split_tags("Java/Python"), ["Java", "Python"])

    def test_truthy(self):
        """空 / 全空白 / 空容器 = 空；列表按「有任一非空元素」判定（[0] 视为无内容）。"""
        for v in (None, "", "  ", [], {}, [""], [0]):
            self.assertFalse(B.truthy(v), repr(v))
        for v in ("x", ["0"], {"a": "b"}, 1, [["0", "", ""]]):
            self.assertTrue(B.truthy(v), repr(v))

    def test_esc(self):
        self.assertEqual(B.esc('a<b>&"c"'), "a&lt;b&gt;&amp;&quot;c&quot;")

    def test_png8_smaller_than_lossless(self):
        """技术分层图走 PNG8 量化：体积必须真的降下来，否则这个开关没意义。"""
        src = os.path.join(self.tmp, "flat.png")
        im = Image.new("RGB", (900, 600), (255, 255, 255))
        for i in range(12):
            for x in range(20, 880):
                for y in range(20 + i * 46, 40 + i * 46):
                    im.putpixel((x, y), (30 + i * 15, 90, 200))
        im.save(src)
        _u1, raw1 = B.to_data_uri(src, passthrough=True)
        _u2, raw2 = B.to_data_uri(src, png8=True)
        self.assertLess(len(raw2), len(raw1))

    def test_passthrough_keeps_bytes(self):
        raw = open(self.img, "rb").read()
        uri, out = B.to_data_uri(self.img, passthrough=True)
        self.assertEqual(raw, out)
        self.assertTrue(uri.startswith("data:image/png;base64,"))

    def test_col_class(self):
        self.assertEqual(B.col_class(4), "")
        self.assertEqual(B.col_class(3), " c3")
        self.assertEqual(B.col_class(2), " c2")
        self.assertEqual(B.col_class(1), "")


if __name__ == "__main__":
    unittest.main()
