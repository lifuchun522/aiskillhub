#!/usr/bin/env python3
"""三源枚举：从源码 / 接口 / UI 提取项目特性清单，输出 Markdown。

用法:
    python enum_features.py <repo-dir> [--api http://127.0.0.1:8080] [--depth 2]
"""
import argparse
import ast
import json
import os
import re
import sys
import urllib.request

SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".idea", ".vscode",
        "storage", "dist", "build", ".pytest_cache", ".mypy_cache", "output"}


def tree(root, depth=2):
    lines = []

    def walk(d, prefix, level):
        try:
            entries = sorted(
                [e for e in os.listdir(d) if e not in SKIP and not e.startswith(".git")],
                key=lambda x: (not os.path.isdir(os.path.join(d, x)), x.lower()),
            )
        except PermissionError:
            return
        if level > depth:
            return
        for i, name in enumerate(entries):
            p = os.path.join(d, name)
            last = i == len(entries) - 1
            lines.append(prefix + ("└── " if last else "├── ") + name +
                         ("/" if os.path.isdir(p) else ""))
            if os.path.isdir(p):
                walk(p, prefix + ("    " if last else "│   "), level + 1)

    lines.append(os.path.basename(os.path.abspath(root)) + "/")
    walk(root, "", 1)
    return "\n".join(lines)


def py_files(root, sub):
    d = os.path.join(root, sub)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith(".py") and f != "__init__.py")


def scan_specs(root):
    """抓注册表声明，如 XxxSpec("id", ...)。

    用 ast 而非正则：正则会把 docstring / 注释里的示例也计入（实测漏算 1 项误报），
    ast 只认真实调用表达式。
    """
    suffixes = ("Spec", "Provider", "Registry", "Adapter")
    ident = re.compile(r"^[a-z0-9_.\-]+$")
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            try:
                src = open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
                tree = ast.parse(src)
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if not name or not name.endswith(suffixes):
                    continue
                a0 = node.args[0]
                if (isinstance(a0, ast.Constant) and isinstance(a0.value, str)
                        and ident.match(a0.value)):
                    found.setdefault(name, []).append(a0.value)
    return {k: sorted(set(v)) for k, v in found.items()}


def scan_routes(root):
    """两种声明方式都要扫：@router.get(...) 装饰器 与 router.add_api_route(..., methods=[...])。"""
    pat_deco = re.compile(r'@\w+\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']')
    pat_add = re.compile(
        r'\.add_api_route\(\s*["\']([^"\']+)["\'][^)]*?methods\s*=\s*\[([^\]]*)\]', re.S)
    routes = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            try:
                s = open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in pat_deco.finditer(s):
                routes.append((m.group(1).upper(), m.group(2), rel))
            for m in pat_add.finditer(s):
                for verb in re.findall(r'["\'](\w+)["\']', m.group(2)):
                    routes.append((verb.upper(), m.group(1), rel))
    return sorted(set(routes), key=lambda x: (x[1], x[0]))


def scan_ui_labels(root):
    """猜 UI 文件里的可见文案（Streamlit/Gradio），供整理控件清单。"""
    cands = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        if "webui" not in dirpath.lower() and "ui" not in os.path.basename(dirpath).lower():
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                cands.append(os.path.relpath(os.path.join(dirpath, fn), root))
    return sorted(set(cands))


def fetch_openapi(url):
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/openapi.json", timeout=15) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        return None, f"抓取失败: {e}"
    rows = []
    for path, ops in sorted(d.get("paths", {}).items()):
        for method, op in ops.items():
            rows.append((method.upper(), path, (op.get("summary") or "")[:70]))
    title = d.get("info", {}).get("title", "")
    version = d.get("info", {}).get("version", "")
    return (f"{title} {version}", rows), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--api", default="", help="运行中的服务地址，用于抓 openapi.json")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--out", default="feature-enum.md", help="Markdown 输出路径")
    a = ap.parse_args()

    root = a.repo.rstrip("/\\")
    out = []
    out.append(f"# 特性枚举 · {os.path.basename(os.path.abspath(root))}\n")

    out.append("## 1. 目录结构（深度 %d）\n```\n%s\n```\n" % (a.depth, tree(root, a.depth)))

    svc = [s for s in ("app/services", "src/services", "services", "internal", "pkg") if os.path.isdir(os.path.join(root, s))]
    if svc:
        out.append("## 2. 服务 / 模块层\n")
        for s in svc:
            out.append(f"**{s}/** — {len(py_files(root, s))} 个模块")
            out.append("```\n" + "\n".join(py_files(root, s)) + "\n```\n")

    specs = scan_specs(root)
    if specs:
        out.append("## 3. 注册表 / Provider 声明（可插拔点）\n")
        for k, v in specs.items():
            out.append(f"**{k}** — {len(v)} 项\n```\n" + "\n".join(v) + "\n```\n")

    routes = scan_routes(root)
    if routes:
        out.append("## 4. 源码中的路由声明\n")
        out.append("| 方法 | 路径 | 文件 |")
        out.append("|---|---|---|")
        for m, p, f in routes:
            out.append(f"| {m} | `{p}` | `{f}` |")
        out.append("")

    ui = scan_ui_labels(root)
    if ui:
        out.append("## 5. UI 层入口（去浏览器里读控件标签）\n")
        out.append("```\n" + "\n".join(ui) + "\n```\n")

    if a.api:
        res, err = fetch_openapi(a.api)
        out.append("## 6. 运行时接口清单（openapi.json）\n")
        if err:
            out.append(f"> {err}\n")
        else:
            title, rows = res
            paths = {p for _, p, _ in rows}
            out.append(f"**{title}** — {len(paths)} 条路径 / {len(rows)} 个方法级端点\n")
            out.append("| 方法 | 路径 | 摘要 |")
            out.append("|---|---|---|")
            for m, p, s in rows:
                out.append(f"| {m} | `{p}` | {s} |")
            out.append("")

    text = "\n".join(out)
    path = os.path.abspath(a.out)
    open(path, "w", encoding="utf-8").write(text)
    print(text)
    print(f"\n[saved] {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
