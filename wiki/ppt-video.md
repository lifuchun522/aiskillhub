# ppt-video｜PPT 讲解视频双版本出片（v1.0.0）

> 把一份 **PPT（可配一篇文章/讲稿）** 做成 **1920×1080 的双版本讲解视频**：右侧显示当前讲解页，左侧是结构化逻辑动图，底部单行字幕；页切换与字幕严格对齐真实配音时轴，输出 **原速** 与 **1.2 倍速** 两个 mp4。

仓库路径：[`workbuddy/skill/ppt-video/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/ppt-video)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/ppt-video/SKILL.md) ｜ 概览：[`README.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/ppt-video/README.md)

## 一句话

**PPT（+ 可选文章）进，原速与 1.2 倍速两个讲解成片出**，页切换、字幕、左栏逻辑图三者的时轴都对齐真实配音。

## 它解决什么问题

「把 PPT 念一遍录个屏」做出来的东西没人看得完。真正的讲解视频难在三件事：

| 难点 | 本技能的做法 |
|---|---|
| 说到哪页就该翻到哪页 | 配音时轴驱动切页，`--page-segs` 断言页数 N 是硬约束 |
| 口头逻辑看不见 | 左栏结构化卡片（分类/流程/对照/分层/关系/数据），把话「画」出来 |
| 字幕对不上嘴 | 词级时间戳单行字幕，与音频帧级对齐 |

再加双版本交付：原速给人细看，1.2 倍速发平台、通勤听。

## 能力边界

| 做 | 不做 |
|---|---|
| PPT / PPTX / PDF / 已拆页图 → 讲解视频 | 真人出镜、实拍剪辑 |
| 有配套文章时按文章补深度（PPT 仍是骨架） | 只有零散想法、没有 PPT（先用其它技能做 deck） |
| 云扬配音 + 词级时间戳字幕 | 多语言配音 |
| 结构化卡片：分类/流程/对照/分层/关系/数据 | 把 PPT 原样导出成视频（那不是讲解） |

## 安装

```bash
cp -r workbuddy/skill/ppt-video ~/.workbuddy/skills/ppt-walkthrough-video
cd ~/.workbuddy/skills/ppt-walkthrough-video
python scripts/bootstrap.py    # 准备 Remotion 工程，约 1 分钟，优先复用本机已有依赖
```

依赖：Python 3.10+、ffmpeg / ffprobe、Node 18+、Chrome 或 Edge。PowerPoint 可选（装了导出页图更还原；没有则用 LibreOffice 转 PDF）。

## 九步流水线（骨架）

完整命令与验收点见仓库内 `references/pipeline.md`：

```bash
SK=~/.workbuddy/skills/ppt-walkthrough-video
# 0 准备工程（一次）
python "$SK/scripts/bootstrap.py"
# 1 导出页图并数清页数 N
python "$SK/scripts/export_slides.py" --src deck.pptx --out ./slides_src
python "$SK/scripts/prep_slides.py" --src ./slides_src --project "$SK/project" --tag p1 --expect N
# 2 时长预算（字数 ≈ T × 350，段数 ≈ 字数 ÷ 48）
python "$SK/scripts/budget.py" --pages N [--minutes T]
# 3 写 script.txt（段落间空一行）
# 4 配音 + 字幕
python "$SK/scripts/narrate.py" --text script.txt --dir . --lead-in 4.2
# 5 卡片计划 → 编译校验（必须 --narrow）
python "$SK/scripts/plan_cards.py" --segments segments.json --plan cards_plan.py \
    --out cards.json --sections-out sections.json --narrow
# 6 props + 页时间轴
python "$SK/scripts/prepare_props.py" --audio final.mp3 --transcript final.srt \
    --project "$SK/project" --title "..." --subtitle "署名 ｜ 系列" \
    --cards cards.json --sections sections.json --audio-name audio_p1.mp3 \
    --out props_p1.json --maxlen 20 --font-size 46 --caption-bottom 96 --title-card 4.0
python "$SK/scripts/add_slides.py" --props "$SK/project/props_p1.json" \
    --segments segments.json --page-segs 2,5,4,... --src-prefix slides_p1/p --pages N --ext png
# 7 渲染前语义核对
python "$SK/scripts/semantic_check.py" --props "$SK/project/props_p1.json" --segments segments.json
# 8 探测 → 分块渲染 → 合并
python "$SK/scripts/render.py" --out out/probe.mp4 --frames=9000-9200 --props=props_p1.json
bash "$SK/scripts/render_chunks.sh" props_p1.json TOTAL_FRAMES 4 p1
bash "$SK/scripts/merge_chunks.sh" p1 4 . final.mp3 full_p1.mp4
# 9 两版后期（响度 + 真峰值闭环）
python "$SK/scripts/post_final.py" --src full_p1.mp4 --srt final.srt \
    --outdir final --name "第1讲_主题_口播讲解" --i -16 --tp -1.0
```

总帧数：`TOTAL = ceil(音频秒数 × 30) + 1`，末帧是 `TOTAL-1`（多算 1 帧会让最后一块越界）。

## 版式（固定，别改）

1920×1080 / 30fps，深色底，左右分屏：

| 区域 | 坐标 | 内容 |
|---|---|---|
| 左栏 | `x=48 w=800` | 结构化卡片（分类/流程/对照/分层/关系…），字号比宽版大 18% |
| 右栏 | `x=920 w=940` | **当前讲解页**的 PPT 图 + 右下页码 `09/34` |
| 字幕 | 底部 `bottom=96`，46px 单行 | 与配音词级时轴对齐 |

左栏卡片是「把口头逻辑画出来」，不是为了好看。

## 六条铁律（每条都对应一次真实返工）

1. **页数 N 是硬约束**：N 张页图 = N 个起点 = N 页。多切一页，从那一页起全片错位。用 `--page-segs` 而不是手写 `--starts`，脚本会断言。
2. **PPT 是骨架，文章是血肉**：页序永远照 PPT；文章只补例子、判断、数字、金句。
3. **一页并列 N 条总结，就拆 N 张卡**：一张三行卡配三句话，必错。
4. **渲染前先跑 `semantic_check.py`**：跨段清单逐条判断，改卡只需 1 分钟；渲完再改要重渲帧区间。
5. **必须分块渲染**：全片 40~70 分钟，一次跑完被打断就全丢；每块 ~9000 帧，断点续跑。
6. **响度在 AAC 编码之后测**：wav 达标不等于成片达标，AAC 会把峰值抬高 0.5~0.7 dB。

## 交付标准

| 项 | 标准 |
|---|---|
| 版本 | `_原速.mp4` + `_1.2倍速.mp4` + `_1.2倍速.srt` |
| 时长 | 1.2 倍速版 **5~20 分钟**（用户指定则对齐；未指定 ≤15 分钟） |
| 响度 | `I = -16 ± 0.5 LUFS`，真峰值 `TP ≤ -1.0 dBTP` |
| 画质 | 1920×1080 / 30fps；原速版视频流直接 copy，无二次压缩 |
| 一致性 | 每页抽 1 帧：右栏是当页图、左栏卡与字幕讲同一件事 |

## 脚本索引

| 脚本 | 作用 |
|---|---|
| `bootstrap.py` | 准备 Remotion 工程（优先复用已有 node_modules） |
| `export_slides.py` | PPT/PDF → 逐页 PNG（PowerPoint COM 优先，LibreOffice 兜底） |
| `prep_slides.py` | 页图改名 `pNN`、校验 16:9、报出页数 N 与清单 |
| `budget.py` | 时长 → 字数/段数预算；越界校验 |
| `narrate.py` | 逐字稿 → 云扬配音 + 单行字幕 + 段落实测时点（含 429 退避） |
| `plan_cards.py` | 卡片计划表 → cards/sections，做字数与结构校验 |
| `prepare_props.py` | 音频+字幕+卡片 → Remotion props |
| `add_slides.py` | 注入页时间轴（`--starts` 或 `--page-segs`，含页数断言） |
| `semantic_check.py` | 渲染前语义核对：空页、跨段、数量不符 |
| `render.py` | 渲染包装器（浏览器/缓存/换盘/改名四个坑已抹平） |
| `render_chunks.sh` | 分块渲染，断点续跑 |
| `merge_chunks.sh` | 合并分块并重挂主音轨（音画零漂移） |
| `post_final.py` | 原速 + 1.2 倍速双版本，响度与真峰值闭环 |
| `verify.py` | 成片体检（片头静音、时长、双轨、响度、抽帧） |

工程模板在 `assets/project/`（Remotion 分屏源码）；卡片计划样例在 `assets/cards_plan.example.py`。

## 参考手册

| 文档 | 内容 |
|---|---|
| `references/intake.md` | 开场问询话术与决策树 |
| `references/pipeline.md` | 九步命令与验收点 |
| `references/page-mapping.md` | 页=骨架，切页铁律 |
| `references/cards.md` | 11 种卡片与字数上限 |
| `references/ppt-export.md` | PPT → 页图的三种途径 |
| `references/pitfalls.md` | 踩坑手册 |
| `references/checklist.md` | 交付前 25 项 |
