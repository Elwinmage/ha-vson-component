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

# GitHub repository, used to pre-fill a "new issue" link for unknown devices.
GITHUB_REPO = "Elwinmage/ha-vson-component"

# ── Repairs ───────────────────────────────────────────────────────────────────
# Raised once per unknown device "type" so a new family can be mapped.
ISSUE_UNKNOWN_DEVICE = "unknown_device"

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
# The VSON auto-feeders are all driven by the "Bley" endpoints, but they split
# into two sub-families by how a manual feed is triggered (confirmed from the
# app's per-model view-models):
#   • base WP8621  (types 8621 / 86211) → updateBleyFeed(mac)
#   • WP8621A/8622 (types 86221 / 8622 / 8623) → queryBleyRotateUrl(id)
# Type codes map to the app's Constant.* (T1=8621, Y1=86211, V1=86221, U1=8622,
# X1=8623). Realtime data (queryBleyHomepage by mac) and settings
# (queryBleyEquipment by id) are shared by all of them.
TYPE_WP8621 = "8621"  # Constant.T1
TYPE_WP8621_ALT = "86211"  # Constant.Y1
TYPE_WP8621A = "86221"  # Constant.V1 — "Intelligent fish feeder (classic)"
TYPE_WP8622 = "8622"  # Constant.U1
TYPE_WP8623 = "8623"  # Constant.X1

# Manual-feed strategies.
FEED_MODE_FEED_MAC = "feed_mac"  # updateBleyFeed(mac)
FEED_MODE_ROTATE_ID = "rotate_id"  # queryBleyRotateUrl(id)

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
EP_BLEY_ROTATE = "queryBleyRotateUrl"  # field: id -> manual feed (8622/86221/8623)
