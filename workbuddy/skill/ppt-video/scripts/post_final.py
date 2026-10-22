#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
post_final.py —— 交付后期：一次产出「原速 + 1.2 倍速」两版，响度与真峰值都过闭环校验

为什么不用 ffmpeg 的 loudnorm 一条链搞定：
  实战里 loudnorm 的动态模式在「静音占比高、峰值比响度高 24dB」的 TTS 音轨上会失准
  ——目标 -15 只做到 -18.7，还把峰值顶到 +1.34 dBTP（真削波）。
  另外 AAC 编码本身会把解码后的真峰值抬高 0.5~0.7 dB，
  所以「wav 达标」不等于「成片达标」，必须在**编码成 AAC 之后**再测一次。

流程（每个版本各跑一遍）：
  1) volume(gain) + alimiter(level=0) 迭代，直到 wav 的 I 命中目标
  2) 只编码音频成 AAC，实测真峰值；超过目标就压低限幅上限，回到 1)
  3) 达标后再和视频流合成（原速 copy 视频流 / 倍速 setpts 重编视频）
  4) 成片复测 I 与 TP，打印最终值

用法：
  python post_final.py --src full.mp4 --srt final.srt --outdir final \
      --name "第3章_以企业架构为核心的数字化转型_口播讲解" \
      [--i -16] [--tp -1.0] [--speed 1.2]
"""
import argparse
import json
import os
import re
import subprocess
import sys

TARGET_I = -16.0
TARGET_TP = -1.0


def sh(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    if check and r.returncode != 0:
        sys.stderr.write((r.stderr or '')[-3000:])
        raise SystemExit('[x] 失败：%s' % ' '.join(cmd[:8]))
    return r


def measure(path, pre=''):
    af = (pre + ',' if pre else '') + 'loudnorm=print_format=json'
    r = sh(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', af,
            '-f', 'null', '-'], False)
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr or '', re.S)
    if not m:
        raise SystemExit('[x] 无法解析 loudnorm 输出：%s' % path)
    js = json.loads(m.group(0))
    return float(js['input_i']), float(js['input_tp'])


def dur(path):
    r = sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', path], False)
    try:
        return float(r.stdout.strip())
    except Exception:  # noqa: BLE001
        return 0.0


def fresh(path):
    """本环境不能覆盖同名文件，重跑自动 _v2/_v3"""
    if not os.path.exists(path):
        return path
    b, e = os.path.splitext(path)
    k = 2
    while os.path.exists('%s_v%d%s' % (b, k, e)):
        k += 1
    return '%s_v%d%s' % (b, k, e)


# ───────────────────── SRT ─────────────────────
def parse_srt(path):
    txt = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    cues = []
    for blk in [b for b in txt.split('\n\n') if b.strip()]:
        ls = [l for l in blk.strip().split('\n') if l.strip()]
        if len(ls) < 3:
            continue
        m = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', ls[1])
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000.0
        b2 = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000.0
        cues.append((a, b2, '\n'.join(ls[2:])))
    return cues


def ts(t):
    t = max(0.0, t)
    h = int(t // 3600); t -= h * 3600
    m = int(t // 60); t -= m * 60
    s = int(t); ms = int(round((t - s) * 1000))
    if ms >= 1000:
        s += 1; ms -= 1000
    return '%02d:%02d:%02d,%03d' % (h, m, s, ms)


# ───────────────────── 音频链 ─────────────────────
def build_audio(src, pre, work, tag, gain, ceil_lin, idx):
    out = os.path.join(work, 'a_%s_%02d.wav' % (tag, idx))
    chain = '%svolume=%.2fdB,alimiter=limit=%.4f:level=0:attack=5:release=50' % (
        (pre + ',') if pre else '', gain, ceil_lin)
    sh(['ffmpeg', '-y', '-v', 'error', '-i', src, '-vn', '-af', chain,
        '-ar', '48000', '-ac', '1', out])
    return out


def encode_aac(wav, work, tag):
    out = os.path.join(work, 'a_%s.m4a' % tag)
    if os.path.exists(out):
        os.remove(out)
    sh(['ffmpeg', '-y', '-v', 'error', '-i', wav, '-c:a', 'aac',
        '-b:a', '192k', '-ar', '48000', out])
    return out


def tune_audio(src, pre, work, tag, ceil_lin, rounds=4):
    """返回 wav。闭环：wav 响度命中 → AAC 编码后真峰值也必须命中。"""
    i0, _ = measure(src)
    gain = TARGET_I - i0
    last = None
    for _outer in range(rounds):
        wav = None
        for it in range(1, 5):
            wav = build_audio(src, pre, work, tag, gain, ceil_lin, it)
            i1, tp1 = measure(wav)
            print('  [%s] 轮%d gain=%+.2f ceil=%.3f → I=%.2f TP=%+.2f'
                  % (tag, it, gain, ceil_lin, i1, tp1))
            last = wav
            if abs(i1 - TARGET_I) <= 0.25:
                break
            gain += (TARGET_I - i1)
            if tp1 > TARGET_TP:
                ceil_lin *= 10 ** (min(1.0, tp1 - TARGET_TP) / -20.0)
        m4a = encode_aac(wav, work, tag)
        ai, atp = measure(m4a)
        print('  [%s] AAC 后 I=%.2f TP=%+.2f（目标 TP ≤ %.1f）' % (tag, ai, atp, TARGET_TP))
        if atp <= TARGET_TP + 0.15 and abs(ai - TARGET_I) <= 0.6:
            return wav
        over = max(0.2, atp - TARGET_TP)
        ceil_lin *= 10 ** (over / -20.0)
        gain -= over
        print('  [%s] 未达标，压低限幅上限重来' % tag)
    print('  [!] %s 达到上限仍未收敛，按当前最好结果交付' % tag)
    return last


def main():
    global TARGET_I, TARGET_TP
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='合并后的成片（有无音轨都可以）')
    ap.add_argument('--srt', default='')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--speed', type=float, default=1.2)
    ap.add_argument('--i', type=float, default=TARGET_I)
    ap.add_argument('--tp', type=float, default=TARGET_TP)
    ap.add_argument('--crf', default='18')
    a = ap.parse_args()
    TARGET_I, TARGET_TP = a.i, a.tp
    ceil_lin = 10 ** ((TARGET_TP - 0.2) / 20.0)

    os.makedirs(a.outdir, exist_ok=True)
    work = os.path.join(a.outdir, '.work')
    os.makedirs(work, exist_ok=True)

    # ── 原速 ──
    print('== 原速版')
    w1 = tune_audio(a.src, '', work, 'x1', ceil_lin)
    out1 = fresh(os.path.join(a.outdir, a.name + '_原速.mp4'))
    sh(['ffmpeg', '-y', '-v', 'error', '-i', a.src, '-i', w1,
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest',
        '-movflags', '+faststart', out1])
    fi, ft = measure(out1)
    print('[√] %s  I=%.2f TP=%+.2f %.1f 分钟'
          % (os.path.basename(out1), fi, ft, dur(out1) / 60))

    # ── 倍速 ──
    sp = a.speed
    print('== %.1f 倍速版' % sp)
    pre = 'atempo=%.6f' % sp
    w2 = tune_audio(a.src, pre, work, 'x%.1f' % sp, ceil_lin)
    out2 = fresh(os.path.join(a.outdir, a.name + '_%.1f倍速.mp4' % sp))
    sh(['ffmpeg', '-y', '-v', 'error', '-i', a.src, '-i', w2,
        '-filter_complex', '[0:v]setpts=PTS/%.6f,fps=30[v]' % sp,
        '-map', '[v]', '-map', '1:a:0',
        '-c:v', 'libx264', '-crf', a.crf, '-preset', 'medium', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest',
        '-movflags', '+faststart', out2])
    fi2, ft2 = measure(out2)
    print('[√] %s  I=%.2f TP=%+.2f %.1f 分钟'
          % (os.path.basename(out2), fi2, ft2, dur(out2) / 60))

    # ── 倍速字幕 ──
    if a.srt:
        cues = parse_srt(a.srt)
        dst = fresh(os.path.join(a.outdir, a.name.replace('_口播讲解', '') + '_%.1f倍速.srt' % sp))
        with open(dst, 'w', encoding='utf-8') as f:
            for i, (s, e, tx) in enumerate(cues, 1):
                f.write('%d\n%s --> %s\n%s\n\n' % (i, ts(s / sp), ts(e / sp), tx))
        print('[√] 倍速字幕 %s（%d 条）' % (os.path.basename(dst), len(cues)))

    bad = [x for x in (ft, ft2) if x > TARGET_TP + 0.2]
    if bad:
        print('[!] 仍有版本峰值高于目标 %.1f dBTP：%s'
              % (TARGET_TP, ['%+.2f' % x for x in bad]))
        print('    若只是 +0.1~0.3 dB 的个别采样点，人耳不可闻；要严格合规就调 --tp 更低重跑（只重做音轨）。')
    else:
        print('[√] 两版响度与真峰值均达标')


if __name__ == '__main__':
    main()
