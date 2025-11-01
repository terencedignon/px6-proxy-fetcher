"""Core helpers for talking to the PROXY6.net API."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import List, Mapping, MutableMapping, Optional, Sequence

import requests

logger = logging.getLogger(__name__)
API_ROOT = "https://px6.link/api/{api_key}/getproxy"


class Px6ProxyFetcherError(RuntimeError):
    """Raised when the PROXY6.net API request fails."""


def fetch_proxies(api_key: str, *, session: Optional[requests.Session] = None, timeout: int = 30) -> List[str]:
    """Fetch active proxies for the account associated with ``api_key``.

    Args:
        api_key: PROXY6.net personal API key.
        session: Optional pre-configured ``requests.Session`` instance.
        timeout: Timeout for the API call in seconds.

    Returns:
        List of proxy URLs in ``scheme://user:pass@host:port`` format.

    Raises:
        Px6ProxyFetcherError: If the request fails or the API returns an error.
    """
    url = API_ROOT.format(api_key=api_key)
    http = session or requests

    logger.debug("Fetching proxies from %s", url)

    try:
        response = http.get(url, timeout=timeout)
    except requests.RequestException as exc:
        raise Px6ProxyFetcherError(f"Failed to call PROXY6.net API: {exc}") from exc

    try:
        payload: MutableMapping[str, object] = response.json()
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


def _extract_proxy_urls(proxy_list: object) -> List[str]:
    records = []

    if isinstance(proxy_list, Mapping):
        items = proxy_list.items()
    elif isinstance(proxy_list, Sequence):
        items = enumerate(proxy_list)
    else:
        raise Px6ProxyFetcherError(f"Unexpected proxy list type: {type(proxy_list)!r}")

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

        formatted_host = f"[{host}]" if ":" in str(host) and not str(host).startswith("[") else str(host)
        proxy_url = f"{proxy_type}://{user}:{password}@{formatted_host}:{port}"
        records.append(proxy_url)

    return records


def write_proxies(proxies: Sequence[str], destination: Path | str = "proxies.txt") -> Path:
    """Persist the given proxy list to ``destination``.

    A short metadata header is written ahead of the proxy URLs.
    """
    path = Path(destination)
    header_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Proxies from PROXY6.net\n")
        handle.write(f"# Generated: {header_time}\n")
        handle.write(f"# Count: {len(proxies)}\n\n")
        for proxy in proxies:
            handle.write(f"{proxy}\n")

    logger.info("Wrote %s proxies to %s", len(proxies), path)
    return path


def format_env_exports(proxies: Sequence[str], *, strategy: str = "round_robin") -> str:
    """Return shell export instructions for the proxy list."""
    proxy_list = ",".join(proxies)
    return (
        f"export PROXY_LIST='{proxy_list}'\n"
        f"export PROXY_STRATEGY='{strategy}'"
    )
