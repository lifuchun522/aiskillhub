# -*- coding: utf-8 -*-
"""
add_slides.py —— 把「每一页 PPT 占据的时间段」写进 props.json 的 slides 字段（分屏版式靠它切页）

两种给法，二选一：
  --starts     每页的起始段号，逗号分隔： 0,2,5,11,...
  --page-segs  每页包含几段，逗号分隔：    2,3,6,4,...（自动累加成 starts，更不容易算错）

段落时点全部取自 segments.json 的**实测值**，页边界严格落在段落边界上，
不按字数估算——否则页会提前或滞后切换，越到后面越明显。

铁律（脚本会拦）：
  · 起点个数必须等于页数，否则整片从错位那一页起全歪；
  · 第一页必须从 0 开始；
  · 每个起点的段落必须真实存在。

用法：
  python add_slides.py --props <project>/props_d1.json --segments segments.json \
      --starts 0,2,5,11,15 --src-prefix slides_d1/p --pages 5 --ext jpg
  python add_slides.py ... --page-segs 2,3,6,4,5        # 等价写法
"""
import argparse
import json
import sys

ap = argparse.ArgumentParser()
ap.add_argument('--props', required=True)
ap.add_argument('--segments', required=True)
ap.add_argument('--starts', default='', help='每页起始段号，逗号分隔')
ap.add_argument('--page-segs', default='', help='每页包含的段数，逗号分隔（与 --starts 二选一）')
ap.add_argument('--src-prefix', required=True, help='如 slides_d1/p')
ap.add_argument('--pages', type=int, required=True, help='PPT 页数（必须等于页图张数）')
ap.add_argument('--digits', type=int, default=2)
ap.add_argument('--ext', default='png', help='页图扩展名：png / jpg')
a = ap.parse_args()

seg = json.load(open(a.segments, encoding='utf-8'))
props = json.load(open(a.props, encoding='utf-8'))
segs = seg['segments']
total = seg['total']

if a.page_segs:
    counts = [int(x) for x in a.page_segs.split(',') if x.strip()]
    starts, acc = [], 0
    for c in counts:
        starts.append(acc)
        acc += c
    if acc != len(segs):
        print('[x] 每页段数之和 %d ≠ 实际段数 %d（差 %+d）' % (acc, len(segs), len(segs) - acc))
        sys.exit(2)
elif a.starts:
    starts = [int(x) for x in a.starts.split(',') if x.strip()]
else:
    sys.exit('[x] 需要 --starts 或 --page-segs')

if len(starts) != a.pages:
    print('[x] 起点 %d 个 ≠ 页数 %d。先数清页图张数，再定同样多的起点。'
          % (len(starts), a.pages))
    print('    已给起点：%s' % ','.join(str(x) for x in starts))
    sys.exit(2)
if starts[0] != 0:
    sys.exit('[x] 第一页必须从段 0 开始，收到 %d' % starts[0])
if any(s >= len(segs) for s in starts):
    sys.exit('[x] 有起点超出段数范围（共 %d 段）' % len(segs))

slides = []
for k, s0 in enumerate(starts):
    start = segs[s0]['start']
    if k + 1 < len(starts):
        nxt = starts[k + 1]
        prev_end = segs[nxt - 1]['end'] if nxt - 1 >= s0 else start
        end = max(prev_end, start + 0.1)
    else:
        end = total
    src = '%s%0*d.%s' % (a.src_prefix, a.digits, k + 1, a.ext)
    slides.append({'start': round(start, 3), 'end': round(end, 3),
                   'src': src, 'index': k + 1})

props['slides'] = slides
json.dump(props, open(a.props, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('注入 %d 页（对照每页首段，确认讲的就是这张图）：' % len(slides))
for s, s0 in zip(slides, starts):
    print('  P%-2d %7.2f ~ %7.2f  段%-3d %s'
          % (s['index'], s['start'], s['end'], s0, segs[s0]['text'][:34]))
print('\n[√] 末页结束于 %.1f 秒（音频总长 %.1f）' % (slides[-1]['end'], total))
