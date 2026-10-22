# ppt-walkthrough-video

把一份 **PPT（可配一篇文章/讲稿）** 做成 **1920×1080 的双版本讲解视频**：
右侧显示当前讲解页，左侧是结构化逻辑动图，底部单行字幕；
页切换与字幕严格对齐真实配音时轴，输出 **原速** 与 **1.2 倍速** 两个 mp4。

## 能力边界

| 做 | 不做 |
|---|---|
| PPT / PPTX / PDF / 已拆页图 → 讲解视频 | 真人出镜、实拍剪辑 |
| 有配套文章时按文章补深度（PPT 仍是骨架） | 只有零散想法、没有 PPT（先用其它技能做 deck） |
| 云扬配音 + 词级时间戳字幕 | 多语言配音 |
| 结构化卡片：分类/流程/对照/分层/关系/数据 | 把 PPT 原样导出成视频（那不是讲解） |

## 开工前会问清四件事

1. **PPT 文件**（必需）
2. **有没有配套文章 / 讲稿 / 笔记** —— 有就用它补 PPT 上没有的例子与判断；
   没有就完全基于 PPT 页面结构讲
3. **视频多长** —— 可选 **5~20 分钟**（口径：1.2 倍速版）；
   不指定则按 **15 分钟以内** 做，且不低于 5 分钟
4. **片头署名 / 品牌**

## 安装

放到用户级技能目录即可：

```
~/.workbuddy/skills/ppt-walkthrough-video/
```

首次使用先准备渲染工程（约 1 分钟，会优先复用本机已有的 Remotion 依赖）：

```
python scripts/bootstrap.py
```

依赖：Python 3.10+、ffmpeg / ffprobe、Node 18+、Chrome 或 Edge。
PowerPoint 可选（装了导出页图更还原；没有则用 LibreOffice 转 PDF）。

## 用法

直接对 Agent 说：

> 把这个 PPT 做成讲解视频：`D:\课程\第3讲.pptx`，配套文章也在同目录，时长 12 分钟

然后按 `SKILL.md` 的九步流水线执行。产物：

```
final/xxx_原速.mp4
final/xxx_1.2倍速.mp4
final/xxx_1.2倍速.srt
```

## 目录

```
SKILL.md                 # 入口：何时用、问询、流水线、六条铁律
references/intake.md     # 开场问询话术与决策树
references/pipeline.md   # 九步命令与验收点
references/page-mapping.md # 页=骨架，切页铁律
references/cards.md      # 11 种卡片与字数上限
references/ppt-export.md # PPT → 页图的三种途径
references/pitfalls.md   # 踩坑手册
references/checklist.md  # 交付前 25 项
scripts/                 # 全部可执行脚本
assets/project/          # Remotion 工程模板（分屏版式）
assets/cards_plan.example.py
```
