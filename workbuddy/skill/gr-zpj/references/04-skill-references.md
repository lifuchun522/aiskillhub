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
| `jl-zpj` | 上游：从**简历 / 作品集 PDF** 抽素材、多端适配、打包交付的完整六阶段流水线。`gr-zpj` 的模板与编码策略沿用它，但入口换成表单，并把区块裁减改成声明式标记 | 本仓库 `workbuddy/skill/` 内同名目录（发布名 `jl-zpj`） |
| `delivery-no-pseudoblock` | 交付前闸门：任何一次向用户交付之前必须实跑 D1–D12 快照 | `~/.workbuddy/skills/delivery-no-pseudoblock/` |
| `workbuddy-docx` | 把作品集内容再产出 Word 版（投递用） | 内置技能 |
| `workbuddy-pptx` | 把 `diagrams/` 归档图组装成 PPT | 内置技能 |
| `wechat-article-publisher` | 需要把作品集当「个人介绍文章」发布时 | `~/.workbuddy/skills/wechat-article-publisher/` |

## 路径换算

| 语境 | 写法 |
|---|---|
| Git Bash / 本技能脚本 | `/d/src/github/.../gr-zpj` |
| Python（Windows） | `D:/src/github/.../gr-zpj` 或 `D:\\src\\github\\...` |
| JSON 配置里的 `src` / `archive` | 统一用正斜杠 `D:/…`；相对路径以 `paths.src_dir` 为基准 |
| `file://` URL（浏览器 / Playwright） | `file:///D:/…`（三个斜杠 + 正斜杠） |

## 交付检查清单

```bash
# 1. 资产同步（改了模板或示例之后必须做）
python scripts/sync_assets.py --check

# 2. 单测（56 项，含 16 项浏览器端）
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
| v1.0.0 | 首个版本。表单驱动采集 → 即时生成单页作品集；声明式区块标记（`SEC/NAV/HR/N`）；表单与命令行两处渲染一致性由测试守护；56 项单测（37 项离线 + 19 项浏览器端） |
