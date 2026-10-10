# zaobao v6.1.0 增强记录

- 首页 `index.html` 的资源导航固定为三个相对路径：`index.html`、`talk.htm`、`md/zaobao.md`；所有链接在新标签页打开，带 `rel="noopener noreferrer"`。
- `index.json.resourceLinks` 与首页三条导航一致；仍保留原有两份 MD、两份 HTML、全部本期手绘配图和 ImageGen 来源记录。
- 每次运行 `scripts/build.py` 结束时自动生成 `article-YYYYMMDDHHMM.zip`，时间戳为打包时在用户所在时区的日期时分。默认 `Asia/Shanghai`，通过 `--timezone` 指定其他 IANA 时区。
- 生成器命令行仅输出最终 ZIP 的准确路径。调用 `zaobao` 的用户可见最终回复默认只提供这个 ZIP 下载链接；明确要求 Skill 或报告时例外。
- 不改变经过确认的手绘白板图片规则：白底、粗黑线条、橙红强调、独立矩形内容区；技术图来自 Image 2.5。

## 本期校验

- 57 项快速单元测试：通过 52 项，5 项需要真实 ImageGen 文件时跳过。
- 同轮真实 ImageGen 集成：端到端构建完成，归档包含 17 个文件、三个导航链接，资源和哈希校验通过；同时核验保留原始图片与裁剪规则。
- 另外对上轮图像相关的第 48~57 项测试进行了真实图片输入复验，10 项通过。
- 时区确定性测试：UTC 2026-10-10 04:57 对应 Asia/Shanghai 的 `article-202610101257.zip`。
