# 页面导出：PPT → 逐页图

## 为什么不能直接截屏

截屏会带进任务栏、缩放不一致、页数靠手工数。导出成图能保证：
页数与 PPT 完全一致、分辨率统一、后续脚本可自动化。

## 三种途径，按优先级

### 1. PowerPoint COM（Windows，首选）

`export_slides.py` 默认先试这条。要求本机装了 PowerPoint（`.ppt` 老格式也支持）。

```
python export_slides.py --src "第1讲.pptx" --out ./slides_src
```

- 输出 1920×1080 PNG，版式、字体、SmartArt 全部按原样渲染；
- 缺点是依赖桌面版 Office，且会短暂占用 PowerPoint 进程。

**如果导出的第一页是白底、缺字**：多半是 PPT 用的字体本机没装，装上字体重导。

### 2. LibreOffice → PDF → 渲染（没装 Office 时）

```
soffice --headless --convert-to pdf --outdir ./tmp "第1讲.pptx"
python export_slides.py --src ./tmp/第1讲.pdf --out ./slides_src --zoom 1.4
```

- 中文字体和复杂排版的还原度不如 PowerPoint，**只作兜底**；
- 默认导出图会比 1920 小（16:9 下 `zoom=1.4` 约 1344×756），
  右栏显示 940px 宽，其实够清晰；要更清楚就 `--zoom 2.0`。

### 3. 本来就是 PDF / 图片目录

- PDF：`python export_slides.py --src deck.pdf --out ./slides_src`
- 图片目录（有人先把 PPT 拆成了 jpg）：跳过导出，直接跑 `prep_slides.py`

## 导出后必须做的规范化

```
python prep_slides.py --src ./slides_src --project <工程目录> --tag p1 --expect N
```

它做四件事：

1. 按**页码数字**自然排序（避免 1,10,2 的顺序）；
2. 改名成 `p01.png / p02.png ...`（**两位数**；渲染端按这个名字找图，
   `p1.png` 会 404，表现为右栏空白）；
3. 复制到 `<工程>/public/slides_p1/`；
4. 校验尺寸：非 16:9 会警告（右栏会留黑边，不致命但不好看）。

`--expect N` 用来拦漏页：PDF 导出偶发丢页、或用户给的是删减版。

## 关于分辨率

| 来源 | 典型尺寸 | 右栏 940px 显示效果 |
|---|---|---|
| PowerPoint COM 1920×1080 | 1920×1080 | 最佳 |
| LibreOffice PDF，zoom=1.4 | 1344×756 | 够用（缩放 0.7） |
| LibreOffice PDF，zoom=2.0 | 1920×1080 | 最佳，文件更大 |
| 用户给的原图 1280×720 | 1280×720 | 够用 |

## 页数与「讲解单元」不是一回事

- 一张 PPT 可以讲 3~5 段话（信息密度高的架构图往往最值得展开）；
- 但**页数永远不能变**：N 张图就是 N 个时间段，多切一段就是错位。

如果某一页实在讲不完，正确做法是**换卡继续讲同一页**，而不是拆成两页。
