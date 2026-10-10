import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'scripts'))
from build import validate, brief_md, forum_md, brief_html, talk_html, image_quality, make_zip, build, sha, resource_nav, RESOURCE_NAV, local_nav_targets, validate_local_navigation, timestamped_archive_name, normalize_canvas, CANVAS

class ZaobaoV6Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((HERE/'examples/demo-2026-10-08.json').read_text('utf8'))
    def test_01_input_valid(self):self.assertTrue(validate(self.data))
    def test_02_source_columns_in_order(self):self.assertEqual([x['tag'] for x in self.data['raw_sections']],['科技热点','架构文章推荐','今日一言'])
    def test_03_source_raw_preserved(self):
        text=brief_md(self.data)
        for x in self.data['raw_sections']:self.assertIn(x['text'].replace("\n\n","\n"),text)
    def test_04_brief_three_blocks(self):self.assertEqual(len(brief_md(self.data).strip().split('\n\n')),3)
    def test_05_each_brief_one_separator(self):
        for x in brief_md(self.data).strip().split('\n\n'):self.assertEqual(x.count(' | '),1)
    def test_06_all_brief_questions(self):
        for i,x in enumerate(self.data['brief'],1):self.assertIn('技术思考问题'+str(i)+'：'+x['question'],brief_md(self.data))
    def test_07_models_are_defined(self):
        for x in self.data['brief']+self.data['forum']:
            for m in x['models']:self.assertTrue(len(m['definition'])>=8)
    def test_08_brief_answers_short(self):
        from build import count_answer,model_text
        for x in self.data['brief']:
            a=''.join([model_text(x['models']),x['core'],x['analysis'],' '.join(x['actions']),x['boundary'],x['summary']])
            self.assertLessEqual(count_answer(a),500)
    def test_09_forum_answers_short(self):
        from build import count_answer,model_text
        for x in self.data['forum']:
            a=''.join([x['core'],model_text(x['models']),x['reason'],x['project'],x['improve'],x['metrics'],x['one_liner']])
            self.assertLessEqual(count_answer(a),500)
    def test_10_forum_provenance_each_column(self):
        for raw,x in zip(self.data['raw_sections'],self.data['forum']):self.assertIn(x['anchor'],raw['text'])
    def test_11_one_question_per_intro(self):
        for x in self.data['forum']:self.assertEqual(x['message'].count('？'),1)
    def test_12_wechat_tone(self):
        for x in self.data['forum']:self.assertTrue(x['message'].startswith('各位老师早上好。'))
    def test_13_initial_stance_before_question(self):
        for x in self.data['forum']:
            self.assertLess(x['message'].index('我的判断是：'),x['message'].index('？'))
    def test_14_forum_direct_copy_code_blocks(self):self.assertEqual(forum_md(self.data).count('```text'),3)
    def test_15_forum_images_references(self):
        for i in (1,2,3):self.assertIn(f'../img/talk-topic-{i}.png',forum_md(self.data))
    def test_16_original_reference(self):self.assertIn('2756348',brief_md(self.data))
    def test_17_html_raw_text(self):
        h=brief_html(self.data)
        for raw in self.data['raw_sections']:self.assertIn(raw['text'][:23],h)
    def test_18_html_copyable_text(self):self.assertIn('user-select:text',talk_html(self.data))
    def test_19_html_no_script_or_external_css(self):
        for h in [brief_html(self.data),talk_html(self.data)]:
            self.assertNotIn('<script',h);self.assertNotIn('<link rel=',h);self.assertIn('style=',h)
    def test_20_html_all_topic_images(self):
        h=talk_html(self.data)
        for i in (1,2,3):self.assertIn(f'img/talk-topic-{i}.png',h)
    def test_21_bad_column_rejected(self):
        d=copy.deepcopy(self.data);d['raw_sections'][0]['tag']='架构文章推荐'
        with self.assertRaises(ValueError):validate(d)
    def test_22_cross_column_anchor_rejected(self):
        d=copy.deepcopy(self.data);d['forum'][1]['anchor']='GPT-6 Sol'
        with self.assertRaises(ValueError):validate(d)
    def test_23_missing_model_definition_rejected(self):
        d=copy.deepcopy(self.data);d['forum'][0]['models'][0]['definition']=''
        with self.assertRaises(ValueError):validate(d)
    def test_24_double_question_rejected(self):
        d=copy.deepcopy(self.data);d['forum'][0]['message']+='第二个问题呢？'
        with self.assertRaises(ValueError):validate(d)
    def test_25_missing_stance_rejected(self):
        d=copy.deepcopy(self.data);d['forum'][0]['message']=d['forum'][0]['message'].replace('我的判断是：','')
        with self.assertRaises(ValueError):validate(d)
    def test_26_long_answer_rejected(self):
        d=copy.deepcopy(self.data);d['forum'][0]['project']='增加自我重复无效内容'*90
        with self.assertRaises(ValueError):validate(d)
    def test_27_missing_raw_rejected(self):
        d=copy.deepcopy(self.data);d['raw_sections'][0]['text']=''
        with self.assertRaises(ValueError):validate(d)
    def test_28_wrong_protocol_rejected(self):
        d=copy.deepcopy(self.data);d['brief'][0]['refs']=['ftp://bad.example']
        with self.assertRaises(ValueError):validate(d)
    def test_29_missing_genid_rejected(self):
        from build import build
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):build(self.data,'/missing','/missing',td,'','same')
    def test_30_unreadable_image_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.png';p.write_bytes(b'not image')
            with self.assertRaises(Exception):image_quality(p)
    def test_31_forum_md_starts_prompts_before_answer(self):
        m=forum_md(self.data)
        self.assertLess(m.index('群发引导语（直接复制）'),m.index('我的参考回答（讨论后再发）'))
    def test_32_en_names(self):
        result=['md/zaobao.md','md/talk.md'];self.assertTrue(all(z.isascii() for z in result))
    def test_33_integrated_package_and_provenance(self):
        sources=(os.environ.get('ZAOBAO_TEST_BRIEF_IMAGE'),os.environ.get('ZAOBAO_TEST_TALK_IMAGE'))
        if not all(sources):self.skipTest('未设置真实 ImageGen 画稿路径，不能用伪图片代测')
        with tempfile.TemporaryDirectory() as td:
            info=build(self.data,*sources,td,'3136aa9f-e539-4607-99ec-c09d0549f76b','5a874041-2e30-47a1-9dd3-0a207a960a51')
            zpath=Path(td)/timestamped_archive_name();num=make_zip(td,zpath)
            self.assertGreaterEqual(num,16)
            with zipfile.ZipFile(zpath) as z:
                self.assertIsNone(z.testzip());names=set(z.namelist())
                self.assertTrue({'md/zaobao.md','md/talk.md','index.html','talk.htm','index.json'}.issubset(names))
                self.assertFalse(any(x.startswith(('skill/','zaobao/')) for x in names))
                meta=json.loads(z.read('index.json'))
                self.assertEqual(meta['checkStatus'],'unaudited')
                manifest=json.loads(z.read('imagegen-provenance.json'))
                self.assertTrue(manifest['final_posters_are_derived_from_real_imagegen_art'])
                self.assertTrue(manifest['images_are_genuine_imagegen_art'])
                self.assertEqual(len(manifest['images']),10)
                self.assertEqual(len([x for x in names if x.startswith('img/')]),10)
                self.assertEqual({x['path'] for x in meta['resourceLinks']},{'index.html','talk.htm','md/zaobao.md'})
                for resource in local_nav_targets():self.assertIn(resource,names)
                for i in range(1,4):
                    self.assertIn(f'img/talk-topic-{i}.png',names)
                    self.assertIn(f'img/brief-topic-{i}.png',names)
            self.assertGreaterEqual(info['all_links']['checked_all_anchors'],16)

    def test_34_navigation_adds_only_requested_markdown(self):
        page=brief_html(self.data)
        self.assertIn('<nav aria-label="资源导航" id="resources"',page)
        self.assertIn('HTML 页面',page)
        self.assertIn('自媒体创作',page)
        self.assertIn('href="md/zaobao.md"',page)
        self.assertNotIn('可复制文稿',page);self.assertNotIn('手绘白板图片',page)
        self.assertNotIn('本页定位',page)

    def test_35_navigation_two_html_plus_one_markdown(self):
        page=brief_html(self.data)
        from html.parser import HTMLParser
        class NavParser(HTMLParser):
            def __init__(self):super().__init__();self.in_nav=False;self.refs=[]
            def handle_starttag(self,t,attrs):
                v=dict(attrs)
                if t=='nav':self.in_nav=True
                if t=='a' and self.in_nav:self.refs.append(v)
            def handle_endtag(self,t):
                if t=='nav':self.in_nav=False
        n=NavParser();n.feed(page)
        self.assertEqual({x['href'] for x in n.refs},{'index.html','talk.htm','md/zaobao.md'})
        for a in n.refs:self.assertEqual(a['target'],'_blank')
        self.assertEqual(set(local_nav_targets()),{'index.html','talk.htm','md/zaobao.md'})

    def test_36_inline_question_ids_preserved_without_nav(self):
        page=brief_html(self.data)
        for i in range(1,4):
            self.assertIn(f'id="question-{i}"',page)
            self.assertNotIn(f'href="#question-{i}"',page)

    def test_37_talk_return_is_new_tab(self):
        page=talk_html(self.data)
        self.assertIn('href="index.html#resources" target="_blank"',page)

    def test_38_navigation_relative_only(self):
        for uri in local_nav_targets():
            self.assertFalse(uri.startswith('/'))
            self.assertNotIn('..',Path(uri).parts)
            self.assertEqual(Path(uri).suffix.lower(),{ 'index.html':'.html', 'talk.htm':'.htm', 'md/zaobao.md':'.md'}[uri])

    def test_39_broken_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'index.html').write_text(brief_html(self.data),'utf8')
            (root/'index.html').write_text((root/'index.html').read_text('utf8').replace('href="talk.htm"','href="lost.htm"'),'utf8')
            (root/'talk.htm').write_text(talk_html(self.data),'utf8')
            with self.assertRaises(ValueError):validate_local_navigation(root)

    def test_40_missing_blank_is_rejected(self):
        from build import validate_all_html_links
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'index.html').write_text(brief_html(self.data).replace('href="talk.htm" target="_blank"','href="talk.htm"'),'utf8')
            (root/'talk.htm').write_text(talk_html(self.data),'utf8')
            with self.assertRaisesRegex(ValueError,'未使用 _blank'):validate_all_html_links(root)

    def test_41_navigation_no_script(self):
        nav=resource_nav();self.assertNotIn('<script',nav);self.assertNotIn('onclick=',nav)
        self.assertEqual(sum(len(items) for _,items in RESOURCE_NAV),3)

    def test_42_real_images_whiteboard_style(self):
        sources=(os.environ.get('ZAOBAO_TEST_BRIEF_IMAGE'),os.environ.get('ZAOBAO_TEST_TALK_IMAGE'))
        if not all(sources):self.skipTest('无真实 ImageGen 输入图')
        for path in sources:
            q=image_quality(path)
            self.assertGreater(q['bright_ratio'],0.50)
            self.assertGreater(q['red_orange_ratio'],0.01)

    def test_43_every_anchor_is_blank_in_both_html(self):
        from html.parser import HTMLParser
        class Links(HTMLParser):
            def __init__(self):super().__init__();self.links=[]
            def handle_starttag(self,tag,attrs):
                if tag=='a':self.links.append(dict(attrs))
        for page in (brief_html(self.data),talk_html(self.data)):
            p=Links();p.feed(page)
            self.assertGreater(len(p.links),2)
            for link in p.links:
                self.assertEqual(link.get('target'),'_blank')
                self.assertIn('noopener',link.get('rel',''))
                self.assertIn('noreferrer',link.get('rel',''))

    def test_44_only_zaobao_markdown_not_other_resources(self):
        nav=resource_nav()
        self.assertIn('href="md/zaobao.md"',nav)
        for marker in ('href="md/talk.md"','href="img/','href="#question','href="md/talk-prompts.txt"'):
            self.assertNotIn(marker,nav)

    def test_45_original_topics_only_in_three_sections(self):
        d=self.data
        self.assertIn('Gemini Agent',d['raw_sections'][0]['text'])
        self.assertIn('AI编程和VibeCoding',d['raw_sections'][1]['text'])
        self.assertIn('技术判断力无法只靠阅读获得',d['raw_sections'][2]['text'])

    def test_46_source_art_preserved_without_pillow_repainting(self):
        from PIL import Image
        sources=(os.environ.get('ZAOBAO_TEST_BRIEF_IMAGE'),os.environ.get('ZAOBAO_TEST_TALK_IMAGE'))
        if not all(sources):self.skipTest('需要实际 ImageGen 文件')
        with tempfile.TemporaryDirectory() as td:
            build(self.data,*sources,td,'real-brief','source-from-prior-imagegen')
            for path,kind in [(sources[0],'brief'),(sources[1],'talk')]:
                self.assertEqual((Path(td)/'img'/f'original-{kind}-imagegen.png').read_bytes(),Path(path).read_bytes())

    def test_47_framing_is_pixel_crop_only(self):
        from PIL import Image,ImageChops
        sources=(os.environ.get('ZAOBAO_TEST_BRIEF_IMAGE'),os.environ.get('ZAOBAO_TEST_TALK_IMAGE'))
        if not all(sources):self.skipTest('需要实际 hy3 文件')
        with tempfile.TemporaryDirectory() as td:
            build(self.data,*sources,td,'real-brief','source-from-prior-hy3')
            image=normalize_canvas(Image.open(sources[0]).convert('RGB'))
            for i,box in enumerate([(9,150,475,1073),(483,150,935,1073),(941,150,1439,1073)],1):
                crop=Image.open(Path(td)/'img'/f'brief-topic-{i}.png').convert('RGB')
                self.assertIsNone(ImageChops.difference(crop,image.crop(box)).getbbox())

    def test_48_no_purpose_copy_in_talk_poster_header(self):
        from PIL import Image,ImageChops
        sources=(os.environ.get('ZAOBAO_TEST_BRIEF_IMAGE'),os.environ.get('ZAOBAO_TEST_TALK_IMAGE'))
        if not all(sources):self.skipTest('需要实际 hy3 文件')
        with tempfile.TemporaryDirectory() as td:
            build(self.data,*sources,td,'real-brief','source-from-prior-hy3')
            normalized=normalize_canvas(Image.open(sources[1]).convert('RGB'))
            final=Image.open(Path(td)/'img/02-talk-whiteboard.png').convert('RGB')
            self.assertEqual(final.size,(1448,975))
            self.assertIsNone(ImageChops.difference(final,normalized.crop((0,101,1448,1076))).getbbox())

    def test_49_invalid_security_rel_is_rejected(self):
        from build import validate_all_html_links
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'index.html').write_text(brief_html(self.data).replace('rel="noopener noreferrer"','rel="noopener"'),'utf8')
            (root/'talk.htm').write_text(talk_html(self.data),'utf8')
            with self.assertRaisesRegex(ValueError,'缺少安全 rel'):validate_all_html_links(root)

    def test_51_visual_style_reference_is_packaged(self):
        self.assertTrue((HERE/'assets/style-reference-brief.png').exists())
        self.assertTrue((HERE/'assets/style-reference-talk.png').exists())

    def test_52_purpose_text_is_banned_by_skill(self):
        doc=(HERE/'SKILL.md').read_text('utf8')
        self.assertIn('禁止制作用途文案',doc)
        self.assertIn('用户确认的白板漫画手绘',doc)
        self.assertIn('article-YYYYMMDDHHMM.zip',doc)

    def test_50_safe_new_tab_return_and_links(self):
        self.assertEqual(len([uri for uri in local_nav_targets() if uri.endswith(('.htm','.html'))]),2)
        self.assertIn('target="_blank"',talk_html(self.data))

    def test_53_filename_uses_user_timezone_and_12_digits(self):
        from datetime import datetime, timezone
        self.assertEqual(timestamped_archive_name(datetime(2026,10,10,4,57,tzinfo=timezone.utc)),
                         'article-202610101257.zip')
        self.assertEqual(timestamped_archive_name(datetime(2026,10,10,4,57,tzinfo=timezone.utc),'America/New_York'),
                         'article-202610100057.zip')

    def test_54_bad_timezones_and_naive_datetimes_rejected(self):
        from datetime import datetime
        with self.assertRaises(ValueError):timestamped_archive_name(datetime(2026,10,10,12,57))
        with self.assertRaises(ValueError):timestamped_archive_name(timezone_name='Invalid/NeverExists')

    def test_55_archive_name_format(self):
        import re
        self.assertRegex(timestamped_archive_name(),r'^article-\d{12}\.zip$')

    def test_56_page_md_link_is_new_tab_and_safe(self):
        page=brief_html(self.data)
        self.assertIn('href="md/zaobao.md" target="_blank" rel="noopener noreferrer"',page)

    def test_57_skill_final_output_contract(self):
        doc=(HERE/'SKILL.md').read_text('utf8')
        self.assertIn('最终回复只展示',doc)
        self.assertIn('article-YYYYMMDDHHMM.zip',doc)
        self.assertIn('默认不得额外展示',doc)

if __name__=='__main__':unittest.main()
