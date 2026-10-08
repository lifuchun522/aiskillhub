#!/usr/bin/env node
/**
 * cdpfetch · GitHub 客观指标拉取
 *
 * 为什么需要单独一步：官网页面上的「多少 Star / 什么协议」是**转述**，
 * 会过期、会被营销口径修饰。仓库的 star / fork / license / 最近提交时间是
 * **平台 API 的一手事实**，比页面文字更硬——做对比看板时用它交叉印证。
 *
 * 用法:
 *   node gh_metrics.mjs agentscope-ai/agentscope langchain-ai/langchain microsoft/autogen
 *   node gh_metrics.mjs owner/repo --out gh_metrics.json
 *   GITHUB_TOKEN=xxx node gh_metrics.mjs owner/repo      # 抬高限流额度（未认证 60 次/小时）
 *
 * 退出码: 0 全部成功 / 1 存在失败项（失败项已写入结果数组，不中断其余仓库）
 */
import fs from 'node:fs';
import process from 'node:process';

function arg(name, fallback = undefined) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const v = process.argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}

const outPath = arg('out');
const repos = process.argv.slice(2).filter((a) => /^[\w.-]+\/[\w.-]+$/.test(a));

if (repos.length === 0) {
  console.error('用法: node gh_metrics.mjs owner/repo [owner/repo ...] [--out gh_metrics.json]');
  process.exit(2);
}

const token = process.env.GITHUB_TOKEN;
const headers = {
  Accept: 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28',
  'User-Agent': 'cdpfetch/1.0',
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
};

async function one(fullName) {
  const rec = { repo: fullName, fetched_at: new Date().toISOString(), ok: false };
  try {
    const res = await fetch(`https://api.github.com/repos/${fullName}`, { headers });
    if (!res.ok) {
      rec.error = `HTTP ${res.status}${res.status === 403 ? '（可能触发限流，配置 GITHUB_TOKEN 可解除）' : ''}`;
      return rec;
    }
    const j = await res.json();
    Object.assign(rec, {
      ok: true,
      description: j.description,
      stars: j.stargazers_count,
      forks: j.forks_count,
      open_issues: j.open_issues_count,
      language: j.language,
      license: j.license?.spdx_id ?? null,
      archived: j.archived,
      created_at: j.created_at,
      pushed_at: j.pushed_at,
      homepage: j.homepage,
      topics: j.topics ?? [],
      default_branch: j.default_branch,
    });
    return rec;
  } catch (e) {
    rec.error = `${e.name || 'Error'}: ${e.message || e}`;
    return rec;
  }
}

const results = [];
for (const r of repos) {
  const rec = await one(r);
  results.push(rec);
  console.log(
    rec.ok
      ? `[OK ] ${r.padEnd(34)} ★${String(rec.stars).padStart(7)}  ${rec.license ?? '-'}  最近提交 ${rec.pushed_at}`
      : `[ERR] ${r.padEnd(34)} ${rec.error}`,
  );
}

if (outPath && outPath !== true) {
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2), 'utf8');
  console.log(`\n[OUT] ${outPath}`);
}

const failed = results.filter((r) => !r.ok).length;
if (failed) console.log(`[WARN] ${failed}/${results.length} 个仓库未取到`);
process.exit(failed ? 1 : 0);
