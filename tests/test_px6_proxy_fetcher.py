import json

import pytest

from px6_proxy_fetcher.core import Px6ProxyFetcherError, fetch_proxies


class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _MockSession:
    def __init__(self, payload):
        self._payload = payload
        self.called = False

    def get(self, url, timeout=30):
        self.called = True
        return _MockResponse(self._payload)


def test_fetch_proxies_skips_inactive_records():
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
    payload = {
        "status": "yes",
        "list": {"1": {"active": "0"}},
        "list_count": 1,
    }
    session = _MockSession(payload)

    proxies = fetch_proxies("dummy", session=session)

    assert proxies == []


def test_fetch_proxies_returns_empty_for_zero_count():
    payload = {"status": "yes", "list": {}, "list_count": 0}
    session = _MockSession(payload)

    proxies = fetch_proxies("dummy", session=session)

    assert proxies == []


def test_fetch_proxies_brackets_ipv6_hosts():
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
    payload = {"status": "no", "error": "bad key"}
    session = _MockSession(payload)

    with pytest.raises(Px6ProxyFetcherError) as excinfo:
        fetch_proxies("dummy", session=session)

    assert "bad key" in str(excinfo.value)


def test_fetch_proxies_raises_on_invalid_json():
    payload = json.JSONDecodeError("fail", doc="", pos=0)
    session = _MockSession(payload)

    with pytest.raises(Px6ProxyFetcherError):
        fetch_proxies("dummy", session=session)
