"""检查常规 Markdown 的字数与图片路径；语义与事实仍需独立审稿。"""
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


图片表达式 = re.compile(r"!\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)")
链接表达式 = re.compile(r"\[([^\]]+)\]\([^\s)]+(?:\s+\"[^\"]*\")?\)")


def count_text(text):
    """按非空白 Unicode 字符计数，排除常规 Markdown 标记、图片及URL。"""
    text = 图片表达式.sub("", text)
    text = 链接表达式.sub(r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"(?m)^\s*(?:#{1,6}\s+|>\s*|[-+]\s+|\d+[.)]\s+|```[^\n]*$)", "", text)
    text = re.sub(r"[*`~]", "", text)
    return len(re.sub(r"\s", "", html.unescape(text)))


def _paragraphs(text):
    return re.split(r"\n\s*\n", text.replace("\r\n", "\n"))


def analyze(text, base_dir, max_total=1500, max_answer=100,
            max_reflection=100, max_post=100, author_label="老李思考"):
    """只对实际检测的机械规则返回错误；保留不能自动确定的事项。"""
    result = {"总字数": count_text(text), "回答字数": [], "思考字数": [],
              "会后要点字数": [], "图片": [], "错误": [],
              "需复核": ["人工对照来源、观点归属、回答缺项与数字边界",
                         "人工检查先答后析、生活类比、行动与图片内容"]}
    if not text.strip():
        result["错误"].append("文章为空")
    if result["总字数"] > max_total:
        result["错误"].append(f"正文超限：{result['总字数']} > {max_total}")
    post_section = False
    for paragraph in _paragraphs(text):
        heading = re.match(r"^##(?!#)\s+([^\n]+)", paragraph.strip())
        if heading:
            post_section = bool(re.search(r"会后|圆桌之后|交流感悟", heading.group(1)))
        match = re.match(r"\*\*(老师答|老师回答|嘉宾回答|" + re.escape(author_label)
                         + r")：\*\*(.*)", paragraph.strip(), re.S)
        if match:
            personal = match.group(1) == author_label
            key = "思考字数" if personal else "回答字数"
            limit = max_reflection if personal else max_answer
            length = count_text(match.group(2))
            result[key].append(length)
            if length > limit:
                result["错误"].append(f"{key}第{len(result[key])}段超限：{length} > {limit}")
        numbered = re.match(r"\*\*(?:[①②③④⑤⑥⑦⑧⑨⑩]|\d+[.、])", paragraph.strip())
        labeled_post = post_section and not match and re.match(
            r"\*\*[^*\n]+[：。]\*\*", paragraph.strip())
        if numbered or labeled_post:
            length = count_text(paragraph)
            result["会后要点字数"].append(length)
            if length > max_post:
                result["错误"].append(f"编号要点超限：{length} > {max_post}")
    for match in 图片表达式.finditer(text):
        source = match.group(1)
        parsed = urlsplit(source)
        result["图片"].append(source)
        if parsed.scheme in ("http", "https", "data"):
            result["需复核"].append(f"远程图片未验证：{source}")
        elif not (Path(base_dir) / unquote(source)).is_file():
            result["错误"].append(f"本地图片不存在：{source}")
    if not result["回答字数"] and not result["思考字数"]:
        result["需复核"].append("未识别问答标签；核对是否为纯图文模式或标签格式不同")
    result["范围"] = "仅检查常规Markdown字数、规范标签段落及图片路径存在性；不等于D1—D12或事实审稿通过"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article", type=Path, help="待检查的Markdown文章")
    parser.add_argument("--max-total", type=int, default=1500, help="正文总字数上限")
    parser.add_argument("--max-answer", type=int, default=100, help="每段嘉宾回答上限")
    parser.add_argument("--max-reflection", type=int, default=100, help="每段作者思考上限")
    parser.add_argument("--max-post", type=int, default=100, help="每段编号要点上限（含小标题）")
    parser.add_argument("--author-label", default="老李思考", help="个人思考标签")
    args = parser.parse_args()
    if min(args.max_total, args.max_answer, args.max_reflection, args.max_post) < 1:
        parser.error("所有字数上限必须是正整数")
    try:
        result = analyze(args.article.read_text(encoding="utf-8"), args.article.parent,
                         args.max_total, args.max_answer, args.max_reflection,
                         args.max_post, args.author_label)
    except (OSError, UnicodeError) as error:
        print(json.dumps({"错误": [str(error)]}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["错误"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
