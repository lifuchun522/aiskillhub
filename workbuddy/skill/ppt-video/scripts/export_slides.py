#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
export_slides.py —— 把 PPT / PPTX / PDF 拆成逐页 PNG（1920×1080 优先）

三条路径，自动择优：
  1) Windows + 装了 PowerPoint → 走 COM 导出（版式 100% 还原，含字体、动画首帧）
  2) 没装 PowerPoint 但有 LibreOffice → 先转 PDF，再用 PyMuPDF 渲染
  3) 输入本来就是 PDF → 直接 PyMuPDF 渲染

不用 LibreOffice 直接导 PNG：它对中文字体和复杂版式还原差，只有兜底时才用。

用法：
  python export_slides.py --src "第1章：xxx.pptx" --out ./slides
  python export_slides.py --src deck.pdf --out ./slides --zoom 1.4

产物：<out>/幻灯片1.PNG ... 或 page_001.png ...（下一步统一交给 prep_slides.py 改名）
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

PAGE_EXTS = ('.png', '.PNG', '.jpg', '.JPG', '.jpeg')


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors='replace', **kw)


def export_by_powerpoint(src, out, w, h):
    """用 PowerPoint COM 导出 PNG。返回导出的文件列表（失败返回 []）。"""
    if os.name != 'nt':
        return []
    ps = r'''
$ErrorActionPreference = "Stop"
$src = "%s"; $out = "%s"
$ppt = New-Object -ComObject PowerPoint.Application
$pres = $ppt.Presentations.Open($src, $true, $false, $false)
$pres.Export($out, "PNG", %d, %d)
$pres.Close()
$ppt.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
''' % (src.replace('\\', '\\\\'), out.replace('\\', '\\\\').replace('/', '\\'), w, h)
    try:
        r = sh(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps])
    except Exception as e:  # noqa: BLE001
        print('[!] PowerPoint 导出异常：%s' % e)
        return []
    if r.returncode != 0:
        print('[!] PowerPoint 导出失败：%s' % (r.stderr or r.stdout).strip()[:300])
        return []
    return sorted(glob.glob(os.path.join(out, '*')))


def find_soffice():
    for c in (r'C:\Program Files\LibreOffice\program\soffice.exe',
              r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
              '/Applications/LibreOffice.app/Contents/MacOS/soffice',
              shutil.which('soffice') or ''):
        if c and os.path.isfile(c):
            return c
    return ''


def to_pdf(src, out):
    soffice = find_soffice()
    if not soffice:
        raise SystemExit('[x] 没找到 PowerPoint，也没有 LibreOffice。\n'
                         '    请任选其一安装，或先用其它工具把 PPT 导成 PDF 再传入本脚本。')
    print('[i] 用 LibreOffice 转 PDF……')
    r = sh([soffice, '--headless', '--convert-to', 'pdf', '--outdir', out, src])
    if r.returncode != 0:
        raise SystemExit('[x] LibreOffice 转换失败：%s' % (r.stderr or r.stdout)[:300])
    pdfs = glob.glob(os.path.join(out, '*.pdf'))
    if not pdfs:
        raise SystemExit('[x] 转换后没有找到 PDF')
    return pdfs[0]


def render_pdf(pdf, out, zoom):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise SystemExit('[x] 缺少 PyMuPDF：pip install pymupdf')
    doc = fitz.open(pdf)
    n = doc.page_count
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(os.path.join(out, 'page_%03d.png' % i))
    print('[√] PDF 渲染 %d 页（zoom=%.2f → %dx%d）' % (n, zoom, pix.width, pix.height))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='ppt / pptx / pdf')
    ap.add_argument('--out', required=True, help='页图输出目录')
    ap.add_argument('--width', type=int, default=1920)
    ap.add_argument('--height', type=int, default=1080)
    ap.add_argument('--zoom', type=float, default=1.4, help='PDF 渲染倍率（16:9 的 PPT → 1.4 约 1344×756）')
    a = ap.parse_args()

    src = os.path.abspath(a.src)
    if not os.path.isfile(src):
        raise SystemExit('[x] 文件不存在：%s' % src)
    os.makedirs(a.out, exist_ok=True)

    ext = os.path.splitext(src)[1].lower()
    if ext == '.pdf':
        render_pdf(src, a.out, a.zoom)
        return

    if ext not in ('.ppt', '.pptx', '.pps', '.ppsx'):
        raise SystemExit('[x] 只支持 ppt / pptx / pdf，收到：%s' % ext)

    files = export_by_powerpoint(src, a.out, a.width, a.height)
    if files:
        print('[√] PowerPoint COM 导出 %d 页 → %s' % (len(files), a.out))
        return

    print('[i] 回退到 LibreOffice + PDF 渲染')
    tmp = os.path.join(a.out, '_pdf')
    os.makedirs(tmp, exist_ok=True)
    pdf = to_pdf(src, tmp)
    render_pdf(pdf, a.out, a.zoom)


if __name__ == '__main__':
    main()
