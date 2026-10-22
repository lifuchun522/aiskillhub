# -*- coding: utf-8 -*-
"""
narrate.py —— 口播逐字稿 → 云扬配音 + 精准单行字幕 + 段落时点

核心保证（这两点是硬要求，不是优化项）：

1) 片头静音必须真正写进音频流。
   只把 lead_in 加进时点、却没写进音频，会让音频从 0 秒就开口，
   而字幕从 lead_in 起算 → 整体错位 lead_in 秒，且缺口被尾部补齐。
   本脚本把 lead-in / 段间停顿 / 尾部留白全部作为真实 PCM 样本写入。

2) 按「样本数」拼接，而不是按 mp3 帧拼接。
   逐段 concat mp3 时，每段帧边界对齐会引入 0~26ms padding 误差，
   50 段累积可达数百毫秒，后段越走越偏。
   本脚本把每段解码成 24kHz/mono/s16 WAV，用采样数累加时点，零漂移。

另外：每段都带缓存（mp3 + 词级时间戳），改文案只重跑变动的段。

用法：
  python narrate.py --text 逐字稿.txt --dir ./build [--lead-in 4.2] [--gap 0.55]
输出：
  <dir>/final.mp3         口播音频（含片头/停顿/尾部）
  <dir>/final.srt         单行单显字幕
  <dir>/segments.json     每段起止秒（配图时点靠它对齐）
  <dir>/audio/*.mp3       分段音频缓存（含 .words.json）
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

VOICE = 'zh-CN-YunyangNeural'
RATE = '+6%'
HARD = '。！？'
SOFT = '，；：、'
MAXC = 20            # 单行字幕最大字数（超过即换行，20 字在 1080p 下不会折行）
SR, CH, SW = 24000, 1, 2


# ───────────────────────── 字幕切分 ─────────────────────────
def _even_split(a, b):
    L = b - a
    n = (L + MAXC - 1) // MAXC
    step = (L + n - 1) // n
    return [(i, min(i + step, b)) for i in range(a, b, step)]


def ranges(text):
    """把一段话切成若干 <=MAXC 字的单行窗口 [(start_char, end_char)]"""
    sents, cur = [], 0
    for i, ch in enumerate(text):
        if ch in HARD:
            sents.append((cur, i + 1))
            cur = i + 1
    if cur < len(text):
        sents.append((cur, len(text)))

    out = []
    for a, b in sents:
        if b - a <= MAXC:
            out.append((a, b))
            continue
        parts, p = [], a
        for i in range(a, b):
            if text[i] in SOFT:
                parts.append((p, i + 1))
                p = i + 1
        if p < b:
            parts.append((p, b))
        fi = []
        for qa, qb in parts:
            if qb - qa > MAXC:
                fi += _even_split(qa, qb)
            else:
                fi.append((qa, qb))
        # 相邻小片回填合并，避免出现 2~3 字的碎行
        ba, bl = None, 0
        for qa, qb in fi:
            L = qb - qa
            if ba is None:
                ba, bl = qa, L
            elif bl + L <= MAXC:
                bl += L
            else:
                out.append((ba, ba + bl))
                ba, bl = qa, L
        if ba is not None:
            if out and bl < 6 and (out[-1][1] - out[-1][0] + bl) <= MAXC + 4:
                pa, _ = out.pop()
                out.append((pa, ba + bl))
            else:
                out.append((ba, ba + bl))
    return out


def char_times(text, words):
    """词级时间戳 → 字符级时间戳。words = [[秒, 词], ...]"""
    ct = [None] * len(text)
    cur = 0
    for off, tok in words:
        idx = text.find(tok, cur)
        if idx < 0:
            idx = text.find(tok)
        if idx < 0:
            continue
        for k in range(idx, min(idx + len(tok), len(text))):
            ct[k] = off
        cur = idx + len(tok)
    last = 0.0
    for i in range(len(ct)):
        if ct[i] is None:
            ct[i] = last
        else:
            last = ct[i]
    return ct


def srt_ts(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return '%02d:%02d:%02d,%03d' % (h, m, sec, ms)


# ───────────────────────── 合成 ─────────────────────────
async def synth(mp3, text):
    """单段合成。对 429（限流）做指数退避重试——批量配音时这是最常见的失败。"""
    import edge_tts
    for attempt in range(8):
        try:
            words = []
            comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary='WordBoundary')
            with open(mp3, 'wb') as f:
                async for ch in comm.stream():
                    if ch.get('type') == 'audio':
                        f.write(ch['data'])
                    elif ch.get('type') == 'WordBoundary':
                        words.append([ch['offset'] / 1e7, ch['text']])
            if os.path.getsize(mp3) > 1000 and words:
                return words
            raise RuntimeError('返回为空')
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            # 429 / 5xx 是限流，等久一点；其它错误快速重试
            wait = 90 if ('429' in msg or '5' == msg[:1]) else min(60, 3 * 2 ** attempt)
            print('   retry %d（%d 秒后）: %s' % (attempt + 1, wait, msg[:80]))
            await asyncio.sleep(wait)
    raise SystemExit('[x] 合成失败（已重试 8 次）：%s' % text[:24])


# ───────────────────────── 音频工具 ─────────────────────────
def ff(*a):
    subprocess.run(['ffmpeg', '-y', '-v', 'error'] + list(a), check=True)


def fresh(path):
    """禁止覆盖已存在文件：重跑自动换名 _v2/_v3"""
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    n = 2
    while os.path.exists('%s_v%d%s' % (root, n, ext)):
        n += 1
    return '%s_v%d%s' % (root, n, ext)


def to_wav(src, dst):
    if not (os.path.exists(dst) and os.path.getsize(dst) > 44):
        ff('-i', src, '-ar', str(SR), '-ac', str(CH), '-c:a', 'pcm_s16le', dst)
    return dst


def silence_wav(dst, sec):
    if not (os.path.exists(dst) and os.path.getsize(dst) > 44):
        ff('-f', 'lavfi', '-i', 'anullsrc=r=%d:cl=mono' % SR,
           '-t', '%.4f' % sec, '-c:a', 'pcm_s16le', dst)
    return dst


def pcm(path):
    with wave.open(path, 'rb') as w:
        spec = (w.getframerate(), w.getnchannels(), w.getsampwidth())
        if spec != (SR, CH, SW):
            raise SystemExit('[x] %s 规格异常 %s' % (path, spec))
        return w.readframes(w.getnframes())


def mean_vol(path, ss=0.0, t=1.0):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats',
                        '-ss', '%.3f' % ss, '-t', '%.3f' % t, '-i', path,
                        '-af', 'volumedetect', '-f', 'null', '-'],
                       capture_output=True, text=True, errors='ignore')
    m = re.search(r'mean_volume:\s*(-?[\d.]+)', r.stderr)
    return float(m.group(1)) if m else None


# ───────────────────────── 主流程 ─────────────────────────
async def main():
    global VOICE, RATE, MAXC
    ap = argparse.ArgumentParser()
    ap.add_argument('--text', required=True, help='逐字稿（纯文本，段落以空行分隔）')
    ap.add_argument('--dir', default='./build')
    ap.add_argument('--gap', type=float, default=0.55, help='段间停顿秒数')
    ap.add_argument('--lead-in', type=float, default=4.2, help='片头静音秒数（片头标题卡要落在这段里）')
    ap.add_argument('--tail', type=float, default=2.2, help='尾部留白秒数')
    ap.add_argument('--maxlen', type=int, default=MAXC, help='单行字幕最大字数')
    ap.add_argument('--bitrate', default='96k')
    ap.add_argument('--voice', default=VOICE)
    ap.add_argument('--rate', default=RATE)
    ap.add_argument('--out-mp3', default='final.mp3')
    ap.add_argument('--out-srt', default='final.srt')
    ap.add_argument('--out-segments', default='segments.json')
    args = ap.parse_args()

    VOICE, RATE, MAXC = args.voice, args.rate, args.maxlen
    import edge_tts_patch  # noqa: F401  旧端点 403，必须打补丁

    base = os.path.abspath(args.dir)
    aud = os.path.join(base, 'audio')
    os.makedirs(aud, exist_ok=True)

    raw = open(args.text, encoding='utf-8').read()
    lines = [l.rstrip() for l in raw.splitlines()]
    paras = [p.strip() for p in re.split(r'\n\s*\n', '\n'.join(lines)) if p.strip()]
    # 去掉 markdown 标题/引用等非口播行
    paras = [p for p in paras if not p.startswith(('#', '>', '```', '|'))]
    print('段落数 %d，总字数 %d' % (len(paras), sum(len(p) for p in paras)))
    if not paras:
        raise SystemExit('[x] 逐字稿没有解析到任何段落')

    # ---- 1. 逐段音频（带缓存）+ 转 WAV 量样本 ----
    seg_frames, seg_dur, all_words = [], [], []
    for i, p in enumerate(paras):
        mp3 = os.path.join(aud, 'seg%03d.mp3' % i)
        if os.path.exists(mp3) and os.path.exists(mp3 + '.words.json'):
            words = json.load(open(mp3 + '.words.json', encoding='utf-8'))
        else:
            words = await synth(mp3, p)
            json.dump(words, open(mp3 + '.words.json', 'w', encoding='utf-8'),
                      ensure_ascii=False)
        w = to_wav(mp3, os.path.join(aud, 'w%03d.wav' % i))
        fr = pcm(w)
        seg_frames.append(fr)
        seg_dur.append(len(fr) / SW / SR)
        all_words.append(words)
        print('  [%2d/%d] %6.3fs  %s' % (i + 1, len(paras), seg_dur[-1], p[:20]))

    # ---- 2. 静音件（同样按样本精确）----
    lead_fr = pcm(silence_wav(os.path.join(aud, 'leadin.wav'), args.lead_in))
    gap_fr = pcm(silence_wav(os.path.join(aud, 'gapst.wav'), args.gap))
    tail_fr = pcm(silence_wav(os.path.join(aud, 'tailst.wav'), args.tail))

    # ---- 3. 精确组装：时点 = 采样数累加 ----
    chunks = [lead_fr]
    t = args.lead_in
    segs, cues = [], []
    for i, p in enumerate(paras):
        start, d = t, seg_dur[i]
        ct = char_times(p, [tuple(x) for x in all_words[i]])
        rng = ranges(p)
        local = []
        for j, (a, b) in enumerate(rng):
            s = p[a:b]
            if b - a <= 1 and s in '，、；：':
                continue
            disp = s.rstrip('，、；：') or s
            st = ct[a]
            en = ct[rng[j + 1][0]] - 0.10 if j + 1 < len(rng) else d
            local.append([st, en, disp])
        for j in range(len(local)):
            if j + 1 < len(local) and local[j][1] > local[j + 1][0]:
                local[j][1] = local[j + 1][0] - 0.05
            if local[j][1] <= local[j][0]:
                local[j][1] = local[j][0] + 0.6
        for a, b, tx in local:
            cues.append({'start': round(start + a, 3), 'end': round(start + b, 3),
                         'text': tx})
        segs.append({'i': i, 'text': p, 'start': round(start, 3),
                     'end': round(start + d, 3), 'dur': round(d, 3)})
        chunks.append(seg_frames[i])
        t += d
        if i < len(paras) - 1:
            chunks.append(gap_fr)
            t += args.gap
    chunks.append(tail_fr)
    total = t + args.tail

    # ---- 4. 落盘：WAV 拼完再转 MP3 ----
    data = b''.join(chunks)
    real_dur = len(data) / SW / SR
    out_wav = fresh(os.path.join(base, 'assembly.wav'))
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(CH)
        w.setsampwidth(SW)
        w.setframerate(SR)
        w.writeframes(data)

    out_mp3 = fresh(os.path.join(base, args.out_mp3))
    ff('-i', out_wav, '-c:a', 'libmp3lame', '-b:a', args.bitrate, out_mp3)

    out_srt = fresh(os.path.join(base, args.out_srt))
    with open(out_srt, 'w', encoding='utf-8') as f:
        for i, c in enumerate(cues, 1):
            f.write('%d\n%s --> %s\n%s\n\n'
                    % (i, srt_ts(c['start']), srt_ts(c['end']), c['text']))

    seg_path = fresh(os.path.join(base, args.out_segments))
    json.dump({'voice': VOICE, 'rate': RATE, 'total': round(total, 3),
               'leadIn': args.lead_in, 'gap': args.gap,
               'segments': segs},
              open(seg_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # ---- 5. 时轴自检（三项硬指标）----
    head = mean_vol(out_mp3, 0.05, max(0.4, args.lead_in - 0.3))
    speech = mean_vol(out_mp3, args.lead_in + 0.15, 1.0)
    drift = abs(real_dur - total)
    print('\n=== 汇总 ===')
    print('总时长 %.3fs = %d:%02d' % (total, total // 60, total % 60))
    print('音频   %s  (%.2f MB)' % (out_mp3, os.path.getsize(out_mp3) / 1048576))
    print('字幕   %s  共 %d 条' % (out_srt, len(cues)))
    print('时点   %s  共 %d 段' % (seg_path, len(segs)))
    print('---- 时轴自检 ----')
    ok = True
    if head is not None and head > -55:
        ok = False
    if speech is not None and speech < -40:
        ok = False
    if drift > 0.05:
        ok = False
    print('片头区间电平 %7.1f dB  (要求 < -55，证明片头是真空)' % (head if head else 0))
    print('首句区间电平 %7.1f dB  (要求 > -40，证明确实在说话)' % (speech if speech else 0))
    print('音频/规划差 %7.3f s   (要求 < 0.05)' % drift)
    print('首句字幕起点 %6.3fs / 片头 %.2fs' % (cues[0]['start'], args.lead_in))
    print('[√] 时轴自检通过' if ok else '[!] 时轴自检未通过，先别往下渲染')


if __name__ == '__main__':
    asyncio.run(main())
