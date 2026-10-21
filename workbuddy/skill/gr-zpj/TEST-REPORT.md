# gr-zpj 测试报告（v1.1.0）

> **结论先行**：62 项自动化测试全绿；两条入口（表单 / 命令行）的产物**各自**跑完整 `verify.py` 均 `PASS`；开发期抓到 3 个「不报错、文字全对」的真 bug，已全部修掉并转为硬断言。

日期：2026-10-21　｜　被测版本：`gr-zpj` v1.1.0　｜　基线提交：`8ca9f76`（v1.0.0）
　｜　v1.1.0 变更：图片外置到 `img/`、按既有简历重建 9 个项目与 8 段履历

---

## 0. 结论摘要

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 单测（`unittest discover -s tests -t .`） | **62 / 62 OK**，耗时 67.7s（含 19 项浏览器端，随负载浮动） |
| 2 | 命令行路径 `verify.py`（结构 + 内容 + 五端渲染） | **PASS：全部检查通过** |
| 3 | 表单路径产物跑同一套 `verify.py` | **PASS：全部检查通过** |
| 4 | 两条入口渲染一致性（parity，逐项比对） | **6 项断言全过**（结构计数 / 序号 / 导航 / 文本 / 标题 / 破图） |
| 5 | 五端渲染（1440 / 820 / 390 / 360 / 320） | **19 / 19 通过**，无横向溢出、正文字号 ≥14.5px |
| 6 | 资产一致性（模板 / 示例 ↔ 表单内联） | `--check` 通过，`md5 34116dbe6797` |
| 7 | 构建可重复性 | 两次构建 `bytes` 逐字节相同（68490）＋ 22 张外置图字节相同 |
| 8 | 仓库副本独立运行（`git archive` 导出后） | `--check` 通过 + 62 项单测 OK |
| 9 | 开发期发现的真 bug | **3 个 P0**，全部已修并加断言 |
| 10 | 未覆盖 / 判不了 | 4 类，见 §8（一律记 NA，不写 PASS） |

---

## 1. 测试环境

| 项 | 值 |
|---|---|
| 操作系统 | Windows（本机开发机） |
| Python | 3.13.14（WorkBuddy 隔离环境 `envs/default`） |
| Pillow | 12.3.0（图片编码 / PNG8 量化） |
| Playwright | 1.62.0 + Chromium（浏览器端单测与五端渲染） |
| 被测产物 | `index.html` 68,490 B + `img/` 1.77 MB（命令行路径，外置）<br>`index.html` 0.66 MB 全内联（表单路径） |

表单路径**零第三方依赖**：只用浏览器原生 API（`FileReader` / `canvas` / `iframe`）。

---

## 2. 测试资产总览

| 文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `tests/test_build.py` | **34** | 结构化渲染、区块裁减、配置门禁、编码工具、图片外置、无图项目 |
| `tests/test_sync.py` | **9** | 模板 / 示例与表单内联的一致性、离线自包含 |
| `tests/test_browser.py` | **19** | 表单交互（13）+ 两处渲染一致性（6） |
| 合计 | **62** | 全部离线可跑（浏览器端只需本机 Chromium） |

---

## 3. 离线单测明细（43 项）

### 3.1 `test_build.py` — 构建器（34 项）

**`TestStructure`（9）**

| 用例 | 断言的是什么 |
|---|---|
| `test_full_render` | 全字段配置能构建出完整页面 |
| `test_no_template_residue` | 产物里不残留 `{{TOKEN}}` / `<!--SEC:…-->` 等任何标记 |
| `test_section_numbers_are_dom_ordered` | 章节序号按 DOM 顺序连续（`01 / CAPABILITY`……） |
| `test_separators_between_sections_only` | 分隔线数量 == 区块数 − 1，且不落在 `main` 首尾 |
| `test_nav_has_no_dead_link` | 导航每一项都有对应锚点，无死链 |
| `test_token_defaults_are_derived` | 派生 token（`CAREER_LEAD` / `PROJ_LEAD`…）由数据生成 |
| `test_metrics_columns_match_rows` | 数据条列数（`--mc`）== 实际条数 |
| `test_data_uri_input_passthrough` | 表单导出的内联图能被构建器直接吃下 |
| `test_string_inputs_shorthand` | **字符串形态与数组形态构建出逐字相同的页面** |

**`TestSectionPruning`（7）**

| 用例 | 断言的是什么 |
|---|---|
| `test_drop_capability` | 删中间区块后，分隔线同步少一条、导航项一起消失 |
| `test_drop_tail_credential` | 删尾部区块不留「什么都没有的分隔线」 |
| `test_only_projects_no_separator` | 只剩一个区块时，分隔线为 0 条 |
| `test_empty_content_still_valid_page` | 空内容仍是一张合法页面（不崩、不留脏标记） |
| `test_card_without_image_is_dropped` | 配了 `card` 但没给图 → 不渲染空图，也不报错 |
| `test_cert_without_image_skipped` | 证书缺图 → 跳过该条 |
| `test_qr_without_url_skipped` | 二维码缺链接 → 跳过该条 |

**`TestGates`（6）**

| 用例 | 断言的是什么 |
|---|---|
| `test_unknown_top_key` | 顶层未知键 → 报错退出（防拼写错误静默失效） |
| `test_unknown_content_key` | `content` 段未知键 → 报错退出 |
| `test_top_only_key_misplaced` | 只允许在顶层的键写到 `content` 里 → 报错退出 |
| `test_unknown_asset_key` | 正文引用了 `images` 里没有的键 → 报错退出（防破图） |
| `test_missing_file` | 配置文件不存在 → 报错退出 |
| `test_token_mismatch` | 模板写了 `texts` 段没有的 token → 报错而不是留脏 token |

**`TestEncoding`（6）**

| 用例 | 断言的是什么 |
|---|---|
| `test_split_tags_keeps_slash_words` | 标签按 `" / "` 切分，`TCP/IP` 这类词不被误切 |
| `test_truthy` | 空 / 全空白 / 空容器 = 空；`[0]` 视为无内容 |
| `test_esc` | HTML 转义正确 |
| `test_png8_smaller_than_lossless` | 技术分层图走 PNG8 后体积**必须真的降下来** |
| `test_passthrough_keeps_bytes` | 无需重编码时直通原始字节（不累积画质损失） |
| `test_col_class` | 证书 / 二维码网格列数类正确 |

**`TestExternalAssets`（4）— 图片外置**

| 用例 | 断言的是什么 |
|---|---|
| `test_external_mode_writes_files_and_uses_relative_src` | 图**真的落盘**到 `img/…`，页面里存的是相对路径（不是 `data:`），且路径与落盘位置一致 |
| `test_external_respects_file_and_group_fields` | `file` 显式指定优先；`group` 决定默认分组目录 |
| `test_external_skips_archive` | 外置时不再往 `diagrams/` 归档 —— 同一份字节不落两份 |
| `test_inline_remains_default` | 不写 `external` 时行为不变：仍产出单文件内嵌页 |

> 外置最容易静默出错的地方是**扩展名**：源图 png 被压成 jpeg，文件名若还叫 `.png`，
> 浏览器按后缀猜 MIME 会破图。所以扩展名取的是**实际编码出的 MIME**，不是源文件后缀。

**`TestProjectWithoutFigure`（2）— 无主图项目**

| 用例 | 断言的是什么 |
|---|---|
| `test_project_without_fig_renders_text_only` | `fig` 为空 → 只出文字卡，不渲染空 `.figure` 占位 |
| `test_mixed_projects_keep_numbering_continuous` | 有图 / 无图项目混排时编号仍连续，`figure` 计数只算有图的 |

### 3.2 `test_sync.py` — 资产一致性（9 项）

| 用例 | 断言的是什么 |
|---|---|
| `test_template_markers_exist` | 表单里有 `TPL` / `DEMO` 两个注入标记区 |
| `test_embedded_template_equals_file` | 表单内联模板 == `assets/template.html` |
| `test_embedded_demo_equals_file` | 表单内联示例 == `examples/demo-content.json` |
| `test_script_end_tag_escaped` | `</script>` 必须被转义成 `<\/script>` |
| `test_no_bare_script_close_inside_literals` | 字面量里不存在裸 `</script>`（会提前闭合宿主 script） |
| `test_check_mode_passes` | `sync_assets.py --check` 在干净仓库上通过 |
| `test_form_has_no_external_resource` | **离线可用**：没有任何 http(s) 外链 / CDN |
| `test_example_and_demo_share_content` | `content.json` 与 `demo-content.json` 内容同源 |
| `test_demo_size_is_reasonable` | 内联示例体积 < 900 KB（不拖慢表单加载） |

---

## 4. 浏览器端单测明细（19 项）

### 4.1 `TestFormUI` — 表单交互（13）

| 用例 | 断言的是什么 |
|---|---|
| `test_no_js_error_on_load` | 打开表单 JS 错误为 0 |
| `test_nine_blocks_present` | 九个采集区块全部在场 |
| `test_template_and_demo_injected` | 模板与示例已正确内联（非空、可解析） |
| `test_empty_state_warns_about_name` | 空态下检查面板报出「姓名未填」 |
| `test_load_demo_fills_every_block` | 点「载入示例」后九个区块全部填满 |
| `test_add_and_remove_rows` | 列表行可增可删，删后 DOM 与数据同步 |
| `test_extra_images_subrow` | 项目卡能挂多张补充架构图 |
| `test_project_numbering_is_positional` | 删掉第一个项目后，剩下的仍从 `01` 开始 |
| `test_export_shape_is_buildable` | 导出的 JSON **能被命令行构建器直接构建**（离线互通） |
| `test_import_export_roundtrip` | 导出 → 导入往返一致 |
| `test_disk_paths_are_flagged_not_silently_dropped` | 导入命令行格式的磁盘路径图 → 给出提示，不静默丢弃 |
| `test_generate_opens_preview` | 点「生成作品集」打开预览弹层 |
| `test_summary_reflects_counts` | 检查面板进度与实际填写量一致 |

### 4.2 `TestRenderParity` — 两处渲染一致性（6）

把**表单生成的页面**与**命令行构建的页面**都灌进浏览器，逐项比对：

| 用例 | 比对内容 | 结果 |
|---|---|---|
| `test_structure_counts_identical` | 结构计数（pillars / metrics / cards / zoom / certs / qrs / tl / stack / navlinks / anchors） | 逐项相等 |
| `test_section_index_and_nav_identical` | 章节序号 + 导航锚点 | 相等 |
| `test_visible_text_identical` | 页面可见文本（`innerText`） | 相等 |
| `test_title_identical` | `<title>` | 相等 |
| `test_form_output_has_no_residue` | 两处产物都不残留任何标记 | 均为 0 |
| `test_form_output_images_all_load` | **破图列表为空**（资源字典形状写错时这一步会炸） | 均为 0 |

> 缩放元素只用「类型序列」比对（`e.className.split(' ')[0]`），因为两条入口生成的**资源键名本来就不同**（表单按位置 `fig_1 / x_1_1`，手写 JSON 用语义键 `nh_agentx`）。这是设计如此，不是缺陷。

---

## 5. 端到端：双路径 `verify.py`

### 5.1 命令行路径（`index.html` 68,490 B + `img/` 22 张图 1.77 MB）

```
外置资源 1.77 MB ｜ index.html 0.07 MB ｜ 区块 capability+stack+career+credential+projects
STATS: {"metrics":6,"namecard":1,"intro":1,"pillars":3,"projects":9,"stack":6,
        "timeline":8,"certs":4,"qrs":4,"images":22,
        "kept":["capability","stack","career","credential","projects"],
        "bytes":68490,"assets_bytes":1854370,"external":"img"}

[0] 产物文本   无残留 模板 token / 区块标记 / 分隔线标记 / 序号标记   PASS []
[1] 运行时     JS 错误                                          PASS []
[2] 资源      破图 PASS []        图片总数>0 PASS imgs=23
[3] 结构      计数 pillars 3 / herocard 1 / metrics 6 / cards 9 / zoom 18 / certs 4
              qrs 4 / tl 8 / stack 6 / navlinks 6 / anchors 6        PASS
              数据条列数=条数 PASS --mc=6 条数=6
              导航无死链 PASS []   无遗留页脚 PASS footer=0
              body 无游离区块 PASS []   末尾非孤立分隔线 PASS last=.
              末区块为 projects PASS capability->stack->career->credential->projects
              章节序号按 DOM 顺序连续 PASS ['01','02','03','04','05']
              章节序号与标题对应 PASS
[3c] 首屏主体  名片占屏宽比 PASS 77% (1108x624)
[3b] 自述名片  自述文本非空 PASS 184 字   名片已加载 PASS 1672x941（外置）   名片可放大 PASS
[5] 数据映射  主图映射顺序 PASS（6 项，与 --expect 逐项相等）
              项目按时间降序 PASS ['2025.07','2024.11','2023.05','2021.12','2021.12',
                                   '2020.04','2018.09','2015.01','2011.07']
              项目编号连续 PASS ['01'…'09']
[6] 交互      灯箱打开 / 灯箱 ESC 关闭 / 二维码链接 4 个            PASS
[7] 多端渲染  见 §5.3
PASS: 全部检查通过
```

> 项目 07 / 08 / 09 没有留存架构图（`fig: ""`），因此 `cards 9` 但 `主图映射` 只有 6 项、
> `zoom 18`（6 组主图 + 3 组补充图 + 名片 + 4 张证书 + 4 张二维码）。**无图项目不占图位**，
> 编号仍然连续到 `09`。

### 5.2 表单路径（`index.html` 0.66 MB，内联 22 张演示尺寸图）

点「载入示例」→ 点「生成作品集」→ 取弹层 `iframe` 里真实渲染的结果，丢进**同一个** `verify.py`：

```
[0] 产物文本   无残留 模板 token / 区块标记 / 分隔线标记 / 序号标记   PASS []
[1] 运行时     JS 错误                                          PASS []
[2] 资源      破图 PASS []        图片总数>0 PASS imgs=23
[3] 结构      计数与命令行产物逐项一致（pillars 3 / metrics 6 / cards 9 / zoom 18 /
              certs 4 / qrs 4 / tl 8 / stack 6 / navlinks 6 / anchors 6）
              导航无死链 PASS   末尾非孤立分隔线 PASS
              末区块为 projects PASS   章节序号 ['01','02','03','04','05'] PASS
[3c] 首屏主体  名片占屏宽比 PASS 77% (1108x624)
[3b] 自述名片  名片已加载 PASS 560x315（内嵌）   名片可放大 PASS
[5] 数据映射  项目编号连续 PASS ['01'…'09']   项目按时间降序 PASS
[7] 多端渲染  1440 / 820 / 390 / 360 / 320 全部无横向溢出、正文字号 ≥14.5px
PASS: 全部检查通过
```

表单路径的资源键名按位置生成（`fig_1…fig_6`），命令行路径用语义键（`nh_gfs` 等）——
所以上面两条的 `[5]` 段键名不同、结构计数完全相同。这是设计如此，parity 只比「类型序列」。

### 5.3 五端渲染明细

| 视口 | 无横向溢出 | 关键区块不超宽 | 正文字号 | 名片在首屏 |
|---|---|---|---|---|
| 1440px（桌面 Chrome） | PASS 1440/1440 | PASS | — | PASS top=170 / vh=900 |
| 820px（平板） | PASS 820/820 | PASS | 15.0px | PASS top=181 / vh=1100 |
| 390px（iPhone · 微信） | PASS 390/390 | PASS | 14.5px | PASS top=163 / vh=844 |
| 360px（Android · 微信） | PASS 360/360 | PASS | 14.5px | PASS top=163 / vh=780 |
| 320px（iPhone · 企业微信） | PASS 320/320 | PASS | 14.5px | PASS top=182 / vh=568 |

`scrollW == clientW` 这 5 条是关键 —— 手机端一旦出现横向滚动，页面就「能打开但不能看」。

---

## 6. 开发期发现的 3 个真 bug（全部已修 + 加断言）

这三条的共同点是：**不抛异常、不报错、文字全对，只是页面悄悄错**。也是它们决定了这套测试为什么必须包含「破图 / 分隔线数量 / 序号连续性」这类硬断言。

### P0-1 表单产物全是破图（文字与计数全对）

| 项 | 内容 |
|---|---|
| 现象 | 表单生成的页面里所有图片都是破图图标 |
| 根因 | **资源字典形状错位**：配置里是 `{key: {src: …}}`，运行时要字符串 `ASSETS[key]`，`el.src` 变成 `"[object Object]"` |
| 暴露方式 | 截图肉眼看出来的（纯文本 parity 测试发现不了） |
| 修复 | `renderPortfolio` 里显式转换 `assets[k] = v.src` |
| 回归断言 | 新增 `test_form_output_images_all_load`，比对两处 `broken` 列表与图片数 |

### P0-2 表单看着填满，导出 JSON 全是空数组

| 项 | 内容 |
|---|---|
| 现象 | `stack` 是 `[['','','']]`、`certs` 是 `[['cert_1','','']]`，`metrics` 键直接缺失 |
| 根因 | 动态生成的重复行**只写 `placeholder`、从不写 `value`**；且回填发生在行创建**之前** |
| 暴露方式 | `window.__grzpj.payload()` 打出来看到空数组 |
| 修复 | ① 列表行改用真实嵌套路径以复用 `setPath/getPath`；② `renderLists()` 末尾紧跟一次回填；③ `fillFixed` 跳过 `type==="file"` |
| 回归断言 | `test_load_demo_fills_every_block`、`test_export_shape_is_buildable`、`test_import_export_roundtrip` |

### P0-3 删掉首个区块后，页面开头凭空多一条分隔线

| 项 | 内容 |
|---|---|
| 现象 | 删首块后开头多一条光秃秃的分隔线 |
| 根因 | 分隔线归一在**整篇 HTML** 上切分，页面前缀（nav / hero）被当成第一个非空片段 |
| 暴露方式 | 单测断言 `hr == 区块数 - 1`（4 个用例同时失败） |
| 修复 | Python 与 JS 两侧都改为**只在 `<main>` 内**归一（`re.sub(r"(?s)(<main>)(.*?)(</main>)", fix, html, count=1)`） |
| 回归断言 | `test_separators_between_sections_only`、`test_drop_capability`、`test_drop_tail_credential`、`test_only_projects_no_separator` |

---

## 7. 构建可重复性与仓库副本独立运行复验

「在我机器上是好的」不算证据。做了三层复核：

| # | 复核方式 | 结果 |
|---|---|---|
| 1 | 同一配置连跑两次构建，比对 `STATS.bytes` 与 22 张外置图的字节 | 两次均 `68490` + 外置合计 `1854370`，逐字节相同 |
| 2 | 把技能目录整份拷到临时目录（模拟「解压后独立运行」）跑 `sync_assets.py --check` + 62 项单测 | `PASS` ／ `Ran 62 tests ... OK` |
| 3 | 用 `git archive HEAD` 导出**提交后的字节**（经 `.gitattributes` 的 LF 归一）再跑 `--check` + 62 项单测 | `PASS`（`md5 34116dbe6797`）／ `Ran 62 tests ... OK` |

第 3 层最要紧：仓库开启 `* text=auto eol=lf`，提交会把 CRLF 归一成 LF。若「模板 ↔ 表单内联」这条一致性依赖于行尾字节，克隆下来就会失败 —— 实测不会，因为内联用的是 `json.dumps` 后的转义字面量，换行在字符串里是 `\n` 两个字符而非真实行尾。

外置模式另有一条交付纪律：**产物是「目录」不是「文件」**。`index.html` 里的 `src="img/…"`
是相对路径，单独把 HTML 拷走就会全页破图；`package.py` 会把 `img/` 连带打进去，
`verify.py` 的破图断言（`naturalWidth > 0`）也能在解压后的目录里拦住这类失误。

---

## 8. 未覆盖 / 判不了的部分（一律 NA，不写 PASS）

| # | 项 | 为什么判不了 |
|---|---|---|
| 1 | 内容质量（文案是否打动人、项目是否够分量） | 人的判断，脚本给不了 |
| 2 | 图片审美（架构图是否清晰、配色是否协调） | 同上 |
| 3 | 真实微信 / 企业微信客户端内的最终渲染 | 本技能用真实 UA + Chromium 近似，**不是真机**；客户端内核（X5 等）差异测不到 |
| 4 | 表单路径的体积优化 | 浏览器里做不了 PNG8 调色板量化 —— **能力边界，不是 bug**；产物 > 5 MB 时检查面板会直接建议改用命令行 |

---

## 9. 复现命令

```bash
cd ~/.workbuddy/skills/gr-zpj

# 1) 资产一致性：模板 / 示例 ↔ 表单内联
python scripts/sync_assets.py --check

# 2) 全部 62 项单测（浏览器端需 chromium）
python -W ignore::ResourceWarning -m unittest discover -s tests -t . -v

# 3) 命令行路径：构建 → 五端自检 → 打包
python scripts/build_portfolio.py examples/content.json --skill-dir . --stats
python scripts/verify.py "<out>/index.html" \
    --expect nh_digitalhuman,nh_gfs,nh_herodash,nh_game,nh_lowcode,yunshu_tech \
    --last-section projects --must "我的项目" --absent "重点项目" --shots shots/
python scripts/package.py "<out>"

# 4) 表单路径：双击 assets/form.html → 载入示例 → 生成作品集 → 另存 HTML
#    再把产物喂给同一套 verify.py
python scripts/verify.py "<表单另存的 index.html>" --last-section projects --must "我的项目"
```

退出码约定：`verify.py` 与 `sync_assets.py --check` 通过为 `0`，任一断言失败为非 `0` —— 可直接挂 CI 当门禁。

---

## 10. 结论

- **62 / 62 单测通过**，覆盖构建器、区块裁减、配置门禁、编码工具、图片外置、无图项目、
  资产一致性、表单交互、两处渲染一致性。
- **两条入口的产品化程度对等**：表单路径产出的页面跑同一套 `verify.py` 同样 `PASS`，两处渲染由 6 项 parity 断言逐项比对。
- **五端渲染 19 / 19 通过**，手机 / 微信 / 企业 IM 场景下无横向溢出、正文字号 ≥14.5px。
- **3 个「不报错型」真 bug 已闭环**：从「靠截图肉眼发现」升级为「断言拦得住」。
- 剩余 4 类不可自动判定的项已在 §8 显式标 NA，不用 PASS 掩盖。
