#!/usr/bin/env python3
"""OSS 自定义域名「访问入口」只读识别。

判定流量是直连 OSS 还是经过 CDN：**以响应头为主证据**，CNAME 仅作弱提示。
只读：一次 DNS 查询 + 一次 HTTPS GET（不读响应体），不申请、不部署、不改任何资源。
"""
from __future__ import annotations

import argparse
import json
import random
import socket
import ssl
import struct
import urllib.error
import urllib.request

OPERATION = "READ_ONLY_ENTRY_PROBE"

# 强证据：CDN 回包特征头
CDN_HEADER_SIGNS = (
    "x-cache",
    "x-cache-status",
    "via",
    "x-swift-cachetime",
    "ali-swift-stat-host",
    "x-served-by",
    "x-cdn",
    "x-ali-cdn",
)
# 强证据：OSS 回包特征
OSS_SERVER_SIGN = "aliyunoss"
OSS_HEADER_PREFIX = "x-oss-"
# 弱提示：只有名字出现这些片段时，才把 CNAME 当作 CDN 线索
CDN_CNAME_HINTS = (
    "kunlun",
    "alikunlun",
    "alicdn",
    "cdngslb",
    "wscloudcdn",
    "tlcdn",
    "txcdn",
    "cloudfront",
    "fastly",
    "akamai",
)


def classify_entry(
    *,
    server_header: str = "",
    headers: dict | None = None,
    cname_chain: list | None = None,
) -> tuple[str, str]:
    """按「响应头优先、CNAME 仅弱提示」判定入口。返回 (entry, evidence)。

    entry ∈ {OSS_DIRECT, BEHIND_CDN, UNKNOWN}。
    注意：CNAME 名称不含 oss-cn-* **不能**据此推断入口；只有回包才可定性。
    """
    headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    cname_chain = list(cname_chain or [])

    hit_cdn = sorted(k for k in headers if k in CDN_HEADER_SIGNS)
    if hit_cdn:
        shown = "、".join(f"{k}: {headers[k]}" for k in hit_cdn[:3])
        return "BEHIND_CDN", f"响应头出现 CDN 特征（{shown}）"

    has_oss_header = sorted(k for k in headers if k.startswith(OSS_HEADER_PREFIX))
    if OSS_SERVER_SIGN in server_header.lower() or has_oss_header:
        why = f"Server: {server_header}" if server_header else f"{has_oss_header[0]}"
        return "OSS_DIRECT", f"回包由 OSS 直接应答（{why}），未见 CDN 特征头"

    weak = [c for c in cname_chain if any(h in c.lower() for h in CDN_CNAME_HINTS)]
    if weak:
        return "BEHIND_CDN", f"仅 CNAME（{weak[0]}）疑似 CDN，未取得可用响应头，结论为弱提示"

    return "UNKNOWN", "未取得 OSS/CDN 特征头，且 CNAME 无可识别线索；入口未确定"


def _decode_name(data: bytes, offset: int) -> tuple[str, int]:
    """解析 DNS 域名，支持压缩指针。返回 (name, 下一个 offset)。"""
    labels: list[str] = []
    jumped = False
    nxt = offset
    while True:
        if offset >= len(data):
            raise ValueError("DNS 报文截断")
        length = data[offset]
        if length == 0:
            offset += 1
            if not jumped:
                nxt = offset
            break
        if length & 0xC0 == 0xC0:
            pointer = struct.unpack("!H", data[offset : offset + 2])[0] & 0x3FFF
            if not jumped:
                nxt = offset + 2
            jumped = True
            offset = pointer
            continue
        labels.append(data[offset + 1 : offset + 1 + length].decode("ascii", "replace"))
        offset += 1 + length
    return ".".join(labels), nxt


def _default_dns_cname(domain: str, server: str | None, timeout: float) -> list:
    """向解析服务器查一次 CNAME，返回链式目标（最多 5 跳）。失败抛异常。"""
    server = server or "223.5.5.5"
    chain: list = []
    current = domain
    for _ in range(5):
        query = struct.pack("!HHHHHH", random.randint(0, 0xFFFF), 0x0100, 1, 0, 0, 0)
        for label in current.split("."):
            if not label:
                continue
            query += bytes([len(label)]) + label.encode("ascii")
        query += b"\x00" + struct.pack("!HH", 5, 1)  # QTYPE=CNAME, QCLASS=IN

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(query, (server, 53))
            data, _ = sock.recvfrom(4096)

        qdcount, ancount = struct.unpack("!HH", data[4:8])
        offset = 12
        for _ in range(qdcount):
            _, offset = _decode_name(data, offset)
            offset += 4  # QTYPE + QCLASS

        target = None
        for _ in range(ancount):
            _, offset = _decode_name(data, offset)
            rrtype, _, _, rdlength = struct.unpack("!HHIH", data[offset : offset + 10])
            offset += 10
            if rrtype == 5:
                name, _ = _decode_name(data, offset)
                target = name
            offset += rdlength
        if not target:
            break
        chain.append(target)
        current = target
    return chain


def _default_http(domain: str, port: int, timeout: float) -> tuple:
    """一次只读 HTTPS GET，只取响应头，不读响应体。返回 (status, headers)。"""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(f"https://{domain}:{port}/", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as err:
        return err.code, {k.lower(): v for k, v in (err.headers or {}).items()}


def check_entry(
    domain: str,
    *,
    port: int = 443,
    timeout: float = 8.0,
    dns_server: str | None = None,
    http_probe=None,
    dns_probe=None,
) -> dict:
    """只读识别访问入口。任何外部失败都如实记录，不猜根因、不臆断为 OSS 直连。"""
    http_probe = http_probe or _default_http
    dns_probe = dns_probe or _default_dns_cname
    result = {
        "domain": domain,
        "operation": OPERATION,
        "entry": "UNKNOWN",
        "cname_chain": [],
        "http_status": None,
        "server_header": "",
        "evidence": "",
        "errors": [],
    }
    try:
        result["cname_chain"] = list(dns_probe(domain, dns_server, timeout) or [])
    except Exception as err:  # noqa: BLE001 - 只读探针，任何 DNS 异常都如实记录
        result["errors"].append({"step": "dns_cname", "error_type": type(err).__name__, "error": str(err)})

    headers: dict = {}
    try:
        status, raw_headers = http_probe(domain, port, timeout)
        headers = {str(k).lower(): v for k, v in (raw_headers or {}).items()}
        result["http_status"] = status
        result["server_header"] = str(headers.get("server", ""))
    except Exception as err:  # noqa: BLE001 - 外部失败统一记录，不编造结论
        result["errors"].append({"step": "https_get", "error_type": type(err).__name__, "error": str(err)})

    entry, evidence = classify_entry(
        server_header=result["server_header"],
        headers=headers,
        cname_chain=result["cname_chain"],
    )
    result["entry"] = entry
    result["evidence"] = evidence
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--dns-server", default=None, help="解析服务器，默认 223.5.5.5")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            check_entry(
                args.domain,
                port=args.port,
                timeout=args.timeout,
                dns_server=args.dns_server,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
