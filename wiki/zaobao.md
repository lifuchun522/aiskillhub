# zaobao｜架构师早报三问与同盟讨论（v6.1）

仓库路径：[`gpt/skill/zaobao/`](https://github.com/lifuchun522/aiskillhub/tree/main/gpt/skill/zaobao)

完整使用说明：[`README.md`](https://github.com/lifuchun522/aiskillhub/blob/main/gpt/skill/zaobao/README.md)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/gpt/skill/zaobao/SKILL.md)

## 一句话

输入【科技热点】【架构文章推荐】【今日一言】三栏原文，闭环产出芒格三问、同盟讨论、微信 HTML、手绘白板图，最终只交付一个 `article-YYYYMMDDHHMM.zip`。

## 安装

```bash
# 从本仓库拷贝整目录
cp -r gpt/skill/zaobao ~/.codex/skills/zaobao
# 或上传到 GPT / ChatGPT 自定义 Skill（按平台约定）
```

## 自然语言用法

在已安装 Skill 的对话中粘贴三栏原文并说明「用 zaobao 跑本期早报」。Agent 应自动完成研究、写作、Image 2.5 出图、打包与 D1–D12 闸门；最终回复**只给一个**带本地时间戳的 ZIP 下载链接（默认时区 `Asia/Shanghai`）。

## 本地打包（已有核验 ImageGen 原画时）

```bash
cd gpt/skill/zaobao
python scripts/build.py \
  --input examples/demo-2026-10-08.json \
  --brief-image /path/to/verified_brief.png \
  --talk-image /path/to/verified_talk.png \
  --gen-brief <真实ID> --gen-talk <真实ID> \
  --out ./zaobao-build --timezone Asia/Shanghai
```

## 交付物结构

```text
article-YYYYMMDDHHMM.zip
├── index.html / talk.htm / index.json
├── md/zaobao.md, talk.md, talk-prompts.txt
├── img/ 原画、白板、六张主题截图
└── imagegen-provenance.json
```

硬约束：ZIP 不含 `skill/`；首页导航仅 `index.html`、`talk.htm`、`md/zaobao.md`；全部 `<a>` 须 `_blank` + `noopener noreferrer`；`checkStatus=unaudited`。

## 相关文件

| 文件 | 说明 |
|---|---|
| `scripts/build.py` | 确定性打包与时间戳命名 |
| `scripts/browser_smoke.py` | HTML 冒烟 |
| `tests/` | 回归单测 |
| `assets/style-reference-*.png` | 白板风格锚点 |
| `references/D1-D12.md` | 交付前闸门 |
| `references/wxp-json.md` | index.json 契约 |

更多细节以仓库内 `SKILL.md` 为准。
