#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
prepare_props.py —— 口播成片前置处理

输入：口播音频（mp3/m4a/wav，或含音轨的 mp4）+ 逐字稿
输出：public/props.json（Remotion 渲染所需的完整 props）+ public/audio.mp3

支持三种逐字稿格式（自动识别）：
  1) 带演讲人+时间戳：  何明璐(00:00:23): 今天讲三件事……
  2) SRT 字幕：         1\\n00:00:01,000 --> 00:00:04,000\\n文本
  3) 纯文本：           按标点切句，按总时长按字数比例分配

时间轴策略（关键）：
  - 有逐字时间戳/SRT 时点时 —— 用真实时点定句子窗口，窗口内再按字数比例切分单行；
  - 无时点时 —— 按全篇字数比例分配，标点位置附加停顿权重；
  - 末尾长静音保护：最后一句按全篇平均语速推算，避免把尾部静音全算给最后一句。

用法：
  python prepare_props.py --audio 口播.mp3 --transcript 逐字稿.txt \
      --project <remotion工程目录> --title "本体论一体化平台" --subtitle "何明璐"
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# ---------------------------------------------------------------- 基础工具


def eprint(*a):
    print(*a, file=sys.stderr)


def read_text(path):
    for enc in ('utf-8-sig', 'utf-8', 'gb18030'):
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise SystemExit(f'[x] 无法解码逐字稿文件：{path}')


def probe_duration(path):
    """用 ffprobe 拿媒体时长（秒）"""
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=nw=1:nk=1', path]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except Exception as e:
        raise SystemExit(f'[x] ffprobe 读取时长失败：{e}\n    请确认已安装 ffmpeg 并加入 PATH')


def ensure_audio(src, public_dir, audio_name):
    """把任意音/视频转成 public/<audio_name>，返回 (文件名, 时长秒)"""
    os.makedirs(public_dir, exist_ok=True)
    dst = os.path.join(public_dir, audio_name)
    ext = os.path.splitext(src)[1].lower()
    # 已存在且大小一致就跳过：受限环境下无法覆盖同名文件，也让重跑变成幂等操作
    if os.path.isfile(dst) and os.path.getsize(dst) > 0:
        try:
            if ext == '.mp3' and os.path.getsize(dst) == os.path.getsize(src):
                return audio_name, probe_duration(dst)
        except OSError:
            pass
        if ext != '.mp3':
            return audio_name, probe_duration(dst)
    if ext == '.mp3':
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)
    else:
        cmd = ['ffmpeg', '-y', '-v', 'error', '-i', src,
               '-vn', '-acodec', 'libmp3lame', '-q:a', '2', dst]
        subprocess.run(cmd, check=True)
    return audio_name, probe_duration(dst)


# ---------------------------------------------------------------- 文本切分

PUNCT = '，。！？；、：,.;:!?）)》」' 
_SENT_SPLIT = re.compile(r'[^，。！？；、：,;:!?]*[，。！？；、：,;:!?]?')


def is_cjk(c):
    return ord(c) > 0x2E80


def weight(text):
    """时长权重：实义字符算 1，标点算 0.35（念标点要停一下但不占字）"""
    w = 0.0
    for c in text:
        if c in PUNCT or c in ' \t':
            w += 0.0 if c in ' \t' else 0.35
        elif is_cjk(c):
            w += 1.0
        elif c.isalnum():
            w += 0.45
        else:
            w += 0.3
    return max(w, 0.5)


def split_single_line(text, maxlen):
    """把一句话切成若干「不超过 maxlen 字」的单行，优先在标点处断"""
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []
    parts = [p for p in _SENT_SPLIT.findall(text) if p.strip()]
    chunks, cur = [], ''
    for p in parts:
        if len(cur) + len(p) <= maxlen:
            cur += p
            continue
        if cur:
            chunks.append(cur)
            cur = ''
        if len(p) <= maxlen:
            cur = p
        else:
            for i in range(0, len(p), maxlen):
                seg = p[i:i + maxlen]
                if len(seg) == maxlen:
                    chunks.append(seg)
                else:
                    cur = seg
    if cur:
        chunks.append(cur)
    return [c.strip() for c in chunks if c.strip()]


def allocate(win_start, win_end, chunks):
    """在一个时间窗口内按字数比例给每个单行分配时长（带最小时长保护）"""
    if not chunks:
        return []
    span = max(0.25, win_end - win_start)
    ws = [weight(c) for c in chunks]
    tot = sum(ws) or 1.0
    durs = [span * w / tot for w in ws]
    if len(durs) > 1:
        MIN = 0.32
        durs = [max(d, MIN) for d in durs]
        s = sum(durs)
        durs = [d * span / s for d in durs]
    out, t = [], win_start
    for c, d in zip(chunks, durs):
        out.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': c})
        t += d
    return out


# ---------------------------------------------------------------- 逐字稿解析

TS_RE = re.compile(r'^\s*(?P<sp>[^\(（]{0,24})[\(（]\s*(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)\s*[\)）]\s*[:：]?\s*(?P<tx>.*)$')
SRT_IDX_RE = re.compile(r'^\s*\d+\s*$')
SRT_TIME_RE = re.compile(
    r'(?P<a>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(?P<b>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})')


def hms_to_sec(s):
    p = [float(x.replace(',', '.')) for x in s.split(':')]
    if len(p) == 3:
        return p[0] * 3600 + p[1] * 60 + p[2]
    if len(p) == 2:
        return p[0] * 60 + p[1]
    return p[0]


def parse_transcript(raw):
    """返回 (kind, items)。kind: 'ts' | 'srt' | 'plain'"""
    lines = [l.rstrip() for l in raw.splitlines()]

    # --- SRT ---
    if any(SRT_TIME_RE.search(l) for l in lines):
        cues, cur = [], None
        for l in lines:
            m = SRT_TIME_RE.search(l)
            if m:
                if cur:
                    cues.append(cur)
                cur = {'start': hms_to_sec(m.group('a')), 'end': hms_to_sec(m.group('b')), 'text': ''}
            elif cur is not None:
                if SRT_IDX_RE.match(l):
                    continue
                if l.strip():
                    cur['text'] += (' ' if cur['text'] else '') + l.strip()
        if cur:
            cues.append(cur)
        cues = [c for c in cues if c['text'].strip()]
        if cues:
            return 'srt', cues

    # --- 演讲人 + 时间戳 ---
    segs = []
    for l in lines:
        if not l.strip():
            continue
        m = TS_RE.match(l)
        if m and m.group('tx').strip():
            segs.append({'start': hms_to_sec(m.group('ts')), 'text': m.group('tx').strip()})
    if segs:
        segs.sort(key=lambda x: x['start'])
        return 'ts', segs

    # --- 纯文本 ---
    text = ' '.join(l.strip() for l in lines if l.strip())
    return 'plain', [{'start': None, 'text': text}]


# ---------------------------------------------------------------- 主流程


def main():
    ap = argparse.ArgumentParser(description='口播成片前置处理：音频 + 逐字稿 -> props.json')
    ap.add_argument('--audio', required=True, help='口播音频（mp3/m4a/wav 或含音轨的 mp4）')
    ap.add_argument('--transcript', required=True, help='逐字稿（txt/srt/md）')
    ap.add_argument('--project', required=True, help='Remotion 工程目录（props.json 写入其 public/）')
    ap.add_argument('--title', default='口播视频')
    ap.add_argument('--subtitle', default='')
    ap.add_argument('--accent', default='#FFD400', help='主强调色（字幕高亮/下划线）')
    ap.add_argument('--brand', default='#CC0000', help='品牌色（左上竖条）')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--width', type=int, default=1920)
    ap.add_argument('--height', type=int, default=1080)
    ap.add_argument('--font-size', type=int, default=52)
    ap.add_argument('--caption-bottom', type=int, default=150)
    ap.add_argument('--maxlen', type=int, default=25, help='单行最大字数（防折行）')
    ap.add_argument('--title-card', type=float, default=4.0, help='片头标题卡秒数，0=不要')
    ap.add_argument('--sections', default='', help='章节 JSON 文件：[{"start":12,"text":"第一部分"}]')
    ap.add_argument('--cards', default='', help='内容卡 JSON 文件：[{"start":..,"end":..,"kind":"bullets",...}]')
    ap.add_argument('--bgm', default='', help='BGM 音频（复制进 public/）')
    ap.add_argument('--bgm-volume', type=float, default=0.12)
    ap.add_argument('--out', default='', help='props.json 输出路径（默认 <project>/public/props.json）')
    ap.add_argument('--audio-name', default='audio.mp3',
                    help='写入 public/ 的音频文件名。受限环境下无法覆盖同名旧文件，'
                         '重跑时给个新名字即可（如 audio_v2.mp3）')
    args = ap.parse_args()

    public_dir = os.path.join(args.project, 'public')
    audio_name, duration = ensure_audio(args.audio, public_dir, args.audio_name)

    raw = read_text(args.transcript)
    kind, items = parse_transcript(raw)

    lines = []
    if kind == 'plain':
        chunks = split_single_line(items[0]['text'], args.maxlen)
        lines = allocate(0.0, duration, chunks)
    else:
        # 逐字稿有真实时点：优先用真实窗口
        if kind == 'srt':
            wins = [(c['start'], c['end'], c['text']) for c in items]
        else:
            # 由相邻时间戳推窗口，末句用全篇平均语速兜底
            stamps = [s['start'] for s in items]
            rates = []
            for i in range(len(items) - 1):
                dt = items[i + 1]['start'] - items[i]['start']
                cw = weight(items[i]['text'])
                if dt > 0.3:
                    rates.append(cw / dt)
            avg = sorted(rates)[len(rates) // 2] if rates else 4.5
            wins = []
            for i, s in enumerate(items):
                st = s['start']
                if i < len(items) - 1:
                    en = items[i + 1]['start']
                else:
                    en = min(duration, st + max(1.0, weight(s['text']) / max(avg, 1.0)))
                wins.append((st, en, s['text']))
        for (st, en, tx) in wins:
            en = max(en, st + 0.25)
            lines.extend(allocate(st, en, split_single_line(tx, args.maxlen)))

    if not lines:
        raise SystemExit('[x] 逐字稿解析后没有生成任何字幕行，请检查文件内容/格式')

    sections = json.loads(read_text(args.sections)) if args.sections else []
    cards = json.loads(read_text(args.cards)) if args.cards else []

    bgm_name = ''
    if args.bgm:
        bgm_name = 'bgm' + os.path.splitext(args.bgm)[1].lower()
        shutil.copy2(args.bgm, os.path.join(public_dir, bgm_name))

    props = {
        'title': args.title,
        'subtitle': args.subtitle,
        'audioSrc': audio_name,
        'audioDuration': round(duration, 3),
        'fps': args.fps,
        'width': args.width,
        'height': args.height,
        'accent': args.accent,
        'brand': args.brand,
        'lines': lines,
        'sections': sections,
        'cards': cards,
        'titleCardDuration': args.title_card,
        'captionBottom': args.caption_bottom,
        'fontSize': args.font_size,
        'showProgress': True,
        'bgmSrc': bgm_name,
        'bgmVolume': args.bgm_volume,
    }

    out_path = args.out or os.path.join(public_dir, 'props.json')
    if not os.path.isabs(out_path):
        out_path = os.path.join(args.project, out_path)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    # ---- 摘要（用于人工核对时间轴） ----
    mm, ss = divmod(int(duration), 60)
    print(f'[√] 音频      : {os.path.basename(args.audio)}  ->  public/{audio_name}')
    print(f'[√] 时长      : {mm}分{ss}秒 ({duration:.2f}s)')
    print(f'[√] 逐字稿格式: {kind}')
    print(f'[√] 字幕行数  : {len(lines)} 行（单行单显）')
    print(f'[√] 章节/内容卡: {len(sections)} / {len(cards)}')
    print(f'[√] props     : {out_path}')
    print('---- 时间轴抽样 ----')
    step = max(1, len(lines) // 8)
    for l in lines[::step][:8]:
        print(f'  {l["start"]:>8.2f}s - {l["end"]:>8.2f}s  {l["text"]}')


if __name__ == '__main__':
    main()
