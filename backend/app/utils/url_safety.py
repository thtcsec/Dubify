"""Validate remote URLs before server-side fetch (SSRF mitigation)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    }
)


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def validate_public_http_url(url: str) -> None:
    """Raise ValueError if the URL is not a safe public http(s) target."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are supported.")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed.")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError("URL hostname is missing.")
    if hostname in _BLOCKED_HOSTNAMES or hostname.endswith(".localhost"):
        raise ValueError("Internal/private URLs are not allowed.")

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if _is_blocked_ip(literal):
            raise ValueError("Internal/private URLs are not allowed.")
        return

    try:
        for info in socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM):
            ip = ipaddress.ip_address(info[4][0])
            if _is_blocked_ip(ip):
                raise ValueError("Internal/private URLs are not allowed.")
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host: {hostname}") from exc
