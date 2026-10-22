# 踩坑手册（都是用返工时间换来的）

## 一、版式与字幕

| 症状 | 根因 | 处置 |
|---|---|---|
| 字幕偏高、底部留一大块空 | `prepare_props.py` 漏传 `--caption-bottom`（默认 150） | 显式给 `--caption-bottom 96` |
| 字幕太大、快贴到画面内容 | 漏传 `--font-size`（默认 52） | 显式给 `--font-size 46` |
| 字幕折成两行、压住画面 | `--maxlen` 与配音切分口径不一致 | 固定 `--maxlen 20`，别改小 |
| 片头标题卡时间不够，第一句就进来 | `--title-card` 太小 / `lead-in` 不够 | `--lead-in 4.2` + `--title-card 4.0` 成对给 |
| 字幕整体比语音晚固定几秒 | 片头静音没写进音频流（只偏移了时点） | 必须走 `narrate.py`；它按采样数写入静音 |
| 越到后面字幕越偏 | 逐段 concat mp3 累积 padding 误差 | 同上，`narrate.py` 转 WAV 按采样数拼接 |

## 二、页时间轴（代价最大的一类）

| 症状 | 根因 | 处置 |
|---|---|---|
| 从某页起右边图永远慢一页 | 起点数 ≠ 页数（多切/少切一页） | 先数页图张数 N，再定 N 个起点；用 `--page-segs` |
| 某页一闪而过 / 停留过久 | 起点落在了错误的段落 | 看 `add_slides.py` 打印的「每页首段」 |
| 某页全空、左栏也空 | 该页区间内没有段落 | `semantic_check.py` 会报 ERR |
| 页图 404，右栏空白 | 文件名不是 `pNN.ext` | 用 `prep_slides.py` 统一改名（两位数！`p1.jpg` 找不到） |

**结论：页数错一位，全片作废重渲。** 这一步宁可靠脚本断言，不要靠肉眼数。

## 三、卡片与语义

| 症状 | 根因 | 处置 |
|---|---|---|
| 字幕在说第二条，左栏三条一起亮 | 一张卡盖了多段并列内容 | 按段拆卡（`semantic_check.py` 的「跨段」清单） |
| 旁白说「三个机制」，图上 4 项 | 计划表与旁白不同步 | 以旁白为准改项数 |
| 卡片文字折行/出框 | 超字数上限 | `plan_cards.py` 会拦；按 `references/cards.md` 压缩 |
| 左栏某段停在上一张卡 | 该段没有卡覆盖 | `semantic_check.py` 会提示 |

## 四、配音

| 症状 | 根因 | 处置 |
|---|---|---|
| `429 Invalid response status` | edge-tts 限流 | 脚本内置指数退避（8 次）；密集失败就隔 2 分钟重跑，已合成段会续用 |
| 报 `403` | 旧端点失效 | 必须 `import edge_tts_patch`（`narrate.py` 已内置） |
| `ModuleNotFoundError: aiohttp` | 用了托管 Python | 换 `C:/Python313/python.exe` |
| 时长超预算 | 写稿前没算字数 | 先跑 `budget.py`，写完再 `--script` 复核 |

## 五、渲染

| 症状 | 根因 | 处置 |
|---|---|---|
| 渲染到一半进程消失 | 后台任务在会话结束时被杀（全片 40~70 分钟） | **必须分块渲染**，每块 ~9000 帧 |
| `spawn EFTYPE` / Chrome 起不来 | Remotion 自带 headless shell 在本机不可用 | `render.py` 已改系统 Chrome + `--chrome-mode=chrome-for-testing` |
| webpack 缓存删除失败 | 安全删除 fail-closed | `remotion.config.ts` 已关持久化缓存，别手动打开 |
| 最后一刻 `Permission denied` | 输出文件已存在 | 脚本自动改名 `_v2`；别加 `--overwrite` |
| 最后一块渲染失败 | 总帧数多算 1 帧，末帧越界 | `TOTAL = ceil(dur×30)+1`，末帧 `TOTAL-1` |
| 渲染卡住不动 | 系统盘被中间帧占满 | `render.py` 自动换盘；或传 `--temp-dir` |
| 抽帧看到「只渲染了 3 项」 | 取到了第 0 帧（入场动画未展开） | 抽真实时间段，别取 `frames=0` |

## 六、后期与响度

| 症状 | 根因 | 处置 |
|---|---|---|
| 目标 -14 实收 -18.7，峰值 +1.34 dBTP | `loudnorm` 动态模式在「静音多、峰值突兀」的 TTS 音轨上失准 | 用 `post_final.py`（增益迭代 + 限幅） |
| wav 达标，成片却 +0.5 dBTP | AAC 编码把峰值抬高 0.5~0.7 dB | `post_final.py` 在**编码后**再测峰值并回退重做 |
| 限幅后反而更响、更削波 | `alimiter` 的 `level` 默认 true 会抬电平 | 必须 `level=0` |
| 变速后声画不同步 | `setpts` 写成 `PTS/(1/speed)` | 应为 `PTS/speed`；`post_final.py` 已对 |
| 拼接多章后音量忽大忽小 | 各章响度/声道数不一致 | 先统一到同一 LUFS 与单声道，再 `-c copy` 拼 |

**验收口径：`I ∈ -16 ± 0.5 LUFS`、`TP ≤ -1.0 dBTP`（个别 +0.1~0.3 采样点人耳不可闻，但别当默认）。**

## 七、素材

| 症状 | 根因 | 处置 |
|---|---|---|
| 导出的页图模糊 | LibreOffice 兜底渲染分辨率低 | 优先 PowerPoint COM 导出 1920×1080；或提高 `--zoom` |
| 中文变宋体/丢字 | 本机没装 PPT 里的字体 | 装字体后用 PowerPoint 导出；或在 PPT 里换通用字体 |
| 页面是 4:3 | 原始 PPT 不是 16:9 | 右栏会留边；建议在 PPT 里改成 16:9 再导 |
| 页图顺序乱（1,10,2…） | 按字符串排序 | `prep_slides.py` 按页码数字自然排序 |
