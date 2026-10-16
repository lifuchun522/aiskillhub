#!/usr/bin/env python3
"""OSS 自定义域名证书轮换：重新申请免费证并部署到 OSS。

本模块是 cloudq-oss-cert-rotation 的「写操作半截」，与只读探测层（entry_probe /
cert_probe / probe_report）共用同一套铁律：

  - 任何写操作（申请 / 部署 / 改 DNS）必须显式传 --authorized 才执行；
  - AK/SK 仅从环境变量读取，绝不硬编码、绝不写盘；
  - 未授权时只产出「更新操作单」(plan)，不触碰任何云资源；
  - 依赖第三方 SDK（alibabacloud_cas20200407 / oss2）仅在真正执行时才 import，
    因此本模块可被离线单测（注入假客户端）完整覆盖。

子命令：
  plan     离线生成更新操作单（无需 AK），列出 6 步与风险
  inspect  只读查询：免费额度 / 证书列表 / OSS CNAME 证书状态（需 AK，仍不写）
  rotate   真正执行：申请免费证 -> DNS 验证 -> 轮询签发 -> 下载 -> 部署 OSS（需 --authorized + AK）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Callable

PRODUCT_FREE = "digicert-free-1-free"


class RotationError(Exception):
    """任何授权缺失、配额不足、签发失败等可预期错误。"""


# --------------------------------------------------------------------------- #
# 云客户端构建（仅在执行写操作时、且已确认有 AK 才调用；函数内懒加载 SDK）
# --------------------------------------------------------------------------- #
def build_cas_client(cfg: dict, ak: str, sk: str):
    from alibabacloud_cas20200407.client import Client as CasClient
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models

    config = open_api_models.Config()
    config.access_key_id = ak
    config.access_key_secret = sk
    config.endpoint = "cas.aliyuncs.com"
    if cfg.get("region"):
        config.region_id = cfg["region"]
    client = CasClient(config)
    client._runtime = util_models.RuntimeOptions()
    return client


def build_oss_bucket(cfg: dict, ak: str, sk: str):
    import oss2

    # 若地域要求 V4 签名，改为 oss2.AuthV4(ak, sk)
    auth = oss2.Auth(ak, sk)
    return oss2.Bucket(auth, cfg["oss_endpoint"], cfg["oss_bucket"], region=cfg.get("region"))


def _resp_to_dict(resp: Any) -> dict:
    """把 tea 响应对象或已 dict 统一成 dict，方便取值与测试注入。

    tea SDK 的 client 方法返回响应对象，实际字段包在 `.body` 下；
    同时兼容测试里直接返回纯 dict 的假客户端。
    """
    if not hasattr(resp, "to_map"):
        return resp if isinstance(resp, dict) else {}
    m = resp.to_map()
    if isinstance(m, dict) and isinstance(m.get("body"), dict):
        return m["body"]
    return m


def _cas(client, method: str, request) -> dict:
    """统一调用 CAS 的 with_options 方法并取回 dict。"""
    return _resp_to_dict(getattr(client, method)(request, client._runtime))


# --------------------------------------------------------------------------- #
# 纯逻辑函数（全部可注入 client，便于离线单测，不触网）
# --------------------------------------------------------------------------- #
def inspect_quota(cas_client, product_code: str = PRODUCT_FREE) -> dict:
    """只读：查询免费证书资源包使用概况。返回 {total, used, remain}。"""
    from alibabacloud_cas20200407 import models as cas_models

    req = cas_models.DescribePackageStateRequest(product_code=product_code)
    d = _cas(cas_client, "describe_package_state_with_options", req)
    total = d.get("TotalCount") or d.get("totalCount")
    used = d.get("IssuedCount") or d.get("issuedCount") or d.get("UsedCount") or d.get("usedCount")
    out = {"product_code": product_code, "raw": d}
    if total is not None:
        used = used or 0
        out.update(total=int(total), used=int(used), remain=int(total) - int(used))
    return out


def apply_free_cert(cas_client, domain: str, validate_type: str = "DNS",
                   product_code: str = PRODUCT_FREE) -> str:
    """提交免费证书申请，返回 OrderId。会消耗一张免费额度。"""
    from alibabacloud_cas20200407 import models as cas_models

    req = cas_models.CreateCertificateForPackageRequestRequest(
        product_code=product_code, domain=domain, validate_type=validate_type)
    d = _cas(cas_client, "create_certificate_for_package_request_with_options", req)
    order_id = d.get("OrderId") or d.get("orderId")
    if not order_id:
        raise RotationError("申请免费证书未返回 OrderId: %s" % json.dumps(d, ensure_ascii=False))
    return str(order_id)


def get_validation(cas_client, order_id: str) -> dict:
    """查询申请订单状态。

    CAS 的 DescribeCertificateState 响应体里没有显式 State 字段，需用返回内容推断：
      - 含 certificate + private_key  -> 已签发(issued)
      - 含 record_value               -> 待域名验证(domainVerifyCritical)
      - 其它                          -> 处理中(processing)
    同时解析 DNS TXT 验证记录与证书内容（签发后直接带私钥，便于部署）。
    """
    from alibabacloud_cas20200407 import models as cas_models

    req = cas_models.DescribeCertificateStateRequest(order_id=order_id)
    d = _cas(cas_client, "describe_certificate_state_with_options", req)
    record_value = d.get("RecordValue") or d.get("record_value")
    record_domain = d.get("RecordDomain") or d.get("record_domain")
    cert = d.get("Certificate") or d.get("certificate")
    key = d.get("PrivateKey") or d.get("private_key")
    if cert and key:
        state = "issued"
    elif record_value:
        state = "domainVerifyCritical"
    else:
        state = "processing"
    return {
        "order_id": order_id,
        "state": state,
        "need_validation": bool(record_value) and not (cert and key),
        "record_type": d.get("RecordType") or "TXT",
        "record_domain": record_domain,
        "record_value": record_value,
        "cert_id": d.get("CertId") or d.get("cert_id"),
        "certificate": cert,
        "private_key": key,
    }


def poll_until_issued(cas_client, order_id: str, wait_seconds: int = 30,
                      max_poll: int = 40, sleep: Callable[[float], None] = time.sleep) -> dict:
    """轮询订单状态直到 issued；超时抛 RotationError。"""
    last = None
    for i in range(max_poll):
        st = get_validation(cas_client, order_id)
        last = st
        if st["state"] == "issued":
            return st
        if i < max_poll - 1:
            sleep(wait_seconds)
    raise RotationError("轮询 %d 次仍未签发，最后状态: %s" % (max_poll, json.dumps(last, ensure_ascii=False)))


def download_cert(cas_client, order_id: str, state: dict | None = None) -> tuple[str, str]:
    """拿到证书 PEM 与私钥。CAS 在 DescribeCertificateState 签发后直接返回证书与私钥，
    因此优先用状态回包；若没有则重新查询一次。"""
    st = state or get_validation(cas_client, order_id)
    cert = st.get("certificate")
    key = st.get("private_key")
    if cert and key:
        return cert, key
    # 兜底：再查一次（某些账号首次轮询时证书字段延迟出现）
    st = get_validation(cas_client, order_id)
    cert = st.get("certificate")
    key = st.get("private_key")
    if cert and key:
        return cert, key
    raise RotationError(
        "未能从 API 取得证书内容（签发回包未含 certificate/private_key），"
        "请到控制台手动下载 cert.pem/key.pem 后再执行部署")


def deploy_to_oss(oss_bucket, domain: str, cert_pem: str, key_pem: str) -> None:
    """把证书部署（覆盖）到 OSS 自定义域名。"""
    import oss2

    cert_info = oss2.models.CertInfo(certificate=cert_pem, private_key=key_pem,
                                     force=True, delete_certificate=False)
    req = oss2.models.PutBucketCnameRequest(domain, cert_info)
    oss_bucket.put_bucket_cname(req)


def build_operation_order(cfg: dict) -> dict:
    """离线生成更新操作单，无需 AK。"""
    return {
        "action": "rotate_oss_custom_domain_cert",
        "summary": "重新申请阿里云免费个人测试证书并部署到 OSS 自定义域名 HTTPS",
        "target": {
            "domain": cfg.get("domain"),
            "oss_bucket": cfg.get("oss_bucket"),
            "region": cfg.get("region"),
        },
        "steps": [
            {"step": 1, "op": "check_free_quota", "risk": "none",
             "desc": "查询免费额度是否充足（每年20张单域名）"},
            {"step": 2, "op": "apply_free_cert", "risk": "consumes 1 of 20 yearly free quota",
             "desc": "提交免费证申请（有效期3个月）"},
            {"step": 3, "op": "dns_validate", "risk": "adds TXT record to domain DNS",
             "desc": "完成域名所有权验证（默认手动加TXT；--auto-dns 可自动加）"},
            {"step": 4, "op": "poll_status", "risk": "none", "desc": "轮询至证书签发"},
            {"step": 5, "op": "download_cert", "risk": "in-memory only, not written to disk by default",
             "desc": "下载证书与私钥（默认仅内存，不落盘）"},
            {"step": 6, "op": "deploy_oss", "risk": "overwrites existing OSS cname cert",
             "desc": "部署到 OSS 自定义域名，覆盖旧证书"},
        ],
        "authorization_required": True,
        "preconditions": [
            "免费额度 > 0",
            "域名 DNS 可添加 TXT 记录（或开启 --auto-dns 且该域名 DNS 在同账号）",
            "OSS 自定义域名已绑定到目标 bucket",
        ],
        "note": "未授权时只生成此操作单，不执行任何写操作。",
    }


# --------------------------------------------------------------------------- #
# 编排：rotate
# --------------------------------------------------------------------------- #
def rotate(cfg: dict, ak: str | None, sk: str | None, authorized: bool,
           *, cas_client=None, oss_bucket=None, auto_dns: bool = False,
           confirm_dns: bool = True,
           sleep: Callable[[float], None] = time.sleep) -> dict:
    if not authorized:
        raise RotationError("写操作被拒绝：必须显式传递 --authorized 才能执行申请/部署")
    if not ak or not sk:
        raise RotationError("缺少 AK/SK（请设置环境变量 ALIYUN_ACCESS_KEY_ID / ALIYUN_ACCESS_KEY_SECRET）")

    cas = cas_client or build_cas_client(cfg, ak, sk)
    oss = oss_bucket or build_oss_bucket(cfg, ak, sk)
    domain = cfg["domain"]
    validate_type = cfg.get("validate_type", "DNS")

    quota = inspect_quota(cas)
    if "remain" in quota and quota["remain"] <= 0:
        raise RotationError("免费额度已用尽（remain=0），无法申请新证书")

    order_id = apply_free_cert(cas, domain, validate_type)
    st = get_validation(cas, order_id)
    if st["need_validation"]:
        if auto_dns:
            _alidns_add_txt(cfg, ak, sk, st["record_domain"], st["record_value"])
        else:
            print("请在域名 DNS 添加 TXT 记录以完成验证：")
            print("  主机记录: %s" % st["record_domain"])
            print("  记录类型: TXT")
            print("  记录值:   %s" % st["record_value"])
            if confirm_dns:
                try:
                    input("添加完成后按回车继续轮询签发（测试环境可忽略）...")
                except EOFError:
                    pass
    st = poll_until_issued(cas, order_id, wait_seconds=cfg.get("wait_seconds", 30),
                           max_poll=cfg.get("max_poll", 40), sleep=sleep)
    cert_pem, key_pem = download_cert(cas, order_id, st)
    deploy_to_oss(oss, domain, cert_pem, key_pem)
    return {"order_id": order_id, "domain": domain, "status": "deployed",
            "cert_not_after": _cert_not_after(cert_pem)}


def _cert_not_after(cert_pem: str) -> str | None:
    """粗略抽取证书 notAfter（仅用于结果展示，不影响流程）。"""
    import base64
    import re

    try:
        block = re.search(r"-----BEGIN CERTIFICATE-----\n(.*?)\n-----END", cert_pem, re.S)
        if not block:
            return None
        der = base64.b64decode(block.group(1))
        m = re.search(rb"(\d{2})([A-Z][a-z]{2})(\d{2})\d{6}Z", der)
        return m.group(0).decode() if m else None
    except Exception:
        return None


def _alidns_add_txt(cfg: dict, ak: str, sk: str, host: str, value: str) -> None:
    """可选：用同账号 DNS 自动添加 TXT 验证记录。需 alibabacloud_alidns20150109。"""
    try:
        from alibabacloud_alidns20150109.client import Client as DnsClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_tea_util import models as util_models
        from alibabacloud_alidns20150109 import models as dns_models
    except ImportError:
        print("⚠️ 未安装 alibabacloud_alidns20150109，跳过自动加 TXT，请手动添加")
        return
    config = open_api_models.Config(access_key_id=ak, access_key_secret=sk)
    config.endpoint = "alidns.aliyuncs.com"
    client = DnsClient(config)
    rr = (host or "").split(".")[0] if host else "_dnsauth"
    domain_name = cfg.get("domain")
    req = dns_models.AddDomainRecordRequest(domain_name=domain_name, rr=rr,
                                            type="TXT", value=value)
    try:
        client.add_domain_record_with_options(req, util_models.RuntimeOptions())
        print("✓ 已自动添加 TXT 验证记录")
    except Exception as e:
        print("⚠️ 自动加 TXT 失败，请手动添加：%s" % e)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _load_cfg(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _creds() -> tuple[str | None, str | None]:
    return (os.environ.get("ALIYUN_ACCESS_KEY_ID"),
            os.environ.get("ALIYUN_ACCESS_KEY_SECRET"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cmd", choices=["plan", "inspect", "rotate"])
    parser.add_argument("--config", default="config.json",
                        help="配置文件路径（含 domain/oss_bucket/region/oss_endpoint 等）")
    parser.add_argument("--domain", help="覆盖配置里的 domain")
    parser.add_argument("--oss-bucket", help="覆盖配置里的 oss_bucket")
    parser.add_argument("--region", help="覆盖配置里的 region")
    parser.add_argument("--oss-endpoint", help="覆盖配置里的 oss_endpoint")
    parser.add_argument("--authorized", action="store_true",
                        help="显式授权执行写操作（rotate 必需，否则只出操作单）")
    parser.add_argument("--auto-dns", action="store_true",
                        help="域名 DNS 在同账号时自动添加 TXT 验证记录")
    parser.add_argument("--no-confirm-dns", action="store_true",
                        help="跳过「添加TXT后回车」的交互确认（脚本/测试用）")
    args = parser.parse_args(argv)

    cfg = _load_cfg(args.config)
    for k, v in (("domain", args.domain), ("oss_bucket", args.oss_bucket),
                 ("region", args.region), ("oss_endpoint", args.oss_endpoint)):
        if v:
            cfg[k] = v

    if args.cmd == "plan":
        if not cfg.get("domain"):
            print(json.dumps({"status": "ERROR", "error": "缺少 --domain 或 config.domain"}, ensure_ascii=False))
            return 2
        print(json.dumps(build_operation_order(cfg), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "inspect":
        ak, sk = _creds()
        if not ak or not sk:
            print(json.dumps({"status": "ERROR", "error": "inspect 需 AK（环境变量 ALIYUN_ACCESS_KEY_ID / ALIYUN_ACCESS_KEY_SECRET）"}, ensure_ascii=False))
            return 2
        if not cfg.get("domain") or not cfg.get("oss_bucket"):
            print(json.dumps({"status": "ERROR", "error": "inspect 需 config 含 domain 与 oss_bucket"}, ensure_ascii=False))
            return 2
        cas = build_cas_client(cfg, ak, sk)
        oss = build_oss_bucket(cfg, ak, sk)
        out = {"quota": inspect_quota(cas), "oss_cname": []}
        try:
            for c in oss.list_bucket_cname().cname:
                out["oss_cname"].append({
                    "domain": c.domain, "status": c.status,
                    "cert_status": c.certificate.status, "cert_id": c.certificate.cert_id})
        except Exception as e:
            out["oss_cname_error"] = str(e)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "rotate":
        if not cfg.get("domain") or not cfg.get("oss_bucket"):
            print(json.dumps({"status": "ERROR", "error": "rotate 需 config 含 domain 与 oss_bucket"}, ensure_ascii=False))
            return 2
        ak, sk = _creds()
        try:
            result = rotate(cfg, ak, sk, args.authorized,
                            auto_dns=args.auto_dns,
                            confirm_dns=not args.no_confirm_dns)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except RotationError as e:
            print(json.dumps({"status": "REFUSED_OR_FAILED", "error": str(e)}, ensure_ascii=False))
            return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
