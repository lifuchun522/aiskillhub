"""cert_probe.py 离线回归测试。全部用假连接，不访问真实网络。"""
from __future__ import annotations

import datetime as dt
import socket
import ssl
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cert_probe import check_cert  # noqa: E402

NOW = dt.datetime(2026, 10, 14, 12, 0, 0, tzinfo=dt.timezone.utc)


def _cert(not_after: str, cn: str = "public.joysky.cloud") -> dict:
    return {"notAfter": not_after, "subject": ((("commonName", cn),),)}


class _FakeSock:
    def __init__(self, cert):
        self._cert = cert

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def getpeercert(self):
        return self._cert


def _ok(cert):
    return lambda domain, port, timeout: _FakeSock(cert)


def _boom(exc):
    def _connect(domain, port, timeout):
        raise exc

    return _connect


class CertProbeTest(unittest.TestCase):
    def test_healthy_when_far_from_expiry(self):
        r = check_cert("a.com", 30, now=NOW, connect=_ok(_cert("Jan 10 00:00:00 2027 GMT")))
        self.assertEqual("HEALTHY", r["status"])
        self.assertTrue(r["hostname_and_chain_verified"])
        self.assertGreaterEqual(r["expires_in_days"], 30)

    def test_expiring_within_threshold(self):
        r = check_cert("a.com", 30, now=NOW, connect=_ok(_cert("Oct 30 00:00:00 2026 GMT")))
        self.assertEqual("EXPIRING", r["status"])

    def test_expired_is_unverified_not_healthy(self):
        r = check_cert("a.com", 30, now=NOW, connect=_ok(_cert("Oct 01 00:00:00 2026 GMT")))
        self.assertEqual("UNVERIFIED", r["status"])
        self.assertEqual("Expired", r["error_type"])

    def test_timeout_reports_unverified_with_type(self):
        r = check_cert("example.com", 30, now=NOW, connect=_boom(TimeoutError("offline test")))
        self.assertEqual("UNVERIFIED", r["status"])
        self.assertEqual("TimeoutError", r["error_type"])
        self.assertFalse(r["hostname_and_chain_verified"])
        self.assertEqual("READ_ONLY_TLS_HANDSHAKE", r["operation"])

    def test_hostname_mismatch_keeps_verification_error(self):
        err = ssl.SSLCertVerificationError(1, "hostname mismatch")
        err.verify_message = "Hostname mismatch, certificate is not valid for 'a.com'"
        r = check_cert("a.com", 30, now=NOW, connect=_boom(err))
        self.assertEqual("UNVERIFIED", r["status"])
        self.assertEqual("SSLCertVerificationError", r["error_type"])

    def test_dns_failure_is_unverified(self):
        r = check_cert("nope.invalid", 30, now=NOW, connect=_boom(socket.gaierror("not known")))
        self.assertEqual("UNVERIFIED", r["status"])
        self.assertEqual("gaierror", r["error_type"])

    def test_zero_warn_days_never_expiring(self):
        r = check_cert("a.com", 0, now=NOW, connect=_ok(_cert("Oct 20 00:00:00 2026 GMT")))
        self.assertEqual("HEALTHY", r["status"])

    def test_never_claims_expired_before_parsing(self):
        r = check_cert("a.com", 30, now=NOW, connect=_boom(ssl.SSLError("handshake failure")))
        self.assertNotIn("已过期", str(r))
        self.assertEqual("UNVERIFIED", r["status"])


if __name__ == "__main__":
    unittest.main()
