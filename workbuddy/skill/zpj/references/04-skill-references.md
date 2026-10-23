# 04 · 依赖技能与工具参考地址

## 运行环境

```bash
pip install pillow playwright
python -m playwright install chromium
```

| 依赖 | 谁需要 | 说明 |
|---|---|---|
| `pillow` | `build_portfolio.py` / `make_demo.py` | 图片缩放、格式转换、PNG8 量化 |
| `playwright` + `chromium` | `verify.py` / `tests/test_browser.py` | 五端渲染自检、两处渲染一致性比对 |

一个都不装也能用**表单路径**（纯浏览器），只是没有程序化自检。

## 相关技能

| 技能 | 关系 | 地址 |
|---|---|---|
| `jl-zpj` | 上游：从**简历 / 作品集 PDF** 抽素材、多端适配、打包交付的完整六阶段流水线。`zpj` 的模板与编码策略沿用它，但入口换成表单，并把区块裁减改成声明式标记 | 本仓库 `workbuddy/skill/` 内同名目录（发布名 `jl-zpj`） |
| `delivery-no-pseudoblock` | 交付前闸门：任何一次向用户交付之前必须实跑 D1–D12 快照 | `~/.workbuddy/skills/delivery-no-pseudoblock/` |
| `workbuddy-docx` | 把作品集内容再产出 Word 版（投递用） | 内置技能 |
| `workbuddy-pptx` | 把 `diagrams/` 归档图组装成 PPT | 内置技能 |
| `wechat-article-publisher` | 需要把作品集当「个人介绍文章」发布时 | `~/.workbuddy/skills/wechat-article-publisher/` |

## 路径换算

| 语境 | 写法 |
|---|---|
| Git Bash / 本技能脚本 | `/d/src/github/.../zpj` |
| Python（Windows） | `D:/src/github/.../zpj` 或 `D:\\src\\github\\...` |
| JSON 配置里的 `src` / `archive` | 统一用正斜杠 `D:/…`；相对路径以 `paths.src_dir` 为基准 |
| `file://` URL（浏览器 / Playwright） | `file:///D:/…`（三个斜杠 + 正斜杠） |

## 交付检查清单

```bash
# 1. 资产同步（改了模板或示例之后必须做）
python scripts/sync_assets.py --check

# 2. 单测（62 项，含 19 项浏览器端）
python -m unittest discover -s tests -t . -v

# 3. 构建
python scripts/build_portfolio.py examples/content.json --stats

# 4. 五端自检 + 截图
python scripts/verify.py "<out>/index.html" --expect <主图键,逗号分隔> \
    --last-section projects --must "<新词>" --absent "<旧文案>" --shots <目录>

# 5. 打包
python scripts/package.py "<out>"
```

## 版本历史

| 版本 | 变更 |
|---|---|
| v2.0.0 | 技能包收敛为 `zpj`（原 `gr-zpj`，`git mv` 保留历史）；新增最小示例 `examples/minimal-content.json`（3 KB，1 项目 / 2 段履历）+ `examples/README.md`；`verify.py` 修「未配证书 / 二维码被判失败」的误判（`OPTIONAL_STATS` + `KEY_BLOCKS` 三元组）；表单草稿键改 `zpj-draft-v1`、调试入口改 `window.__zpj` |
| v1.1.0 | 图片可外置：`paths.external` 非空时把图写到 `<out_dir>/img/<分组>/…` 并用相对路径引用，`index.html` 从 2.4 MB 降到 ~70 KB；项目卡支持无主图（`fig` 留空 → 只出文字卡）；`verify.py` 的名片断言从「必须是 data URI」改为「必须解码出像素」，主图映射只比有图项目。62 项单测（43 项离线 + 19 项浏览器端） |
| v1.0.0 | 首个版本。表单驱动采集 → 即时生成单页作品集；声明式区块标记（`SEC/NAV/HR/N`）；表单与命令行两处渲染一致性由测试守护；56 项单测（37 项离线 + 19 项浏览器端） |
