---
name: ppt-walkthrough-video
description: 把一份 PPT（可配一篇文章/讲稿）做成 1920×1080 的双版本讲解视频：右侧显示当前讲解页，左侧是结构化逻辑动图，底部单行字幕；出片为云扬配音，页切换与字幕严格对齐真实配音时轴，并输出原速 + 1.2 倍速两个 mp4。当用户提到「把这个 PPT 做成讲解视频」「PPT 讲解视频」「按这份 PPT 录一课」「把课件做成带字幕的课程视频」「配一篇文章一起讲」「要 1.2 倍速版本」时使用。
---

# PPT 讲解视频（ppt-walkthrough-video）

一句话：**PPT（+ 可选文章）进，原速与 1.2 倍速两个讲解成片出**，
页切换、字幕、左栏逻辑图三者的时轴都对齐真实配音。

## 什么时候用

适用：
- 手上有一份 **PPT / PPTX / PDF / 拆好的页图**，想变成能直接发的讲解视频；
- 最好还有一篇**同主题文章或讲稿**——它决定讲得深不深（见下）；
- 需要**双版本**：原速（给人细看）+ 1.2 倍速（发平台、通勤听）；
- 需要**精准字幕**与**页对齐**：说到哪一页就翻到哪一页。

不适用：
- 只有零散想法、没有 PPT → 先用别的技能做 deck，或用 `koubo-video-studio`（纯逐字稿路线）；
- 真人出镜、实拍剪辑 → 不是本技能；
- 只是想把 PPT 转成图片/PDF → 用 `pdf` 类技能。

## 开工前必须先问清四件事

**不要拿到 PPT 就开始写稿。** 按 `references/intake.md` 的话术一次问完：

1. **PPT 文件路径**（必需，要文件不要标题）
2. **有没有配套文章 / 讲稿 / 笔记**（**必须主动问**）
   - 有 → 先通读，页序仍以 PPT 为准，文章只提供例子与判断；
   - 没有 → 完全基于 PPT 页面结构来讲，不臆造案例。
   - 用户说「暂时找不到」→ 按「没有」开工，并告知后续补料需要重做那几页。
3. **视频多长**（口径：**1.2 倍速版**）
   - 必须落在 **5~20 分钟**；越界就回问一次，不要自己裁；
   - **不指定** → 按 **15 分钟以内**做，且不低于 5 分钟；
   - 换算：`字数 ≈ T × 350`、`段数 ≈ 字数 ÷ 48`（`budget.py` 自动算）。
4. **片头署名 / 品牌**

## 版式（固定，别改）

1920×1080 / 30fps，深色底，左右分屏：

| 区域 | 坐标 | 内容 |
|---|---|---|
| 左栏 | `x=48 w=800` | 结构化卡片（分类/流程/对照/分层/关系…），字号比宽版大 18% |
| 右栏 | `x=920 w=940` | **当前讲解页**的 PPT 图 + 右下页码 `09/34` |
| 字幕 | 底部 `bottom=96`，46px 单行 | 与配音词级时轴对齐 |

左栏卡片是「把口头逻辑画出来」，不是为了好看。选型看 `references/cards.md`。

## 九步流水线

完整命令与验收点见 `references/pipeline.md`，这里只列骨架：

```bash
SK=~/.workbuddy/skills/ppt-walkthrough-video
# 0 准备工程（一次）
python "$SK/scripts/bootstrap.py"
# 1 导出页图并数清页数 N
python "$SK/scripts/export_slides.py" --src deck.pptx --out ./slides_src
python "$SK/scripts/prep_slides.py" --src ./slides_src --project "$SK/project" --tag p1 --expect N
# 2 时长预算
python "$SK/scripts/budget.py" --pages N [--minutes T]
# 3 写 script.txt（段落间空一行）
# 4 配音 + 字幕
python "$SK/scripts/narrate.py" --text script.txt --dir . --lead-in 4.2
# 5 卡片计划 → 编译校验（必须 --narrow）
python "$SK/scripts/plan_cards.py" --segments segments.json --plan cards_plan.py \
    --out cards.json --sections-out sections.json --narrow
# 6 props + 页时间轴（四个版式参数必须显式给）
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

## 六条铁律（每条都对应一次真实返工）

1. **页数 N 是硬约束**：N 张页图 = N 个起点 = N 页。多切一页，从那一页起全片错位。
   用 `--page-segs`（每页几段）而不是手写 `--starts`，脚本会断言。
2. **PPT 是骨架，文章是血肉**：页序永远照 PPT；文章只补例子、判断、数字、金句。
3. **一页并列 N 条总结，就拆 N 张卡**：一张三行卡配三句话，必错。
4. **渲染前先跑 `semantic_check.py`**：跨段清单逐条判断，改卡只需 1 分钟；渲完再改要重渲帧区间。
5. **必须分块渲染**：全片 40~70 分钟，一次跑完被打断就全丢；每块 ~9000 帧，断点续跑。
6. **响度在 AAC 编码之后测**：wav 达标不等于成片达标，AAC 会把峰值抬高 0.5~0.7 dB。

更细的坑见 `references/pitfalls.md`，交付前的 25 项见 `references/checklist.md`。

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
| `scripts/bootstrap.py` | 准备 Remotion 工程（优先复用已有 node_modules） |
| `scripts/export_slides.py` | PPT/PDF → 逐页 PNG（PowerPoint COM 优先，LibreOffice 兜底） |
| `scripts/prep_slides.py` | 页图改名 `pNN`、校验 16:9、报出页数 N 与清单 |
| `scripts/budget.py` | 时长 → 字数/段数预算；越界校验 |
| `scripts/narrate.py` | 逐字稿 → 云扬配音 + 单行字幕 + 段落实测时点（含 429 退避） |
| `scripts/plan_cards.py` | 卡片计划表 → cards/sections，做字数与结构校验 |
| `scripts/prepare_props.py` | 音频+字幕+卡片 → Remotion props |
| `scripts/add_slides.py` | 注入页时间轴（`--starts` 或 `--page-segs`，含页数断言） |
| `scripts/semantic_check.py` | 渲染前语义核对：空页、跨段、数量不符 |
| `scripts/render.py` | 渲染包装器（浏览器/缓存/换盘/改名四个坑已抹平） |
| `scripts/render_chunks.sh` | 分块渲染，断点续跑 |
| `scripts/merge_chunks.sh` | 合并分块并重挂主音轨（音画零漂移） |
| `scripts/post_final.py` | 原速 + 1.2 倍速双版本，响度与真峰值闭环 |
| `scripts/verify.py` | 成片体检（片头静音、时长、双轨、响度、抽帧） |

工程模板在 `assets/project/`（Remotion 分屏源码）；卡片计划样例在 `assets/cards_plan.example.py`。
参考手册：`intake.md`（问询）、`pipeline.md`（命令）、`page-mapping.md`（切页）、
`cards.md`（卡片类型与字数上限）、`ppt-export.md`（导出）、`pitfalls.md`（坑）、`checklist.md`（验收）。
