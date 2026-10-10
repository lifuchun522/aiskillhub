# zaobao v6.2.0 增强记录

- **出图模型统一为 hy3（混元图像 3.0）**：`SKILL.md`、`README.md`、`build.py` 中所有出图模型表述由旧模型改为 hy3；hy3 在中文标注渲染上明显更强，适配"手绘白板 + 中文技术标注"场景。
- **新增画布归一 `normalize_canvas()`**：hy3 原生输出尺寸不固定（实测出现过 `1440×1072` 与 `1024×1024`），构建时先把两张原画等比归一到标准画布 `1448×1086`，再套用已校准的固定裁剪坐标。归一为确定性衍生操作，在 `imagegen-provenance.json` 中以 `normalize → crop` 如实记录；`original-*-imagegen.png` 仍保留 hy3 原始字节不变。
- **新增出图比例守卫**：`image_quality()` 增加宽高比校验，偏离标准画布 ±28% 直接判定不合格并要求重新生成（拦截了本次生成的 `1024×1024` 方图）。
- **修正质量检测采样**：白底/黑线/橙红比例统计的采样网格由 `160×90` 改为 `320×180`，避免 hy3 较细的马克笔线条在缩采样时被平均掉导致误判（实测黑色比例由 0.010 恢复到 0.041）。
- **跨平台修复**：`browser_smoke.py` 移除写死的 Linux 路径 `/usr/bin/chromium`，改为默认使用 Playwright 自带内核、可用环境变量 `ZAOBAO_CHROMIUM` 覆盖；同时把资源导航链接数断言由 2 修正为 3（v6.1 已加入 `md/zaobao.md`）。
- **`index.json.tags` 改为可配置**：由输入 JSON 的 `tags` 字段决定，缺省时使用通用标签。
- **新增示例输入** `examples/zaobao-2026-10-10.json`。

## 本次校验

- 57 项单元测试：无真实图片时通过 52 项、跳过 5 项；**带真实 hy3 图片全量运行 57 项全部通过**（`Ran 57 tests in 28.289s / OK`）。
- 浏览器渲染 QA：`BROWSER RENDER PASS 4  RESOURCE LINKS VALID 3`（index.html / talk.htm × 桌面 + 移动端）。
- 端到端构建：`article-202610101357.zip`，17 个文件、10 张图片、3 条资源导航链接，ZIP 完整性与哈希校验通过。
- 时间戳确定性：UTC `2026-10-10 04:57` 对应 `Asia/Shanghai` 的 `article-202610101257.zip`。
