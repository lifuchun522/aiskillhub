#!/usr/bin/env python3
"""人工基线 vs Skill 路径：证书巡检效率对照测量（只读）。

把「一次证书巡检」拆成两段，分开处理，不混口径：

- **机器段（可实测）**：人工要手敲的命令序列，与 Skill 的一条命令，各自真实执行
  N 次并计时，用最近秩法给 P50/P95。这一段是实测，有命令、有输出、可复现。
- **人脑段（建模，不假装实测）**：发现异常、判定入口、计算分级、成文操作单。
  这一段本脚本**测不了**，只按显式区间列出，并逐条标注「依据」还是「建模」，
  由读者自行代入自己的耗时。

只读边界：人工侧命令只做 DNS 查询、HTTPS 取响应头、TLS 握手；Skill 侧只调
`probe_report.run_round`（同样三次只读调用）。不申请、不部署、不回滚证书，
不读取云账号 AK/SK；仅向 `--out-dir` 写对照报告。
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as H
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from probe_report import percentile, run_round, summarize_latency  # noqa: E402

OPERATION = "READ_ONLY_EFFICIENCY_BENCH"

# ---------------------------------------------------------------------------
# 人工侧：机器可测的命令序列（一个熟练工程师查一次证书要敲的东西）
# {domain} / {timeout} 由调用方填充
# ---------------------------------------------------------------------------
HUMAN_COMMANDS: tuple[dict, ...] = (
    {
        "name": "dns_cname",
        "cmd": "nslookup -type=CNAME {domain}",
        "desc": "解析 CNAME，拿入口线索",
    },
    {
        "name": "http_headers",
        "cmd": "curl -sSI --max-time {timeout} https://{domain}/",
        "desc": "取响应头，确认是否 OSS 直连",
    },
    {
        "name": "tls_cert",
        "cmd": "openssl s_client -connect {domain}:443 -servername {domain} </dev/null "
        "| openssl x509 -noout -enddate",
        "desc": "读出证书到期时间",
    },
)

# ---------------------------------------------------------------------------
# 人工侧：人脑段（建模区间，单位分钟）。测不了，就不假装测。
# `basis` 注明该区间是「实测依据」还是「建模」。
# ---------------------------------------------------------------------------
HUMAN_MODELED: tuple[dict, ...] = (
    {
        "name": "detect",
        "label": "发现异常",
        "note": "等外部反馈，或自己撞见红色警告后才开始排查",
        "lo_min": 5.0,
        "hi_min": 20.0,
        "basis": "依据：本案例作者自述『折腾了十几分钟』，且起于朋友发来截图",
    },
    {
        "name": "classify",
        "label": "判定入口",
        "note": "读懂响应头判据，判断流量是否经过 CDN",
        "lo_min": 0.5,
        "hi_min": 2.0,
        "basis": "建模：需熟悉 CDN 特征头；不熟悉时会判错并改错地方",
    },
    {
        "name": "grade",
        "label": "计算分级",
        "note": "到期时间与阈值相减，判定 HEALTHY / EXPIRING",
        "lo_min": 0.5,
        "hi_min": 2.0,
        "basis": "建模：日期心算 + 阈值比对 + 复核",
    },
    {
        "name": "write_order",
        "label": "成文操作单",
        "note": "整理证据、写更新准备与回退可行性判断",
        "lo_min": 2.0,
        "hi_min": 5.0,
        "basis": "建模：操作单五段结构中三段需人工成文",
    },
)

# 免费证书有效期 90 天 → 一年至少换 4 次，每次都要先「发现 + 诊断」
DEFAULT_RENEWALS_PER_YEAR = 4


def _ms(x: float) -> float:
    return round(float(x), 1)


def modeled_range() -> dict:
    """人脑段的建模区间合计（分钟）。"""
    lo = sum(s["lo_min"] for s in HUMAN_MODELED)
    hi = sum(s["hi_min"] for s in HUMAN_MODELED)
    return {"lo_min": round(lo, 1), "hi_min": round(hi, 1), "mid_min": round((lo + hi) / 2, 1)}


def run_manual_once(
    domain: str,
    *,
    timeout: float = 8.0,
    shell_runner=None,
) -> dict:
    """把一个熟练工程师的命令序列**逐条真实执行**一次，返回分段耗时与证据摘要。"""
    runner = shell_runner or _default_shell_runner
    per_cmd: list[dict] = []
    total = 0.0
    for item in HUMAN_COMMANDS:
        cmd = item["cmd"].format(domain=domain, timeout=int(timeout))
        t0 = time.perf_counter()
        ok, out, err = runner(cmd, timeout)
        elapsed = (time.perf_counter() - t0) * 1000.0
        total += elapsed
        per_cmd.append(
            {
                "name": item["name"],
                "cmd": cmd,
                "desc": item["desc"],
                "ok": ok,
                "ms": _ms(elapsed),
                "evidence": _evidence(item["name"], out, err),
            }
        )
    return {"per_command": per_cmd, "total_ms": _ms(total)}


def _default_shell_runner(cmd: str, timeout: float) -> tuple[bool, str, str]:
    """执行一条只读命令。失败不抛异常，交由调用方记录。

    人工命令里含管道与 `/dev/null` 重定向，必须有 POSIX shell 才能跑；
    Windows 下 `shell=True` 默认走 cmd.exe，会直接失败。所以这里优先显式调用
    bash，拿不到 bash 才退回系统默认 shell。
    """
    bash = shutil.which("bash") or shutil.which("sh")
    argv = [bash, "-lc", cmd] if bash else cmd
    try:
        proc = subprocess.run(
            argv,
            shell=not bash,
            capture_output=True,
            timeout=timeout + 10,
        )
    except Exception as err:  # noqa: BLE001 - 外部失败统一记录，不编造结论
        return False, "", f"{type(err).__name__}: {err}"
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode == 0, out, err


def shell_name() -> str:
    """记录实际执行人工命令的 shell，便于复现。"""
    bash = shutil.which("bash") or shutil.which("sh")
    return bash or "系统默认 shell"


def _evidence(name: str, out: str, err: str) -> str:
    """从命令输出里摘一行可核对的证据，摘不到就说明摘不到。"""
    text = out or err or ""
    lowered = text.lower()
    if name == "http_headers":
        for line in text.splitlines():
            if line.lower().startswith("server:"):
                return line.strip()
        return "未取到 Server 头"
    if name == "tls_cert":
        for line in text.splitlines():
            if "notafter" in line.lower():
                return line.strip()
        return "未取到 notAfter"
    if name == "dns_cname":
        lines = [ln.strip() for ln in text.splitlines() if "canonical name" in ln.lower()]
        if lines:
            return lines[0]
        return "CNAME 记录未解析到" if "can't find" in lowered or "找不到" in text else "解析结束"
    return text.strip().splitlines()[0][:80] if text.strip() else "无输出"


def run_skill_once(domain: str, *, warn_days: int = 30, port: int = 443, timeout: float = 8.0) -> dict:
    """Skill 侧一次调用：与 `probe_report.py --rounds 1` 同一条路径。"""
    t0 = time.perf_counter()
    result = run_round(domain, warn_days=warn_days, port=port, timeout=timeout)
    elapsed = (time.perf_counter() - t0) * 1000.0
    return {
        "total_ms": _ms(elapsed),
        "entry": result["entry"]["entry"],
        "cert_status": result["cert"].get("status"),
        "expires_in_days": result["cert"].get("expires_in_days"),
        "deliverable": "结论 + 证据 + 分位数 + 结果页面",
    }


def benchmark(
    domain: str,
    *,
    runs: int = 10,
    warn_days: int = 30,
    port: int = 443,
    timeout: float = 8.0,
    renewals_per_year: int = DEFAULT_RENEWALS_PER_YEAR,
    manual_runner=run_manual_once,
    skill_runner=run_skill_once,
) -> dict:
    """同一台机器上交替跑人工命令序列与 Skill 单命令各 `runs` 次，产出对照结构。"""
    if runs < 1:
        raise ValueError("runs 必须 >= 1")
    started = dt.datetime.now(dt.timezone.utc)
    manual_samples, skill_samples = [], []
    manual_last = None
    for _ in range(runs):
        m = manual_runner(domain, timeout=timeout)
        manual_last = m
        manual_samples.append(m["total_ms"])
        s = skill_runner(domain, warn_days=warn_days, port=port, timeout=timeout)
        skill_samples.append(s["total_ms"])
    finished = dt.datetime.now(dt.timezone.utc)

    model = modeled_range()
    manual_machine_p50_min = percentile(manual_samples, 50) / 60000.0
    skill_machine_p50_min = percentile(skill_samples, 50) / 60000.0

    # 单次总账：人工 = 机器段 + 人脑段；Skill = 机器段（成文已含在结果页里）
    single_manual = {
        "lo_min": round(manual_machine_p50_min + model["lo_min"], 2),
        "hi_min": round(manual_machine_p50_min + model["hi_min"], 2),
    }
    single_skill_min = round(skill_machine_p50_min, 3)

    annual_manual = {
        "lo_min": round(single_manual["lo_min"] * renewals_per_year, 1),
        "hi_min": round(single_manual["hi_min"] * renewals_per_year, 1),
    }
    annual_skill = {
        "manual_min": 0.0,
        "note": "定时巡检不占人工；人工只在收到 EXPIRING 后参与写操作授权",
    }

    return {
        "domain": domain,
        "operation": OPERATION,
        "warn_days": warn_days,
        "runs": runs,
        "window": {
            "started_at_utc": started.isoformat(timespec="seconds"),
            "finished_at_utc": finished.isoformat(timespec="seconds"),
            "elapsed_s": round((finished - started).total_seconds(), 2),
        },
        "manual": {
            "machine": summarize_latency(manual_samples),
            "modeled": model,
            "modeled_steps": list(HUMAN_MODELED),
            "last_run": manual_last,
            "shell": shell_name(),
        },
        "skill": {
            "machine": summarize_latency(skill_samples),
            "last_run": skill_runner(domain, warn_days=warn_days, port=port, timeout=timeout),
        },
        "single_account": {
            "manual_min": single_manual,
            "skill_min": single_skill_min,
            "note": "人工含发现/判定/成文；Skill 的成文由结果页自动渲染，故只计机器段",
        },
        "annual": {
            "renewals_per_year": renewals_per_year,
            "manual": annual_manual,
            "skill": annual_skill,
        },
        "scope_note": (
            "对照只覆盖「发现 + 诊断 + 成文」。申请、部署、回滚属写操作，"
            "两条路径都需要人工授权，本对照不宣称节省这部分工时。"
        ),
        "generated_at_utc": finished.isoformat(timespec="seconds"),
    }


def _fmt_min(v: float) -> str:
    return f"{v:.2f} 分钟"


def render_markdown(report: dict) -> str:
    """把对照结构渲染成 Markdown 对照页。"""
    m, s = report["manual"]["machine"], report["skill"]["machine"]
    model = report["manual"]["modeled"]
    sa = report["single_account"]
    lines = [
        f"# 效率对照｜人工基线 vs Skill 路径（{report['domain']}）",
        "",
        f"- 测量时间（UTC）：{report['window']['started_at_utc']} → {report['window']['finished_at_utc']}"
        f"（耗时 {report['window']['elapsed_s']}s）",
        f"- 样本量：每侧 {report['runs']} 次，交替执行",
        f"- 对照范围：{report['scope_note']}",
        "",
        "## 一、机器段（实测）",
        "",
        f"- 人工命令序列（{len(HUMAN_COMMANDS)} 条）：P50 {m['p50_ms']} ms，P95 {m['p95_ms']} ms，"
        f"min {m['min_ms']} ms，max {m['max_ms']} ms",
        f"- Skill 单命令（1 条）：P50 {s['p50_ms']} ms，P95 {s['p95_ms']} ms，"
        f"min {s['min_ms']} ms，max {s['max_ms']} ms",
        "",
        "人工侧逐条命令（最后一次执行）：",
        "",
    ]
    for item in report["manual"]["last_run"]["per_command"]:
        mark = "OK" if item["ok"] else "FAIL"
        lines.append(f"- [{mark}] `{item['cmd']}` → {item['evidence']}（{item['ms']} ms）")
    lines += [
        "",
        "## 二、人脑段（建模区间，非实测）",
        "",
        "| 环节 | 耗时区间 | 依据类型 |",
        "|---|---:|---|",
    ]
    for step in report["manual"]["modeled_steps"]:
        basis_kind = "依据" if step["basis"].startswith("依据") else "建模"
        lines.append(f"| {step['label']} | {step['lo_min']}–{step['hi_min']} 分钟 | {basis_kind} |")
    lines += [
        "",
        f"合计：{model['lo_min']}–{model['hi_min']} 分钟（中位 {model['mid_min']} 分钟）",
        "",
        "## 三、单次总账",
        "",
        f"- 人工：{sa['manual_min']['lo_min']}–{sa['manual_min']['hi_min']} 分钟",
        f"- Skill：{sa['skill_min']} 分钟（机器段；成文由结果页自动渲染）",
        "",
        f"## 四、按一年 {report['annual']['renewals_per_year']} 次换证折算",
        "",
        f"- 人工：{report['annual']['manual']['lo_min']}–{report['annual']['manual']['hi_min']} 分钟/年",
        f"- Skill：{report['annual']['skill']['manual_min']} 分钟人工巡检/年（{report['annual']['skill']['note']}）",
        "",
        "## 边界",
        "",
        "- 机器段为本机真实计时，同机可复现；不同网络环境下绝对值会变，结论是量级差。",
        "- 人脑段为建模区间，已逐条标注依据类型，读者应代入自己的实际耗时。",
        f"- {report['scope_note']}",
    ]
    return "\n".join(lines) + "\n"


def render_html(report: dict) -> str:
    """渲染自包含对照页面（内联样式，便于预览与复制）。"""
    m, s = report["manual"]["machine"], report["skill"]["machine"]
    model = report["manual"]["modeled"]
    sa, annual = report["single_account"], report["annual"]
    e = H.escape

    def n(v):
        return "—" if v is None else e(str(v))

    cmds = "".join(
        f'<li style="margin:7px 0;color:#37424f"><span style="display:inline-block;min-width:58px;'
        f'font-weight:600;color:{"#2f7d4f" if item["ok"] else "#b3422a"}">'
        f'{"OK" if item["ok"] else "FAIL"}</span>'
        f'<code style="background:#f2f5f8;padding:1px 5px;border-radius:4px;font-size:13px">'
        f'{e(item["cmd"])}</code><br><span style="color:#697787;font-size:13.5px">'
        f'证据：{e(item["evidence"])}　耗时 {item["ms"]} ms</span></li>'
        for item in report["manual"]["last_run"]["per_command"]
    )

    rows = ""
    for step in report["manual"]["modeled_steps"]:
        kind = "依据" if step["basis"].startswith("依据") else "建模"
        tone = "#8a6d1f" if kind == "建模" else "#2f7d4f"
        rows += (
            f'<tr><td style="padding:10px 12px;border-bottom:1px solid #e3e8ee;color:#1f2733">'
            f'<strong>{e(step["label"])}</strong><br>'
            f'<span style="color:#697787;font-size:13px">{e(step["note"])}</span></td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e3e8ee;text-align:right;'
            f'white-space:nowrap;color:#37424f;font-variant-numeric:tabular-nums">'
            f'{step["lo_min"]}–{step["hi_min"]} 分钟</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e3e8ee;text-align:center;'
            f'color:{tone};font-size:13.5px">{kind}</td></tr>'
        )

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>效率对照｜人工基线 vs Skill 路径</title></head>
<body style="margin:0;padding:24px;background:#f5f7f9;font:16px/1.8 -apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;color:#1f2733">
<article style="max-width:820px;margin:0 auto;background:#fff;border:1px solid #e3e8ee;border-radius:12px;padding:32px 34px">
<h1 style="margin:0 0 6px;font-size:24px">效率对照：人工基线 vs Skill 路径</h1>
<p style="margin:0 0 20px;color:#697787;font-size:14px">{e(report['domain'])}　·　每侧 {report['runs']} 次交替执行　·　窗口 {e(report['window']['started_at_utc'])} → {e(report['window']['finished_at_utc'])}</p>

<h2 style="margin:26px 0 12px;font-size:18px;border-left:4px solid #d65235;padding-left:11px">一、机器段（实测）</h2>
<table style="width:100%;border-collapse:collapse;font-size:14.5px">
<thead><tr>
<th style="text-align:left;padding:9px 12px;border-bottom:2px solid #cdd7e0">路径</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0">min</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0">P50</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0">P95</th>
<th style="text-align:right;padding:9px 12px;border-bottom:2px solid #cdd7e0">max</th>
</tr></thead><tbody>
<tr><td style="padding:10px 12px;border-bottom:1px solid #e3e8ee">人工命令序列（{len(HUMAN_COMMANDS)} 条）</td>
{''.join(f'<td style="padding:10px 12px;border-bottom:1px solid #e3e8ee;text-align:right;font-variant-numeric:tabular-nums">{n(m[k])}</td>' for k in ('min_ms','p50_ms','p95_ms','max_ms'))}</tr>
<tr><td style="padding:10px 12px;border-bottom:1px solid #e3e8ee">Skill 单命令（1 条）</td>
{''.join(f'<td style="padding:10px 12px;border-bottom:1px solid #e3e8ee;text-align:right;font-variant-numeric:tabular-nums">{n(s[k])}</td>' for k in ('min_ms','p50_ms','p95_ms','max_ms'))}</tr>
</tbody></table>
<p style="margin:12px 0 6px;color:#697787;font-size:13.5px">单位毫秒；最近秩法，不做插值。人工侧逐条命令（最后一次执行）：</p>
<ul style="margin:0;padding-left:20px;font-size:14px">{cmds}</ul>

<h2 style="margin:26px 0 12px;font-size:18px;border-left:4px solid #d65235;padding-left:11px">二、人脑段（建模区间，非实测）</h2>
<table style="width:100%;border-collapse:collapse;font-size:14.5px">{rows}</table>
<p style="margin:12px 0 0;color:#4a5766;font-size:14px">合计 <strong>{model['lo_min']}–{model['hi_min']} 分钟</strong>（中位 {model['mid_min']} 分钟）。标注为「建模」的行，本脚本测不了，读者应代入自身耗时。</p>

<h2 style="margin:26px 0 12px;font-size:18px;border-left:4px solid #d65235;padding-left:11px">三、单次总账与年度折算</h2>
<div style="display:flex;gap:14px;flex-wrap:wrap">
<div style="flex:1;min-width:240px;background:#fdf3f0;border:1px solid #f0d5cc;border-radius:9px;padding:16px 18px">
<p style="margin:0 0 6px;font-weight:600;color:#a8402a">人工路径</p>
<p style="margin:0 0 4px">单次：{sa['manual_min']['lo_min']}–{sa['manual_min']['hi_min']} 分钟</p>
<p style="margin:0;color:#4a5766;font-size:14px">一年 {annual['renewals_per_year']} 次：{annual['manual']['lo_min']}–{annual['manual']['hi_min']} 分钟</p>
</div>
<div style="flex:1;min-width:240px;background:#f0f7f2;border:1px solid #cfe4d6;border-radius:9px;padding:16px 18px">
<p style="margin:0 0 6px;font-weight:600;color:#2f7d4f">Skill 路径</p>
<p style="margin:0 0 4px">单次：{sa['skill_min']} 分钟（机器段）</p>
<p style="margin:0;color:#4a5766;font-size:14px">一年：{annual['skill']['manual_min']} 分钟人工巡检</p>
</div>
</div>

<h2 style="margin:26px 0 12px;font-size:18px;border-left:4px solid #d65235;padding-left:11px">边界</h2>
<p style="margin:0;color:#4a5766;font-size:14px">机器段为本机真实计时，同机可复现；跨网络绝对值会变，结论是量级差而非精确倍数。人脑段为建模区间。{e(report['scope_note'])}</p>
</article>
</body></html>
"""


def write_report(report: dict, out_dir: str) -> dict:
    """写入对照报告，返回产物路径。"""
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "html": os.path.join(out_dir, "baseline-report.html"),
        "markdown": os.path.join(out_dir, "baseline-report.md"),
        "json": os.path.join(out_dir, "baseline-report.json"),
    }
    with open(paths["html"], "w", encoding="utf-8") as fh:
        fh.write(render_html(report))
    with open(paths["markdown"], "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))
    with open(paths["json"], "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--runs", type=int, default=10, help="每侧重复次数，默认 10")
    parser.add_argument("--warn-days", type=int, default=30)
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--renewals-per-year", type=int, default=DEFAULT_RENEWALS_PER_YEAR)
    parser.add_argument("--out-dir", default="report", help="对照报告输出目录")
    parser.add_argument("--json", action="store_true", help="仅打印 JSON，不写文件")
    args = parser.parse_args(argv)

    try:
        report = benchmark(
            args.domain,
            runs=args.runs,
            warn_days=args.warn_days,
            port=args.port,
            timeout=args.timeout,
            renewals_per_year=args.renewals_per_year,
        )
    except ValueError as err:
        print(json.dumps({"domain": args.domain, "status": "ERROR", "error": str(err)}, ensure_ascii=False))
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    paths = write_report(report, args.out_dir)
    print(
        json.dumps(
            {
                "domain": report["domain"],
                "runs": report["runs"],
                "manual_machine_p50_ms": report["manual"]["machine"]["p50_ms"],
                "skill_machine_p50_ms": report["skill"]["machine"]["p50_ms"],
                "manual_modeled_min": report["manual"]["modeled"],
                "single_manual_min": report["single_account"]["manual_min"],
                "single_skill_min": report["single_account"]["skill_min"],
                "annual_manual_min": report["annual"]["manual"],
                "report": paths,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
