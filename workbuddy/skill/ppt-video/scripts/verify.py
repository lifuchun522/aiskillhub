# -*- coding: utf-8 -*-
"""
verify.py —— 交付前自动体检（把「返工才发现」的问题挡在渲染前后）

检查项（任一不过都会列在最后）：
  1. 片头静音   silencedetect 首个事件必须是 silence_start≈0 → silence_end≈lead_in
                （若首个事件是 silence_start: 3.x，说明片头静音没写进音频，
                  字幕会整体错位 lead_in 秒）
  2. 时长一致   音频实测 vs segments.json 规划 vs props.audioDuration
  3. 双轨同步   视频流时长 vs 音频流时长（变速版重点看这个）
  4. 响度       整片 LUFS / 真峰值（语音类建议 -16 ~ -12 LUFS）
  5. 卡片覆盖   每张卡片的中点抽一帧存盘，供肉眼核对版式与字幕对位

用法：
  python verify.py --audio build/final.mp3 --segments build/segments.json
  python verify.py --video out/v.mp4 --segments build/segments.json --frames-dir ./chk
"""
import argparse
import json
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, errors='replace')


def duration(path, sel=''):
    cmd = ['ffprobe', '-v', 'error']
    if sel:
        cmd += ['-select_streams', sel, '-show_entries', 'stream=duration']
    else:
        cmd += ['-show_entries', 'format=duration']
    cmd += ['-of', 'csv=p=0', path]
    r = run(cmd)
    try:
        return float(r.stdout.strip().split(',')[0])
    except Exception:
        return None


def loudness(path):
    r = run(['ffmpeg', '-hide_banner', '-nostats', '-i', path,
             '-af', 'loudnorm=print_format=json', '-f', 'null', '-'])
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr or '', re.S)
    if not m:
        return None, None
    js = json.loads(m.group(0))
    try:
        return float(js['input_i']), float(js['input_tp'])
    except Exception:
        return None, None


def head_silence(path):
    """返回 (第一个 silence_start, 对应的 silence_end)"""
    r = run(['ffmpeg', '-hide_banner', '-nostats', '-i', path,
             '-af', 'silencedetect=n=-38dB:d=0.25', '-f', 'null', '-'])
    txt = r.stderr or ''
    ss = re.search(r'silence_start:\s*([\d.]+)', txt)
    se = re.search(r'silence_end:\s*([\d.]+)', txt)
    return (float(ss.group(1)) if ss else None,
            float(se.group(1)) if se else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--audio', default='')
    ap.add_argument('--video', default='')
    ap.add_argument('--segments', default='')
    ap.add_argument('--props', default='')
    ap.add_argument('--cards', default='')
    ap.add_argument('--frames-dir', default='',
                    help='给了就从视频里按每张卡片中点抽帧，存到这个目录')
    ap.add_argument('--part', action='store_true',
                    help='检查的是片段（--frames 截出来的探针），跳过片头静音判定')
    args = ap.parse_args()

    problems = []
    media = args.video or args.audio
    if not media:
        raise SystemExit('[x] 至少给 --audio 或 --video')
    if not os.path.isfile(media):
        raise SystemExit('[x] 找不到文件：%s' % media)

    plan = {}
    if args.segments and os.path.isfile(args.segments):
        plan = json.load(open(args.segments, encoding='utf-8'))

    # ---- 1. 片头静音 ----
    # 片段（--frames 截出来的探针）从中间开始，本来就没有片头，不能按这项判
    lead = plan.get('leadIn')
    if lead is None and plan.get('segments'):
        lead = plan['segments'][0]['start']   # 旧版 segments 没存 leadIn，用首段起点反推
    if args.part:
        print('片头静音   跳过（--part：检查的是片段）')
    elif lead is None:
        print('片头静音   跳过（未给 segments，无法判断是否完整片）')
    else:
        ss, se = head_silence(media)
        print('片头静音   首个 silence_start=%s  silence_end=%s' % (ss, se))
        if ss is None or ss > 0.4:
            problems.append('片头不是静音（首个 silence_start=%s）：lead-in 没写进音频，'
                            '字幕会整体错位' % ss)
        elif lead and se is not None and abs(se - lead) > 0.5:
            problems.append('片头静音长度 %.2fs 与规划 lead_in %.2fs 不符' % (se, lead))

    # ---- 2. 时长一致 ----
    if args.audio and plan.get('total'):
        d = duration(args.audio)
        print('音频时长   %.3fs（规划 %.3fs，差 %.3fs）'
              % (d or 0, plan['total'], abs((d or 0) - plan['total'])))
        if d and abs(d - plan['total']) > 0.2:
            problems.append('音频实测时长与规划差 %.2fs，时点会整体偏移'
                            % abs(d - plan['total']))

    if args.props and os.path.isfile(args.props) and plan.get('total'):
        p = json.load(open(args.props, encoding='utf-8'))
        print('props      audioDuration=%.3fs  字幕 %d 行  卡片 %d 张'
              % (p.get('audioDuration', 0), len(p.get('lines', [])),
                 len(p.get('cards', []))))
        if abs(p.get('audioDuration', 0) - plan['total']) > 0.2:
            problems.append('props.audioDuration 与 segments 不一致，画面时长会错')

    # ---- 3. 双轨同步 ----
    if args.video:
        vd, ad = duration(args.video, 'v:0'), duration(args.video, 'a:0')
        print('双轨时长   视频 %.3fs / 音频 %.3fs（差 %.3fs）'
              % (vd or 0, ad or 0, abs((vd or 0) - (ad or 0))))
        if vd and ad and abs(vd - ad) > 0.2:
            problems.append('视频流与音频流时长差 %.2fs —— 不是编码尾部 padding，'
                            '要查时轴或变速' % abs(vd - ad))
        print('文件大小   %.1f MB' % (os.path.getsize(args.video) / 1048576))

    # ---- 4. 响度 ----
    i, tp = loudness(media)
    print('响度       %s LUFS / 峰值 %s dBTP' % (i, tp))
    if i is not None:
        if i < -18:
            problems.append('响度 %.1f LUFS 偏小（手机外放明显）→ 用 post.py --lufs -14'
                            % i)
        elif i > -10:
            problems.append('响度 %.1f LUFS 偏大，可能发闷/失真' % i)
    if tp is not None and tp > -0.5:
        problems.append('真峰值 %.1f dBTP 接近 0，可能削波' % tp)

    # ---- 5. 卡片抽帧 ----
    if args.frames_dir and args.video:
        cards = []
        if args.cards and os.path.isfile(args.cards):
            cards = json.load(open(args.cards, encoding='utf-8'))
        elif args.props and os.path.isfile(args.props):
            cards = json.load(open(args.props, encoding='utf-8')).get('cards', [])
        os.makedirs(args.frames_dir, exist_ok=True)
        for i, c in enumerate(cards):
            t = (c['start'] + c['end']) / 2
            dst = os.path.join(args.frames_dir, '%02d_%s_%.0f.jpg' % (i, c['kind'], t))
            run(['ffmpeg', '-y', '-v', 'error', '-ss', '%.2f' % t, '-i', args.video,
                 '-frames:v', '1', '-vf', 'scale=960:-1', '-q:v', '3', dst])
        print('卡片抽帧   %d 张 → %s' % (len(cards), args.frames_dir))

    print('\n=== 结论 ===')
    if problems:
        print('[!] %d 项待处理：' % len(problems))
        for p in problems:
            print('  · ' + p)
        sys.exit(1)
    print('[√] 全部通过')


if __name__ == '__main__':
    main()
