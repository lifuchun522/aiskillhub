# -*- coding: utf-8 -*-
"""
plan_cards.py —— 把「配图计划表」编译成 cards.json / sections.json，并做结构校验

为什么要有这一层：
  配图时点必须落在**实测语音时点**上（segments.json），而不是按字数估算。
  同时卡片文案有硬性字数上限，超了就会折行溢出画面 —— 这类问题
  渲染 30 分钟后才发现，返工代价极高，所以必须在渲染前一次性校验掉。

计划表是一个 Python 文件，定义 PLAN 与 SECTIONS：

    PLAN = [
        ((段号, 段内起点比例), (段号, 段内终点比例), dict(kind='flow', ...)),
    ]
    SECTIONS = [(段号, '一 · 先看清事实'), ...]

用法：
  python plan_cards.py --segments build/segments.json --plan cards_plan.py \
      --out build/cards.json --sections-out build/sections.json
"""
import argparse
import importlib.util
import json
import os
import sys

# 各类型的必填字段
REQUIRED = {
    'flow': ['title', 'items'],
    'quad': ['title', 'items'],
    'split': ['title', 'center', 'items'],
    'compare': ['title', 'leftTitle', 'left', 'rightTitle', 'right'],
    'map': ['title', 'leftTitle', 'left', 'rightTitle', 'right'],
    'integrate': ['title', 'inputs', 'output'],
    'pyramid': ['title', 'items'],
    'relation': ['title', 'center', 'items'],
    'stat': ['title', 'value'],
    'quote': ['note'],
    'bullets': ['title', 'items'],
}

# 字数上限（1080p、内置字号下超过就会折行/出框）
LIMITS = {
    'items_node': 6,      # flow / pyramid 的节点
    'items_cell': 13,     # quad / split / relation / bullets 的条目
    'items_col': 11,      # compare / map 的单栏条目
    'items_input': 12,    # integrate 的来源
    'center': 8,
    'title': 16,
    'note': 27,
    'value': 8,
    'output': 8,
    'colTitle': 6,
}


# 金字塔最多几层（窄栏可到 6，中置卡 4 层以上会压到别的元素）
PY_MAX = 4


def load_plan(path):
    spec = importlib.util.spec_from_file_location('cards_plan', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, 'PLAN', []), getattr(mod, 'SECTIONS', [])


def check_card(idx, card, problems):
    k = card.get('kind')
    if k not in REQUIRED:
        problems.append('卡片 %d：未知 kind=%r（可选：%s）'
                        % (idx, k, ', '.join(REQUIRED)))
        return
    for f in REQUIRED[k]:
        if not card.get(f):
            problems.append('卡片 %d（%s）：缺字段 %s' % (idx, k, f))

    def too_long(field, text, limit):
        if text and len(str(text)) > limit:
            problems.append('卡片 %d（%s）：%s 超长 %d>%d 字 → %s'
                            % (idx, k, field, len(str(text)), limit, text))

    too_long('title', card.get('title'), LIMITS['title'])
    too_long('center', card.get('center'), LIMITS['center'])
    too_long('note', card.get('note'), LIMITS['note'])
    too_long('value', card.get('value'), LIMITS['value'])
    too_long('output', card.get('output'), LIMITS['output'])
    too_long('leftTitle', card.get('leftTitle'), LIMITS['colTitle'])
    too_long('rightTitle', card.get('rightTitle'), LIMITS['colTitle'])

    lim = LIMITS['items_node'] if k in ('flow', 'pyramid') else \
        LIMITS['items_cell'] if k in ('quad', 'split', 'relation', 'bullets') else \
        LIMITS['items_col'] if k in ('compare', 'map') else LIMITS['items_input']
    for f in ('items', 'left', 'right', 'inputs'):
        for it in (card.get(f) or []):
            too_long(f + '[]', it, lim)

    # 结构量约束：这些类型多一项就排不下
    exact = {'quad': ('items', 4), 'compare': ('left', 4), 'pyramid': ('items', PY_MAX),
             'relation': ('items', 4)}
    if k in exact:
        f, n = exact[k]
        if len(card.get(f) or []) > n:
            problems.append('卡片 %d（%s）：%s 最多 %d 项，当前 %d 项'
                            % (idx, k, f, n, len(card.get(f) or [])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--segments', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', default='cards.json')
    ap.add_argument('--sections-out', default='sections.json')
    ap.add_argument('--narrow', action='store_true',
                    help='分屏窄栏版式（左栏 780px）：flow 节点与列标题整行铺开，'
                         '可容纳的字数比中置卡更多，据此放宽校验')
    args = ap.parse_args()

    if args.narrow:
        # 窄栏里 flow/pyramid 节点是整行一个框、compare 列标题也占整栏宽度，
        # 原来的 6 字上限是按横排 4 列估的，窄栏可放宽到 13 / 12。
        LIMITS['items_node'] = 13
        LIMITS['colTitle'] = 12
        global PY_MAX
        PY_MAX = 6

    segs = json.load(open(args.segments, encoding='utf-8'))['segments']
    total = json.load(open(args.segments, encoding='utf-8')).get('total', 0)
    PLAN, SECTIONS = load_plan(args.plan)

    def at(ref):
        p, frac = ref
        if p >= len(segs):
            raise SystemExit('[x] 计划表引用了第 %d 段，但只有 %d 段' % (p, len(segs)))
        s = segs[p]
        return round(s['start'] + frac * s['dur'], 2)

    problems, cards = [], []
    for i, (a, b, spec) in enumerate(PLAN):
        card = dict(spec)
        card['start'], card['end'] = at(a), at(b)
        if card['end'] <= card['start']:
            problems.append('卡片 %d：时长非正 %.2f~%.2f' % (i, card['start'], card['end']))
        check_card(i, card, problems)
        cards.append(card)

    # 时间单调 & 不重叠
    prev_end = -1
    for i, c in enumerate(cards):
        if c['start'] < prev_end - 0.01:
            problems.append('卡片 %d：与上一张重叠 %.2f < %.2f' % (i, c['start'], prev_end))
        prev_end = c['end']

    if total and cards and cards[-1]['end'] > total + 0.2:
        problems.append('最后一张卡片结束 %.2f 超出音频总长 %.2f' % (cards[-1]['end'], total))

    secs = []
    for p, t in SECTIONS:
        secs.append({'start': round(segs[p]['start'], 2), 'text': t})

    kinds = {}
    for c in cards:
        kinds[c['kind']] = kinds.get(c['kind'], 0) + 1

    print('卡片 %d 张 / 章节 %d 个 / 音频 %.2fs' % (len(cards), len(secs), total))
    print('类型分布：%s' % ', '.join('%s×%d' % kv for kv in sorted(kinds.items())))
    for c in cards:
        print('  %7.2f ~ %7.2f  %-9s %s' % (c['start'], c['end'], c['kind'],
                                            c.get('title') or c.get('note', '')[:24]))

    if problems:
        print('\n[!] 校验发现 %d 个问题，先修计划表再渲染：' % len(problems))
        for p in problems:
            print('  · ' + p)
        sys.exit(1)

    json.dump(cards, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(secs, open(args.sections_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n[√] 校验通过 → %s / %s' % (args.out, args.sections_out))


if __name__ == '__main__':
    main()
