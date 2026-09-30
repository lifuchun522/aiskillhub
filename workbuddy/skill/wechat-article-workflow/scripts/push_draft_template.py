# -*- coding: utf-8 -*-
"""push_draft_template.py —— 公众号草稿推送模板

用法:
  1. 复制到文章目录并改名为 push_draft.py，同目录放:
       article_body.html   微信安全HTML，含 {img0}~{imgN} 占位
       publish_config.json 标题/摘要/封面配置
       comics/img0.png...  正文图（img0 = 封面图，也可用 covers/cover_final.png）
       wechat_publisher.py 从本 skill scripts/ 复制
  2. python push_draft.py

铁律（13篇复盘）:
  - 只改 TITLE / DIGEST / IMAGE_FILES，其余逻辑不要重写
  - 先跑 generate_preview.py 看效果，预览通过再推
  - 绝不自动发布，草稿建好后人工确认
"""
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from wechat_publisher import WeChatPublisher, clean_html  # noqa: E402

# ============ 只改这里 ============
COMICS_DIR = os.path.join(BASE_DIR, "comics")
COVER_IMAGE = os.path.join(BASE_DIR, "covers", "cover_final.png")  # thumb，缺则用 comics/img0.png
# 正文图：键 = {imgX} 里的 X，值 = comics/ 下的文件名。键必须与 HTML 占位符一致。
# 数字键按 {img0},{img1}... 连续；非数字键用于脚本生成的结构图（如 {img_arch}）
IMAGE_FILES = {
    "0": "img0.png",
    "1": "img1.png",
    "2": "img2.png",
    "3": "img3.png",
    "_arch": "img_arch.png",
    "4": "img4.png",
}
# ==================================


def load_config():
    p = os.path.join(BASE_DIR, "publish_config.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    cfg = load_config()
    title = cfg["title"]
    digest = cfg.get("digest", "")

    wp = WeChatPublisher()
    print("=" * 50)
    print("推送文章：%s" % title)
    print("标题字数：%d 字" % len(title))
    print("图片数量：%d 张" % len(IMAGE_FILES))
    print("=" * 50)

    print("\n[1/3] 上传正文图片...")
    urls = {}
    for key, fn in IMAGE_FILES.items():
        p = os.path.join(COMICS_DIR, fn)
        if not os.path.exists(p):
            print("  [SKIP] 缺图 {img%s} <- %s" % (key, fn))
            urls[key] = ""
            continue
        urls[key] = wp.upload_image(p)
        print("  {img%s} <- %s  [OK]" % (key, fn))
    # 封面 thumb：优先 covers/cover_final.png，没有就用 comics 里的第一张
    first = next(iter(IMAGE_FILES.values()))
    thumb = COVER_IMAGE if os.path.exists(COVER_IMAGE) else os.path.join(COMICS_DIR, first)

    print("\n[2/3] 读取文章 HTML 模板...")
    with open(os.path.join(BASE_DIR, "article_body.html"), "r", encoding="utf-8") as f:
        tpl = clean_html(f.read())
    # 用 format 注入，避免 f-string 与中文符号冲突
    content = tpl
    for key, u in urls.items():
        content = content.replace("{img%s}" % key, u)
    left = re.findall(r"\{img(\w+)\}", content)
    if left:
        print("  [WARN] 仍有未替换占位符: %s" % left)
    print("  HTML 已加载，图片 URL 已替换")

    print("\n[3/3] 创建草稿...")
    media_id, article = wp.create_draft(title=title, content=content,
                                        digest=digest, thumb_path=thumb)
    print("[草稿] 创建成功! media_id: %s" % media_id)
    print("  -> 去 https://mp.weixin.qq.com/ 「草稿箱」预览并手动发布")


if __name__ == "__main__":
    main()
