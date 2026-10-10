#!/usr/bin/env python3
"""Chromium rendering QA with honest navigation capability reporting.

Static resource links are verified deterministically from their relative hrefs.
No HTTP server is required. The execution environment may block file://
navigation, so embedded images allow checking layout and in-page anchors
without pretending cross-page browser navigation was executed.
"""
import argparse
import base64
import json
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from build import validate_local_navigation, validate_all_html_links, local_nav_targets


def embed_images(root, source):
    def as_embedded(match):
        filename=match.group(1)
        data=(root/filename).read_bytes()
        return 'src="data:image/png;base64,'+base64.b64encode(data).decode('ascii')+'"'
    return re.sub(r'src="(img/[^"<>]+\.png)"',as_embedded,source)


def run(root, reports):
    root=Path(root).resolve()
    reports=Path(reports).resolve();reports.mkdir(parents=True,exist_ok=True)
    nav=validate_local_navigation(root)
    all_links=validate_all_html_links(root)
    findings=[]
    with sync_playwright() as p:
        # Cross-platform: use playwright's bundled chromium unless ZAOBAO_CHROMIUM overrides it.
        launch={'headless':True,'args':['--no-sandbox']}
        exe=os.environ.get('ZAOBAO_CHROMIUM')
        if exe:launch['executable_path']=exe
        browser=p.chromium.launch(**launch)
        for file in ('index.html','talk.htm'):
            for device,width in [('desktop',1366),('mobile',390)]:
                page=browser.new_page(viewport={'width':width,'height':850},device_scale_factor=1)
                source=embed_images(root,(root/file).read_text('utf8'))
                page.set_content(source,wait_until='load',timeout=60000)
                result=page.evaluate('''() => ({
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                    imageCount: document.images.length,
                    loaded: [...document.images].every(x => x.complete && x.naturalWidth > 0),
                    copyable: !!document.querySelector('main') && getComputedStyle(document.querySelector('main')).userSelect !== 'none',
                    bodyText: document.body.innerText.length,
                    promptCount: [...document.querySelectorAll('div')].filter(x => x.textContent.includes('各位老师早上好。') && x.children.length === 0).length,
                    navigationLinks: [...document.querySelectorAll('nav[aria-label="资源导航"] a')].map(a => a.getAttribute('href'))
                })''')
                result.update(file=file,device=device)
                if result['scrollWidth']>result['clientWidth']+2:raise AssertionError(file+' 横向溢出 '+str(result))
                if not result['loaded']:raise AssertionError(file+' 部分配图未加载 '+str(result))
                if not result['copyable'] or result['bodyText']<800:raise AssertionError(file+' 正文丢失或无法选择 '+str(result))
                if file=='index.html':
                    if result['imageCount']!=2:raise AssertionError('首页应有两张主图')
                    if len(result['navigationLinks'])!=3:raise AssertionError('资源导航应为两个 HTML 页面 + 一个早报 Markdown 链接')
                    for relative in local_nav_targets():
                        if relative not in result['navigationLinks'] or not (root/relative).is_file():
                            raise AssertionError('资源导航目标丢失: '+relative)
                    page.screenshot(path=str(reports/(file+'-'+device+'.png')),full_page=True)
                    if page.locator('nav[aria-label="资源导航"] a[target="_blank"]').count()!=3:raise AssertionError('导航需新页签打开')
                    result['new_tab_links']='passed'
                else:
                    if result['imageCount']!=5:raise AssertionError('讨论页应有两张主图和三张分题图')
                    if not page.locator('a[href="index.html#resources"]').count():raise AssertionError('讨论页返回资源导航链接缺失')
                    page.screenshot(path=str(reports/(file+'-'+device+'.png')),full_page=True)
                findings.append(result)
                page.close()
        browser.close()
    report={
        'passed':len(findings),
        'navigation_resource_files':nav,
        'all_html_links':all_links,
        'cross_page_browser_click':'not_verified_relative_files_validated_statically_no_server_started',
        'browser_render_mode':'set_content + original image bytes embedded as data URIs, no style modifications',
        'findings':findings,
    }
    (reports/'browser-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('BROWSER RENDER PASS',len(findings),'RESOURCE LINKS VALID',nav['link_count'])
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--reports',required=True);args=a.parse_args();run(args.root,args.reports)
