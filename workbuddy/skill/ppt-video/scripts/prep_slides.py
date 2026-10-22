#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
prep_slides.py —— 页图规范化：导出目录 → 工程 public/slides_xx/p01.jpg ...

做三件事：
  1) 按「页码数字」自然排序（幻灯片1、幻灯片10 不会排成 1,10,2）；
  2) 复制并改名成 p01..pNN（两位数，与 add_slides.py 的默认 digits=2 对齐）；
  3) 逐页体检：尺寸是否 16:9、是否有空图、总页数是否与预期一致。

⚠️ 页数 N 是后面「页时间轴」的唯一依据：先数清楚 N，再定 N 个起点。
   少一页/多一页，整片从那一页开始全部错位（本技能最难返工的错）。

用法：
  python prep_slides.py --src ./slides --project ../project --tag d1
  python prep_slides.py --src ./slides --project ../project --tag d1 --expect 14
"""
import argparse
import json
import os
import re
import shutil
import sys

EXT = ('.png', '.jpg', '.jpeg')


def natural_key(name):
    m = re.findall(r'(\d+)', os.path.splitext(name)[0])
    return (int(m[-1]) if m else 0, name)


def size_of(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:  # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='导出页图所在目录')
    ap.add_argument('--project', required=True, help='Remotion 工程目录（页图放它的 public/ 下）')
    ap.add_argument('--tag', required=True, help='页图子目录后缀，如 d1 → public/slides_d1')
    ap.add_argument('--expect', type=int, default=0, help='预期页数，用于校验')
    ap.add_argument('--digits', type=int, default=2)
    a = ap.parse_args()

    files = [f for f in os.listdir(a.src)
             if f.lower().endswith(EXT) and not f.startswith('.')]
    if not files:
        raise SystemExit('[x] %s 里没有图片（支持 %s）' % (a.src, '/'.join(EXT)))
    files.sort(key=natural_key)

    ext = os.path.splitext(files[0])[1].lower().lstrip('.')
    dst_dir = os.path.join(a.project, 'public', 'slides_%s' % a.tag)
    os.makedirs(dst_dir, exist_ok=True)
    # 清掉旧的 p*.jpg，避免上一次多出来的页残留
    for old in os.listdir(dst_dir):
        if re.match(r'^p\d+\.\w+$', old):
            os.remove(os.path.join(dst_dir, old))

    manifest, bad = [], []
    for i, f in enumerate(files, 1):
        src = os.path.join(a.src, f)
        name = 'p%0*d.%s' % (a.digits, i, ext)
        shutil.copy2(src, os.path.join(dst_dir, name))
        wh = size_of(src)
        ratio = (wh[0] / wh[1]) if wh else 0
        flag = ''
        if wh and abs(ratio - 16 / 9) > 0.02:
            flag = '  ← 非 16:9（%.3f）' % ratio
            bad.append((i, wh, ratio))
        manifest.append({'page': i, 'file': name, 'src': f,
                         'width': wh[0] if wh else 0,
                         'height': wh[1] if wh else 0})
        print('  P%-3d %-14s ← %s  %s%s' % (
            i, name, f, ('%dx%d' % wh) if wh else '尺寸未知', flag))

    n = len(files)
    print('\n[√] 共 %d 页 → %s' % (n, dst_dir))
    if bad:
        print('[!] %d 页不是 16:9，右栏会留黑边（不影响讲解，但建议重新导出 16:9）' % len(bad))
    if a.expect and a.expect != n:
        print('[x] 页数不符：预期 %d，实际 %d。先查清缺页/多页，否则页时间轴必然错位。'
              % (a.expect, n))
        sys.exit(2)

    mf = os.path.join(dst_dir, 'manifest.json')
    with open(mf, 'w', encoding='utf-8') as fp:
        json.dump({'count': n, 'ext': ext, 'digits': a.digits,
                   'src_prefix': 'slides_%s/p' % a.tag, 'pages': manifest},
                  fp, ensure_ascii=False, indent=1)
    print('[i] 清单：%s' % mf)
    print('[i] 下一步页时间轴用：--src-prefix slides_%s/p --pages %d --ext %s'
          % (a.tag, n, ext))


if __name__ == '__main__':
    main()
