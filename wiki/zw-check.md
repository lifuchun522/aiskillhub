# zw-check｜征文稿件发布前检查（v1.0.0）

> 把「发布前逐项核对」从人肉目测变成可复算的检查：字数口径、加工痕迹、HTML 结构、征文硬性要求、稿件与源码一致性，一条命令跑完，可疑点带原文上下文列出来。

仓库路径：[`workbuddy/zw-check/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/zw-check)

完整使用说明（HTML，逐条可核对）：[`USAGE.html`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/zw-check/USAGE.html)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/zw-check/SKILL.md)

## 一句话

给一篇要投出去的文章跑四类检查 —— **text**（字数与加工痕迹）、**html**（结构与配图）、**rules**（征文硬性要求）、**consist**（稿件里的源码事实与源码对齐），退出码 `0/1/2`，可直接挂 CI 当门禁。

## 它解决什么问题

来自一次真实交付：一篇 OSS 换证复盘文章要同时满足两场征文的要求，被陆续指出「字数太多」「有加工痕迹」「不能用表格」「截图备注要去掉」「目录树跟实际文件对不上」。每一条都得靠人肉翻全文找，而且**改完必须重跑**——靠「我记得我改过了」是不行的。

这类检查的共同点：**机械、可枚举、有明确判据，但人做起来很慢**。正好适合固化成脚本。

| 被指出过的问题 | 对应检查项 | 判定方式 |
|---|---|---|
| 字数太多（要求 1000 字符含空格） | T1 | 可见正文含空格字符数超上限即 FAIL |
| 「本次实测还产出三类可复核文件…」 | T2 交付清单 | 命中即 FAIL（block 级） |
| 正文直出 `report/baseline-report.html` | T2 文件路径外泄 | 命中即 FAIL |
| 「在支持 Skill 的宿主里」 | T3 宿主术语 | WARN，人工确认 |
| 表格在编辑器里样式错乱 | H1 | `<table>` 数必须为 0 |
| 截图备注要去掉 | H2 | `<figcaption>` 数必须为 0 |
| 目录树漏了新增文件 | K1 | 目录树 vs 实际文件集合 |
| 正文里的 `description` 是旧版 | K2 | 与真实 `SKILL.md` 逐字比 |
| 正文写「36 项单测」 | K3 | 真的跑一遍，比对 `Ran N tests` |

## 安装

```bash
cp -r workbuddy/zw-check ~/.workbuddy/skills/zw-check
python3 -m unittest discover -s tests -v      # Ran 51 tests ... OK

# 图片实测是可选能力
pip install playwright && python -m playwright install chromium
```

离线检查只要 Python 3.9+，无第三方依赖；`zwcheck.py` 全程不触网。**只读**：不修改稿件、不改文件名、不写回磁盘。

## 使用步骤

### 1 · 先定口径

| 参数 | 说明 |
|---|---|
| `--track cloudq \| workbuddy \| none` | 决定检查哪套征文规则 |
| `--max-chars 1000` | 字数上限，**含空格**口径（最严） |
| `--min-images 3 --max-images 6` | 配图区间 |
| `--from '<h1'` `--to '<script>'` | 划定正文区域；预览页带工具栏时必填，否则工具栏文字会被算进字数 |

### 2 · 跑检查

```bash
# 一次跑完五组
python3 scripts/zwcheck.py all 稿件.html \
    --track workbuddy --max-chars 1000 --min-images 3 --max-images 6 \
    --from '<h1' --to '<script>'

# 单跑某一类
python3 scripts/zwcheck.py text    稿件.md   --max-chars 1000
python3 scripts/zwcheck.py html    稿件.html --max-images 6
python3 scripts/zwcheck.py rules   稿件.md   --track cloudq --skill-md skill/SKILL.md
python3 scripts/zwcheck.py consist 稿件.md   --skill-dir skill/ --run-tests
```

### 3 · 读结果

| 状态 | 含义 | 动作 |
|---|---|---|
| `PASS` | 通过 | 无 |
| `FAIL` | 硬指标不满足 | 必改，改完复跑 |
| `WARN` | 提示项（痕迹 warn 级） | 人看后决定；放行要 `--allow '<原文串>'` **逐条**写 |
| `NA` | 判不了，附原因 | 看原因：平台侧 / 缺输入 / 人的判断 |

不给「全部忽略」开关：放行必须逐条显式写出，否则等于把闸门关掉。

### 4 · 图片实测

```bash
python3 scripts/check_images.py 稿件.html
```

静态检查只能说「引用了 `img/xx.png`」，说不了「真的能打开」。路径拼错、大小写不符、漏打包，静态检查全都看不出来。

### 5 · 对齐源码事实

```bash
python3 scripts/zwcheck.py consist 稿件.md --skill-dir skill/ --run-tests
```

三项：目录树 vs 实际文件（**只比 basename**）、正文内嵌元数据 vs 真实 `SKILL.md`（逐字）、正文声明的单测数 vs 实跑结果（不加 `--run-tests` 就是 NA）。

### 6 · 接 CI

```bash
python3 scripts/zwcheck.py all 稿件.html --track workbuddy --max-chars 1000 \
    --min-images 3 --max-images 6 --from '<h1' --to '<script>' || exit 1
python3 scripts/check_images.py 稿件.html || exit 1
```

## 本机实测

### 单测

```
Ran 51 tests in 0.136s
OK
```

### 一篇 1000 字符投稿版（WorkBuddy 赛道）

```
== 字数与加工痕迹 ==
  [PASS] 字数（含空格）≤ 1000     含空格 960，不含空格 893，中文 561，余量 40
  [PASS] 加工痕迹（block 级）为 0  未命中
  [PASS] 加工痕迹（warn 级）提示    未命中
== HTML 结构 ==
  [PASS] 无 <table>  · [PASS] 无 <figcaption> · [PASS] 恰有 1 个 <h1>
  [PASS] div / p 标签配平  div 3/3，p 10/10
  [FAIL] 配图 ≥ 3 张       当前 0 张
== 征文规则（track=workbuddy） ==
  [PASS] 标题以「【征文】」开头
  [PASS] 正文与 WorkBuddy 强相关  提及 WorkBuddy 2 次
  [FAIL] 配图 ≥ 3 张       HTML 配图 0 张
  [NA  ] 发布板块 =「实用文章」     平台侧动作，稿件无法自证
结论：FAIL 2 项，需先修正
```

那条 FAIL 是真的：该稿压到 1000 字符时把配图整段删了，而征文要求 ≥ 3 张。检查器如实报出来，不替稿件打圆场 —— 这正是它存在的意义。

### 同一篇稿子清理前的痕迹命中

```
[FAIL] 加工痕迹（block 级）为 0  命中 11 处
[WARN] 加工痕迹（warn 级）提示    命中 10 处
  [block] 交付清单｜本次实测还产出｜…本次实测还产出三类可复核文件：`operation-order…
  [block] 交付清单｜可供二次开发｜…效率对照页。原型可供二次开发，不包含云密钥和自动部署功能。…
  [block] 附件指向｜完整文件和检查脚本｜…完整文件和检查脚本放在文末附件里。…
  [block] 文件路径外泄｜`report/baseline-report.html`｜…对照结果页面在 `report/baseline-report.html`，它把…
```

这 11 条与当时人工找出来并改掉的句子**一一对应**——说明判据是收敛的，不是拍脑袋加的。

### 稿件 ↔ 技能源码一致性

```
[PASS] 正文目录树与实际文件一致            树内 11 个文件 / 实际 11 个
[PASS] 正文内嵌元数据与 SKILL.md 逐字一致  一致
[PASS] 正文所述单测数与实跑一致            正文 36 项 / 实跑 36 项 / 退出码 0
```

### 图片实测

```
加载成功 19/19      失败请求：无      结论：全部加载成功
```

## 判不了的部分（一律 NA，不写 PASS）

1. 平台侧动作：发布板块、交流圈位置、成员资格、投稿时间线；
2. 账号侧事实：每人投稿篇数、原创性、是否刷量；
3. 人的判断：行文流畅性、可读性、案例专业性、创新性；
4. 缺输入：未给 HTML 时的结构与配图项；未加 `--run-tests` 时的单测实测项。

## 相关文件

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 技能规范、触发条件、21 项检查清单、六条铁律 |
| `README.md` | 概览、四类检查详解、常见坑 |
| `USAGE.html` | 精确到每步命令/参数/退出码的使用手册（本页精简版） |
| `scripts/zwcheck.py` | 四类检查 CLI（`text` / `html` / `rules` / `consist` / `all`） |
| `scripts/check_images.py` | 浏览器实测图片加载（可选依赖 playwright） |
| `tests/test_zwcheck.py` | 51 项离线单测，全部纯函数 |
| `references/contest-rules.md` | 两份征文要求 ↔ 检查项 ID 映射 |
| `references/trace-words.md` | 加工痕迹词表、级别、放行方法、真实命中例 |
