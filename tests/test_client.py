"""Tests for the async VSON client."""

from __future__ import annotations

import pytest

from custom_components.vson_cloud import crypto
from custom_components.vson_cloud.client import VsonApiError, VsonAuthError, VsonClient


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


# ── Error paths and remaining endpoints ───────────────────────────────────────


class _RaisingSession:
    """Session whose POST fails at the transport level."""

    def post(self, url, data=None, headers=None):
        from aiohttp import ClientError

        raise ClientError("boom")


async def test_transport_error_raises_connection_error():
    from custom_components.vson_cloud.client import VsonConnectionError

    client = VsonClient(_RaisingSession(), "test@example.com", "secret", token="t")
    with pytest.raises(VsonConnectionError):
        await client.get_devices()


async def test_non_numeric_retcode_is_an_api_error(session):
    client = _client(session, token="t")
    session.queue({"code": "oops", "result": {"x": 1}})
    with pytest.raises(VsonApiError) as err:
        await client.get_devices()
    # Non-string result: no message is extracted.
    assert err.value.message == "unknown error"


async def test_call_air_escape_hatch(session):
    client = _client(session, token="t", base_url="https://example.invalid")
    session.queue({"retCode": 0, "result": {"ok": True}})
    assert await client.call_air("someEndpoint", foo=None, bar=2) == {"ok": True}
    call = session.calls[-1]
    assert call["url"] == "https://example.invalid/vc-air-ws-1.0.2/api/air/someEndpoint"
    assert call["data"] == {"foo": "", "bar": "2"}


async def test_authenticate_reuses_valid_restored_token(session):
    client = _client(session, token="RESTORED")
    session.queue({"retCode": 0, "result": {"equipmentList": []}})
    await client.authenticate()
    # Only the probe request was sent, no login.
    assert len(session.calls) == 1
    assert client.token == "RESTORED"


async def test_authenticate_relogs_when_restored_token_expired(session):
    client = _client(session, token="EXPIRED")
    responses = [
        {"retCode": 1003, "result": "token invalid"},
        {"retCode": 0, "result": {"tk": "FRESH", "userId": crypto.enc_header("u1")}},
    ]
    original_post = session.post

    def post(url, data=None, headers=None):
        session.queue(responses.pop(0))
        return original_post(url, data=data, headers=headers)

    session.post = post
    await client.authenticate()
    assert client.token == "FRESH"
    assert client.user_id == "u1"


async def test_login_without_token_is_auth_error(session):
    client = _client(session)
    session.queue({"retCode": 0, "result": {"userId": None}})
    with pytest.raises(VsonAuthError):
        await client.authenticate()


async def test_undecryptable_user_id_kept_raw(session):
    client = _client(session)
    session.queue({"retCode": 0, "result": {"tk": "T", "userId": "abc"}})
    await client.authenticate()
    assert client.user_id == "abc"


async def test_bley_home_returns_dict_or_empty(session):
    client = _client(session, token="t")
    session.queue({"retCode": 0, "result": {"battery": 50}})
    assert await client.bley_home("MAC") == {"battery": 50}
    session.queue({"retCode": 0, "result": None})
    assert await client.bley_home("MAC") == {}


async def test_bley_commands_send_expected_fields(session):
    client = _client(session, token="t")
    session.queue({"retCode": 0, "result": "ok"})

    assert await client.bley_refresh("MAC") == "ok"
    assert session.calls[-1]["data"] == {"mac": "MAC"}

    assert await client.bley_feed_now("MAC") == "ok"
    assert session.calls[-1]["data"] == {"mac": "MAC"}

    assert await client.bley_rotate("ID") == "ok"
    assert session.calls[-1]["data"] == {"id": "ID"}

    await client.bley_set_schedule_enabled("ID", True)
    assert session.calls[-1]["data"] == {"id": "ID", "isOpen": "1"}
    await client.bley_set_schedule_enabled("ID", False)
    assert session.calls[-1]["data"] == {"id": "ID", "isOpen": "0"}

    await client.bley_set_interval("ID", "08:00", 3, enabled=False)
    assert session.calls[-1]["data"] == {
        "id": "ID",
        "isOpen": "0",
        "openTime": "08:00",
        "frequency": "3",
    }
