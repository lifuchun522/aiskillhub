# 双通道选型：CDP 直连 vs Playwright 无头

cdpfetch 提供两条抓取通道，**产出格式完全一致**（`<key>.txt` / `.links.txt` / `.html` / `_manifest.json`），
所以下游的看板构建与验证脚本对两条通道无差别消费。区别只在「用谁的浏览器」和「带不带登录态」。

## 一、对照表

| 维度 | CDP 直连（`cdp_fetch.mjs`） | Playwright 无头（`fetch_pages.py`） |
|---|---|---|
| 浏览器来源 | 用户**日常在用的** Chrome / Edge | 独立下载的 Chromium |
| 登录态 | **天然携带**（复用你的 profile） | 无，需脚本内登录 |
| 前置条件 | 浏览器需开远程调试端口（`cdp_probe.mjs`） | 只需 `playwright install chromium` |
| 对用户环境的影响 | 会在日常浏览器里开后台 tab（用完即关） | **零影响**，完全隔离 |
| 反爬对抗 | 强（真实浏览器指纹 + 真实登录态） | 中（需 `--disable-blink-features=AutomationControlled`） |
| 并发能力 | 受真实浏览器资源限制，建议 ≤3 | 好，建议 ≤5 |
| HTTP 状态码 | **拿不到**（CDP 不回传 status） | 拿得到（`response.status`） |
| 验证码 / 风控 | 可 `--headed` 人工过 | 需 `--headed` 人工过 |
| 适用场景 | 内部系统、需登录页、强反爬站点 | 公开官网、文档站、批量取数 |

> **CDP 拿不到 HTTP 状态码**这条最容易被忽略：`cdp_fetch.mjs` 里 `status` 记的是「导航被接受」而非真实响应码，
> 所以走 CDP 通道时，**不能把 `status: 200` 当作页面可用的证据**。
> 实测证据（2026-10-08）：对一个**不可解析的域名**发起抓取，CDP 通道返回
> `status: 200` + `title=域名` + 正文 141 字（浏览器的「无法访问此网站」错误页）。
> 仅看 status 会把它当成抓取成功。
>
> `cdp_fetch.mjs` 已内建错误页识别：`final_url` 以 `chrome-error://` 开头、
> 或页面存在 `#main-frame-error` 元素时，直接判 `ok=false` 并写明原因。
> 若要人工复核，`text_len` 与 `title` 仍是第二道判据。
> 这也是本技能把两条通道的 `channel` 字段写进存证的原因：报告里要能说清数据是哪条通道来的。

## 二、默认策略

```
需要登录态 / 内部系统 / 强反爬  ──→  CDP 直连
                  ↓ 不可用（无调试端口）
公开站点批量取数                ──→  Playwright 无头（默认）
                  ↓ 被反爬拦住
                                  升级到 CDP，或 --headed 人工过
```

**先探测，再决定**，不要默认 CDP：

```bash
node scripts/cdp_probe.mjs --json     # available=true / false
```

探测返回 `false` 是常态（多数人日常浏览器不开调试端口），此时**直接回落 Playwright 无头即可**，
不必把一个可自解的前置问题抛给用户。只有在「必须登录态」且 CDP 不可用时，才需要请用户配合开端口或登录。

## 三、开启 CDP 调试端口的正确姿势

**关键点：必须用独立的 `--user-data-dir`，且浏览器要完全退出后重启。**
直接给日常 profile 加 `--remote-debugging-port` 在较新 Chrome 上会被拒绝（Chrome 136+ 对默认 profile 有安全限制）。

```bash
# Windows（Git Bash / PowerShell 均可）
chrome.exe --remote-debugging-port=9222 --user-data-dir="%TEMP%\cdp-profile"

# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir="$TMPDIR/cdp-profile"
```

用独立 profile 换取「不污染日常浏览器」的代价是：**该 profile 里是空登录态**。
要带登录态，就得在这个 profile 里手动登录一次，之后长期复用。

## 四、最小侵入约定（CDP 通道）

- 只在**自己新建的后台 tab** 中操作，绝不读写用户已有的 tab
- 任务结束后用 `/json/close/<targetId>` 关闭自己建的 tab
- `--keep-tabs` 仅用于调试，交付前不要带这个参数

## 五、Node 与 Python 的版本前提

| 通道 | 运行前提 |
|---|---|
| `cdp_fetch.mjs` | **Node.js 22+**（依赖原生 `WebSocket`，18 会报 `WebSocket is not defined`） |
| `cdp_probe.mjs` | Node.js 18+（仅用 `fetch`） |
| `gh_metrics.mjs` | Node.js 18+ |
| `fetch_pages.py` / `verify_dashboard.py` | Python 3.9+，`pip install playwright && playwright install chromium` |
