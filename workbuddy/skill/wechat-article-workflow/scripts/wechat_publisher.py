# -*- coding: utf-8 -*-
"""wechat_publisher.py —— 微信公众号 API 封装（草稿箱推送用）

凭据来源：~/.workbuddy/wechat_config.json
  {"appid": "...", "appsecret": "...", "author": "公众号名"}

Why 这样设计（2026-09-30 踩坑）:
  之前把 APPID/APPSECRET 写在 push_draft.py 里，导致「从上一篇复制」时凭据丢失、
  且不同文章版本不一致。统一改为 load_wechat_config() 从用户级配置读，
  publisher 不导出 APPID/APPSECRET，push_draft.py 只调用方法。

依赖: requests
  未安装时：<managed python> -m pip install requests
"""
import json
import os
import re

try:
    import requests
except ImportError:  # pragma: no cover
    raise SystemExit(
        "缺少依赖 requests。请先安装：\n"
        "  <managed python exe> -m pip install requests"
    )

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".workbuddy", "wechat_config.json")
API = "https://api.weixin.qq.com/cgi-bin"


def load_wechat_config(path=CONFIG_PATH):
    """读取公众号配置。返回 dict(appid, appsecret, author)。"""
    if not os.path.exists(path):
        raise SystemExit(
            "未找到配置文件: %s\n"
            "请创建并填入 appid / appsecret（从 mp.weixin.qq.com -> 设置与开发 -> 基本配置 获取）" % path
        )
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for k in ("appid", "appsecret"):
        v = str(cfg.get(k) or "")
        if not v or v.startswith("填你的"):
            raise SystemExit("配置文件的 %s 尚未填写: %s" % (k, path))
    cfg.setdefault("author", "未署名")
    return cfg


def clean_html(html):
    """清洗不可见脏字符（BOM / 零宽）——微信 API 会因此吞样式。"""
    return re.sub(r"[\ufeff\u200b\u200c\u200d\ufffe]", "", html)


class WeChatPublisher:
    def __init__(self, appid=None, appsecret=None, author=None):
        cfg = load_wechat_config()
        self.appid = appid or cfg["appid"]
        self.appsecret = appsecret or cfg["appsecret"]
        self.author = author or cfg.get("author", "未署名")
        self._token = None

    # ---------- 基础 ----------
    def _post(self, url, payload):
        """ensure_ascii=False，避免中文被转成 \\uXXXX 后公众号显示乱码。"""
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        else:
            body = payload
        r = requests.post(url, data=body,
                          headers={"Content-Type": "application/json; charset=utf-8"},
                          timeout=30)
        return r.json()

    def _check(self, resp, what):
        ec = resp.get("errcode", 0)
        if ec:
            hint = ""
            if ec == 40164:
                hint = "  -> 当前机器公网 IP 不在公众号 IP白名单，去 设置与开发->基本配置 添加"
            elif ec == 45003:
                hint = "  -> 标题超过 64 字限制"
            elif ec == 40001:
                hint = "  -> access_token 失效或 AppSecret 错误"
            raise SystemExit("[微信API错误] %s: errcode=%s errmsg=%s%s"
                             % (what, ec, resp.get("errmsg"), hint))
        return resp

    def access_token(self, force=False):
        if self._token and not force:
            return self._token
        resp = requests.get(
            "%s/token?grant_type=client_credential&appid=%s&secret=%s"
            % (API, self.appid, self.appsecret), timeout=20).json()
        self._check(resp, "获取 access_token")
        self._token = resp["access_token"]
        return self._token

    # ---------- 素材 ----------
    def upload_image(self, path):
        """上传正文内图片，返回可直接写进 <img src> 的 URL。"""
        with open(path, "rb") as f:
            r = requests.post("%s/media/uploadimg?access_token=%s" % (API, self.access_token()),
                              files={"media": (os.path.basename(path), f, "image/png")},
                              timeout=60).json()
        self._check(r, "上传正文图片 %s" % os.path.basename(path))
        return r["url"]

    def upload_thumb(self, path):
        """上传永久图片素材，返回 thumb_media_id（用于封面）。"""
        with open(path, "rb") as f:
            r = requests.post("%s/material/add_material?access_token=%s&type=image" % (API, self.access_token()),
                              files={"media": (os.path.basename(path), f, "image/png")},
                              timeout=60).json()
        self._check(r, "上传封面素材 %s" % os.path.basename(path))
        return r["media_id"]

    # ---------- 草稿 ----------
    def create_draft(self, title, content, digest="", thumb_path=None, author=None,
                     content_source_url="", need_open_comment=0, only_fans_can_comment=0):
        if len(title) > 64:
            raise SystemExit("标题 %d 字，超过微信 64 字上限：%s" % (len(title), title))
        article = {
            "title": title,
            "author": author or self.author,
            "digest": digest,
            "content": clean_html(content),
            "content_source_url": content_source_url,
            "need_open_comment": need_open_comment,
            "only_fans_can_comment": only_fans_can_comment,
        }
        if thumb_path:
            article["thumb_media_id"] = self.upload_thumb(thumb_path)
        resp = self._post("%s/draft/add?access_token=%s" % (API, self.access_token()),
                          {"articles": [article]})
        self._check(resp, "创建草稿")
        return resp["media_id"], article

    # ---------- 发表（非群发，freepublish）----------
    def freepublish_submit(self, media_id):
        """提交草稿发表。不群发、不推粉丝。返回 publish_id。"""
        resp = self._post("%s/freepublish/submit?access_token=%s" % (API, self.access_token()),
                          {"media_id": media_id})
        self._check(resp, "提交发表")
        return resp.get("publish_id")

    def freepublish_get(self, publish_id):
        """查询发表状态。publish_status: 0成功 1发表中 2原创失败 3常规失败 4审核不通过。"""
        resp = self._post("%s/freepublish/get?access_token=%s" % (API, self.access_token()),
                          {"publish_id": publish_id})
        self._check(resp, "查询发表状态")
        return resp

    def freepublish_wait(self, publish_id, timeout_sec=90, interval=3):
        """轮询直到成功或失败。成功返回 article_detail（含 article_url）。"""
        import time
        deadline = time.time() + timeout_sec
        last = None
        while time.time() < deadline:
            last = self.freepublish_get(publish_id)
            st = last.get("publish_status")
            if st == 0:
                return last
            if st in (2, 3, 4, 5, 6):
                raise SystemExit("[发表失败] publish_status=%s detail=%s" % (st, last))
            time.sleep(interval)
        raise SystemExit("[发表超时] publish_id=%s last=%s" % (publish_id, last))

