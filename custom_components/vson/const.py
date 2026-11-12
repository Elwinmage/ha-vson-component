"""Constants for the VSON integration.

Protocol reverse-engineered from the official VSON Android app. Everything is
plain HTTPS POST (form-urlencoded) against apis.myvsoncloud.com:16082, split
into three micro-services. See client.py for the request details.
"""

from __future__ import annotations

import logging
from datetime import timedelta

_LOGGER = logging.getLogger(__package__)

# ── Integration identity ──────────────────────────────────────────────────────
DOMAIN = "vson"
MANUFACTURER = "VSON"

# ── Cloud endpoints ───────────────────────────────────────────────────────────
# Production host (Constant.f6441d in the app). The app also ships a test host
# (ts.vson.com.cn:26082) which users can set via the advanced "server" option.
DEFAULT_BASE_URL = "https://apis.myvsoncloud.com:16082/"

# Micro-service path prefixes.
SVC_MEMBER = "vc-airmas-ws-1.0.2/api/m/"  # auth (login, register, logout)
SVC_COMMON = "vc-css-ws-1.0.2/api/all/"  # common (country codes, SMS codes)
SVC_AIR = "vc-air-ws-1.0.2/api/air/"  # devices (home, status, control)

# Response envelope: {"retCode": <int|str>, "result": <payload>}. 0 == success.
RET_OK = 0
RET_TOKEN_INVALID = 1003
RET_ACCOUNT_UNKNOWN = 1007
RET_WRONG_PASSWORD = 1008

# ── Static request headers (app interceptor network/j.java) ───────────────────
# "md" is the app's own self-identifier, not the controlled device.
HDR_MD = "WP2810"
HDR_PID = "cup033"
HDR_OST = "2"  # Android
HDR_APT = "108"
HDR_CM = "1"
HDR_APV_DEFAULT = "1.0.8"
# Plaintext values behind the app's constant encrypted headers (proven).
HDR_BH_PLAIN = "VSON"
HDR_MAC_PLAIN = "m123456"
HDR_UUID_PLAIN = "u123456"

# ── Login account types ───────────────────────────────────────────────────────
ACCOUNT_TYPE_MOBILE = "101"
ACCOUNT_TYPE_EMAIL = "102"

# ── Config entry keys ─────────────────────────────────────────────────────────
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ACCOUNT_TYPE = "account_type"
CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TOKEN = "token"  # raw login token, persisted to skip re-login

# ── Update interval ───────────────────────────────────────────────────────────
DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 600
UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

# ── Device family type codes (field "type" in queryHomePage) ──────────────────
# The WP8621 auto-feeder (all variants N/E/H/F/B/P/A/C) reports type "8621"
# (or "86211") and is driven by the "Bley" endpoints.
TYPE_WP8621 = "8621"
TYPE_WP8621_ALT = "86211"

# ── Air endpoints for the WP8621 feeder family ("Bley") ───────────────────────
EP_HOME_PAGE = "queryHomePage"  # no field -> all devices grouped by home
EP_BLEY_HOMEPAGE = "queryBleyHomepage"  # field: mac -> realtime home data
EP_BLEY_EQUIPMENT = "queryBleyEquipment"  # field: id -> settings / schedules
EP_BLEY_REFRESH = "queryBleyRefresh"  # field: mac -> push fresh data
EP_BLEY_FEED_NOW = "updateBleyFeed"  # field: mac -> one manual feed
EP_BLEY_FEED_RECORDS = "queryBleyFeedRecords"  # fields: page, mac
EP_BLEY_FEED_IS_OPEN = "updateBleyFeedIsOpen"  # fields: id, isOpen
EP_BLEY_INTERVAL = "updateBleyInterval"  # map: id, isOpen, openTime, frequency
EP_BLEY_PUMP = "updateBleyPump"  # fields: mac, isOpen
EP_BLEY_LIGHT_IS_OPEN = "updateBleyLightIsOpen"  # fields: id, isOpen, type
