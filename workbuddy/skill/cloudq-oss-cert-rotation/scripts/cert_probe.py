#!/usr/bin/env python3
"""OSS 自定义域名证书只读巡检。仅发起一次只读 TLS 握手，不申请、不部署、不回滚。"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import ssl
import sys

OPERATION = "READ_ONLY_TLS_HANDSHAKE"


def _default_connect(domain: str, port: int, timeout: float) -> ssl.SSLSocket:
    """发起一次只读 TLS 握手：开启系统信任链 + 主机名校验。"""
    ctx = ssl.create_default_context()
    sock = socket.create_connection((domain, port), timeout=timeout)
    return ctx.wrap_socket(sock, server_hostname=domain)


def _parse_not_after(value: str) -> dt.datetime:
    """解析证书 notAfter，如 'Jan 10 07:59:59 2027 GMT'。"""
    return dt.datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=dt.timezone.utc)


def check_cert(
    domain: str,
    warn_days: int = 30,
    *,
    port: int = 443,
    timeout: float = 8.0,
    now: dt.datetime | None = None,
    connect=None,
) -> dict:
    """只读探测域名证书。任何外部失败统一返回 UNVERIFIED，保留 error_type，不猜根因。"""
    connect = connect or _default_connect
    now = now or dt.datetime.now(dt.timezone.utc)
    result = {
        "domain": domain,
        "operation": OPERATION,
        "status": "UNVERIFIED",
        "hostname_and_chain_verified": False,
        "warn_days": warn_days,
    }
    try:
        with connect(domain, port, timeout) as ssock:
            cert = ssock.getpeercert()
    except ssl.SSLCertVerificationError as err:
        result.update(error_type=type(err).__name__, error=str(err.verify_message or err))
        return result
    except (socket.timeout, TimeoutError) as err:
        result.update(error_type="TimeoutError", error=str(err) or "handshake timeout")
        return result
    except ssl.SSLError as err:
        result.update(error_type=type(err).__name__, error=str(err))
        return result
    except (socket.gaierror, OSError) as err:
        result.update(error_type=type(err).__name__, error=str(err))
        return result

    not_after = _parse_not_after(cert["notAfter"])
    expires_in_days = (not_after - now).days
    result.update(
        hostname_and_chain_verified=True,
        not_after_utc=not_after.isoformat(),
        expires_in_days=expires_in_days,
        subject=dict(x[0] for x in cert.get("subject", ())).get("commonName", ""),
    )
    if expires_in_days < 0:
        result.update(status="UNVERIFIED", error_type="Expired", error="certificate notAfter is in the past")
    elif expires_in_days < warn_days:
        result["status"] = "EXPIRING"
    else:
        result["status"] = "HEALTHY"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--warn-days", type=int, default=30)
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args(argv)
    try:
        out = check_cert(args.domain, args.warn_days, port=args.port, timeout=args.timeout)
    except ValueError as err:
        print(json.dumps({"domain": args.domain, "status": "ERROR", "error": str(err)}, ensure_ascii=False))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
