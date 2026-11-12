"""Tests for the async VSON client."""

from __future__ import annotations

import pytest

from custom_components.vson import crypto
from custom_components.vson.client import VsonApiError, VsonAuthError, VsonClient


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    async def json(self, content_type=None):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    """Captures the last POST and returns a queued payload."""

    def __init__(self):
        self.calls = []
        self._next = {"retCode": 0, "result": {}}

    def queue(self, payload):
        self._next = payload

    def post(self, url, data=None, headers=None):
        self.calls.append({"url": url, "data": data, "headers": headers})
        return _FakeResponse(self._next)


@pytest.fixture
def session():
    return _FakeSession()


def _client(session, **kw):
    return VsonClient(session, "test@example.com", "secret", **kw)


async def test_login_encrypts_credentials_and_stores_token(session):
    client = _client(session)
    session.queue({"retCode": "0", "result": {"tk": "RAWTOKEN", "userId": None}})
    await client.authenticate()

    assert client.token == "RAWTOKEN"
    body = session.calls[-1]["data"]
    # name/pwd must be CRED-encrypted (decrypt back to the plaintext).
    assert crypto.dec_cred(body["name"]) == "test@example.com"
    assert crypto.dec_cred(body["pwd"]) == "secret"
    assert body["accountType"] == "102"  # e-mail


async def test_tk_header_is_header_encrypted(session):
    client = _client(session, token="RAWTOKEN")
    session.queue({"retCode": 0, "result": {"equipmentList": []}})
    await client.get_devices()
    headers = session.calls[-1]["headers"]
    assert crypto.dec_header(headers["tk"]) == "RAWTOKEN"
    # Static encrypted headers reproduce the app constants.
    assert headers["bh"] == "JmnuSXWflZY="


async def test_retcode_string_success(session):
    client = _client(session, token="t")
    session.queue({"retCode": "0", "result": {"equipmentList": [{"id": "x"}]}})
    devices = await client.get_devices()
    assert devices == [{"id": "x"}]


async def test_api_error_raised(session):
    client = _client(session, token="t")
    session.queue({"retCode": "1017", "result": "Decryption error"})
    with pytest.raises(VsonApiError) as err:
        await client.get_devices()
    assert err.value.ret_code == 1017


async def test_token_invalid_raises_auth(session):
    client = _client(session, token="t")
    session.queue({"retCode": 1003, "result": "token invalid"})
    with pytest.raises(VsonAuthError):
        await client.get_devices()


async def test_get_devices_flattens_homes(session):
    client = _client(session, token="t")
    session.queue(
        {
            "retCode": 0,
            "result": [
                {"equipmentList": [{"id": "a"}, {"id": "b"}]},
                {"equipmentList": [{"id": "c"}]},
            ],
        }
    )
    devices = await client.get_devices()
    assert [d["id"] for d in devices] == ["a", "b", "c"]
