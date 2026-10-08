# 存证规范：`_manifest.json` 与证据表字段

「数据是真实抓取的」这句话，不能靠声明，得靠**可复核的记录**。本技能把抓取过程
固化成一份机器可读的存证清单，任何一条结论都能顺着它回到原始页面。

## 一、文件布局

```
<out>/
├── _manifest.json          抓取清单（本文件规范的对象）
├── <key>.txt               渲染后正文（innerText，判读依据）
├── <key>.links.txt         页面链接清单，`可见文本 :: 绝对URL`
└── <key>.html              渲染后 DOM 快照（结构证据，可离线复查）
```

三件套缺一不可：`.txt` 用于取数，`.links.txt` 用于发现下一跳，`.html` 用于事后复核选择器。

## 二、`_manifest.json` 字段

数组，按 `key` 升序。单条记录：

| 字段 | 类型 | 含义 | 谁写的 |
|---|---|---|---|
| `key` | string | 目标标识，等于落盘文件名主干 | 必填 |
| `requested_url` | string | **发出请求时**的 URL | 自动 |
| `final_url` | string | 渲染结束时的 `location.href` | 自动 |
| `status` | number\|null | HTTP 状态码。**CDP 通道恒为 200 或 null，不代表真实响应码** | 自动 |
| `title` | string | `document.title` | 自动 |
| `text_len` | number | 正文字符数，**判断页面是否真抓到内容的主指标** | 自动 |
| `link_count` | number | 链接条数 | 自动 |
| `text_sha256` / `html_sha256` | string | 内容指纹，用于证明「同一 URL 前后两次抓到的是同一份」 | 自动 |
| `fetched_at` | string | 带时区 ISO 8601，精确到秒 | 自动 |
| `channel` | string | `playwright-headless` / `playwright-headed` / `cdp-local-browser` | 自动 |
| `ok` | boolean | 成功标志 | 自动 |
| `error` | string | 失败原因（`ok=false` 时存在） | 自动 |

### `requested_url` 与 `final_url` 必须分开记

跳转、地区重定向、版本路径归一化都会让两者不同。**报告里注明来源时要用 `final_url`**——
那才是内容实际来自的地址。实战例子：请求 `https://docs.agentscope.io/` 最终落在
`https://docs.agentscope.io/en/versions/2.0.9`，若按 requested_url 标注来源就是错的。

### 错误也是数据

抓取失败不抛异常、不中断整批，而是写成一条 `ok=false` + `error` 的记录。
理由：一批 19 个目标里 1 个超时，**不应该让另外 18 个的成果一起作废**；
同时「哪个源没抓到、为什么」本身就是要向用户交代的信息。

## 三、看板里的「证据表」怎么生成

看板顶部的来源标注与底部的证据表，都从 `_manifest.json` **直接投影**，不手写：

```js
// 典型投影：只保留对外可展示的字段
const evidence = manifest.map(r => ({
  key: r.key,
  url: r.final_url || r.requested_url,   // 用 final_url
  status: r.status,
  at: r.fetched_at,
  len: r.text_len,
  channel: r.channel
}));
```

要点：

1. **必须有 `url` + `at` 两列**——这是「真实抓取、可复核」的最小凭证。
2. 顶部横幅写**抓取窗口**（min→max 的 `fetched_at`），而不是笼统的「今天」。
3. 抓取失败的条目要出现在表里并标注失败，**不能静默剔除**——静默剔除等于制造样本偏差。
4. 交叉来源（如 GitHub API 的 star / license）单独一张表，标清它来自 API 而非页面渲染。

## 四、交叉印证约定

同一事实若有两个来源，**都记**，并标注口径差异：

| 情形 | 处理 |
|---|---|
| 官网一手页 vs 二手报道 | 采信官网，二手仅作线索；差异写进洞察 |
| 页面文字 vs 平台 API | 两个都列，注明 API 是平台一手事实 |
| 两次抓取结果不一致 | 比对 `text_sha256`，不一致则说明页面是动态的，需在报告里声明 |

实战例子：多个第三方站点仍在传播某产品「Professional $25/月」的旧档位，
而官网定价页只剩 Basic / Enterprise 两档。**正确处理是把这条冲突写进洞察**，
而不是悄悄按官网写、也不是按二手写。
