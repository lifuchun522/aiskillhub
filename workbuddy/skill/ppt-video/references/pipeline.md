# 流水线：从 PPT 到成片（九步）

设：
- `SK` = 本技能目录（`~/.workbuddy/skills/ppt-walkthrough-video`）
- `W`  = 本次工作目录（如 `<workspace>/ppt_video`）
- `PJ` = Remotion 工程目录（默认 `$SK/project`，由 bootstrap 准备）
- `PY` = python 解释器。Windows 上**优先 `C:/Python313/python.exe`**；
  托管运行时可能缺 `aiohttp`（edge-tts 依赖），缺了就换系统 Python。

---

## 第 0 步 · 准备工程（每台机器只做一次）

```bash
python "$SK/scripts/bootstrap.py"
```

有旧工程就 junction 复用 `node_modules`（秒级）；没有才 `npm install`（走 npmmirror，3~8 分钟）。
产物在 `$SK/project`。

---

## 第 1 步 · PPT → 页图，并数清页数

```bash
mkdir -p "$W/slides_src"
python "$SK/scripts/export_slides.py" --src "你的文件.pptx" --out "$W/slides_src"
python "$SK/scripts/prep_slides.py" --src "$W/slides_src" --project "$PJ" --tag p1 --expect N
```

- 有 PowerPoint → COM 导出 1920×1080（版式 100% 还原）；没有 → LibreOffice 转 PDF 再渲染。
- `prep_slides.py` 会改名成 `p01..pNN`、检查是否 16:9、报出**最终页数 N**。
- `--expect` 填你在 PPT 里看到的页数，用来拦「漏页/多页」。

**这一步的输出 `N` 是后面所有页时间轴的唯一依据。记下来。**

---

## 第 2 步 · 时长预算（写稿前必做）

```bash
python "$SK/scripts/budget.py" --pages N                  # 用户没指定时长
python "$SK/scripts/budget.py" --pages N --minutes 12     # 用户指定
```

给出：字数预算、段落预算、每页平均字数、段落起点骨架。
超范围（<5 或 >20）会直接报错让你回问用户。

---

## 第 3 步 · 写逐字稿 `$W/script.txt`

格式要求（`narrate.py` 只认这个）：

- 纯文本，**段落之间空一行**（一个空行 = 换段 + 0.55s 停顿）；
- 不要标题、不要 markdown、不要「（配图）」标注；
- 每段 45~70 字，一句话一个意思，能照读；
- 数字写成口语（「十六个百分点」而不是「+16.2pp」）；
- 专有名词第一次出现要报全称，后面可简称。

内容要求（这是「讲解」和「念字」的区别）：

1. **页序 = 讲解顺序**，一页一页讲，不要跳；
2. 每页至少有一句「这页在说什么」，让听众知道自己在哪；
3. 有配套文章时，每页挂 1~2 条 PPT 上没有的例子/判断；
4. 开头 2~3 段讲清「这一讲解决什么问题」，结尾 2 段收束 + 一句记得住的话；
5. 页面上的箭头、层级、括号小字都要念到——那才是作者真正想说的。

写完立刻校验：

```bash
python "$SK/scripts/budget.py" --pages N --script "$W/script.txt"
```

超了就删段，别等配音完再发现。

---

## 第 4 步 · 配音 + 字幕

```bash
cd "$W" && python "$SK/scripts/narrate.py" --text script.txt --dir . --lead-in 4.2
```

产物：`final.mp3` / `final.srt` / `segments.json` / `audio/`（分段缓存，改一两句只重合成那几段）。

**必须看自检三项**，任何一项不对就停下：
- 片头电平 `< -55 dB`（证明确实是静音）
- 首句电平 `> -40 dB`（证明确实说话了）
- 音频/规划时长差 `< 0.05s`

遇到 429 限流：脚本内部已做指数退避（最多 8 次）。仍失败就查网络，重跑会自动续跑已完成段。

---

## 第 5 步 · 设计左栏卡片（唯一需要创作的一步）

看 `references/cards.md` 选卡片类型，写成 `$W/cards_plan.py`（从 `$SK/assets/cards_plan.example.py` 复制改）。

选型只问：**这段话在讲什么结构关系？**（并列→split/quad、流程→flow、对照→compare、
层级→pyramid、汇聚→integrate、中心辐射→relation、映射→map、数字→stat、金句→quote、结论→bullets）

节奏：**每 15~25 秒换一张卡**，最长不超过 35 秒；一页通常 2~5 张卡。

然后编译 + 结构校验（字数超限、时间重叠、字段缺失都会被拦）：

```bash
python "$SK/scripts/plan_cards.py" --segments "$W/segments.json" \
    --plan "$W/cards_plan.py" --out "$W/cards.json" --sections-out "$W/sections.json" --narrow
```

`--narrow` 是分屏版式专用（左栏只有 728px 宽，字数上限比宽版大 18%）。**必须加。**

---

## 第 6 步 · 生成 props + 注入页时间轴

```bash
python "$SK/scripts/prepare_props.py" \
  --audio "$W/final.mp3" --transcript "$W/final.srt" --project "$PJ" \
  --title "这堂课讲什么" --subtitle "署名 ｜ 系列名" \
  --cards "$W/cards.json" --sections "$W/sections.json" \
  --audio-name audio_p1.mp3 --out props_p1.json \
  --maxlen 20 --font-size 46 --caption-bottom 96 --title-card 4.0
```

⚠️ **四个版式参数必须显式给**，吃默认会出两种事故：
- 漏 `--caption-bottom`（默认 150）→ 字幕整体偏高，底部留一大块空；
- 漏 `--font-size`（默认 52）→ 字幕过大，快顶到画面里。

页时间轴（**先数页数，再定同样多的起点**）：

```bash
python "$SK/scripts/add_slides.py" --props "$PJ/props_p1.json" \
  --segments "$W/segments.json" --page-segs 2,5,4,3,... \
  --src-prefix slides_p1/p --pages N --ext png
```

- `--page-segs` 比 `--starts` 安全：给「每页几段」，脚本自己累加，不会算错；
- 起点个数 ≠ 页数会直接报错退出；
- 打印出来的「每页首段原文」要逐行看一遍：**这一页讲的是不是这张图**。

---

## 第 7 步 · 渲染前语义核对（省返工的关键）

```bash
python "$SK/scripts/semantic_check.py" --props "$PJ/props_p1.json" --segments "$W/segments.json"
```

看两块：
- **错误**：空页、页轴错位 → 必须修；
- **跨段**：一张卡盖了 2 段以上 → 逐条判断。并列结构（三条总结/四个场景）必须拆卡；
  同一件事的延续可以合并。

修改只动 `cards_plan.py` → 重新跑第 5、6 步（几十秒），此时还没渲染，等于零成本。

---

## 第 8 步 · 探测渲染 → 分块渲染 → 合并

```bash
# 8.1 先渲 5~8 秒真实片段，抽帧看版式（约 1 分钟）
python "$SK/scripts/render.py" --out out/probe_p1.mp4 --frames=9000-9200 --props=props_p1.json
ffmpeg -y -v error -ss 3 -i "$PJ/out/probe_p1.mp4" -frames:v 1 -vf scale=1100:-1 chk.png

# 8.2 算总帧数 = ceil(音频秒数 × 30) + 1
ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/final.mp3"

# 8.3 分块渲染（每块 ~9000 帧，断点续跑）
bash "$SK/scripts/render_chunks.sh" props_p1.json TOTAL_FRAMES 4 p1

# 8.4 合并分块 + 重挂主音轨
bash "$SK/scripts/merge_chunks.sh" p1 4 "$W" "$W/final.mp3" "$W/full_p1.mp4"
```

**为什么必须分块**：全片 3~4 万帧要 40~70 分钟，一次跑完一旦被打断（会话结束、
机器休眠、显存驱动重置）就全丢。分块后每块 ~10 分钟，重跑自动跳过已完成块。

**帧号是 0 起**：总帧数 `TOTAL = ceil(dur×30)+1`，最后一块的末帧是 `TOTAL-1`。
多算 1 帧会让最后一块越界失败。

抽帧验收要**取真实时间段**，不要取 `frames=0`（那是入场动画第 0 帧，看起来像没渲染完）。

---

## 第 9 步 · 后期：两版 + 响度闭环

```bash
python "$SK/scripts/post_final.py" --src "$W/full_p1.mp4" --srt "$W/final.srt" \
  --outdir "$W/final" --name "第1讲_主题_口播讲解" --i -16 --tp -1.0
```

一次产出：
- `..._原速.mp4`（视频流直接 copy，画质无损）
- `..._1.2倍速.mp4`（`setpts=PTS/1.2`，重编视频）
- `..._1.2倍速.srt`（字幕时点同步 /1.2）

脚本内部是**闭环**：增益迭代 → 编码成 AAC → **再测真峰值** → 超标就压低限幅上限重来。
（AAC 会把峰值抬高 0.5~0.7 dB，只测 wav 会漏掉这个。）

达标判据：`I ≈ -16 LUFS`（±0.5）、`TP ≤ -1.0 dBTP`。

最后核对：

```bash
ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$W/final/xxx_原速.mp4"
for f in "$W/final"/*.mp4; do ffmpeg -hide_banner -nostats -i "$f" -af loudnorm=print_format=json -f null - 2>&1 | grep -E '"input_i"|"input_tp"'; done
# 可选：成片体检（片头静音、时长、响度、按卡片中点抽帧）
python "$SK/scripts/verify.py" --video "$W/final/xxx_原速.mp4" --segments "$W/segments.json" \
    --cards "$W/cards.json" --frames-dir "$W/chk_frames"
```

交付：两个 mp4 + 倍速 srt，用 `present_files` 一起给。
