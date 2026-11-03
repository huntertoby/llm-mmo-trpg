"""經 Tunnel／反向代理時的真實 IP（Phase 5E-3，計畫 30.3；5E-2 待決 4）。

只有連線來源在 ``trusted_proxies`` 裡時才讀轉發標頭；預設清單是空的＝不信任任何轉發標頭（標頭可由
任何人偽造）。來源可信任時：

1. ``CF-Connecting-IP``（合法 IP 才用）；
2. ``X-Forwarded-For``：由右往左跳過可信任的位址，取第一個不可信任的（全部可信任取最左邊）；
3. 都沒有：連線來源本身。
"""

from __future__ import annotations

import ipaddress
from collections.abc import Mapping, Sequence
from typing import Final

from trpg.api.server_config import IpNetwork

__all__ = ["CF_HEADER", "XFF_HEADER", "client_ip"]

CF_HEADER: Final = "cf-connecting-ip"
XFF_HEADER: Final = "x-forwarded-for"

type _Address = ipaddress.IPv4Address | ipaddress.IPv6Address


def _parse(raw: str | None) -> _Address | None:
    if raw is None:
        return None
    try:
        return ipaddress.ip_address(raw.strip())
    except ValueError:
        return None


def _trusted(address: _Address, networks: Sequence[IpNetwork]) -> bool:
    return any(address.version == net.version and address in net for net in networks)


def _from_forwarded_for(header: str, networks: Sequence[IpNetwork]) -> _Address | None:
    hops = [_parse(part) for part in header.split(",")]
    if any(h is None for h in hops):
        return None  # 不合法就整個忽略
    valid = [h for h in hops if h is not None]
    for hop in reversed(valid):
        if not _trusted(hop, networks):
            return hop
    return valid[0] if valid else None


def client_ip(
    peer: str | None, headers: Mapping[str, str], trusted: Sequence[IpNetwork]
) -> str | None:
    """請求的真實來源 IP；``peer`` 是 TCP 連線的來源（``request.client.host``）。"""
    source = _parse(peer)
    if source is None or not trusted or not _trusted(source, trusted):
        return peer
    lowered = {k.lower(): v for k, v in headers.items()}
    cf = _parse(lowered.get(CF_HEADER))
    if cf is not None:
        return str(cf)
    forwarded = lowered.get(XFF_HEADER)
    if forwarded:
        found = _from_forwarded_for(forwarded, trusted)
        if found is not None:
            return str(found)
    return peer
