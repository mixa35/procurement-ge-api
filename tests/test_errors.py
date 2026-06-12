"""Negative tests: error-page detection and markup-drift guards.

No network calls — these feed the documented PHP error signatures (see
docs/endpoint_catalog.yaml) and garbage HTML through the gates that are supposed
to make failures LOUD. Regression guards for the 2026-06-12 audit finding C1
(silent failures everywhere).
"""
from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys_import = __import__("sys")
sys_import.path.insert(0, str(ROOT))

from tenders_client.client import ProcurementClient  # noqa: E402
from tenders_client.errors import (  # noqa: E402
    ParseError,
    PortalError,
    SessionExpiredError,
    TenderNotFoundError,
)
from tenders_client.session import PortalSession  # noqa: E402

# Exact live signatures (captured 2026-05-30 / re-confirmed 2026-06-12)
STALE_BODY = ("[8] Undefined index: lang<br /> File: /var/www/tenders-procurment-public/"
              "public_html/library/controller.php - Line:8")
NOTFOUND_BODY = ("[8] Undefined offset: 0<br /> File: /var/www/tenders-procurment-public/"
                 "public_html/library/controller.php - Line:140  [8]")


# ---------------------------------------------------------------------------
# session-level error sniffing
# ---------------------------------------------------------------------------

def test_detect_error_classifies_signatures():
    assert PortalSession._detect_error(STALE_BODY) == "stale"
    assert PortalSession._detect_error(NOTFOUND_BODY) == "notfound"
    assert PortalSession._detect_error("<div id='app_main'>ok</div>") is None


def test_detect_error_ignores_normal_georgian_content():
    # mentions of 'offset'/'lang' in tender content must not trip the detector
    assert PortalSession._detect_error("Undefined offset in some user text") is None


def test_checked_raises_tender_not_found():
    s = PortalSession.__new__(PortalSession)  # no network init
    with pytest.raises(TenderNotFoundError):
        s._checked(NOTFOUND_BODY, "action=app_main app_id=999999999", retry=lambda: "")


def test_checked_stale_then_recovered(monkeypatch):
    s = PortalSession.__new__(PortalSession)
    monkeypatch.setattr(s, "_init_lang", lambda: None)
    assert s._checked(STALE_BODY, "x", retry=lambda: "<div>fine</div>") == "<div>fine</div>"


def test_checked_stale_twice_raises_session_expired(monkeypatch):
    s = PortalSession.__new__(PortalSession)
    monkeypatch.setattr(s, "_init_lang", lambda: None)
    with pytest.raises(SessionExpiredError):
        s._checked(STALE_BODY, "x", retry=lambda: STALE_BODY)


# ---------------------------------------------------------------------------
# parser-level markup-drift guards (wrapper missing -> ParseError, NOT empty)
# ---------------------------------------------------------------------------

GARBAGE = "<html><body><p>something unexpected</p></body></html>"


def test_parse_search_garbage_raises():
    with pytest.raises(ParseError):
        ProcurementClient._parse_search(GARBAGE)


def test_parse_docs_garbage_raises():
    with pytest.raises(ParseError):
        ProcurementClient._parse_docs(GARBAGE, 0)


def test_parse_docs_empty_wrapper_is_valid_empty():
    d = ProcurementClient._parse_docs("<div id='app_docs'></div>", 0)
    assert d.layout == "empty" and d.files == []


def test_parse_profile_garbage_raises():
    with pytest.raises(ParseError):
        ProcurementClient._parse_profile(GARBAGE, 0)


def test_parse_status_history_garbage_raises():
    with pytest.raises(ParseError):
        ProcurementClient._parse_status_history(GARBAGE)


def test_parse_tech_docs_garbage_raises():
    with pytest.raises(ParseError):
        ProcurementClient._parse_tech_docs(GARBAGE)


def test_parse_bid_history_garbage_raises():
    with pytest.raises(ParseError):
        ProcurementClient._parse_bid_history(GARBAGE)


def test_parse_showapp_rows_garbage_raises():
    with pytest.raises(ParseError):
        ProcurementClient._parse_showapp_rows(GARBAGE, "#today_bids")


# ---------------------------------------------------------------------------
# pagination guard
# ---------------------------------------------------------------------------

def test_pagination_before_search_raises():
    c = ProcurementClient.__new__(ProcurementClient)  # no network init
    with pytest.raises(PortalError):
        c.next_page()
    with pytest.raises(PortalError):
        c.goto_page(2)
