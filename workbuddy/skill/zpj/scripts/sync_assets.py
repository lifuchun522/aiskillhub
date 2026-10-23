# -*- coding: utf-8 -*-
"""zpj · 把 assets/template.html 与 examples/demo-content.json 注入 assets/form.html

为什么要同步而不是让表单去读文件？
  表单必须在 file:// 下双击可用 —— fetch/XHR 读本地文件会被浏览器的同源策略拦掉。
  所以模板与示例数据都以字符串常量的形式内联在表单里；这个脚本负责把「单一事实来源」
  （assets/template.html / examples/demo-content.json）搬进那两个标记区：

      /*@TPL-START@*/  const TPL = "...";   /*@TPL-END@*/
      /*@DEMO-START@*/ const DEMO = {...};  /*@DEMO-END@*/

  这样「表单里预览出来的页面」和「命令行构建出来的页面」用的是同一份模板；
  两边一旦漂移，tests/ 与 verify 的 --check 会立刻报出来。

用法：
    python sync_assets.py            # 注入
    python sync_assets.py --check    # 只校验是否已同步（CI / 测试用，未同步退出码 1）
"""
import argparse
import hashlib
import json
import os
import re
import sys

TPL_START, TPL_END = "/*@TPL-START@*/", "/*@TPL-END@*/"
DEMO_START, DEMO_END = "/*@DEMO-START@*/", "/*@DEMO-END@*/"


def js_literal(text):
    """Python 字符串 -> 可直接写进 JS 源码的字面量。

    ensure_ascii=False 保留中文（表单是 UTF-8 文档，纯 \\uXXXX 会让文件大 3 倍）；
    再把 "</" 转义成 "<\\/"，否则模板里的 </script> 会提前闭合宿主 <script> 元素。
    """
    return json.dumps(text, ensure_ascii=False).replace("</", "<\\/")


def inject(doc, start, end, literal, decl):
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(doc):
        sys.exit("[同步失败] 找不到标记区 %s … %s" % (start, end))
    return pat.sub(lambda _m: "%s\n%s\n%s" % (start, decl + literal + ";", end), doc, count=1)


def extract(doc, start, end):
    pat = re.compile(re.escape(start) + r"\s*(.*?)\s*" + re.escape(end), re.S)
    m = pat.search(doc)
    return m.group(1) if m else None


def digest(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill-dir",
                    default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--check", action="store_true", help="只校验，不写入")
    args = ap.parse_args()

    sk = args.skill_dir
    form_p = os.path.join(sk, "assets", "form.html")
    tpl_p = os.path.join(sk, "assets", "template.html")
    demo_p = os.path.join(sk, "examples", "demo-content.json")

    form = open(form_p, encoding="utf-8").read()
    tpl = open(tpl_p, encoding="utf-8").read()
    demo = None
    if os.path.exists(demo_p):
        demo = json.load(open(demo_p, encoding="utf-8"))

    want_tpl = "const TPL = " + js_literal(tpl)
    want_demo = "const DEMO = " + js_literal(demo if demo is not None else None)

    have_tpl, have_demo = extract(form, TPL_START, TPL_END), extract(form, DEMO_START, DEMO_END)
    # 比较「解出来的字面量」而不是整行 —— 行尾空格 / 换行差异不该算不同步
    ok_tpl = have_tpl is not None and json.loads(have_tpl[len("const TPL = "):].rstrip(";")) == tpl
    ok_demo = (have_demo is not None and
               json.loads(have_demo[len("const DEMO = "):].rstrip(";")) == demo)

    if args.check:
        print("template.html  ->  form.html : %s（md5 %s）"
              % ("已同步" if ok_tpl else "未同步", digest(tpl)))
        print("demo-content.json -> form.html : %s%s"
              % ("已同步" if ok_demo else "未同步",
                 "" if demo is not None else "（无示例文件，允许 DEMO=null）"))
        if not ok_tpl or not ok_demo:
            print("\n请运行：python scripts/sync_assets.py")
            sys.exit(1)
        print("\nPASS: 表单与模板 / 示例数据一致")
        return

    out = inject(form, TPL_START, TPL_END, js_literal(tpl), "const TPL = ")
    out = inject(out, DEMO_START, DEMO_END, js_literal(demo if demo is not None else None),
                 "const DEMO = ")
    open(form_p, "w", encoding="utf-8").write(out)

    print("注入 template.html      %7.1f KB  md5 %s" % (len(tpl) / 1024, digest(tpl)))
    print("注入 demo-content.json  %7.1f KB  %s"
          % ((len(json.dumps(demo, ensure_ascii=False)) / 1024) if demo else 0,
             "有" if demo else "无（DEMO=null）"))
    print("form.html 现在 %.1f KB" % (os.path.getsize(form_p) / 1024))
    print("\nOK ->", form_p)


if __name__ == "__main__":
    main()
