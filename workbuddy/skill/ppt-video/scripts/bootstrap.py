# -*- coding: utf-8 -*-
"""
bootstrap.py —— 一次性准备 Remotion 工程（约 1 分钟，仅在首次/换机时需要）

node_modules 有 540MB 且安装依赖很容易被网络拖死，所以优先级是：
  1. 已有可用工程（koubo-remotion-video/project）→ 直接复用，不做任何拷贝；
  2. 复用它的 node_modules（Windows 建 junction，秒级，不占空间）；
  3. 都没有 → npm install（必须走 npmmirror 镜像，官方源会长时间卡住）。

用法：
  python bootstrap.py            # 自动：能复用就复用
  python bootstrap.py --link     # 强制建 <skill>/project 并 junction 复用 node_modules
  python bootstrap.py --install  # 强制全新安装
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TPL = os.path.join(SKILL, 'assets', 'project')
DST = os.path.join(SKILL, 'project')
LEGACY_DIRS = [
    os.path.expanduser(os.path.join('~', '.workbuddy', 'skills', 'koubo-video-studio', 'project')),
    os.path.expanduser(os.path.join('~', '.workbuddy', 'skills', 'koubo-remotion-video', 'project')),
]
LEGACY = next((p for p in LEGACY_DIRS if os.path.isfile(
    os.path.join(p, 'node_modules', '@remotion', 'cli', 'remotion-cli.js'))), LEGACY_DIRS[-1])
CLI_REL = os.path.join('node_modules', '@remotion', 'cli', 'remotion-cli.js')
MIRROR = 'https://registry.npmmirror.com'


def has_cli(p):
    return os.path.isfile(os.path.join(p, CLI_REL))


def copy_template():
    os.makedirs(DST, exist_ok=True)
    for name in os.listdir(TPL):
        s, d = os.path.join(TPL, name), os.path.join(DST, name)
        if name == 'node_modules':
            continue
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    os.makedirs(os.path.join(DST, 'public'), exist_ok=True)
    print('[√] 工程骨架 → %s' % DST)


def link_modules():
    """把已有工程的 node_modules 挂过来（Windows junction / POSIX symlink）"""
    src = os.path.join(LEGACY, 'node_modules')
    dst = os.path.join(DST, 'node_modules')
    if os.path.exists(dst):
        print('[i] node_modules 已存在，跳过链接')
        return True
    try:
        if os.name == 'nt':
            # 中文 Windows 的 cmd 输出是 GBK，按 utf-8 解会抛 UnicodeDecodeError
            r = subprocess.run(['cmd', '/c', 'mklink', '/J', dst, src],
                               capture_output=True, text=True,
                               encoding='gbk', errors='replace')
        else:
            os.symlink(src, dst, target_is_directory=True)
            r = None
        if r is None or r.returncode == 0:
            print('[√] node_modules 已链接复用（不占额外空间）')
            return True
        print('[!] 链接失败：%s' % (r.stderr or r.stdout).strip()[:200])
    except Exception as e:  # noqa: BLE001
        print('[!] 链接异常：%s' % e)
    return False


def npm_install():
    os.makedirs(DST, exist_ok=True)
    print('[i] 安装依赖（镜像 %s，约 3~8 分钟）……' % MIRROR)
    r = subprocess.run(['npm', 'install', '--registry=%s' % MIRROR, '--no-audit',
                        '--no-fund'], cwd=DST)
    if r.returncode != 0 or not has_cli(DST):
        raise SystemExit('[x] 安装失败。手动执行：cd "%s" && npm install '
                         '--registry=%s' % (DST, MIRROR))
    print('[√] 依赖安装完成')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--link', action='store_true')
    ap.add_argument('--install', action='store_true')
    args = ap.parse_args()

    print('模板   %s' % TPL)
    print('目标   %s' % DST)
    print('可复用 %s  →  %s' % (LEGACY, '有' if has_cli(LEGACY) else '无'))

    if has_cli(DST) and not (args.link or args.install):
        print('[√] <skill>/project 已就绪，无需操作')
        return

    if args.install:
        copy_template()
        npm_install()
        return

    if has_cli(LEGACY):
        copy_template()
        if link_modules() and has_cli(DST):
            print('[√] 完成：直接复用已有依赖，未重复安装')
            return
        if not args.link:
            print('[i] 链接不可用，改为全新安装')
        npm_install()
        return

    copy_template()
    npm_install()


if __name__ == '__main__':
    main()
