"""cert_rotate.py 离线回归测试。全部用假 CAS / OSS 客户端，不访问真实云 API、不读 AK。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from cert_rotate import (  # noqa: E402
    RotationError, build_operation_order, inspect_quota, get_validation,
    download_cert, deploy_to_oss, poll_until_issued, rotate,
)

CFG = {
    "domain": "www.example.com",
    "oss_bucket": "my-bucket",
    "region": "cn-hangzhou",
    "oss_endpoint": "https://oss-cn-hangzhou.aliyuncs.com",
    "validate_type": "DNS",
    "wait_seconds": 0,
    "max_poll": 10,
}


class _Attr:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeCas:
    """可编排的假 CAS 客户端：配额、申请、状态轮询均可注入。

    状态回包字段对齐真实 DescribeCertificateState 响应体：
      含 certificate+private_key -> 已签发；含 record_value -> 待验证。
    """

    def __init__(self, *, quota_remain=5, order_id="ORD-1",
                 state_sequence=None):
        self._runtime = None
        self.quota_remain = quota_remain
        self.order_id = order_id
        self.state_sequence = state_sequence or [
            {"RecordDomain": "_dnsauth.www", "RecordValue": "abc123", "CertId": "C1"},
            {"Certificate": "CERT-PEM", "PrivateKey": "KEY-PEM", "CertId": "C1"},
        ]
        self._idx = 0

    def describe_package_state_with_options(self, req, runtime):
        return {"TotalCount": 20, "IssuedCount": 20 - self.quota_remain}

    def create_certificate_for_package_request_with_options(self, req, runtime):
        return {"OrderId": self.order_id}

    def describe_certificate_state_with_options(self, req, runtime):
        st = dict(self.state_sequence[min(self._idx, len(self.state_sequence) - 1)])
        self._idx += 1
        return st


class FakeOss:
    def __init__(self):
        self._runtime = None
        self.deployed = []
        self._cname = []

    def set_cname(self, domains):
        self._cname = [_Attr(domain=d, status="ENABLED",
                            certificate=_Attr(status="Succeeded", cert_id="cid-" + d))
                       for d in domains]

    def list_bucket_cname(self):
        return _Attr(cname=self._cname)

    def put_bucket_cname(self, req):
        self.deployed.append(req)


class PlanTest(unittest.TestCase):
    def test_plan_offline_needs_no_ak(self):
        order = build_operation_order(CFG)
        self.assertEqual("rotate_oss_custom_domain_cert", order["action"])
        self.assertEqual(6, len(order["steps"]))
        self.assertTrue(order["authorization_required"])
        self.assertIn("免费额度 > 0", order["preconditions"])

    def test_plan_lists_all_risks(self):
        order = build_operation_order(CFG)
        ops = [s["op"] for s in order["steps"]]
        self.assertIn("apply_free_cert", ops)
        self.assertIn("deploy_oss", ops)
        risks = {s["op"]: s["risk"] for s in order["steps"]}
        self.assertNotEqual("none", risks["apply_free_cert"])
        self.assertNotEqual("none", risks["deploy_oss"])


class GateTest(unittest.TestCase):
    def test_rotate_refuses_without_authorized(self):
        with self.assertRaises(RotationError):
            rotate(CFG, "ak", "sk", False, cas_client=FakeCas(), oss_bucket=FakeOss())

    def test_rotate_refuses_without_ak(self):
        with self.assertRaises(RotationError):
            rotate(CFG, None, None, True, cas_client=FakeCas(), oss_bucket=FakeOss())

    def test_rotate_refuses_when_quota_exhausted(self):
        with self.assertRaises(RotationError):
            rotate(CFG, "ak", "sk", True, cas_client=FakeCas(quota_remain=0),
                   oss_bucket=FakeOss(), confirm_dns=False, sleep=lambda x: None)


class FlowTest(unittest.TestCase):
    def test_full_rotate_flow(self):
        cas = FakeCas()
        oss = FakeOss()
        result = rotate(CFG, "ak", "sk", True, cas_client=cas, oss_bucket=oss,
                        confirm_dns=False, sleep=lambda x: None)
        self.assertEqual("deployed", result["status"])
        self.assertEqual("ORD-1", result["order_id"])
        self.assertEqual(1, len(oss.deployed))  # 只部署一次

    def test_download_requires_cert_and_key(self):
        # 已签发但回包未含证书内容：应明确报错，而非返回空/假证书
        cas = FakeCas(state_sequence=[{"CertId": "C1"}])
        with self.assertRaises(RotationError):
            download_cert(cas, "ORD-1")

    def test_dns_record_parsed(self):
        cas = FakeCas(state_sequence=[
            {"RecordDomain": "_dnsauth.www", "RecordValue": "TXTVAL", "CertId": "C1"},
            {"Certificate": "C", "PrivateKey": "K", "CertId": "C1"},
        ])
        st = get_validation(cas, "ORD-1")
        self.assertTrue(st["need_validation"])
        self.assertEqual("TXT", st["record_type"])
        self.assertEqual("TXTVAL", st["record_value"])
        self.assertEqual("_dnsauth.www", st["record_domain"])

    def test_poll_times_out(self):
        cas = FakeCas(state_sequence=[
            {"RecordValue": "R", "CertId": "C1"} for _ in range(5)])
        with self.assertRaises(RotationError):
            poll_until_issued(cas, "ORD-1", max_poll=3, sleep=lambda x: None)

    def test_inspect_quota_parsing(self):
        cas = FakeCas(quota_remain=7)
        q = inspect_quota(cas)
        self.assertEqual(20, q["total"])
        self.assertEqual(13, q["used"])
        self.assertEqual(7, q["remain"])

    def test_deploy_to_oss_called_with_domain(self):
        oss = FakeOss()
        deploy_to_oss(oss, "www.example.com", "CERT", "KEY")
        self.assertEqual(1, len(oss.deployed))


if __name__ == "__main__":
    unittest.main()
