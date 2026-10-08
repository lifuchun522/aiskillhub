#!/usr/bin/env node
/**
 * cdpfetch · CDP 通道抓取器（直连本地浏览器，携带登录态）
 *
 * 与 fetch_pages.py 的差别：CDP 通道复用你日常在用的 Chrome / Edge，
 * 因此**天然带着你的登录态**——需要登录才能看的页面、内部系统、被反爬拦住的
 * 站点，走这条通道。代价是要求本机浏览器已开远程调试端口（见 cdp_probe.mjs）。
 *
 * 行为约定（遵循最小侵入）:
 *   - 只在 自己新建的后台 tab 中操作，绝不碰用户已有的 tab
 *   - 任务结束关闭自己建的 tab，用户环境保持原样
 *
 * 用法:
 *   node cdp_fetch.mjs --targets templates/targets.example.json --out ./raw
 *   node cdp_fetch.mjs --targets t.json --out ./raw --port 9222 --concurrency 3 --keep-tabs
 *
 * 产出: 与 fetch_pages.py 完全一致（<key>.txt / .links.txt / .html / _manifest.json），
 *       便于下游看板与验证脚本对两条通道无差别消费。
 *
 * 依赖: Node.js 22+（原生 WebSocket）
 */
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

/* ------------------------------- 参数 ------------------------------- */

function arg(name, fallback = undefined) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const v = process.argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}

const targetsPath = arg('targets');
if (!targetsPath || targetsPath === true) {
  console.error('用法: node cdp_fetch.mjs --targets <目标清单.json> --out <目录> [--port 9222]');
  process.exit(2);
}
const outDir = String(arg('out', './raw'));
const port = Number(arg('port', 9222));
const concurrency = Number(arg('concurrency', 3));
const timeoutMs = Number(arg('timeout', 60000));
const settleMs = Number(arg('settle', 3500));
const scrollTimes = Number(arg('scroll', 3));
const keepTabs = Boolean(arg('keep-tabs'));
const skipHtml = Boolean(arg('no-html'));

/* ------------------------------- 工具 ------------------------------- */

const since = (t) => new Date(t).toISOString().replace(/Z$/, 'Z');

function nowIso() {
  // 与 Python 侧一致：带本地时区偏移、精确到秒
  const d = new Date();
  const off = -d.getTimezoneOffset();
  const sign = off >= 0 ? '+' : '-';
  const pad = (n) => String(Math.abs(n)).padStart(2, '0');
  const tz = `${sign}${pad(off / 60)}:${pad(off % 60)}`;
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
  return `${local}${tz}`;
}

async function sha256Hex(text) {
  const { createHash } = await import('node:crypto');
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

function loadTargets(p) {
  const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
  if (!Array.isArray(raw) || raw.length === 0) throw new Error('目标清单必须是非空 JSON 数组');
  const seen = new Set();
  return raw.map((item) => {
    const key = item.key ?? item[0];
    const url = item.url ?? item[1];
    if (!key || !url) throw new Error(`目标缺少 key 或 url: ${JSON.stringify(item)}`);
    if (seen.has(key)) throw new Error(`key 重复会导致落盘覆盖: ${key}`);
    seen.add(key);
    return { key, url };
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* --------------------------- 极简 CDP 客户端 --------------------------- */

class CdpSession {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.id = 0;
    this.pending = new Map();
    this.waiters = [];
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      const onOpen = () => resolve();
      const onErr = (e) => reject(new Error(`WS 连接失败: ${e.message || e}`));
      this.ws.addEventListener('open', onOpen, { once: true });
      this.ws.addEventListener('error', onErr, { once: true });
    });
    this.ws.addEventListener('message', (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(`${msg.error.message} (code ${msg.error.code})`));
        else resolve(msg.result);
        return;
      }
      if (msg.method) {
        for (let i = this.waiters.length - 1; i >= 0; i -= 1) {
          if (this.waiters[i].method === msg.method) {
            const w = this.waiters.splice(i, 1)[0];
            clearTimeout(w.timer);
            w.resolve(msg.params);
          }
        }
      }
    });
  }

  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP 调用超时: ${method}`));
        }
      }, timeoutMs);
    });
  }

  waitFor(method, ms = timeoutMs) {
    return new Promise((resolve, reject) => {
      const w = { method, resolve };
      w.timer = setTimeout(() => {
        const i = this.waiters.indexOf(w);
        if (i >= 0) this.waiters.splice(i, 1);
        reject(new Error(`等待 ${method} 超时`));
      }, ms);
      this.waiters.push(w);
    });
  }

  close() {
    try {
      this.ws?.close();
    } catch {
      /* 忽略 */
    }
  }
}

/* ------------------------------ HTTP 助手 ------------------------------ */

async function httpJson(url, init) {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`HTTP ${res.status} ← ${url}`);
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

/** 新建后台 tab。旧版 Chrome 只认 GET，新版要求 PUT，两种都试。 */
async function createTab(initialUrl) {
  const q = encodeURIComponent(initialUrl);
  try {
    return await httpJson(`http://127.0.0.1:${port}/json/new?${q}`, { method: 'PUT' });
  } catch {
    return await httpJson(`http://127.0.0.1:${port}/json/new?${q}`);
  }
}

async function closeTab(targetId) {
  try {
    await fetch(`http://127.0.0.1:${port}/json/close/${targetId}`);
  } catch {
    /* 关闭失败不影响结果 */
  }
}

/* -------------------------------- 抓取 -------------------------------- */

const TEXT_JS = "(() => document.body ? document.body.innerText : '')()";

const LINKS_JS = `(() => {
  const out = [];
  for (const a of document.querySelectorAll('a[href]')) {
    const t = (a.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 60);
    if (t) out.push(t + ' :: ' + a.href);
  }
  return Array.from(new Set(out));
})()`;

async function evaluate(session, expression) {
  const r = await session.send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text || '页面内求值异常');
  return r.result?.value;
}

/** 统一的逐条结果输出。两处退出路径（正常结束 / 错误页早退）共用，避免日志格式漂移。 */
function logRec(rec) {
  console.log(
    `[${rec.ok ? 'OK ' : 'ERR'}] ${rec.key.padEnd(24)} ${rec.status ?? ''} ${rec.ok ? rec.text_len : rec.error}`,
  );
}

async function fetchOne({ key, url }) {
  const rec = {
    key,
    requested_url: url,
    fetched_at: nowIso(),
    channel: 'cdp-local-browser',
    ok: false,
  };
  let target = null;
  let session = null;
  try {
    target = await createTab('about:blank');
    if (!target?.webSocketDebuggerUrl) throw new Error('未能取得新 tab 的调试端点');
    session = new CdpSession(target.webSocketDebuggerUrl);
    await session.connect();
    await session.send('Page.enable');
    await session.send('Runtime.enable');

    const loaded = session.waitFor('Page.loadEventFired').catch(() => null);
    const nav = await session.send('Page.navigate', { url });
    rec.status = nav?.frameId ? 200 : null; // CDP 不回传 HTTP 状态，200 仅代表导航被接受
    await loaded;
    await sleep(settleMs);

    // 滚动触发懒加载
    for (let i = 0; i < scrollTimes; i += 1) {
      await evaluate(session, 'window.scrollBy(0, 2600)');
      await sleep(900);
    }
    if (scrollTimes) {
      await evaluate(session, 'window.scrollTo(0, 0)');
      await sleep(300);
    }

    rec.final_url = await evaluate(session, 'location.href');
    rec.title = await evaluate(session, 'document.title');

    // CDP 不回传 HTTP 状态码，导航失败会停在浏览器的错误页上，而错误页同样是
    // 「加载完成」——不显式识别就会把错误页当成抓取成功（实测：不可解析的域名
    // 得到 status=200、title=域名、正文 141 字）。final_url 的 chrome-error://
    // 与错误页的 #main-frame-error 是两个确定信号，直接判失败。
    const isErrorPage = /^chrome-error:\/\//.test(rec.final_url || '')
      || (await evaluate(session, "!!document.querySelector('#main-frame-error')"));
    if (isErrorPage) {
      rec.ok = false;
      rec.error = `浏览器错误页（导航未成功）：${rec.final_url}`;
      rec.text_len = 0;
      logRec(rec);
      return rec;
    }

    const text = (await evaluate(session, TEXT_JS)) || '';
    const links = (await evaluate(session, LINKS_JS)) || [];
    const html = (await session.send('Runtime.evaluate', {
      expression: 'document.documentElement.outerHTML',
      returnByValue: true,
    })).result?.value || '';

    rec.text_len = text.length;
    rec.link_count = links.length;
    rec.text_sha256 = await sha256Hex(text);
    rec.html_sha256 = await sha256Hex(html);
    rec.ok = true;

    fs.writeFileSync(path.join(outDir, `${key}.txt`), text, 'utf8');
    fs.writeFileSync(path.join(outDir, `${key}.links.txt`), links.join('\n'), 'utf8');
    if (!skipHtml) fs.writeFileSync(path.join(outDir, `${key}.html`), html, 'utf8');
  } catch (e) {
    rec.error = `${e.name || 'Error'}: ${e.message || e}`;
  } finally {
    session?.close();
    if (target?.id && !keepTabs) await closeTab(target.id);
  }
  logRec(rec);
  return rec;
}

async function pool(items, limit, worker) {
  const results = new Array(items.length);
  let cursor = 0;
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (cursor < items.length) {
        const i = cursor;
        cursor += 1;
        results[i] = await worker(items[i]);
      }
    }),
  );
  return results;
}

/* -------------------------------- 主流程 -------------------------------- */

async function main() {
  let targets;
  try {
    targets = loadTargets(targetsPath);
  } catch (e) {
    console.error(`[FATAL] ${e.message}`);
    process.exit(2);
  }

  try {
    const v = await httpJson(`http://127.0.0.1:${port}/json/version`);
    console.log(`[INFO] 已连接 ${v.Browser}（协议 ${v['Protocol-Version']}）`);
  } catch (e) {
    console.error(`[FATAL] CDP 端点不可用（127.0.0.1:${port}）：${e.message}`);
    console.error('        先运行: node cdp_probe.mjs   获取开启指引');
    console.error('        或改用: python fetch_pages.py --targets <清单> --out <目录>');
    process.exit(1);
  }

  fs.mkdirSync(outDir, { recursive: true });
  const started = Date.now();
  const results = (await pool(targets, concurrency, fetchOne)).sort((a, b) => a.key.localeCompare(b.key));

  const manifest = path.join(outDir, '_manifest.json');
  fs.writeFileSync(manifest, JSON.stringify(results, null, 2), 'utf8');

  const ok = results.filter((r) => r.ok).length;
  console.log(`\n[MANIFEST] ${manifest}`);
  console.log(`[SUMMARY ] ${ok}/${results.length} 成功，耗时 ${((Date.now() - started) / 1000).toFixed(1)}s`);
  process.exit(ok === results.length ? 0 : 1);
}

main().catch((e) => {
  console.error(`[FATAL] ${e?.stack || e}`);
  process.exit(1);
});
