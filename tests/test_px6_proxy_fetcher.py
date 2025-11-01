"""Tests for px6_proxy_fetcher core functionality."""

import json

import pytest
import requests

from px6_proxy_fetcher.core import (
    Px6ProxyFetcherError,
    fetch_proxies,
    write_proxies,
)


class _MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, payload, exception=None):
        self._payload = payload
        self._exception = exception

    def json(self):
        """Return JSON payload or raise exception."""
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def raise_for_status(self):
        """Raise HTTP exception if configured."""
        if self._exception:
            raise self._exception


class _MockSession:
    """Mock requests session for testing."""

    def __init__(self, payload, exception=None):
        self._payload = payload
        self._exception = exception
        self.called = False

    def get(self, url, timeout=30):
        """Mock GET request."""
        self.called = True
        self.timeout = timeout
        return _MockResponse(self._payload, self._exception)


def test_fetch_proxies_skips_inactive_records():
    """Test that inactive proxies are filtered out from results."""
    payload = {
        "status": "yes",
        "list": {
            "1": {
                "type": "http",
                "user": "active",
                "pass": "secret",
                "host": "proxy.px6.net",
                "port": "1234",
                "version": "4",
                "active": "1",
            },
            "2": {"active": "0"},
        },
        "list_count": 2,
    }
    session = _MockSession(payload)

    proxies = fetch_proxies("dummy", session=session)

    assert proxies == ["http://active:secret@proxy.px6.net:1234"]
    assert session.called is True


def test_fetch_proxies_returns_empty_when_none_active():
    """Test that an empty list is returned when all proxies are inactive."""
    payload = {
        "status": "yes",
        "list": {"1": {"active": "0"}},
        "list_count": 1,
    }
    session = _MockSession(payload)

    proxies = fetch_proxies("dummy", session=session)

    assert proxies == []


def test_fetch_proxies_returns_empty_for_zero_count():
    """Test that an empty list is returned when list_count is zero."""
    payload = {"status": "yes", "list": {}, "list_count": 0}
    session = _MockSession(payload)

    proxies = fetch_proxies("dummy", session=session)

    assert proxies == []


def test_fetch_proxies_brackets_ipv6_hosts():
    """Test that IPv6 addresses are properly bracketed in proxy URLs."""
    payload = {
        "status": "yes",
        "list": [
            {
                "type": "socks5",
                "user": "v6user",
                "pass": "v6pass",
                "ip": "2001:db8::1",
                "port": "9000",
                "version": "6",
                "active": "1",
            },
        ],
        "list_count": 1,
    }
    session = _MockSession(payload)

    proxies = fetch_proxies("dummy", session=session)

    assert proxies == ["socks5://v6user:v6pass@[2001:db8::1]:9000"]


def test_fetch_proxies_raises_when_api_reports_error():
    """Test that API errors are properly raised as Px6ProxyFetcherError."""
    payload = {"status": "no", "error": "bad key"}
    session = _MockSession(payload)

    with pytest.raises(Px6ProxyFetcherError) as excinfo:
        fetch_proxies("dummy", session=session)

    assert "bad key" in str(excinfo.value)


def test_fetch_proxies_raises_on_invalid_json():
    """Test that invalid JSON responses raise Px6ProxyFetcherError."""
    payload = json.JSONDecodeError("fail", doc="", pos=0)
    session = _MockSession(payload)

    with pytest.raises(Px6ProxyFetcherError):
        fetch_proxies("dummy", session=session)


def test_fetch_proxies_raises_on_http_error():
    """Test that HTTP errors are converted to Px6ProxyFetcherError."""
    session = _MockSession({}, exception=requests.HTTPError("boom"))

    with pytest.raises(Px6ProxyFetcherError):
        fetch_proxies("dummy", session=session)


def test_write_proxies_sets_restrictive_permissions(tmp_path):
    """Test that written proxy files have 0o600 permissions."""
    output = tmp_path / "proxies.txt"

    proxies = ["http://user:pass@proxy:1234"]
    result_path = write_proxies(proxies, destination=output)

    assert result_path == output
    assert output.exists()
    assert output.stat().st_mode & 0o777 == 0o600
