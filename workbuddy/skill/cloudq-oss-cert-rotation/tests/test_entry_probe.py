#!/usr/bin/env python3
"""entry_probe 离线回归：判定规则全部用假数据驱动，不访问真实网络。"""
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from entry_probe import classify_entry, check_entry  # noqa: E402


class TestClassifyEntry(unittest.TestCase):
    def test_oss_direct_by_server_header(self):
        entry, _ = classify_entry(server_header="AliyunOSS", headers={"x-oss-request-id": "abc"})
        self.assertEqual(entry, "OSS_DIRECT")

    def test_behind_cdn_by_cache_header(self):
        entry, evidence = classify_entry(server_header="Tengine", headers={"x-cache": "HIT"})
        self.assertEqual(entry, "BEHIND_CDN")
        self.assertIn("x-cache", evidence)

    def test_non_oss_cname_must_not_decide(self):
        """CNAME 名不含 oss-cn-* 时，不得据此否定 OSS 直连——回包才是强证据。"""
        entry, _ = classify_entry(
            server_header="AliyunOSS",
            headers={},
            cname_chain=["publichtml.cn-shenzhen.taihangpfm.cn"],
        )
        self.assertEqual(entry, "OSS_DIRECT")

    def test_unknown_when_nothing_recognizable(self):
        entry, evidence = classify_entry(
            server_header="nginx", headers={"content-type": "text/html"}, cname_chain=["foo.example.net"]
        )
        self.assertEqual(entry, "UNKNOWN")
        self.assertIn("未确定", evidence)

    def test_cdn_cname_hint_only_when_headers_inconclusive(self):
        weak, _ = classify_entry(server_header="", headers={}, cname_chain=["k1.wscloudcdn.com"])
        self.assertEqual(weak, "BEHIND_CDN")
        strong, _ = classify_entry(server_header="AliyunOSS", headers={}, cname_chain=["k1.wscloudcdn.com"])
        self.assertEqual(strong, "OSS_DIRECT")


class TestCheckEntry(unittest.TestCase):
    def test_external_failures_are_recorded_not_fabricated(self):
        def boom(*_args, **_kwargs):
            raise TimeoutError("offline test")

        result = check_entry("example.com", http_probe=boom, dns_probe=boom)
        self.assertEqual(result["entry"], "UNKNOWN")
        self.assertEqual(result["http_status"], None)
        self.assertEqual([e["step"] for e in result["errors"]], ["dns_cname", "https_get"])
        self.assertEqual({e["error_type"] for e in result["errors"]}, {"TimeoutError"})

    def test_happy_path_reports_oss_direct(self):
        result = check_entry(
            "public.example.com",
            http_probe=lambda *_a, **_k: (403, {"Server": "AliyunOSS", "x-oss-request-id": "rid"}),
            dns_probe=lambda *_a, **_k: ["publichtml.cn-shenzhen.taihangpfm.cn"],
        )
        self.assertEqual(result["entry"], "OSS_DIRECT")
        self.assertEqual(result["server_header"], "AliyunOSS")
        self.assertEqual(result["http_status"], 403)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["cname_chain"], ["publichtml.cn-shenzhen.taihangpfm.cn"])


if __name__ == "__main__":
    unittest.main()
