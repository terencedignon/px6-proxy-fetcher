"""Core helpers for talking to the PROXY6.net API."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import suppress
from datetime import datetime
from datetime import timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)
API_ROOT = "https://px6.link/api/{api_key}/getproxy"
"""Base URL template for PROXY6.net API endpoints."""


class Px6ProxyFetcherError(RuntimeError):
    """Raised when the PROXY6.net API request fails."""


def fetch_proxies(
    api_key: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 30
) -> list[str]:
    """Fetch active proxies for the account associated with api_key.

    Args:
        api_key: PROXY6.net personal API key.
        session: Optional pre-configured requests.Session instance.
        timeout: Timeout for the API call in seconds.

    Returns:
        List of proxy URLs in scheme://user:pass@host:port format.

    Raises:
        Px6ProxyFetcherError: If the request fails or the API returns an
            error.
    """
    url = API_ROOT.format(api_key=api_key)
    http = session or requests

    logger.debug("Fetching proxies from %s", url)

    try:
        response = http.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        msg = f"Failed to call PROXY6.net API: {exc}"
        raise Px6ProxyFetcherError(msg) from exc

    try:
        payload: dict[str, object] = response.json()
    except json.JSONDecodeError as exc:
        raise Px6ProxyFetcherError("API response was not valid JSON") from exc

    if payload.get("status") != "yes":
        message = payload.get("error") or "Unknown API error"
        raise Px6ProxyFetcherError(message)

    proxy_list = payload.get("list") or []
    proxy_count = int(payload.get("list_count") or 0)

    if proxy_count == 0:
        logger.info("API returned zero active proxies.")
        return []

    return _extract_proxy_urls(proxy_list)


def _extract_proxy_urls(proxy_list: object) -> list[str]:
    """Extract and format proxy URLs from API response data.

    Args:
        proxy_list: Proxy data from API, either a mapping or sequence.

    Returns:
        List of formatted proxy URLs for active proxies only.

    Raises:
        Px6ProxyFetcherError: If proxy_list is not a mapping or sequence.
    """
    records = []

    if isinstance(proxy_list, Mapping):
        items = proxy_list.items()
    elif isinstance(proxy_list, Sequence):
        items = enumerate(proxy_list)
    else:
        msg = f"Unexpected proxy list type: {type(proxy_list)!r}"
        raise Px6ProxyFetcherError(msg)

    for proxy_id, proxy_info in items:
        if not isinstance(proxy_info, Mapping):
            logger.debug("Skipping malformed proxy entry %r", proxy_id)
            continue

        if proxy_info.get("active") != "1":
            continue

        proxy_type = proxy_info.get("type") or "http"
        user = proxy_info.get("user")
        password = proxy_info.get("pass")
        version = proxy_info.get("version") or "4"

        if version == "6":
            host = proxy_info.get("ip")
        else:
            host = proxy_info.get("host") or proxy_info.get("ip")

        port = proxy_info.get("port")

        if not all([proxy_type, user, password, host, port]):
            logger.debug("Skipping incomplete proxy entry %r", proxy_id)
            continue

        host_str = str(host)
        needs_brackets = ":" in host_str and not host_str.startswith("[")
        formatted_host = f"[{host}]" if needs_brackets else host_str
        proxy_url = f"{proxy_type}://{user}:{password}@{formatted_host}:{port}"
        records.append(proxy_url)

    return records


def write_proxies(
    proxies: Sequence[str],
    destination: Path | str = "proxies.txt"
) -> Path:
    """Persist the given proxy list to destination.

    A short metadata header is written ahead of the proxy URLs.
    The file is created with restrictive permissions (0o600) since it
    contains credentials.

    Args:
        proxies: List of proxy URLs to write.
        destination: Output file path. Defaults to proxies.txt.

    Returns:
        Path object pointing to the written file.
    """
    path = Path(destination)
    timestamp = datetime.now(timezone.utc)
    header_time = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")

    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.parent / f".{path.name}.tmp"

    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(tmp_path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("# Proxies from PROXY6.net\n")
            handle.write(f"# Generated: {header_time}\n")
            handle.write(f"# Count: {len(proxies)}\n\n")
            for proxy in proxies:
                handle.write(f"{proxy}\n")

        os.replace(tmp_path, path)
        os.chmod(path, 0o600)
    finally:
        with suppress(FileNotFoundError):
            os.remove(tmp_path)

    logger.info("Wrote %s proxies to %s", len(proxies), path)
    return path


def format_env_exports(
    proxies: Sequence[str],
    *,
    strategy: str = "round_robin"
) -> str:
    """Return shell export instructions for the proxy list.

    Args:
        proxies: List of proxy URLs.
        strategy: Load balancing strategy name. Defaults to round_robin.

    Returns:
        Shell export commands as a string.
    """
    proxy_list = ",".join(proxies)
    return (
        f"export PROXY_LIST='{proxy_list}'\n"
        f"export PROXY_STRATEGY='{strategy}'"
    )
