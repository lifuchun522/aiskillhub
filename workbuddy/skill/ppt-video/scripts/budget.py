#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
budget.py —— 时长预算计算器：把「想要多长」换算成「能写多少字、分几段、每页几段」

口径（写死在技能里，避免每次重新拍脑袋）：
  · 询问的时长 = **1.2 倍速成片的时长**（交付主推版）
  · 原速时长 = 目标时长 × 1.2
  · 云扬 +6% 实测约 292 字/分钟（原速）→ 1.2 倍速下约 350 字/分钟
  · 所以：字数预算 = 目标分钟 × 1.2 × 292 ≈ 目标分钟 × 350
  · 段落：每段 45~70 字，平均约 48 字 → 段数 ≈ 字数 ÷ 48

规则：
  · 目标时长必须落在 5~20 分钟；
  · 用户不指定 → 默认按 15 分钟上限（1.2 倍速版 ≤ 15 分钟，且不低于 5 分钟）。

用法：
  python budget.py --pages 34                      # 未指定时长
  python budget.py --pages 34 --minutes 18
  python budget.py --pages 34 --script script.txt  # 写完稿后实测校验
  python budget.py --pages 34 --segments segments.json   # 配音后实测校验
"""
import argparse
import json
import os
import sys

CPM = 292.0          # 原速每分钟字数（云扬 +6% 实测）
MIN_MIN, MAX_MIN = 5.0, 20.0
DEFAULT_CAP = 15.0   # 未指定时的 1.2 倍速上限
SPEED = 1.2


def load_script(path):
    s = open(path, encoding='utf-8').read()
    paras = [p.strip() for p in s.split('\n\n') if p.strip()]
    chars = len(''.join(s.split()))
    return len(paras), chars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', type=int, required=True, help='PPT 页数')
    ap.add_argument('--minutes', type=float, default=0,
                    help='目标时长（1.2 倍速版，分钟）。不填则按默认上限 15 分钟')
    ap.add_argument('--script', default='', help='逐字稿，用于实测字数校验')
    ap.add_argument('--segments', default='', help='segments.json，用于实测时长校验')
    a = ap.parse_args()

    pages = a.pages
    specified = a.minutes > 0
    target = a.minutes if specified else DEFAULT_CAP

    print('=' * 58)
    print('时长预算（口径：1.2 倍速版）')
    print('=' * 58)
    if specified:
        if not (MIN_MIN <= target <= MAX_MIN):
            print('[x] 目标时长 %.1f 分钟超出允许区间：必须落在 %.0f~%.0f 分钟之间。'
                  % (target, MIN_MIN, MAX_MIN))
            print('    请回问用户重新给一个 5~20 分钟的值，或选择「不指定」。')
            sys.exit(2)
        print('目标时长      : %.1f 分钟（1.2 倍速版，用户指定）' % target)
    else:
        print('目标时长      : 未指定 → 上限 %.1f 分钟（1.2 倍速版，且不低于 %.0f 分钟）'
              % (DEFAULT_CAP, MIN_MIN))

    orig = target * SPEED
    chars = target * SPEED * CPM
    segs = chars / 48.0
    print('原速时长约    : %.1f 分钟' % orig)
    print('字数预算      : %.0f 字（区间 %.0f ~ %.0f）' % (chars, chars * 0.88, chars * 1.08))
    print('段落预算      : %.0f 段（每段 45~70 字）' % segs)
    print('页数          : %d 页 → 平均每页 %.1f 段 / %.0f 字'
          % (pages, segs / pages, chars / pages))
    if chars / pages < 40:
        print('[!] 每页不足 40 字：34 页这种大 deck 会很赶。要么接受「每页只讲一句」，')
        print('    要么和用户确认合并页面、或放宽时长。')
    print()

    # 均分骨架：只作初稿参考，实际起点必须按内容归属定
    n = max(1, round(segs))
    per = n / pages
    starts, acc = [], 0.0
    for k in range(pages):
        starts.append(int(round(acc)))
        acc += per
    print('段落起点骨架（均分，仅供起草；最终必须按「这段话在讲哪一页」重排）：')
    print('  ' + ','.join(str(x) for x in starts))
    print('  末页结束段号 ≈ %d' % n)
    print()

    ok = True
    if a.script and os.path.isfile(a.script):
        ps, ch = load_script(a.script)
        est_o = ch / CPM
        est_f = est_o / SPEED
        print('实测（逐字稿 %s）：%d 段 / %d 字' % (os.path.basename(a.script), ps, ch))
        print('  预计 1.2 倍速 %.2f 分钟 / 原速 %.2f 分钟' % (est_f, est_o))
        if not (MIN_MIN <= est_f <= (target if specified else DEFAULT_CAP) + 0.3):
            print('  [x] 超出预算：目标 %.1f 分钟，预计 %.2f 分钟（差 %+.2f）'
                  % (target, est_f, est_f - target))
            print('      调整量：%+d 字' % int((target - est_f) * SPEED * CPM))
            ok = False
        else:
            print('  [√] 落在预算内')
        print('  平均每段 %.1f 字' % (ch / max(1, ps)))
        print()

    if a.segments and os.path.isfile(a.segments):
        d = json.load(open(a.segments, encoding='utf-8'))
        total = d['total']
        print('实测（配音 %s）：%d 段 / 原速 %.2f 分钟 / 1.2 倍速 %.2f 分钟'
              % (os.path.basename(a.segments), len(d['segments']), total / 60, total / 60 / SPEED))
        if not (MIN_MIN <= total / 60 / SPEED <= MAX_MIN):
            print('  [x] 1.2 倍速成片 %.2f 分钟，超出 %.0f~%.0f 分钟区间'
                  % (total / 60 / SPEED, MIN_MIN, MAX_MIN))
            ok = False
        else:
            print('  [√] 落在 %.0f~%.0f 分钟区间' % (MIN_MIN, MAX_MIN))
        print('  总帧数（30fps）= %d' % (int(total * 30) + 1))

    sys.exit(0 if ok else 3)


if __name__ == '__main__':
    main()
