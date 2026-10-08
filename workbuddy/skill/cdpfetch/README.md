# 真实浏览器抓取与证据看板（cdpfetch）

一个**工程化**的 Agent Skill：把「抓多个网页做对比」这件事，从「打开页面抄几行」变成
**可回溯、可验证、可交付**的一条流水线。

它解决的不是「怎么把网页内容读出来」——那是基础能力。它解决的是抓取类任务里那些
**反复踩、反复忘的工程问题**：抓到的是残缺正文却看起来正常、CDP 通道拿不到 HTTP 状态码、
二手站点传播已下架的旧定价、单文件 HTML 被外部依赖污染、报「验证通过」实则没覆盖全。

> 独立 Agent Skill，遵循通用 `SKILL.md` 规范，可在 WorkBuddy / Claude Code / Codex / Cursor 等支持 Agent Skills 的工具中安装使用。

---

## 它解决什么问题

| 失效形态 | 后果 | cdpfetch 的对策 |
|---|---|---|
| 懒加载没滚动 | 拿到**看似完整实则残缺**的正文 | 抓取脚本内置滚动 + `text_len` 判据 |
| CDP 没有 HTTP 状态码 | 把 `status: 200` 当成页面可用的证据 | 存证记录 `channel`，状态码不作为可用性依据 |
| 用二手站点数值 | 定价、配额写错 | 强制回一手页；冲突写进洞察 |
| 单个目标失败中断整批 | 18 个成功的一起作废 | 失败即数据，写入存证不中断 |
| 单文件看板引 CDN | 离线/内网打开全白 | 验证脚本断言外部引用为 0 |
| 「验证通过」没覆盖全 | 假阴性漏报 | 确定性计数 + 期望值 vs 实测值逐项列出 |
| key 重复静默覆盖 | 少一个来源而毫无察觉 | 加载清单时主动检测重复并退出 |

---

## 两条抓取通道

产出格式**完全一致**，下游无差别消费：

| | CDP 直连 `cdp_fetch.mjs` | Playwright 无头 `fetch_pages.py` |
|---|---|---|
| 浏览器 | 你**日常在用的** Chrome / Edge | 独立 Chromium |
| 登录态 | **天然携带** | 无 |
| 前置 | 浏览器需开远程调试端口 | `playwright install chromium` |
| 对环境影响 | 在日常浏览器里开后台 tab（用完即关） | **零影响** |
| HTTP 状态码 | **拿不到** | 拿得到 |
| 适用 | 内部系统、需登录页、强反爬 | 公开官网、批量取数 |

选型细节与开端口姿势见 [`references/channels.md`](./references/channels.md)。

---

## 安装

整目录拷贝到你所用工具的 skills 目录：

```bash
# WorkBuddy / Claude Code（用户级，全项目可用）
cp -r cdpfetch ~/.workbuddy/skills/          # 或 ~/.claude/skills/

# 项目级（随仓库共享，团队协作更合适）
cp -r cdpfetch <项目>/.workbuddy/skills/
```

安装后无需配置，用自然语言提需求即会自动唤起。

依赖：

```bash
# Python 通道
pip install playwright && playwright install chromium

# Node 通道（原生 WebSocket，仅 cdp_fetch.mjs 需要）
node -v    # 需 ≥ 22
```

---

## 快速开始

```bash
# 1. 编目：写目标清单（key 要唯一）
cat > targets.json <<'JSON'
[
  { "key": "vendorA_home",    "url": "https://www.example-a.com/" },
  { "key": "vendorA_pricing", "url": "https://www.example-a.com/pricing" }
]
JSON

# 2. 抓取（默认 Playwright 无头通道）
python scripts/fetch_pages.py --targets targets.json --out ./raw --concurrency 5

# 3. 补一手客观指标（可选，开源项目）
node scripts/gh_metrics.mjs example-a/example-a --out gh_metrics.json

# 4. 出看板后验证
python scripts/verify_dashboard.py --file dashboard.html --spec spec.json \
  --shots ./shots --sections "#sec-cards,#sec-price" --toggle-lang
```

---

## 脚本参数

### `scripts/cdp_probe.mjs` — CDP 端点探测

```
node cdp_probe.mjs [--port 9222] [--json]
退出码 0 可用 / 1 不可用（stdout 给出开启指引）
```

### `scripts/cdp_fetch.mjs` — CDP 通道抓取（带登录态）

```
node cdp_fetch.mjs --targets <清单> --out <目录> [选项]

  --port 9222         调试端口          --concurrency 3    并发 tab 数（受真实浏览器限制）
  --timeout 60000     单页超时(ms)      --settle 3500      导航后基础等待(ms)
  --scroll 3          懒加载滚动次数    --no-html          不落盘 DOM 快照
  --keep-tabs         保留 tab（仅调试）
```

### `scripts/fetch_pages.py` — Playwright 无头并发抓取

```
python fetch_pages.py --targets <清单> --out <目录> [选项]

  --concurrency 5     并发上下文数      --scroll 3         懒加载滚动次数（0 = 不滚动）
  --timeout 60000     单页导航超时(ms)  --settle 3500      导航后基础等待(ms)
  --no-html           不落盘 DOM 快照   --headed           显示窗口，便于人工过验证码
  --locale zh-CN      页面 locale       --user-agent ...   覆盖 UA
  --width 1440 --height 1000
```

### `scripts/gh_metrics.mjs` — GitHub 客观指标

```
node gh_metrics.mjs owner/repo [owner/repo ...] [--out gh_metrics.json]
GITHUB_TOKEN=xxx node gh_metrics.mjs ...    # 抬高限流额度（未认证 60 次/小时）
```

### `scripts/verify_dashboard.py` — 产出物确定性验证

```
python verify_dashboard.py --file <html> [--spec spec.json] [--shots <目录>]
                          [--sections "#a,#b"] [--toggle-lang]

退出码 0 全绿 / 1 存在未通过项
```

`spec.json`：`selectors`（选择器→期望计数）、`zero_console_errors`、`forbid_external_refs`、
`forbid_anchor_href`、`sections`、`title_contains`。全部可省。

---

## 目录结构

```
cdpfetch/
├── SKILL.md                          技能入口：触发条件、五步流程、三条纪律
├── README.md                         本文件：安装与使用说明
├── scripts/
│   ├── cdp_probe.mjs                 CDP 调试端点探测
│   ├── cdp_fetch.mjs                 CDP 通道抓取（带登录态）
│   ├── fetch_pages.py                Playwright 无头并发抓取
│   ├── gh_metrics.mjs                GitHub REST API 客观指标
│   └── verify_dashboard.py           产出物确定性验证 + 分区块截图
├── references/
│   ├── channels.md                   双通道选型、开端口姿势、最小侵入约定
│   ├── evidence-schema.md            存证字段规范、证据表生成、交叉印证口径
│   ├── dashboard-spec.md             单文件看板硬约束、可视化选型、验证规格
│   └── pitfalls.md                   踩坑清单（P0/P1/P2，15 条，全部来自真实返工）
└── templates/
    └── targets.example.json          目标清单模板
```

---

## 产出物

```
<out>/
├── _manifest.json     存证清单：key / requested_url / final_url / status / title
│                      / text_len / link_count / text_sha256 / fetched_at / channel
├── <key>.txt          渲染后正文
├── <key>.links.txt    链接清单 `可见文本 :: 绝对URL`
└── <key>.html         渲染后 DOM 快照（可离线复核）
```

三件套缺一不可：`.txt` 取数、`.links.txt` 发现下一跳、`.html` 事后复核选择器。
字段含义见 [`references/evidence-schema.md`](./references/evidence-schema.md)。

---

## 常见问题

**Q：`cdp_probe.mjs` 说没有浏览器开着调试端口，一定要去开吗？**
不用。多数情况下直接走 Playwright 无头通道即可——它同样是真实 Chromium 渲染，且不碰你的桌面浏览器。
只有「必须登录态」或「强反爬」时才有必要开端口。

**Q：为什么给日常 Chrome 加 `--remote-debugging-port` 没反应？**
较新 Chrome（136+）对默认 profile 有安全限制，会拒绝开调试端口。
必须配独立的 `--user-data-dir`，并完全退出浏览器后重启。见 `references/channels.md` 第三节。

**Q：走 CDP 通道时 `status` 全是 200，能信吗？**
不能。CDP 协议不回传 HTTP 响应码，那个 200 只代表导航请求被接受。
判断页面可用性看 `text_len` 和 `title`。

**Q：抓下来的正文明显偏短？**
大概率是懒加载没触发。加大 `--scroll`（例如 6）重抓，并对比 `text_len` 是否升到正常量级。

**Q：看板在本地打开正常，发给别人就白了？**
一定是有外部引用（CDN 字体、图标库、图片）。跑 `verify_dashboard.py` 看
`externalRefs` 是否为 0。

**Q：中英切换要不要接翻译 API？**
不要。用**双侧编译**：数据里每个文案存 `{zh, en}`，切换只改 `LANG` 后整体重渲染。
运行时翻译会丢可视化状态且译文不可控。

---

## 自检记录（2026-10-08）

技能包内的脚本都实跑过，不是「写出来就算」：

| 验证项 | 方式 | 结果 |
|---|---|---|
| Node 脚本语法 | `node --check` × 3 | 全部通过 |
| Python 脚本语法 | `py_compile` × 2 | 全部通过 |
| 目标清单模板 | 解析 + key 唯一性 | 7 条，唯一 |
| `fetch_pages.py` 正常路径 | 抓 2 个真实站点 | 均 200，生成 `_manifest.json` |
| `fetch_pages.py` 失败路径 | 混入 1 个不可解析域名 | 该条 `ok=false` 记 error，其余 2 条照常成功，退出码 1 |
| `cdp_probe.mjs` 无端点 | 本机未开调试端口 | 退出码 1，列出 3 个端口探测结果与开启指引 |
| **CDP 通道端到端** | 起真实 Chromium（`:9333`）+ probe + fetch | probe 退出码 0；fetch 2 成功 1 失败，`channel=cdp-local-browser` |
| CDP 错误页识别 | 上述不可解析域名 | 修正后正确判 `ok=false`（原因：浏览器错误页）；修正前误判为成功 |
| `gh_metrics.mjs` | 拉 2 个真实仓库 | 取到 star / 协议 / 最近提交 |
| `verify_dashboard.py` 正例 | 验一份已知合格的看板 | 12 项检查全绿，退出码 0 |
| `verify_dashboard.py` 反例 | 故意做坏的页面（外链 + 计数不符 + JS 报错） | 准确保报 3 项未通过，退出码 1 |

反例那一项是必须的——**只验证「能报绿」的验证器等于没验证**。

---

## 授权

本技能可自由用于个人与商业项目。转载或二次分发请保留作者署名。

---

## 联系

- 作者：李福春 · 资深架构师
- 邮箱：hello@carter.li
- GitHub：[@lifuchun522](https://github.com/lifuchun522)
