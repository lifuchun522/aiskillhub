"""验证字数边界、内容归属与真实图片路径，不评判文章语义。"""
import importlib.util
import tempfile
import unittest
from pathlib import Path


模块路径 = Path(__file__).resolve().parents[1] / "scripts" / "check_article.py"
规格 = importlib.util.spec_from_file_location("dhg_check", 模块路径)
检查器 = importlib.util.module_from_spec(规格)
规格.loader.exec_module(检查器)


class 文章检查测试(unittest.TestCase):
    def test_字数不计图片和链接地址(self):
        文本 = "# 题目\n\n[书名](https://example.org/long-address)\n\n![图片说明](图片/现场.jpg)"
        self.assertEqual(检查器.count_text(文本), len("题目书名"))

    def test_标点和英文计入字数(self):
        self.assertEqual(检查器.count_text("**AI：** 先答。\n再解释"), len("AI：先答。再解释"))

    def test_总字数边界(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            self.assertFalse(检查器.analyze("中" * 1500, Path(临时目录))["错误"])
            self.assertTrue(检查器.analyze("中" * 1501, Path(临时目录))["错误"])

    def test_回答边界和多行段落(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            目录 = Path(临时目录)
            正常 = 检查器.analyze("**老师答：**" + "答" * 50 + "\n" + "答" * 50, 目录)
            超限 = 检查器.analyze("**老师答：**" + "答" * 101, 目录)
            self.assertEqual(正常["回答字数"], [100])
            self.assertFalse(正常["错误"])
            self.assertTrue(超限["错误"])

    def test_个人判断与老师回答分开计数(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            结果 = 检查器.analyze("**老师答：**答案。\n\n**老李思考：**我的判断。", Path(临时目录))
            self.assertEqual(结果["回答字数"], [3])
            self.assertEqual(结果["思考字数"], [5])

    def test_会后要点边界(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            目录 = Path(临时目录)
            self.assertFalse(检查器.analyze("**① " + "字" * 99 + "**", 目录)["错误"])
            self.assertTrue(检查器.analyze("**① " + "字" * 100 + "**", 目录)["错误"])

    def test_缺图失败而真实图片路径通过(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            目录 = Path(临时目录)
            (目录 / "现场.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            self.assertFalse(检查器.analyze("![现场](现场.png)", 目录)["错误"])
            self.assertTrue(检查器.analyze("![不存在](缺失.png)", 目录)["错误"])

    def test_远程图片保留未验证状态(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            结果 = 检查器.analyze("![远程图](https://example.org/a.png)", Path(临时目录))
            self.assertIn("远程图片未验证", " ".join(结果["需复核"]))

    def test_空稿失败(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            self.assertTrue(检查器.analyze("   \n", Path(临时目录))["错误"])

    def test_会后节自定义标签不能漏检(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            结果 = 检查器.analyze("## 会后交流\n\n**连接与合作：**" + "字" * 101, Path(临时目录))
            self.assertEqual(结果["会后要点字数"], [107])
            self.assertTrue(结果["错误"])

    def test_离开会后节不误判其他粗体段落(self):
        with tempfile.TemporaryDirectory() as 临时目录:
            结果 = 检查器.analyze("## 会后交流\n\n**连接：**短句。\n\n## 总结\n\n**行动：**" + "字" * 101, Path(临时目录))
            self.assertEqual(结果["会后要点字数"], [6])
            self.assertFalse(结果["错误"])


if __name__ == "__main__":
    unittest.main()
