"""Smoke tests for constants and endpoint wiring."""

from __future__ import annotations

from custom_components.vson import const


def test_domain():
    assert const.DOMAIN == "vson"


def test_base_url_is_production_host():
    assert "myvsoncloud.com" in const.DEFAULT_BASE_URL


def test_feeder_endpoints_present():
    assert const.EP_BLEY_FEED_NOW == "updateBleyFeed"
    assert const.EP_BLEY_HOMEPAGE == "queryBleyHomepage"
    assert const.EP_HOME_PAGE == "queryHomePage"


def test_scan_interval_bounds():
    assert (
        const.MIN_SCAN_INTERVAL
        <= const.DEFAULT_SCAN_INTERVAL
        <= const.MAX_SCAN_INTERVAL
    )
