#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
render.py —— Remotion 渲染包装器（把本机的坑都抹平）

工程目录解析顺序（都不用改代码）：
  1. --project 参数
  2. 环境变量 PPTW_PROJECT / KOUBO_PROJECT
  3. <skill>/project          （bootstrap.py 装好的，优先）
  4. 其它技能里已有 node_modules 的 Remotion 工程（koubo-video-studio / koubo-remotion-video）

四个必踩的坑，逐个处理：

1. webpack 缓存清理被安全删除拦截
   Remotion 换 webpack 配置时会 fs.rm node_modules/.cache/webpack/remotion-production-*，
   受限环境 fail-closed 直接让打包失败。
   → assets/project/remotion.config.ts 已用 overrideWebpackConfig 关掉持久化缓存，
     这里再做 best-effort 清理兜底。

2. Remotion 自带 Chrome Headless Shell 不可用（解压产物 spawn EFTYPE）
   → 复用系统 Chrome / Edge。

3. 新版 Chrome 没有旧版 headless 模式
   → 用系统 Chrome 必须带 --chrome-mode=chrome-for-testing。

4. 系统盘空间不足导致渲染卡死
   一条 9 分钟 1080p 成片会产生 1.6 万张中间帧、5~8GB 占用。
   → 可用空间 < 25GB 时自动把 TEMP 切到其它盘。

另：本环境禁止覆盖已存在文件，ffmpeg 到最后一刻会 Permission denied 白跑一场。
   → 输出已存在时自动改名 _v2/_v3。

用法：
  python render.py --out out/v.mp4
  python render.py --out out/smoke.mp4 --frames=3240-3449   # 抽真实片段验画面
  python render.py --out out/g.mp4 --composition CardGallery --frames=0-1
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLI_REL = os.path.join('node_modules', '@remotion', 'cli', 'remotion-cli.js')
LEGACY_DIRS = [
    os.path.expanduser(os.path.join('~', '.workbuddy', 'skills', 'koubo-video-studio', 'project')),
    os.path.expanduser(os.path.join('~', '.workbuddy', 'skills', 'koubo-remotion-video', 'project')),
]

SYSTEM_BROWSERS = [
    os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
]


def find_project(explicit=''):
    cands = []
    if explicit:
        cands.append(explicit)
    for env in ('PPTW_PROJECT', 'KOUBO_PROJECT'):
        if os.environ.get(env):
            cands.append(os.environ[env])
    cands.append(os.path.join(os.path.dirname(HERE), 'project'))
    cands += LEGACY_DIRS
    for c in cands:
        if c and os.path.isfile(os.path.join(c, CLI_REL)):
            return os.path.abspath(c)
    raise SystemExit(
        '[x] 找不到可用的 Remotion 工程（需要 node_modules/@remotion/cli）。\n'
        '    先跑：python scripts/bootstrap.py\n'
        '    或指定：--project <已有工程目录>')


def find_browser(project):
    for c in SYSTEM_BROWSERS:
        if os.path.isfile(c):
            return c.replace('\\', '/'), True
    for plat in ('win64', 'mac-arm64', 'mac-x64', 'linux64'):
        for exe in ('chrome-headless-shell.exe', 'chrome-headless-shell'):
            g = glob.glob(os.path.join(project, 'node_modules', '.remotion',
                                       'chrome-headless-shell', plat,
                                       '*' + exe))
            if g:
                return g[0].replace('\\', '/'), False
    return '', False


def purge_webpack_cache(project):
    try:
        shutil.rmtree(os.path.join(project, 'node_modules', '.cache', 'webpack'),
                      ignore_errors=True)
    except Exception:
        pass


def pick_temp_dir():
    sys_temp = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
    try:
        if shutil.disk_usage(sys_temp).free > 25 * 1024 ** 3:
            return ''
    except Exception:
        return ''
    best, best_free = '', 0
    for drive in ('D', 'E', 'F', 'G', 'H'):
        root = '%s:/' % drive
        if not os.path.exists(root):
            continue
        try:
            free = shutil.disk_usage(root).free
        except Exception:
            continue
        if free > best_free:
            best, best_free = root, free
    if best and best_free > 25 * 1024 ** 3:
        d = os.path.join(best, 'remotion-temp')
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            return ''
    return ''


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--out', required=True)
    ap.add_argument('--props', default='public/props.json')
    ap.add_argument('--composition', default='KouboVideo',
                    help='KouboVideo（成片）| CardGallery（卡片版式自检）')
    ap.add_argument('--project', default='')
    ap.add_argument('--frames', default='')
    ap.add_argument('--still', action='store_true')
    ap.add_argument('--frame', default='')
    ap.add_argument('--crf', default='')
    ap.add_argument('--concurrency', default='',
                    help='并发。本机 20 核实测 12 最稳；16 会打崩本地服务')
    ap.add_argument('--browser', default='')
    ap.add_argument('--chrome-mode', default='')
    ap.add_argument('--overwrite', action='store_true')
    ap.add_argument('--temp-dir', default='')
    args, passthrough = ap.parse_known_args()

    project = find_project(args.project)
    CLI = os.path.join(project, CLI_REL)
    print('[i] 工程：%s' % project)

    purge_webpack_cache(project)

    temp_dir = args.temp_dir or pick_temp_dir()
    if temp_dir:
        print('[i] 系统盘空间紧张，中间帧临时目录 → %s' % temp_dir)

    out = args.out if os.path.isabs(args.out) else os.path.join(project, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and not args.overwrite:
        root, ext = os.path.splitext(out)
        n = 2
        while os.path.exists('%s_v%d%s' % (root, n, ext)):
            n += 1
        out = '%s_v%d%s' % (root, n, ext)
        print('[i] 目标已存在，改写为：%s' % out)

    browser, new_headless = (args.browser, True) if args.browser else find_browser(project)
    chrome_mode = args.chrome_mode or ('chrome-for-testing' if new_headless else '')

    if args.still:
        cmd = ['node', CLI, 'still', 'src/index.ts', args.composition, out,
               '--props=%s' % args.props]
        if args.frame:
            cmd.append('--frame=%s' % args.frame)
    else:
        cmd = ['node', CLI, 'render', 'src/index.ts', args.composition, out,
               '--props=%s' % args.props]
        for k, v in (('--frames', args.frames), ('--crf', args.crf),
                     ('--concurrency', args.concurrency)):
            if v:
                cmd.append('%s=%s' % (k, v))

    if browser:
        cmd.append('--browser-executable=%s' % browser)
        print('[i] 浏览器：%s' % browser)
    if chrome_mode:
        cmd.append('--chrome-mode=%s' % chrome_mode)
    cmd += passthrough

    print('[i] 开始渲染……（打包约 1 分钟，之后按帧数推进）')
    env = dict(os.environ)
    if temp_dir:
        env['TEMP'] = env['TMP'] = env['TMPDIR'] = temp_dir
    r = subprocess.run(cmd, cwd=project, env=env)
    if r.returncode == 0 and os.path.isfile(out):
        print('[√] 完成：%s  (%.2f MB)' % (out, os.path.getsize(out) / 1048576))
    sys.exit(r.returncode)


if __name__ == '__main__':
    main()
