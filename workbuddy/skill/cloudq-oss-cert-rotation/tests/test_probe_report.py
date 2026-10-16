#!/usr/bin/env python3
"""probe_report 离线回归：分位数、汇总、渲染全部用假数据驱动，不访问真实网络。"""
from __future__ import annotations

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from probe_report import (  # noqa: E402
    EXTERNAL_CALLS_PER_ROUND,
    inspect,
    percentile,
    render_html,
    render_markdown,
    summarize_latency,
)


def fake_report():
    """一份不含真实网络调用的结果结构。"""
    def runner(domain, **_kw):
        return {
            "entry": {"entry": "OSS_DIRECT", "evidence": "Server: AliyunOSS", "cname_chain": [], "http_status": 403, "server_header": "AliyunOSS"},
            "entry_errors": [],
            "cert": {"domain": domain, "status": "HEALTHY", "expires_in_days": 87, "not_after_utc": "2027-01-09T23:59:59+00:00", "warn_days": 30},
            "ms": {"entry": 120.0, "cert": 90.0, "total": 210.0},
        }

    return inspect("public.example.com", rounds=5, warn_days=30, runner=runner)


class TestPercentile(unittest.TestCase):
    def test_nearest_rank_no_interpolation(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertEqual(percentile(values, 50), 30.0)
        self.assertEqual(percentile(values, 95), 50.0)
        self.assertEqual(percentile(values, 100), 50.0)

    def test_ten_samples(self):
        values = [float(i) for i in range(1, 11)]
        self.assertEqual(percentile(values, 50), 5.0)
        self.assertEqual(percentile(values, 95), 10.0)

    def test_empty_and_bad_p(self):
        self.assertNotEqual(percentile([], 50), percentile([], 50))  # NaN 不等于自身
        with self.assertRaises(ValueError):
            percentile([1.0], 0)


class TestSummarize(unittest.TestCase):
    def test_empty_is_none_not_zero(self):
        got = summarize_latency([])
        self.assertEqual(got["rounds"], 0)
        self.assertIsNone(got["p95_ms"])

    def test_fields_present(self):
        got = summarize_latency([100.0, 200.0, 300.0])
        self.assertEqual(got["rounds"], 3)
        self.assertEqual(got["min_ms"], 100.0)
        self.assertEqual(got["max_ms"], 300.0)
        self.assertEqual(got["p50_ms"], 200.0)


class TestInspect(unittest.TestCase):
    def test_sample_size_and_call_count(self):
        report = fake_report()
        self.assertEqual(report["rounds"], 5)
        self.assertEqual(report["external_calls"]["per_round"], EXTERNAL_CALLS_PER_ROUND)
        self.assertEqual(report["external_calls"]["total"], EXTERNAL_CALLS_PER_ROUND * 5)
        self.assertEqual(report["failed_rounds"], 0)
        self.assertEqual(report["latency"]["total"]["p50_ms"], 210.0)

    def test_unknown_entry_counts_as_failed_round(self):
        def runner(domain, **_kw):
            return {
                "entry": {"entry": "UNKNOWN", "evidence": "未确定", "cname_chain": [], "http_status": None, "server_header": ""},
                "entry_errors": [{"step": "dns_cname", "error_type": "TimeoutError", "error": "offline"}],
                "cert": {"domain": domain, "status": "HEALTHY", "expires_in_days": 10},
                "ms": {"entry": 5.0, "cert": 5.0, "total": 10.0},
            }

        report = inspect("x.example.com", rounds=4, runner=runner)
        self.assertEqual(report["failed_rounds"], 4)
        self.assertEqual(report["failure_rate"], 1.0)

    def test_rounds_must_be_positive(self):
        with self.assertRaises(ValueError):
            inspect("x.example.com", rounds=0, runner=lambda *_a, **_k: {})


class TestRender(unittest.TestCase):
    def test_markdown_has_window_and_quantiles(self):
        md = render_markdown(fake_report())
        self.assertIn("巡检结果页", md)
        self.assertIn("P50", md)
        self.assertIn("P95", md)
        self.assertIn("OSS_DIRECT", md)
        self.assertIn("HEALTHY", md)

    def test_html_is_self_contained_and_escaped(self):
        report = fake_report()
        report["domain"] = "a<script>.example.com"
        html = render_html(report)
        self.assertIn("<!doctype html", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        # 不得引用外部样式/脚本
        self.assertIsNone(re.search(r'(src|href)="https?://', html))

    def test_html_marks_missing_values(self):
        def runner(domain, **_kw):
            return {
                "entry": {"entry": "OSS_DIRECT", "evidence": "ok", "cname_chain": [], "http_status": 200, "server_header": "AliyunOSS"},
                "entry_errors": [],
                "cert": {"domain": domain, "status": "UNVERIFIED", "expires_in_days": None},
                "ms": {"entry": 1.0, "cert": 1.0, "total": 2.0},
            }

        html = render_html(inspect("x.example.com", rounds=2, runner=runner))
        self.assertIn("—", html)
        self.assertIn("UNVERIFIED", html)


if __name__ == "__main__":
    unittest.main()
