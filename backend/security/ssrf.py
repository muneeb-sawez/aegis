"""AEGIS SSRF (Server-Side Request Forgery) Defense Engine.

Enforces strict URL validation on every outbound destination (health_url, admin_url,
probe endpoints). Blocks cloud metadata services, link-local IPs, dangerous schemes,
and embedded credentials.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Well-known cloud provider instance metadata endpoints
BLOCKED_METADATA_HOSTS = {
    "169.254.169.254",          # AWS / GCP / Azure Link-Local Metadata
    "metadata.google.internal", # GCP Internal Metadata DNS
    "metadata",                 # GCP / Container Metadata Alias
    "100.100.100.200",          # Alibaba Cloud Metadata
    "169.254.170.2",            # AWS ECS Task Metadata
    "instance-data",            # AWS Legacy Metadata Host
}

ALLOWED_SCHEMES = {"http", "https"}


def validate_url_ssrf(url: str, allow_private_networks: bool = True) -> str:
    """Validate that a URL is safe against SSRF vulnerabilities.

    Args:
        url: The candidate URL string (e.g. health_url, admin_url).
        allow_private_networks: If True, allows RFC1918 / loopback (required for local
            microservice containers & testbed), but strictly blocks cloud metadata and link-local.
            If False, also blocks all RFC1918 private subnets and 127.0.0.1.

    Returns:
        The validated URL string if safe.

    Raises:
        ValueError: If the URL fails scheme, hostname, port, or SSRF security rules.
    """
    if not url or not isinstance(url, str) or not url.strip():
        raise ValueError("Endpoint URL cannot be empty.")

    clean_url = url.strip()

    try:
        parsed = urlparse(clean_url)
    except Exception as e:
        raise ValueError(f"Malformed URL: {e}")

    # 1. Validate Scheme
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted for safety."
        )

    # 2. Reject Embedded Credentials (http://user:pass@host)
    if parsed.username or parsed.password:
        raise ValueError("User credentials are not allowed in endpoint URLs.")

    # 3. Validate Hostname
    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise ValueError("URL must include a valid hostname or IP address.")

    # 4. Check Blocked Metadata Hostnames
    if hostname in BLOCKED_METADATA_HOSTS:
        raise ValueError(f"Target host '{hostname}' is blocked for security purposes (SSRF cloud metadata).")

    # 5. Validate Port Range
    if parsed.port is not None:
        if not (1 <= parsed.port <= 65535):
            raise ValueError(f"Port {parsed.port} is outside valid range (1-65535).")

    # 6. Check IP-Level Boundaries (Link-Local, Multicast, Unspecified)
    try:
        ip = ipaddress.ip_address(hostname)

        if ip.is_link_local:
            raise ValueError(f"Link-local IP address '{hostname}' is blocked (SSRF defense).")

        if ip.is_multicast:
            raise ValueError(f"Multicast IP address '{hostname}' is blocked.")

        if ip.is_unspecified:
            raise ValueError(f"Unspecified IP address '{hostname}' (0.0.0.0) is blocked.")

        # If strict private networks are disabled:
        if not allow_private_networks and (ip.is_private or ip.is_loopback):
            raise ValueError(f"Private network address '{hostname}' is not permitted.")

    except ValueError as e:
        if "is blocked" in str(e) or "not permitted" in str(e):
            raise
        # Not a literal IP address (e.g. domain name or Docker service name like "paymentservice")
        # Optional: Resolve DNS to verify it does not secretly resolve to 169.254.169.254
        if hostname not in ("localhost", "127.0.0.1", "::1") and "." in hostname:
            try:
                resolved_ip_str = socket.gethostbyname(hostname)
                resolved_ip = ipaddress.ip_address(resolved_ip_str)
                if resolved_ip.is_link_local or resolved_ip_str in BLOCKED_METADATA_HOSTS:
                    raise ValueError(
                        f"Target host '{hostname}' resolves to blocked link-local metadata IP '{resolved_ip_str}'."
                    )
            except (socket.gaierror, socket.herror):
                # Unresolvable in local sandbox without network; allowable for container names
                pass

    return clean_url
