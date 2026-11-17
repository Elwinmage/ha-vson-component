"""Async client for the VSON cloud API (apis.myvsoncloud.com).

Reverse-engineered from the official Android app. All traffic is HTTPS POST
form-urlencoded; there is no proprietary socket protocol for read/control.

Authentication facts proven against the live API:
  - Login sends name + password 3DES-encrypted with the CRED key; accountType
    is 101 (phone) or 102 (e-mail).
  - The login response returns an opaque token ``tk`` and an encrypted userId.
  - Every subsequent request carries the token in the ``tk`` header,
    re-encrypted with the HEADER key (app class k.g: e0.b.e(getTk())). Sending
    the raw token yields API error 1017 "Decryption error".
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from . import crypto
from .const import (
    ACCOUNT_TYPE_EMAIL,
    ACCOUNT_TYPE_MOBILE,
    DEFAULT_BASE_URL,
    EP_BLEY_FEED_IS_OPEN,
    EP_BLEY_FEED_NOW,
    EP_BLEY_HOMEPAGE,
    EP_BLEY_INTERVAL,
    EP_BLEY_REFRESH,
    EP_BLEY_ROTATE,
    EP_HOME_PAGE,
    HDR_APT,
    HDR_APV_DEFAULT,
    HDR_BH_PLAIN,
    HDR_CM,
    HDR_MAC_PLAIN,
    HDR_MD,
    HDR_OST,
    HDR_PID,
    HDR_UUID_PLAIN,
    RET_OK,
    RET_TOKEN_INVALID,
    SVC_AIR,
    SVC_MEMBER,
)

_LOGGER = logging.getLogger(__name__)


class VsonError(Exception):
    """Base class for VSON client errors."""


class VsonAuthError(VsonError):
    """Login failed, or the session token is invalid/expired."""


class VsonConnectionError(VsonError):
    """A transport or server error prevented the request."""


class VsonApiError(VsonError):
    """The API returned a non-zero retCode."""

    def __init__(self, ret_code: int, message: str | None = None) -> None:
        self.ret_code = ret_code
        self.message = message or "unknown error"
        super().__init__(f"VSON API error {ret_code}: {self.message}")


class VsonClient:
    """Client for a single VSON cloud account."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
        account_type: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = None,
        app_version: str = HDR_APV_DEFAULT,
        lang: str = "en",
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._account_type = account_type or (
            ACCOUNT_TYPE_EMAIL if "@" in username else ACCOUNT_TYPE_MOBILE
        )
        self._base_url = base_url if base_url.endswith("/") else base_url + "/"
        self._token = token  # raw login token (not the encrypted header form)
        self._user_id: str | None = None
        self._app_version = app_version
        self._lang = (lang or "en").split("-")[0]

        # Constant encrypted headers, computed once.
        self._static_headers = {
            "bh": crypto.enc_header(HDR_BH_PLAIN),
            "md": HDR_MD,
            "pid": HDR_PID,
            "ost": HDR_OST,
            "apt": HDR_APT,
            "apv": self._app_version,
            "cm": HDR_CM,
            "mac": crypto.enc_header(HDR_MAC_PLAIN),
            "uuid": crypto.enc_header(HDR_UUID_PLAIN),
            "mpb": crypto.enc_header("homeassistant"),
            "mpm": crypto.enc_header("vson"),
            "osv": "13",
            "language": self._lang,
            "timeZone": "GMT+00:00",
        }

    # ── Public state ──────────────────────────────────────────────────────────

    @property
    def token(self) -> str | None:
        """Raw login token, to persist and restore across restarts."""
        return self._token

    @property
    def user_id(self) -> str | None:
        """Decrypted user id of the account (available after authenticate)."""
        return self._user_id

    # ── Low-level request ─────────────────────────────────────────────────────

    def _headers(self, action: str) -> dict[str, str]:
        headers = dict(self._static_headers)
        headers["an"] = action  # client-side cancellation tag; server ignores it
        if self._token:
            # The server decrypts the "tk" header to validate the session, so
            # it must be the login token re-encrypted with the header key.
            headers["tk"] = crypto.enc_header(self._token)
        return headers

    async def _post(
        self, prefix: str, endpoint: str, fields: dict[str, Any] | None = None
    ) -> Any:
        """POST a form-urlencoded request and return the unwrapped ``result``."""
        url = self._base_url + prefix + endpoint
        data = {k: ("" if v is None else str(v)) for k, v in (fields or {}).items()}
        try:
            async with self._session.post(
                url, data=data, headers=self._headers(endpoint)
            ) as resp:
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except ClientError as exc:
            raise VsonConnectionError(str(exc)) from exc

        raw_ret = payload.get("retCode", payload.get("code"))
        try:
            ret = int(raw_ret)
        except (TypeError, ValueError):
            ret = raw_ret
        if ret != RET_OK:
            result = payload.get("result")
            msg = result if isinstance(result, str) else None
            if ret == RET_TOKEN_INVALID:
                raise VsonAuthError(msg or "token invalid")
            raise VsonApiError(ret, msg)
        return payload.get("result")

    async def call_air(self, endpoint: str, **fields: Any) -> Any:
        """Call any ``/api/air/`` endpoint directly (escape hatch)."""
        return await self._post(SVC_AIR, endpoint, fields)

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def authenticate(self) -> None:
        """Log in (unless a restored token still works) and store the session."""
        if self._token:
            try:
                await self.get_devices()
                return
            except VsonAuthError:
                self._token = None  # restored token expired, fall through

        fields = {
            "name": crypto.enc_cred(self._username),
            "pwd": crypto.enc_cred(self._password),
            "accountType": self._account_type,
        }
        result = await self._post(SVC_MEMBER, "login", fields)
        if not isinstance(result, dict) or not result.get("tk"):
            raise VsonAuthError("login succeeded but no token returned")
        self._token = result["tk"]
        raw_uid = result.get("userId")
        try:
            self._user_id = crypto.dec_header(raw_uid) if raw_uid else None
        except Exception:
            self._user_id = raw_uid

    # ── Device discovery ──────────────────────────────────────────────────────

    async def get_devices(self) -> list[dict]:
        """Flattened list of all devices on the account.

        Each item carries at least ``id``, ``mac``, ``type``, ``typeName``,
        ``name`` and ``status`` when the server provides them.
        """
        data = await self._post(SVC_AIR, EP_HOME_PAGE)
        devices: list[dict] = []
        homes = data if isinstance(data, list) else [data]
        for home in homes:
            devices.extend((home or {}).get("equipmentList", []) or [])
        return devices

    # ── WP8621 feeder (family "Bley") ─────────────────────────────────────────

    async def bley_home(self, mac: str) -> dict:
        """Realtime state of a WP8621 feeder (Device8621HomeDataBean)."""
        result = await self._post(SVC_AIR, EP_BLEY_HOMEPAGE, {"mac": mac})
        return result if isinstance(result, dict) else {}

    async def bley_refresh(self, mac: str) -> Any:
        """Ask the device to push fresh data to the cloud."""
        return await self._post(SVC_AIR, EP_BLEY_REFRESH, {"mac": mac})

    async def bley_feed_now(self, mac: str) -> Any:
        """Dispense one portion immediately (base WP8621, by mac)."""
        return await self._post(SVC_AIR, EP_BLEY_FEED_NOW, {"mac": mac})

    async def bley_rotate(self, device_id: str) -> Any:
        """Dispense one portion immediately (WP8621A/8622/8623, by id).

        The classic feeder feeds by triggering the rotor through
        ``queryBleyRotateUrl`` keyed on the equipment id, not ``updateBleyFeed``.
        """
        return await self._post(SVC_AIR, EP_BLEY_ROTATE, {"id": device_id})

    async def bley_set_schedule_enabled(self, device_id: str, enabled: bool) -> Any:
        """Enable or disable the feeder's scheduled feeding."""
        return await self._post(
            SVC_AIR,
            EP_BLEY_FEED_IS_OPEN,
            {"id": device_id, "isOpen": "1" if enabled else "0"},
        )

    async def bley_set_interval(
        self, device_id: str, open_time: str, frequency: int, enabled: bool = True
    ) -> Any:
        """Configure interval-mode feeding."""
        return await self._post(
            SVC_AIR,
            EP_BLEY_INTERVAL,
            {
                "id": device_id,
                "isOpen": "1" if enabled else "0",
                "openTime": open_time,
                "frequency": frequency,
            },
        )
