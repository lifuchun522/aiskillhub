#!/usr/bin/env python3
"""zaobao v6.1: ImageGen sketches + screenshot regions + a single timestamped article archive.

Usage: python scripts/build.py --input examples/demo-2026-10-08.json \
       --brief-image /path/to/imagegen.png --talk-image /path/to/imagegen2.png \
       --out /mnt/data/zaobao-build --timezone Asia/Shanghai --gen-brief <real_image_gen_id> --gen-talk <real_image_gen_id>
All text is UTF-8. The original ImageGen drawings are retained byte for byte.
Framed poster PNG files are transparently labeled deterministic derivatives,
not falsely claimed to be direct ImageGen outputs.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re
import shutil
import zipfile
from PIL import Image, ImageStat

TAGS=('科技热点','架构文章推荐','今日一言')
STYLE='font-family:Microsoft YaHei,PingFang SC,Noto Sans CJK SC,Arial,sans-serif;color:#242424;font-size:16px;line-height:1.86;overflow-wrap:anywhere;word-break:break-word;'
BASE='margin:0 auto;max-width:740px;padding:14px 16px 36px;background:#fff;'
H2='font-size:22px;line-height:1.5;margin:25px 0 12px;color:#212121;padding-left:12px;border-left:5px solid #cc4929;'
P='margin:10px 0 15px;line-height:1.85;overflow-wrap:anywhere;word-break:break-word;'
RED='#b94127'
# Portable resources: all local paths resolve inside article.zip; page fragments target sections.
# A navigation link is never published unless its target is included in the package.
RESOURCE_NAV=(
    ('HTML 页面', (('早报与三问三答', 'index.html'), ('架构师同盟讨论', 'talk.htm'))),
    ('自媒体创作', (('早报 Markdown', 'md/zaobao.md'),)),
)


def resource_nav():
    """Return an inline-styled, script-free, mobile-wrapping offline resource menu."""
    parts=['<nav aria-label="资源导航" id="resources" style="margin:20px 0 24px;padding:15px 14px;'
           'border:1px solid #dfd3cb;border-radius:8px;background:#fffaf7;">',
           '<strong style="display:block;font-size:18px;color:#a43d24;margin:0 0 7px;">资源导航</strong>',
           '<p style="margin:0 0 12px;font-size:13px;color:#665d59;line-height:1.65;">'
           'HTML 页面和早报 Markdown 创作素材，均在新标签页打开。</p>']
    style=('display:inline-block;max-width:100%;box-sizing:border-box;margin:4px 7px 4px 0;'
           'padding:5px 10px;border:1px solid #e9c5b8;border-radius:5px;background:#fff;'
           'color:#a33e27;text-decoration:none;font-size:14px;line-height:1.5;'
           'overflow-wrap:anywhere;vertical-align:middle;')
    for category,items in RESOURCE_NAV:
        parts.append('<div style="margin:8px 0 10px;line-height:1.9;">'
                     f'<span style="display:inline-block;font-weight:700;font-size:14px;'
                     f'color:#444;margin-right:8px;">{html.escape(category)}</span>')
        for label,uri in items:
            parts.append(f'<a href="{html.escape(uri,quote=True)}" target="_blank" rel="noopener noreferrer" style="{style}">{html.escape(label)}</a>')
        parts.append('</div>')
    parts.append('</nav>')
    return ''.join(parts)

def local_nav_targets():
    return tuple(uri for _,items in RESOURCE_NAV for _,uri in items if not uri.startswith('#'))

def validate_local_navigation(root):
    """Pure deterministic validation: every relative nav link and fragment must exist."""
    from html.parser import HTMLParser
    class LinkCollector(HTMLParser):
        def __init__(self):super().__init__();self.hrefs=[];self.ids=set()
        def handle_starttag(self,tag,attrs):
            kv=dict(attrs)
            if kv.get('id'):self.ids.add(kv['id'])
            if tag=='a' and kv.get('href'):self.hrefs.append(kv['href'])
    root=Path(root); page=root/'index.html'
    if not page.is_file():raise ValueError('缺少首页 index.html')
    c=LinkCollector();c.feed(page.read_text(encoding='utf8'))
    expected={uri for _,items in RESOURCE_NAV for _,uri in items}
    if not expected.issubset(set(c.hrefs)):raise ValueError('首页资源导航链接缺失')
    for href in expected:
        if href.startswith('#'):
            if href[1:] not in c.ids:raise ValueError(f'资源导航无效页内锚点: {href}')
            continue
        if href.startswith('/') or '..' in Path(href).parts or '://' in href or not (root/href).is_file():
            raise ValueError(f'资源导航无效文件链接: {href}')
    return {'link_count':len(expected),'html_links':sum(u.endswith(('.htm','.html')) for u in local_nav_targets()),'md_links':sum(u.endswith('.md') for u in local_nav_targets()),'anchor_links':0}

def validate_all_html_links(root):
    """Deterministically validate EVERY link of BOTH pages: blank, safe, resolvable."""
    from html.parser import HTMLParser
    from urllib.parse import urlsplit, unquote
    class Inspector(HTMLParser):
        def __init__(self):super().__init__();self.links=[];self.ids=set()
        def handle_starttag(self, tag, attrs):
            props=dict(attrs)
            if props.get('id'):self.ids.add(props['id'])
            if tag=='a':self.links.append(props)
    root=Path(root);data={}
    for name in ('index.html','talk.htm'):
        parser=Inspector();parser.feed((root/name).read_text('utf8'));data[name]=parser
    seen=0
    for name,parser in data.items():
        for link in parser.links:
            seen+=1;uri=link.get('href','')
            if not uri:raise ValueError(f'{name} 链接缺失 href')
            if link.get('target')!='_blank':raise ValueError(f'{name} 链接未使用 _blank: {uri}')
            rel=set(link.get('rel','').split())
            if not {'noopener','noreferrer'}.issubset(rel):raise ValueError(f'{name} 链接缺少安全 rel: {uri}')
            url=urlsplit(uri)
            if url.scheme in ('https','http'):continue
            if url.scheme or uri.startswith(('/', '//')):raise ValueError('禁止非相对或不安全的内部资源链接: '+uri)
            target=unquote(url.path) or name
            path=Path(target)
            if '..' in path.parts:raise ValueError('链接含路径穿越: '+uri)
            if not (root/path).is_file():raise ValueError('链接目标不存在: '+uri)
            if url.fragment and target in data and url.fragment not in data[target].ids:
                raise ValueError('链接锚点不存在: '+uri)
    return {'checked_all_anchors':seen,'pages_checked':2,'all_target_blank':True,
            'all_rel_noopener_noreferrer':True}

def sha(data):return hashlib.sha256(data).hexdigest()
def txt(s):return html.escape(s,quote=True).replace('\n','<br/>')
def para(s,highlight=False):
    deco='padding:11px 13px;border-left:3px solid #ea815c;background:#fff9f5;' if highlight else ''
    return f'<p style="{P}{deco}">{linkify(s)}</p>'
def linkify(s):
    urls=re.compile(r'https?://[^\s、，；。<>]+');i=0;out=[]
    for m in urls.finditer(s):
        out.append(txt(s[i:m.start()]));u=m.group(0).rstrip('）)')
        out.append(f'<a href="{html.escape(u,quote=True)}" target="_blank" rel="noopener noreferrer" style="color:{RED};text-decoration:underline;overflow-wrap:anywhere;">{html.escape(u)}</a>')
        if len(u)<len(m.group()):out.append(txt(m.group()[len(u):]))
        i=m.end()
    out.append(txt(s[i:]));return ''.join(out)
def img(src,alt):return f'<img src="{html.escape(src)}" alt="{html.escape(alt)}" style="display:block;width:100%;height:auto;margin:14px 0 23px;border:1px solid #dadada;border-radius:4px;"/>'
def layout(title,body):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width,initial-scale=1"/>'
        f'<title>{txt(title)}</title></head><body style="margin:0;padding:0;background:#fff;">'
        f'<main style="{BASE}{STYLE}">'+body+'</main></body></html>')
def model_text(models):return ' + '.join(f'{m["name"]}（定义：{m["definition"]}）' for m in models)
def count_answer(answer):return len(re.sub(r'https?://\S+','',answer))

def validate(d):
    if [r.get('tag') for r in d.get('raw_sections',[])]!=list(TAGS):raise ValueError('三栏不全或顺序错误')
    if len(d.get('brief',[]))!=3 or len(d.get('forum',[]))!=3:raise ValueError('问题数量必须3+3')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',d.get('date','')):raise ValueError('日期格式')
    for i,(r,a,t) in enumerate(zip(d['raw_sections'],d['brief'],d['forum']),1):
        if not r['text'].strip():raise ValueError('原始素材缺失')
        if t['anchor'] not in r['text']:raise ValueError(f'第{i}讨论话题未锚定该栏目原文')
        if not (a['question'].endswith('？') and len(a['question'])<80):raise ValueError('尖锐问题不合法')
        if len(a['models']) not in (1,2) or len(t['models']) not in (1,2):raise ValueError('芒格模型数量或定义缺失')
        for m in a['models']+t['models']:
            if not m.get('definition') or not m.get('name'):raise ValueError('芒格模型未说明定义')
        for k in ['core','analysis','actions','boundary','summary','refs']:
            if not a.get(k):raise ValueError(f'第{i}早报答案缺少{k}')
        if not (3<=len(a['actions'])<=5):raise ValueError('工程行动应为3至5项')
        for k in ['headline','background','angle','message','core','reason','project','improve','metrics','one_liner','refs']:
            if not t.get(k):raise ValueError(f'第{i}讨论缺少{k}')
        if not t['message'].startswith('各位老师早上好。'):raise ValueError('群发引导语不符合真实微信群语境')
        if t['message'].count('？')!=1:raise ValueError('群发引导语只能抛一个尖锐问题')
        if '我的判断是：' not in t['message']:raise ValueError('群发引导语必须先给明确判断')
        if not (100<=len(t['message'])<=340):raise ValueError('群发引导语过短/过长')
        if t['core'].startswith('建议'):raise ValueError('核心回答第一句不够坚定')
        for refs in (a['refs'],t['refs']):
            if not all(z.startswith('https://') for z in refs):raise ValueError('非真实规范链接')
        answer=''.join([model_text(a['models']),a['core'],a['analysis'],' '.join(a['actions']),a['boundary'],a['summary']])
        fa=''.join([t['core'],model_text(t['models']),t['reason'],t['project'],t['improve'],t['metrics'],t['one_liner']])
        if count_answer(answer)>500 or count_answer(fa)>500:raise ValueError(f'第{i}题超过500字')
    return True

def brief_md(d):
    ps=[]
    for i,(raw,a) in enumerate(zip(d['raw_sections'],d['brief']),1):
        sections=[f'芒格模型：{model_text(a["models"])}。',f'核心结论：{a["core"]}',
                  f'模型推演：{a["analysis"]}',
                  '工程落地：'+'；'.join(f'{j}、{act}' for j,act in enumerate(a['actions'],1))+'。',
                  f'边界与验证：{a["boundary"]}',f'一句话小结：{a["summary"]}',
                  '参考资料：'+'；'.join(a['refs'])]
        ps.append(f'技术思考问题{i}：{a["question"]} | '+''.join(sections)+f' ---【{raw["tag"]}】'+raw['text'].replace('\n\n','\n'))
    return '\n\n'.join(ps)+'\n'

def forum_md(d):
    out=['# 架构师同盟 · 三个可直接发群的讨论话题','',
      '> 每个话题来自早报对应栏目；先复制“群发引导语”到群里，再发送下面的单题架构图。标准回答供主持人备用，不建议开场全部贴出。','']
    for i,(raw,t) in enumerate(zip(d['raw_sections'],d['forum']),1):
        msg=t['message'].replace('**','')
        out += [f'## 话题{i}：{t["headline"]}','','**对应栏目：**'+raw['tag']+' · **原文抓手：**'+t['anchor'],'',
                '### 群发引导语（直接复制）','','```text',msg,'```','',
                f'![话题{i}独立手绘架构图](../img/talk-topic-{i}.png)','',
                '**讨论背景：**'+t['background'],'',
                '**核心取舍：**'+t['angle'],'',
                '### 我的参考回答（讨论后再发）','',
                '**第一句回答：**'+t['core'],'',
                '**芒格模型：**'+model_text(t['models']),'',
                '**模型推演：**'+t['reason'],'',
                '**数字人 / 智能客服项目方案：**'+t['project'],'',
                '**待改进项：**'+t['improve'],'',
                '**验证指标：**'+t['metrics'],'',
                '**一句话小结：**'+t['one_liner'],'',
                '**参考资料：**'+'；'.join(t['refs']),'', '---','']
    return '\n'.join(out).rstrip()+'\n'

def brief_html(d):
    parts=[img('img/01-brief-whiteboard.png','架构师早报三栏手绘白板图'),
         '<h1 style="font-size:27px;line-height:1.5;margin:14px 0 8px;">架构师早报 · 三问三答</h1>',
         para('科技热点、架构文章、今日一言，三条原文各对应一个尖锐问题和芒格模型分析。'),
         resource_nav()]
    for i,(r,a) in enumerate(zip(d['raw_sections'],d['brief']),1):
        parts += [f'<section id="question-{i}" style="margin:22px 0 32px;padding-bottom:18px;border-bottom:1px dashed #bbb;">',
                  f'<h2 style="{H2}">技术思考问题{i}：{txt(a["question"])}</h2>',
                  para('核心结论：'+a['core'],True),para('芒格模型：'+model_text(a['models'])),
                  para('模型推演：'+a['analysis']),
                  para('工程落地：'+'；'.join(f'{j}. {act}' for j,act in enumerate(a['actions'],1))),
                  para('边界与验证：'+a['boundary']),para('一句话小结：'+a['summary'],True),
                  para('参考资料：'+'；'.join(a['refs'])),
                  '<h3 style="font-size:17px;color:#a43d24;margin:15px 0 6px;">早报原始文案 · '+txt(r['tag'])+'</h3>',
                  para(r['text']),'</section>']
    parts += [img('img/02-talk-whiteboard.png','架构师同盟三题架构讨论白板图')]
    return layout('架构师早报 · 三问三答','\n'.join(parts))

def talk_html(d):
    parts=[img('img/02-talk-whiteboard.png','架构师同盟三个独立手绘讨论话题'),
           '<h1 style="font-size:27px;line-height:1.45;margin:12px 0 8px;">架构师同盟 · 可直接发群的三个话题</h1>',
           para('每题先发群聊引导语，再发对应配图。下面的参考回答适合讨论后补充，不应提前替大家回答。'),
           '<p style="margin:12px 0;padding:9px 12px;border:1px solid #e9c5b8;background:#fffaf7;">'
           '<a href="index.html#resources" target="_blank" rel="noopener noreferrer" style="color:#a43d24;text-decoration:underline;">← 返回早报资源导航</a></p>']
    for i,(r,t) in enumerate(zip(d['raw_sections'],d['forum']),1):
        msg=t['message'].replace('**','')
        parts += [f'<section style="margin:28px 0 38px;padding-bottom:24px;border-bottom:1px dashed #aaa;">',
                  f'<h2 style="{H2}">话题{i}：{txt(t["headline"])}</h2>',
                  '<p style="margin:6px 0;color:#777;font-size:13px;">来自 '+txt(r['tag'])+' · '+txt(t['anchor'])+'</p>',
                  '<p style="font-size:15px;font-weight:700;color:#ba472d;margin:14px 0 6px;">可直接复制到微信群</p>',
                  '<div style="white-space:pre-wrap;font-family:inherit;font-size:16px;line-height:1.9;padding:16px 14px;'
                  'border:1px solid #efb8a6;border-left:4px solid #df6242;background:#fffaf7;user-select:text;'
                  '-webkit-user-select:text;">'+txt(msg).replace('<br/>','\n')+'</div>',
                  img(f'img/talk-topic-{i}.png',f'话题{i}独立手绘图：{t["headline"]}'),
                  '<p style="font-size:15px;font-weight:700;color:#a34728;">主持人参考答案（讨论后使用）</p>',
                  para('第一句回答：'+t['core'],True),para('芒格模型：'+model_text(t['models'])),
                  para('讨论背景：'+t['background']),para('冲突角度：'+t['angle']),
                  para('模型推演：'+t['reason']),para('数字人/智能客服项目方案：'+t['project']),
                  para('待改进项：'+t['improve']),para('验证指标：'+t['metrics']),
                  para('一句话小结：'+t['one_liner'],True),
                  para('参考资料：'+'；'.join(t['refs'])),'</section>']
    parts += [img('img/01-brief-whiteboard.png','本期早报三栏手绘信息图')]
    return layout('架构师同盟 · 三个技术讨论话题','\n'.join(parts))

def image_quality(path):
    im=Image.open(path);im.verify();im=Image.open(path).convert('RGB')
    if im.width<1200 or im.height<650:raise ValueError('白板图分辨率过低')
    # Whiteboard background, minority orange/red writing: deterministic coarse check only.
    sm=im.resize((160,90));pix=list(sm.get_flattened_data());bright=sum(min(q)>195 for q in pix)/len(pix)
    black=sum(max(q)<125 for q in pix)/len(pix)
    orange=sum(q[0]>q[1]*1.22 and q[0]>q[2]*1.2 and q[0]>115 for q in pix)/len(pix)
    if bright<0.48 or black<0.015 or orange<0.001:raise ValueError('白底黑线红橙强调特征不足')
    return {'dimensions':list(im.size),'bright_ratio':round(bright,3),'dark_ratio':round(black,3),'red_orange_ratio':round(orange,4)}

def build(d, img_brief, img_talk, out, gen_brief, gen_talk):
    """v6: deliver the approved original ImageGen whiteboard artwork, not card re-composition.

    Only permissible postprocessing: crop a complete pre-existing rectangular TOPIC
    and crop top decorative header on the old talk artwork. Never redraw labels.
    """
    validate(d)
    if not gen_brief or not gen_talk:raise ValueError('原画溯源说明不得为空')
    out=Path(out);(out/'img').mkdir(parents=True,exist_ok=True);(out/'md').mkdir(exist_ok=True)
    sources=[]
    for src, name, receipt in [(img_brief,'original-brief-imagegen.png',gen_brief),
                               (img_talk,'original-talk-imagegen.png',gen_talk)]:
        src=Path(src);image_quality(src); raw=src.read_bytes();(out/'img'/name).write_bytes(raw)
        sources.append({'file':name,'source':'image_gen generated image','generation_id':receipt,
                        'sha256_original':sha(raw),'original_pixels_unchanged':True})
    # Render the actual generated art, not the earlier Pillow-rendered template.
    brief=Image.open(out/'img/original-brief-imagegen.png').convert('RGB')
    talk=Image.open(out/'img/original-talk-imagegen.png').convert('RGB')
    if brief.size!=(1448,1086) or talk.size!=(1448,1086):
        raise ValueError('本次验收样例要求已复核的 1448×1086 手绘原画，别的图片需要重新人工核验裁切坐标')
    brief.save(out/'img/01-brief-whiteboard.png',optimize=True)
    # Remove only the old image's top-right production note by cropping its header.
    talk_crop=[0,101,1448,1076]
    talk.crop(tuple(talk_crop)).save(out/'img/02-talk-whiteboard.png',optimize=True)
    items=[]
    for group, src_img, slices in [
        ('brief', brief, [(9,150,475,1073),(483,150,935,1073),(941,150,1439,1073)]),
        ('talk',talk,[(7,101,469,1076),(480,101,929,1076),(937,101,1438,1076)])
    ]:
        for i,rect in enumerate(slices,1):
            name=f'{group}-topic-{i}.png'
            src_img.crop(rect).save(out/'img'/name,optimize=True)
            items.append({'file':name,'derived_from':'original-'+group+'-imagegen.png',
                         'operation':'topic pixel crop only','crop_xyxy':list(rect),
                         'sha256':sha((out/'img'/name).read_bytes())})
    bmd=brief_md(d);tmd=forum_md(d)
    (out/'md/zaobao.md').write_text(bmd,encoding='utf8')
    (out/'md/talk.md').write_text(tmd,encoding='utf8')
    (out/'index.html').write_text(brief_html(d),encoding='utf8')
    (out/'talk.htm').write_text(talk_html(d),encoding='utf8')
    (out/'md/talk-prompts.txt').write_text('\n\n'.join(f'【话题{i}】\n'+t['message'].replace('**','') for i,t in enumerate(d['forum'],1))+'\n',encoding='utf8')
    thumbs=[{'file':'01-brief-whiteboard.png','derived_from':'original-brief-imagegen.png',
              'operation':'lossless re-encode; no diagram redraw','sha256':sha((out/'img/01-brief-whiteboard.png').read_bytes())},
            {'file':'02-talk-whiteboard.png','derived_from':'original-talk-imagegen.png',
              'operation':'crop top 101px production copy only','crop_xyxy':talk_crop,
              'sha256':sha((out/'img/02-talk-whiteboard.png').read_bytes())}]
    images=sources+thumbs+items
    imagepaths=['img/'+r['file'] for r in images]
    meta={'title':d['title'],'summary':'三条早报素材对应三道技术问答和三道可发群的架构讨论。',
          'backgroundImage':'img/01-brief-whiteboard.png','articlePath':'index.html','talkPath':'talk.htm',
          'imagePaths':imagepaths,'tags':['架构师早报','架构师同盟','Gemini Agent','AI编程','技术判断力'],
          'checkStatus':'unaudited',
          'resourceLinks':[{'category':cat,'label':label,'path':uri} for cat,entries in RESOURCE_NAV for label,uri in entries]}
    (out/'index.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
    manifest={'style_version':'approved-cartoon-whiteboard-v6',
              'images_are_genuine_imagegen_art':True,
              'final_posters_are_derived_from_real_imagegen_art':True,
              'note':'talk source imported from prior ImageGen conversation; generation ID unavailable, not invented',
              'images':images,'research_note':d['research_note']}
    (out/'imagegen-provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    return {'all_links':validate_all_html_links(out), 'navigation':validate_local_navigation(out),
            'brief_answer_chars':[count_answer(''.join([model_text(a['models']),a['core'],a['analysis'],' '.join(a['actions']),a['boundary'],a['summary']])) for a in d['brief']],
            'forum_answer_chars':[count_answer(''.join([t['core'],model_text(t['models']),t['reason'],t['project'],t['improve'],t['metrics'],t['one_liner']])) for t in d['forum']],
            'assets':[str(x.relative_to(out)) for x in out.rglob('*') if x.is_file()]}

def timestamped_archive_name(at=None, timezone_name='Asia/Shanghai'):
    """Deterministically name the sole deliverable article-YYYYMMDDHHMM.zip.

    at: an optional timezone-aware datetime for tests or a known execution clock.
    The clock is converted into the specified user timezone before formatting.
    """
    try:
        user_tz=ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as ex:
        raise ValueError('无效用户时区: '+str(timezone_name)) from ex
    if at is None:
        at=datetime.now(user_tz)
    elif not isinstance(at,datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError('测试或调用时指定的时间必须包含时区')
    return 'article-'+at.astimezone(user_tz).strftime('%Y%m%d%H%M')+'.zip'

def make_zip(folder,output):
    folder=Path(folder); output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    contents=[p for p in folder.rglob('*') if p.is_file() and not p.name.endswith('.zip') and not p.relative_to(folder).parts[0]=='reports']
    if any('skill' in p.relative_to(folder).parts for p in contents):raise ValueError('正式 article ZIP 严禁包含 Skill 目录')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in contents:z.write(p,p.relative_to(folder).as_posix())
    with zipfile.ZipFile(output) as z:
        if z.testzip():raise ValueError('ZIP 校验失败')
        names=set(z.namelist());needed={'md/zaobao.md','md/talk.md','index.html','talk.htm','index.json'}
        if not needed.issubset(names):raise ValueError('必需文件缺失')
        if any(p.startswith('skill/') for p in names):raise ValueError('Skill 被混入正式包')
        meta=json.loads(z.read('index.json'))
        if not set(meta['imagePaths']).issubset(names):raise ValueError('图片路径失效')
        if not set(link['path'] for link in meta.get('resourceLinks',[])).issubset(names):
            raise ValueError('index.json 资源导航路径失效')
        if not set(local_nav_targets()).issubset(names):raise ValueError('ZIP资源导航目标缺失')
        # Link coverage within the ZIP is separately revalidated by the navigation parser.
        validate_local_navigation(folder)
        validate_all_html_links(folder)
        manifest=json.loads(z.read('imagegen-provenance.json'))
        for r in (r for r in manifest['images'] if 'sha256_original' in r):
            if sha(z.read('img/'+r['file']))!=r['sha256_original']:raise ValueError('ImageGen 原图哈希不一致')
        for r in (r for r in manifest['images'] if 'sha256' in r):
            if sha(z.read('img/'+r['file']))!=r['sha256']:raise ValueError('分区成品或截图哈希不一致')
    return len(contents)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--brief-image',required=True)
    ap.add_argument('--talk-image',required=True);ap.add_argument('--out',required=True);ap.add_argument('--gen-brief',required=True);ap.add_argument('--gen-talk',required=True)
    ap.add_argument('--timezone',default='Asia/Shanghai',help='用户时区，默认 Asia/Shanghai；格式为 IANA 时区名称')
    a=ap.parse_args();d=json.loads(Path(a.input).read_text('utf8'))
    build(d,a.brief_image,a.talk_image,a.out,a.gen_brief,a.gen_talk)
    archive=Path(a.out)/timestamped_archive_name(timezone_name=a.timezone)
    make_zip(a.out,archive)
    print(archive)
if __name__=='__main__':main()
