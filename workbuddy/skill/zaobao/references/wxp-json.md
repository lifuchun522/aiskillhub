# wxp-writer JSON 契约

```json
{
  "title": "本期早报标题",
  "summary": "10至80字概要",
  "backgroundImage": "img/01-brief-whiteboard.png",
  "articlePath": "index.html",
  "talkPath": "talk.htm",
  "imagePaths": [
    "img/01-brief-whiteboard.png",
    "img/02-talk-whiteboard.png",
    "img/talk-topic-1.png",
    "img/talk-topic-2.png",
    "img/talk-topic-3.png"
  ],
  "tags": ["架构师早报","深圳同盟","数字人","智能客服","芒格模型"],
  "checkStatus": "unaudited",
  "resourceLinks": [
    {"category":"HTML 页面", "label":"早报与三问三答", "path":"index.html"},
    {"category":"HTML 页面", "label":"架构师同盟讨论", "path":"talk.htm"},
    {"category":"自媒体创作", "label":"早报 Markdown", "path":"md/zaobao.md"}
  ]
}
```

`index.json` 原始契约参考：`wxp-writer`。`talkPath` 与 `checkStatus` 是 zaobao 的非破坏性扩展。所有图片路径必须是 正式归档 ZIP 中可直接读取的相对路径；发布编辑器通常需要独立上传图像，不等于离线 HTML 自动携带微信素材。

`resourceLinks` 由生成器生成且仅收集三个首页资源导航入口：两个 HTML 文件和 `md/zaobao.md`。不能引用不存在的资源，也不追加其他 Markdown、图片或页内锚点。
