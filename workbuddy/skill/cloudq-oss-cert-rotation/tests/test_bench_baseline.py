#!/usr/bin/env python3
"""bench_baseline 离线回归：机器段用假 runner 驱动，人脑段只校验建模口径，不访问真实网络。"""
from __future__ import annotations

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from bench_baseline import (  # noqa: E402
    HUMAN_COMMANDS,
    HUMAN_MODELED,
    _evidence,
    benchmark,
    modeled_range,
    render_html,
    render_markdown,
    run_manual_once,
)


def fake_manual(domain, *, timeout=8.0):
    """假的人工命令序列：三段固定耗时。"""
    return {
        "per_command": [
            {"name": "dns_cname", "cmd": "nslookup -type=CNAME " + domain, "desc": "d",
             "ok": True, "ms": 300.0, "evidence": "canonical name = x"},
            {"name": "http_headers", "cmd": "curl -sSI https://" + domain + "/", "desc": "d",
             "ok": True, "ms": 400.0, "evidence": "Server: AliyunOSS"},
            {"name": "tls_cert", "cmd": "openssl s_client ...", "desc": "d",
             "ok": True, "ms": 500.0, "evidence": "notAfter=Jan  9 23:59:59 2027 GMT"},
        ],
        "total_ms": 1200.0,
    }


def fake_skill(domain, *, warn_days=30, port=443, timeout=8.0):
    return {
        "total_ms": 1500.0,
        "entry": "OSS_DIRECT",
        "cert_status": "HEALTHY",
        "expires_in_days": 87,
        "deliverable": "结论 + 证据 + 分位数 + 结果页面",
    }


def fake_bench(runs=5):
    return benchmark("public.example.com", runs=runs, manual_runner=fake_manual, skill_runner=fake_skill)


class TestModeledRange(unittest.TestCase):
    def test_sum_matches_steps(self):
        got = modeled_range()
        self.assertEqual(got["lo_min"], sum(s["lo_min"] for s in HUMAN_MODELED))
        self.assertEqual(got["hi_min"], sum(s["hi_min"] for s in HUMAN_MODELED))
        self.assertLess(got["lo_min"], got["hi_min"])

    def test_every_step_declares_basis_kind(self):
        for step in HUMAN_MODELED:
            self.assertTrue(
                step["basis"].startswith("依据") or step["basis"].startswith("建模"),
                step["name"],
            )


class TestManualRun(unittest.TestCase):
    def test_injected_shell_runner_is_used(self):
        calls = []

        def runner(cmd, timeout):
            calls.append(cmd)
            return True, "notAfter=Jan 9 2027 GMT\n", ""

        got = run_manual_once("public.example.com", shell_runner=runner)
        self.assertEqual(len(calls), len(HUMAN_COMMANDS))
        self.assertEqual(len(got["per_command"]), len(HUMAN_COMMANDS))
        self.assertGreaterEqual(got["total_ms"], 0.0)
        # 域名被真实注入到命令里
        self.assertIn("public.example.com", calls[0])

    def test_evidence_extraction(self):
        self.assertEqual(_evidence("http_headers", "HTTP/1.1 403\nServer: AliyunOSS\n", ""), "Server: AliyunOSS")
        self.assertEqual(_evidence("tls_cert", "notAfter=Jan  9 23:59:59 2027 GMT", ""), "notAfter=Jan  9 23:59:59 2027 GMT")
        self.assertIn("未取到", _evidence("tls_cert", "some other text", ""))


class TestBenchmark(unittest.TestCase):
    def test_machine_summaries_and_account(self):
        report = fake_bench(runs=5)
        self.assertEqual(report["manual"]["machine"]["rounds"], 5)
        self.assertEqual(report["manual"]["machine"]["p50_ms"], 1200.0)
        self.assertEqual(report["skill"]["machine"]["p50_ms"], 1500.0)
        # Skill 单次 = 机器段；人工单次 = 机器段 + 人脑段
        self.assertAlmostEqual(report["single_account"]["skill_min"], 1500.0 / 60000.0, places=3)
        self.assertGreater(report["single_account"]["manual_min"]["lo_min"], report["single_account"]["skill_min"])

    def test_annual_projection(self):
        report = fake_bench(runs=3)
        n = report["annual"]["renewals_per_year"]
        self.assertEqual(n, 4)
        self.assertAlmostEqual(
            report["annual"]["manual"]["lo_min"],
            round(report["single_account"]["manual_min"]["lo_min"] * n, 1),
            places=1,
        )
        self.assertEqual(report["annual"]["skill"]["manual_min"], 0.0)

    def test_scope_note_excludes_write_ops(self):
        report = fake_bench(runs=2)
        self.assertIn("写操作", report["scope_note"])

    def test_runs_must_be_positive(self):
        with self.assertRaises(ValueError):
            benchmark("x.example.com", runs=0, manual_runner=fake_manual, skill_runner=fake_skill)


class TestRender(unittest.TestCase):
    def test_markdown_labels_measured_and_modeled(self):
        md = render_markdown(fake_bench(runs=3))
        self.assertIn("机器段（实测）", md)
        self.assertIn("人脑段（建模区间，非实测）", md)
        self.assertIn("效率对照", md)
        self.assertIn("边界", md)

    def test_html_self_contained_and_escaped(self):
        report = fake_bench(runs=3)
        report["domain"] = "a<script>.example.com"
        html = render_html(report)
        self.assertIn("<!doctype html", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIsNone(re.search(r'(src|href)="https?://', html))


if __name__ == "__main__":
    unittest.main()
