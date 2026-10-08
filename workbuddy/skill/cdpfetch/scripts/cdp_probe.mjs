#!/usr/bin/env node
/**
 * cdpfetch · CDP 调试端点探测
 *
 * 判断「CDP 直连本地浏览器」通道当前是否可用——即本机是否有 Chromium 系浏览器
 * 打开了远程调试端口。CDP 通道的价值在于复用你的日常浏览器，天然携带登录态。
 *
 * 用法:
 *   node cdp_probe.mjs                 # 人类可读输出
 *   node cdp_probe.mjs --json          # 机器可读，供上层脚本判定
 *   node cdp_probe.mjs --port 9333     # 指定端口
 *
 * 退出码:
 *   0 = CDP 可用（stdout 给出 browser / webSocketDebuggerUrl）
 *   1 = 不可用（stdout 给出各端口探测结果与开启指引）
 *
 * 注意: Node.js 22+ 必需（cdp_fetch.mjs 依赖原生 WebSocket，本脚本仅用 fetch）。
 */
import process from 'node:process';

const DEFAULT_PORTS = [9222, 9223, 9333];

function arg(name, fallback = undefined) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const v = process.argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}

async function probe(port, timeoutMs = 1500) {
  const url = `http://127.0.0.1:${port}/json/version`;
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: ac.signal });
    if (!res.ok) return { port, up: false, reason: `HTTP ${res.status}` };
    const j = await res.json();
    return {
      port,
      up: true,
      browser: j.Browser || null,
      protocol: j['Protocol-Version'] || null,
      userAgent: j['User-Agent'] || null,
      webSocketDebuggerUrl: j.webSocketDebuggerUrl || null,
    };
  } catch (e) {
    return { port, up: false, reason: e.name === 'AbortError' ? 'timeout' : String(e.message || e) };
  } finally {
    clearTimeout(timer);
  }
}

const portArg = arg('port');
const ports = portArg && portArg !== true ? [Number(portArg)] : DEFAULT_PORTS;
const asJson = Boolean(arg('json'));

const results = [];
for (const p of ports) results.push(await probe(p));

const hit = results.find((r) => r.up);

if (asJson) {
  console.log(JSON.stringify({ available: Boolean(hit), channels: results }, null, 2));
} else if (hit) {
  console.log(`[OK]   CDP 通道可用 → 127.0.0.1:${hit.port}`);
  console.log(`       浏览器      : ${hit.browser}`);
  console.log(`       协议版本    : ${hit.protocol}`);
  console.log(`       调试 WS 端点: ${hit.webSocketDebuggerUrl}`);
  console.log('       下一步      : node cdp_fetch.mjs --targets <目标清单> --out ./raw');
} else {
  console.log('[ERR]  没有任何浏览器打开远程调试端口，CDP 通道不可用。');
  for (const r of results) console.log(`       127.0.0.1:${r.port} → ${r.reason}`);
  console.log('');
  console.log('       开启方式（择一，需完全退出浏览器后重启）:');
  console.log('         Chrome : chrome.exe --remote-debugging-port=9222 --user-data-dir="%TEMP%\\cdp-profile"');
  console.log('         Edge   : msedge.exe --remote-debugging-port=9222 --user-data-dir="%TEMP%\\cdp-profile"');
  console.log('       若不想动日常浏览器，改用 Playwright 无头通道:');
  console.log('         python fetch_pages.py --targets <目标清单> --out ./raw');
}

process.exit(hit ? 0 : 1);
