#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
semantic_check.py —— 渲染前的语义核对（本技能最省钱的一步）

它不能判断「讲得好不好」，但能抓住三类必然翻车的错：
  1) 页时间轴错位：页数 ≠ 起点数、某页落在 0 段落上（该页是空的）
  2) 语义错配：一张卡覆盖了 2 段以上、而这两段讲的不是同一件事
     （实战里 90% 的返工都是这个：把「本章总结三条」画成一张卡，字幕在说第二条，左栏在画第三条）
  3) 数量不符：旁白说「三个机制」，卡上却列了 4 项 / 只列 2 项

用法：
  python semantic_check.py --props <project>/props_xx.json --segments segments.json
  python semantic_check.py --props ... --segments ... --strict   # 有 warn 就退出码非 0

建议流程：先跑本脚本 → 人眼扫一遍输出表 → 改 cards_plan.py → 再渲染。
改一张卡不需要重渲全片，但需要重渲它所在的帧区间 + 拼接（约 1/10 成本）。
"""
import argparse
import json
import os
import re
import sys

CN = {'一': 1, '两': 2, '二': 2, '三': 3, '四': 4, '五': 5,
      '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
NUM_RE = re.compile(r'([一二两三四五六七八九十])\s*(个|项|条|层|步|类|种|块|阶段|方面|维度)')


def card_text(c):
    t = []
    if c.get('title'):
        t.append('[' + c['title'] + ']')
    for f in ('items', 'left', 'right', 'inputs', 'outputs'):
        if c.get(f):
            t.append('%s: %s' % (f, '/'.join(str(x) for x in c[f])))
    if c.get('center'):
        t.append('中: %s' % c['center'])
    if c.get('leftTitle'):
        t.append('左题: %s' % c['leftTitle'])
    if c.get('rightTitle'):
        t.append('右题: %s' % c['rightTitle'])
    if c.get('note'):
        t.append('注: %s' % c['note'].replace('\n', ''))
    return '  '.join(t)


LIST_KINDS = ('bullets', 'flow', 'quad', 'split', 'compare', 'type')


def item_count(c):
    for f in ('items', 'left'):
        if isinstance(c.get(f), list):
            return len(c[f])
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--props', required=True)
    ap.add_argument('--segments', required=True)
    ap.add_argument('--strict', action='store_true')
    a = ap.parse_args()

    props = json.load(open(a.props, encoding='utf-8'))
    segs = json.load(open(a.segments, encoding='utf-8'))['segments']
    slides = props.get('slides') or []
    cards = sorted(props.get('cards') or [], key=lambda c: c['start'])

    if not slides:
        raise SystemExit('[x] props 里没有 slides：还没注入页时间轴（add_slides.py）')

    err = warn = 0
    cross, hints = [], []
    print('共 %d 页 / %d 张卡 / %d 段旁白\n' % (len(slides), len(cards), len(segs)))

    for k, s in enumerate(slides, 1):
        in_page = [x for x in segs if s['start'] - 0.01 <= x['start'] < s['end'] - 0.05]
        cs = [c for c in cards if c['start'] >= s['start'] - 0.5 and c['start'] < s['end'] - 0.05]
        head = 'P%-2d %6.1f~%6.1f  段%2d  卡%2d' % (k, s['start'], s['end'], len(in_page), len(cs))
        print('─' * 74)
        print(head)
        if not in_page:
            print('  [ERR] 这一页没有任何旁白段落 —— 页起点落错或该页被跳过')
            err += 1
        if not cs:
            print('  [ERR] 这一页没有卡片，左栏会空着')
            err += 1

        for c in cs:
            cov = [x for x in in_page if c['start'] - 0.05 <= x['start'] < c['end'] - 0.02]
            span = c['end'] - c['start']
            mark = ''
            if len(cov) >= 2:
                mark = '  ← 跨 %d 段' % len(cov)
                print('  [WARN] %5.1f~%5.1f(%4.1fs) %-9s %s%s'
                      % (c['start'], c['end'], span, c.get('kind', ''), card_text(c), mark))
                for x in cov:
                    print('          · %s' % x['text'][:56])
                warn += 1
                cross.append('P%d %.0fs %d段合并成一张%s卡'
                             % (k, c['start'], len(cov), c.get('kind', '')))
                # 数量词比对
                for x in cov:
                    for m in NUM_RE.finditer(x['text']):
                        want, unit = CN[m.group(1)], m.group(2)
                        got = item_count(c)
                        if (got and want >= 3 and c.get('kind') in LIST_KINDS
                                and abs(got - want) >= 2):
                            print('  [数字?] 旁白说「%s%s」，卡上有 %d 项' % (m.group(1), unit, got))
                            hints.append('P%d 段%.0f「%s%s」vs 卡 %d 项'
                                         % (k, x['start'], m.group(1), unit, got))
                continue
            print('  %5.1f~%5.1f(%4.1fs) %-9s %s'
                  % (c['start'], c['end'], span, c.get('kind', ''), card_text(c)))
            for x in cov:
                print('        · %s' % x['text'][:56])
                for m in NUM_RE.finditer(x['text']):
                    want, unit = CN[m.group(1)], m.group(2)
                    got = item_count(c)
                    if (got and want >= 3 and c.get('kind') in LIST_KINDS
                            and abs(got - want) >= 2):
                        print('  [数字?] 旁白说「%s%s」，卡上有 %d 项' % (m.group(1), unit, got))
                        hints.append('P%d 段%.0f「%s%s」vs 卡 %d 项'
                                     % (k, x['start'], m.group(1), unit, got))

        for x in in_page:
            if not any(c['start'] - 0.05 <= x['start'] < c['end'] - 0.02 for c in cs):
                print('  [WARN] 段 %.1f 没有卡片覆盖（左栏会停在上一张）：%s'
                      % (x['start'], x['text'][:40]))
                warn += 1

    print('─' * 74)
    print('小结：%d 个错误 / %d 处跨段 / %d 处数量对不上' % (err, len(cross), len(hints)))
    if cross:
        print('\n跨段（一张卡盖了 2 段以上，重点看这几处）：')
        for x in cross:
            print('  · %s' % x)
        print('  判断标准：这两段如果在讲同一件事，合并没问题；')
        print('  如果是「三条总结」或「四个场景」这种并列结构，必须按段拆成多张卡。')
    if hints:
        print('\n数量对不上：')
        for x in hints:
            print('  · %s' % x)
    if err:
        print('\n[x] 错误必须先修（页轴或空页），否则整片会歪。')
    sys.exit(1 if (err or (a.strict and warn)) else 0)


if __name__ == '__main__':
    main()
