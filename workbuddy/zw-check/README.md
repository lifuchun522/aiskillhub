# zw-check

投稿 / 征文稿件的**发布前机械检查**技能（v1.0.0）。把「发布前逐项核对」从人肉目测变成可复算的检查：一条命令给出字数口径、加工痕迹、HTML 结构、征文硬性要求、稿件与源码一致性五组结果，可疑点带原文上下文。

来自一次真实交付：一篇 OSS 换证复盘文章要同时满足两场征文的要求，先后被指出「字数太多」「有加工痕迹」「不能用表格」「截图备注要去掉」「目录树跟实际文件对不上」——每一条都靠人肉翻全文找。这个技能把那些检查固化下来。

- **只读**：不修改稿件，不改文件名，不写回磁盘；结果只打印到标准输出。
- **离线**：`zwcheck.py` 纯标准库，不触网；`check_images.py` 只渲染本地 `file://` 页面。
- **不猜**：判不了的项标 `NA` 并写明原因（平台侧动作、风格判断、缺输入），不拿「大概没问题」糊过去。
- **可复算**：每条判定都是纯函数 + 显式正则/阈值，能被单测复现。
- **不自动改稿**：发现 FAIL 后怎么改由人或宿主决定。

## 快速开始

```bash
# 一次跑完五组检查（推荐入口）
python3 scripts/zwcheck.py all 稿件.html \
    --track workbuddy --max-chars 1000 --min-images 3 --max-images 6 \
    --from '<h1' --to '<script>'

# 单跑某一类
python3 scripts/zwcheck.py text  稿件.md  --max-chars 1000
python3 scripts/zwcheck.py html  稿件.html --max-images 6
python3 scripts/zwcheck.py rules 稿件.md  --track cloudq --skill-md skill/SKILL.md
python3 scripts/zwcheck.py consist 稿件.md --skill-dir skill/ --run-tests

# 图片实测（需要 playwright）
python3 scripts/check_images.py 稿件.html

# 单测
python3 -m unittest discover -s tests -v
```

退出码：`0` 全部通过 · `1` 存在 FAIL · `2` 参数或文件错误。可直接挂进 CI 当门禁。

## 四类检查

### text — 字数与加工痕迹

| 口径 | 说明 |
|---|---|
| 含空格 | 默认判定口径，最严 |
| 不含空格 | 便于与工具统计对照 |
| 中文汉字 | 参考值 |

可见正文的取法：HTML 去 `script`/`style`/`figure`/`img` 与全部标签、实体反转义、空白归一为单空格；Markdown 去图片语法、默认去围栏代码块（`keep_code` 可保留）。

**加工痕迹**分两级：

- `block` 必改：交付清单（「本次实测还产出…」「可供二次开发」）、附件指向（「见文末附件」）、文件路径外泄（`report/x.html`、`references/y.md`）、疑似未脱敏内部域名；
- `warn` 视文体斟酌：自证腔（「不拿关键词当成绩」）、写作元信息（「本文工程设计」）、宿主术语（「支持 Skill 的宿主」）、过程口吻（「本次实测」）。

放行个别命中用 `--allow '<原文串>'`，必须显式写出来，不提供「全部忽略」开关。

### html — 结构完整性

`<table>` = 0（编辑器易错乱样式）、`<figcaption>` = 0（截图备注）、`<h1>` 恰 1 个、`div`/`p` 标签配平、图片全部相对路径或 Base64 内嵌、配图数量落在区间内。

### rules — 征文硬性要求

按赛道取规则集（`--track cloudq|workbuddy`）：标题「【征文】」前缀、正文与 WorkBuddy 强相关、六维度齐全、三层口径齐全、赛道标签**每篇仅一个**（按 token 数判定，一行写三个也算违规）且落在官方候选集合、`SKILL.md` 元数据仅 `name` + `description`、正文含工具/步骤/边界/铁律。

### consist — 稿件与技能源码一致

- 正文里嵌的 ASCII 目录树 vs 技能目录实际文件集合（**只比 basename**，树里没写层级）；
- 正文里嵌的 `SKILL.md` 元数据 vs 真实 `SKILL.md`（逐字比较）；
- 正文声明的单测数量 vs 实跑 `unittest` 的结果（需 `--run-tests`；不加则 NA，绝不拿「正文写了 36 项」当作「实测 36 项」）。

## 输出判读

```
  [PASS] 字数（含空格）≤ 1000     含空格 960，不含空格 893，中文 561，余量 40
  [FAIL] 配图 ≥ 3 张             当前 0 张
  [WARN] 加工痕迹（warn 级）提示    命中 2 处，按文体斟酌
  [NA  ] 发布板块 =「实用文章」      平台侧动作，稿件无法自证
```

- `PASS` 通过 · `FAIL` 必须改 · `WARN` 人看后决定（放行要 `--allow`）· `NA` 有明确原因，需要谁补就写谁补。
- `--json` 输出结构化结果，便于接自动化。

## 常见坑

1. **字数算多了/少了**：预览页带工具栏时，工具栏文字会一起计入。用 `--from '<h1'` `--to '<script>'` 划定正文区域。
2. **「图片引用了」不等于「图片能打开」**：路径大小写、漏打包、相对路径层级错，静态检查全都看不出来 —— 跑 `check_images.py`。
3. **一致性检查不能用去代码块的可见正文**：目录树和元数据都在围栏里，用可见正文会全部漏检（CLI 已按原始文本比对）。
4. **同名文件歧义**：目录树只写 basename，`scripts/a.py` 与 `tests/a.py` 会被视作同一项，需人工确认。

## 文件结构

```
zw-check/
├── SKILL.md                      # 技能规范（元数据仅 name + description）
├── README.md                     # 本文件
├── scripts/
│   ├── zwcheck.py                # 四类检查（text / html / rules / consist / all）
│   └── check_images.py           # 浏览器实测图片加载（可选依赖）
├── tests/
│   └── test_zwcheck.py           # 51 项离线单测
├── references/
│   ├── contest-rules.md          # 征文要求 ↔ 检查项映射
│   └── trace-words.md            # 痕迹词表与放行方法
└── USAGE.html                    # 使用步骤手册
```

## 已知边界

- 不判行文流畅性、不判事实真伪、不判是否「像日记」——这些是人的判断；
- `html` 模式针对**要粘进编辑器的稿件 HTML**（禁表格是为了防样式错乱）；技能自带的说明页（如 `USAGE.html`，本身就用表格排版）不在检查范围；
- 平台侧动作（发布板块、成员资格、截稿时间线）一律 NA；
- `check_images.py` 需要 `playwright` + `chromium`，未安装时返回 `2` 并提示安装命令；
- 目录树比对只到 basename 粒度。

## 环境

Python 3.9+（标准库即可）。图片实测可选：`pip install playwright && python -m playwright install chromium`。
