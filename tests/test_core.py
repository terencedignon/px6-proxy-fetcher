from px6_proxy_fetcher.core import fetch_proxies


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self._payload = payload
        self.called = False

    def get(self, url, timeout=30):
        self.called = True
        return FakeResponse(self._payload)


def test_fetch_proxies_returns_only_active_entries():
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
    session = FakeSession(payload)

    proxies = fetch_proxies("dummy", session=session)

    assert proxies == ["http://active:secret@proxy.px6.net:1234"]
    assert session.called is True


def test_fetch_proxies_wraps_ipv6_addresses():
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
    session = FakeSession(payload)

    proxies = fetch_proxies("dummy", session=session)

    assert proxies == ["socks5://v6user:v6pass@[2001:db8::1]:9000"]
