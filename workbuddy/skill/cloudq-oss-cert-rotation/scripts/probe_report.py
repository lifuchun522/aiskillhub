#!/usr/bin/env python3
"""OSS 自定义域名巡检 + 结果页面生成。

一次巡检 = 入口识别（DNS + 响应头）+ 证书只读探活（TLS 握手）。
可重复 R 轮，统计端到端耗时 P50 / P95、失败轮次与外部调用次数，
最后把结果渲染成**结果页面**（自包含 HTML）与 Markdown 报告。

只读边界：只查一次 DNS、只发一次 HTTPS GET（不读响应体）、只做一次 TLS 握手；
不申请、不部署、不回滚，不读取云账号 AK/SK。仅向 `--out-dir` 写报告文件。
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as H
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cert_probe import check_cert  # noqa: E402
from entry_probe import check_entry  # noqa: E402

OPERATION = "READ_ONLY_INSPECTION"

# 每轮巡检固定发起的只读外部调用；调用数是成本口径的分母，必须显式列出。
EXTERNAL_CALLS: tuple[tuple[str, str], ...] = (
    ("dns_cname", "DNS 查询 CNAME（默认解析服务器 223.5.5.5:53/UDP）"),
    ("https_get", "HTTPS GET 只取响应头，不读响应体"),
    ("tls_handshake", "只读 TLS 握手，开启系统信任链与主机名校验"),
)
EXTERNAL_CALLS_PER_ROUND = len(EXTERNAL_CALLS)

# 视为「未按预期完成」的终态，用于失败轮次统计
_BAD_CERT_STATUS = {"UNVERIFIED"}
_BAD_ENTRY = {"UNKNOWN"}


def percentile(values: list[float], p: float) -> float:
    """最近秩法（nearest-rank）百分位，不做插值。

    `p` 取 0–100；空样本返回 `float('nan')`，由调用方决定如何呈现。
    """
    if not values:
        return float("nan")
    if not 0 < p <= 100:
        raise ValueError("p 必须在 (0, 100] 区间")
    ordered = sorted(values)
    rank = -(-len(ordered) * p // 100)  # ceil(n * p / 100)，整数运算避免浮点误差
    index = max(0, int(rank) - 1)
    return float(ordered[index])


def _round_ms(value: float) -> float:
    return round(float(value), 1)


def summarize_latency(samples_ms: list[float]) -> dict:
    """把一组耗时（毫秒）汇总成 min / P50 / P95 / max / mean。"""
    values = [float(v) for v in samples_ms]
    if not values:
        return {"rounds": 0, "min_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None, "mean_ms": None}
    return {
        "rounds": len(values),
        "min_ms": _round_ms(min(values)),
        "p50_ms": _round_ms(percentile(values, 50)),
        "p95_ms": _round_ms(percentile(values, 95)),
        "max_ms": _round_ms(max(values)),
        "mean_ms": _round_ms(sum(values) / len(values)),
    }


def run_round(
    domain: str,
    *,
    warn_days: int = 30,
    port: int = 443,
    timeout: float = 8.0,
    dns_server: str | None = None,
) -> dict:
    """跑一轮巡检，返回入口结论、证书结论与分段耗时（毫秒）。"""
    t0 = time.perf_counter()
    entry = check_entry(domain, port=port, timeout=timeout, dns_server=dns_server)
    t1 = time.perf_counter()
    cert = check_cert(domain, warn_days, port=port, timeout=timeout)
    t2 = time.perf_counter()
    entry_ms = (t1 - t0) * 1000.0
    cert_ms = (t2 - t1) * 1000.0
    return {
        "entry": {k: entry[k] for k in ("entry", "evidence", "cname_chain", "http_status", "server_header")},
        "entry_errors": entry.get("errors", []),
        "cert": cert,
        "ms": {
            "entry": _round_ms(entry_ms),
            "cert": _round_ms(cert_ms),
            "total": _round_ms(entry_ms + cert_ms),
        },
    }


def inspect(
    domain: str,
    *,
    rounds: int = 5,
    warn_days: int = 30,
    port: int = 443,
    timeout: float = 8.0,
    dns_server: str | None = None,
    runner=run_round,
) -> dict:
    """连续巡检 `rounds` 轮，产出带样本量、观测窗口与耗时分位的结果结构。"""
    if rounds < 1:
        raise ValueError("rounds 必须 >= 1")
    started = dt.datetime.now(dt.timezone.utc)
    samples = [runner(domain, warn_days=warn_days, port=port, timeout=timeout, dns_server=dns_server) for _ in range(rounds)]
    finished = dt.datetime.now(dt.timezone.utc)

    entry_summary = summarize_latency([s["ms"]["entry"] for s in samples])
    cert_summary = summarize_latency([s["ms"]["cert"] for s in samples])
    total_summary = summarize_latency([s["ms"]["total"] for s in samples])

    failed = sum(
        1
        for s in samples
        if s["cert"].get("status") in _BAD_CERT_STATUS or s["entry"].get("entry") in _BAD_ENTRY
    )

    return {
        "domain": domain,
        "operation": OPERATION,
        "warn_days": warn_days,
        "port": port,
        "rounds": rounds,
        "window": {
            "started_at_utc": started.isoformat(timespec="seconds"),
            "finished_at_utc": finished.isoformat(timespec="seconds"),
            "elapsed_s": round((finished - started).total_seconds(), 2),
        },
        "external_calls": {
            "per_round": EXTERNAL_CALLS_PER_ROUND,
            "total": EXTERNAL_CALLS_PER_ROUND * rounds,
            "items": [{"name": n, "desc": d} for n, d in EXTERNAL_CALLS],
        },
        "latency": {"entry": entry_summary, "cert": cert_summary, "total": total_summary},
        "failed_rounds": failed,
        "failure_rate": round(failed / rounds, 4),
        "entry_final": samples[-1]["entry"],
        "cert_final": samples[-1]["cert"],
        "samples": samples,
        "generated_at_utc": finished.isoformat(timespec="seconds"),
    }


def _pct(value) -> str:
    return "—" if value is None else f"{value}%"


def _num(value) -> str:
    return "—" if value is None else str(value)


def render_markdown(report: dict) -> str:
    """把结果结构渲染成 Markdown 结果页。"""
    lat = report["latency"]
    entry = report["entry_final"]
    cert = report["cert_final"]
    lines = [
        f"# 证书巡检结果页｜{report['domain']}",
        "",
        f"- 巡检时间（UTC）：{report['window']['started_at_utc']} → {report['window']['finished_at_utc']}"
        f"（耗时 {report['window']['elapsed_s']}s）",
        f"- 样本量：{report['rounds']} 轮；预警阈值：{report['warn_days']} 天",
        f"- 外部只读调用：每轮 {report['external_calls']['per_round']} 次，合计 {report['external_calls']['total']} 次",
        "",
        "## 结论",
        "",
        f"- 访问入口：{entry['entry']}（{entry['evidence']}）",
        f"- 证书状态：{cert['status']}；剩余 {_num(cert.get('expires_in_days'))} 天；"
        f"到期 {cert.get('not_after_utc', '—')}",
        "",
        "## 端到端耗时（毫秒，最近秩法）",
        "",
        "| 阶段 | min | P50 | P95 | max | 均值 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, label in (("entry", "入口识别"), ("cert", "证书探活"), ("total", "整轮合计")):
        s = lat[key]
        lines.append(
            f"| {label} | {_num(s['min_ms'])} | {_num(s['p50_ms'])} | {_num(s['p95_ms'])} | "
            f"{_num(s['max_ms'])} | {_num(s['mean_ms'])} |"
        )
    lines += [
        "",
        f"失败轮次：{report['failed_rounds']} / {report['rounds']}（失败率 {_pct(round(report['failure_rate'] * 100, 2))}）",
        "",
        "## 外部只读调用清单",
        "",
    ]
    for item in report["external_calls"]["items"]:
        lines.append(f"- `{item['name']}`：{item['desc']}")
    lines += [
        "",
        "## 边界",
        "",
        "- 本页数据来自本机真实只读探测，证书结论以握手结果为准；写操作仍未执行。",
        f"- 耗时随网络与解析路径波动，{report['rounds']} 轮样本不构成跨环境性能承诺。",
    ]
    return "\n".join(lines) + "\n"


def render_html(report: dict) -> str:
    """把结果结构渲染成自包含结果页面（内联样式，便于复制/打印）。"""
    lat = report["latency"]
    entry = report["entry_final"]
    cert = report["cert_final"]
    e = H.escape

    def cell(v):
        return "—" if v is None else e(str(v))

    rows = "".join(
        f'<tr><th style="text-align:left;padding:9px 12px;border-bottom:1px solid #e3e8ee;'
        f'font-weight:600;color:#1f2733">{label}</th>'
        + "".join(
            f'<td style="text-align:right;padding:9px 12px;border-bottom:1px solid #e3e8ee;'
            f'color:#37424f;font-variant-numeric:tabular-nums">{cell(s[k])}</td>'
            for k in ("min_ms", "p50_ms", "p95_ms", "max_ms", "mean_ms")
        )
        + "</tr>"
        for key, label in (("entry", "入口识别"), ("cert", "证书探活"), ("total", "整轮合计"))
        for s in (lat[key],)
    )

    calls = "".join(
        f'<li style="margin:6px 0;color:#37424f"><span style="display:inline-block;min-width:118px;'
        f'font-weight:600;color:#1f2733">{e(item["name"])}</span>{e(item["desc"])}</li>'
        for item in report["external_calls"]["items"]
    )

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>证书巡检结果页｜{e(report['domain'])}</title></head>
<body style="margin:0;padding:24px;background:#f5f7f9;font:16px/1.8 -apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;color:#1f2733">
<article style="max-width:760px;margin:0 auto;background:#ffffff;border:1px solid #e3e8ee;border-radius:12px;padding:32px 34px">
<h1 style="margin:0 0 6px;font-size:24px;line-height:1.4">证书巡检结果页</h1>
<p style="margin:0 0 22px;color:#697787;font-size:14px">{e(report['domain'])}　·　只读巡检　·　{report['rounds']} 轮样本</p>

<h2 style="margin:26px 0 12px;font-size:18px;border-left:4px solid #d65235;padding-left:11px">巡检结论</h2>
<div style="background:#f7f9fb;border:1px solid #e3e8ee;border-radius:9px;padding:16px 18px;margin:0 0 8px">
<p style="margin:0 0 8px"><strong>访问入口：</strong>{e(entry['entry'])}</p>
<p style="margin:0 0 8px;color:#4a5766;font-size:14px">判据：{e(entry['evidence'])}</p>
<p style="margin:0 0 8px"><strong>证书状态：</strong>{e(str(cert.get('status', '—')))}　剩余 {cell(cert.get('expires_in_days'))} 天</p>
<p style="margin:0;color:#4a5766;font-size:14px">到期时间（UTC）：{cell(cert.get('not_after_utc'))}</p>
</div>

<h2 style="margin:26px 0 12px;font-size:18px;border-left:4px solid #d65235;padding-left:11px">端到端耗时（毫秒）</h2>
<p style="margin:0 0 12px;color:#697787;font-size:14px">口径：最近秩法（nearest-rank），不做插值；样本量 {report['rounds']} 轮，窗口 {e(report['window']['started_at_utc'])} → {e(report['window']['finished_at_utc'])}</p>
<table style="width:100%;border-collapse:collapse;font-size:14.5px">
<thead><tr>
<th style="text-align:left;padding:9px 12px;border-bottom:2px solid #cdd7e0;color:#1f2733">阶段</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0;color:#1f2733">min</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0;color:#1f2733">P50</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0;color:#1f2733">P95</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0;color:#1f2733">max</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0;color:#1f2733">均值</th>
</tr></thead><tbody>{rows}</tbody></table>
<p style="margin:12px 0 0;color:#4a5766;font-size:14px">失败轮次：{report['failed_rounds']} / {report['rounds']}（失败率 {_pct(round(report['failure_rate'] * 100, 2))}）</p>

<h2 style="margin:26px 0 12px;font-size:18px;border-left:4px solid #d65235;padding-left:11px">外部只读调用</h2>
<p style="margin:0 0 10px;color:#4a5766;font-size:14px">每轮 {report['external_calls']['per_round']} 次，合计 {report['external_calls']['total']} 次（成本口径分母）</p>
<ul style="margin:0;padding-left:20px;font-size:14.5px">{calls}</ul>

<h2 style="margin:26px 0 12px;font-size:18px;border-left:4px solid #d65235;padding-left:11px">边界</h2>
<p style="margin:0;color:#4a5766;font-size:14px">数据来自本机真实只读探测，证书结论以握手结果为准；写操作未执行。耗时随网络与解析路径波动，{report['rounds']} 轮样本不构成跨环境性能承诺。</p>
</article>
</body></html>
"""


def write_report(report: dict, out_dir: str) -> dict:
    """把结果页面写入 `out_dir`，返回产物路径。"""
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "cert-report.html")
    md_path = os.path.join(out_dir, "cert-report.md")
    json_path = os.path.join(out_dir, "cert-report.json")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(render_html(report))
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return {"html": html_path, "markdown": md_path, "json": json_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--rounds", type=int, default=5, help="重复轮数（样本量），默认 5")
    parser.add_argument("--warn-days", type=int, default=30)
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--dns-server", default=None, help="解析服务器，默认 223.5.5.5")
    parser.add_argument("--out-dir", default="report", help="结果页面输出目录")
    parser.add_argument("--json", action="store_true", help="仅打印 JSON 结果，不写文件")
    args = parser.parse_args(argv)

    try:
        report = inspect(
            args.domain,
            rounds=args.rounds,
            warn_days=args.warn_days,
            port=args.port,
            timeout=args.timeout,
            dns_server=args.dns_server,
        )
    except ValueError as err:
        print(json.dumps({"domain": args.domain, "status": "ERROR", "error": str(err)}, ensure_ascii=False))
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    paths = write_report(report, args.out_dir)
    summary = {
        "domain": report["domain"],
        "entry": report["entry_final"]["entry"],
        "cert_status": report["cert_final"].get("status"),
        "expires_in_days": report["cert_final"].get("expires_in_days"),
        "rounds": report["rounds"],
        "external_calls_total": report["external_calls"]["total"],
        "failed_rounds": report["failed_rounds"],
        "latency_ms": report["latency"]["total"],
        "report": paths,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
