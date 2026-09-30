#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""process_comics.py —— 出图后处理：裁水印 + 归位命名 imgN.png

背景（2026-09-30 新增踩坑）:
  WorkBuddy ImageGen（混元）生成的图，右下角会强制带 "AI生成 / WORKBUDDY" 水印，
  且生成文件名由 prompt 前缀 + 时间戳拼成，前缀相同的两次调用会互相覆盖。
  -> 统一裁掉底部 CROP_BOTTOM 像素去除水印，再按 imgN.png 归位。

用法:
  1. 改下方 MAPPING（源文件名关键词 -> imgN）
  2. python process_comics.py
"""
import io
import os
import sys

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMICS = os.path.join(BASE_DIR, "comics")

CROP_BOTTOM = 90   # 水印高度（1536x1024 原图实测）
TARGET_W = 1080    # 微信正文图统一宽度

# 源文件名关键词 -> 目标序号
MAPPING = [
    ("Cover_artwork__Misty_river_sce", 0),
    ("Modern_minimal_illustration__c", 1),
    ("Traditional_Chinese_ink_wash_p", 2),
    ("Minimal_surreal_illustration___", 3),
    ("Traditional_Chinese_ink_wash_l", 4),
]


def main():
    srcs = sorted(os.listdir(COMICS))
    done = []
    for key, idx in MAPPING:
        cand = [s for s in srcs if s.startswith(key)]
        if not cand:
            print("  [MISS] img%d 未找到源图（关键词 %s）" % (idx, key))
            continue
        src = os.path.join(COMICS, cand[0])
        im = Image.open(src).convert("RGB")
        w, h = im.size
        im = im.crop((0, 0, w, h - CROP_BOTTOM))
        im = im.resize((TARGET_W, int(im.height * TARGET_W / im.width)), Image.LANCZOS)
        out = os.path.join(COMICS, "img%d.png" % idx)
        im.save(out, "PNG", optimize=True)
        done.append(idx)
        print("  img%d <- %s  (%dx%d)" % (idx, cand[0][:38], im.width, im.height))

    print("[OK] 已处理 %d 张 -> %s" % (len(done), COMICS))
    if sorted(done) != list(range(len(MAPPING))):
        print("  [WARN] 序号不连续，检查 MAPPING")


if __name__ == "__main__":
    main()
