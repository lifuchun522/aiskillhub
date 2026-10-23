# -*- coding: utf-8 -*-
"""jl-zpj · 阶段 6：打包交付

把作品集目录打成 zip，并做完整性校验：
  - 目录条目排序稳定（同一输入 -> 同一 zip）
  - testzip() 校验 CRC
  - 打印逐文件清单与体积，便于交付前核对

用法：
    python package.py <作品集目录> [--zip <输出 zip 路径>]

默认 zip 名 = <作品集目录名>.zip，落在作品集目录的上一级。
"""
import argparse
import os
import sys
import zipfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="作品集目录")
    ap.add_argument("--zip", dest="zip_path", default="")
    args = ap.parse_args()

    src = os.path.abspath(args.src.rstrip("/\\"))
    if not os.path.isdir(src):
        sys.exit("不是目录：%s" % src)
    base = os.path.basename(src)
    zip_path = args.zip_path or os.path.join(os.path.dirname(src), base + ".zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)

    items = []
    for dp, _dn, fns in os.walk(src):
        for fn in fns:
            fp = os.path.join(dp, fn)
            arc = os.path.join(base, os.path.relpath(fp, src)).replace("\\", "/")
            items.append((fp, arc))
    items.sort(key=lambda x: x[1])

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for fp, arc in items:
            z.write(fp, arc)

    size_mb = os.path.getsize(zip_path) / 1024 / 1024
    print("zip   : %s  (%.2f MB / %d files)" % (zip_path, size_mb, len(items)))
    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        print("完整性: %s" % (bad or "OK（CRC 全通过）"))
        for i in z.infolist():
            print("  %-62s %8.1f KB" % (i.filename, i.file_size / 1024))
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
