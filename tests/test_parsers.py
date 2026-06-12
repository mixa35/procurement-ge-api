"""Fixture-backed parser tests.

All tests parse HTML from tests/fixtures/ — no network calls.
Fixtures are a curated subset of public tender pages captured 2026-05-28/29
against the live portal, committed so `pytest` is green on a fresh clone.
"""
from __future__ import annotations

import pathlib
import re

import pytest
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
DISC = pathlib.Path(__file__).resolve().parent / "fixtures"

sys_import = __import__("sys")
sys_import.path.insert(0, str(ROOT))

from tenders_client.client import ProcurementClient, _enrich_row  # noqa: E402
from tenders_client.models import TenderRow  # noqa: E402
from tenders_client.session import PortalSession  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def soup(filename: str) -> BeautifulSoup:
    return BeautifulSoup((DISC / filename).read_text(encoding="utf-8"), "lxml")


# ---------------------------------------------------------------------------
# search results parser
# ---------------------------------------------------------------------------

def test_search_parser_returns_rows():
    html = (DISC / "search_app_default_p1.html").read_text(encoding="utf-8")
    page = ProcurementClient._parse_search(html)
    assert page.total_records is not None and page.total_records > 0
    assert page.total_pages is not None and page.total_pages > 0
    assert page.current_page == 1
    assert len(page.rows) > 0


def test_search_parser_row_fields():
    html = (DISC / "search_app_default_p1.html").read_text(encoding="utf-8")
    page = ProcurementClient._parse_search(html)
    row = page.rows[0]
    assert isinstance(row.app_id, int) and row.app_id > 0
    # NAT/B2B code — at least one row should have it
    codes = [r.nat_code for r in page.rows if r.nat_code]
    assert len(codes) > 0, "no rows had a nat_code"
    # buyer — at least one row should have it
    buyers = [r.buyer for r in page.rows if r.buyer]
    assert len(buyers) > 0, "no rows had a buyer"
    # category & estimated_value — the search HTML carries both; the model promises
    # them, so _enrich_row must populate them (regression guard for the audit gap)
    cats = [r.category for r in page.rows if r.category]
    assert len(cats) > 0, "no rows had a category"
    vals = [r.estimated_value for r in page.rows if r.estimated_value]
    assert len(vals) > 0, "no rows had an estimated_value"


# ---------------------------------------------------------------------------
# app_bids — awarded state (has bidder table)
# ---------------------------------------------------------------------------

def test_app_bids_awarded_has_bidder_table():
    s = soup("app_bids_656756.html")
    assert s.select_one("#app_bids") is not None
    # No TenderCountdown in awarded state
    assert s.select_one("#TenderCountdown") is None
    rows = s.select("#app_bids table.ktable tbody tr[id]")
    assert len(rows) >= 1, "expected at least one bidder row"


def test_app_bids_awarded_row_structure():
    s = soup("app_bids_656756.html")
    row = s.select_one("#app_bids table.ktable tbody tr[id]")
    assert row is not None
    row_id = row.get("id", "")
    # Row id format: B<app_id><bidder_id>
    assert row_id.startswith("B"), f"unexpected row id format: {row_id!r}"
    # Winning bidder row has activebid1 class on cells
    cells = row.find_all("td")
    assert any("activebid1" in (c.get("class") or []) for c in cells), \
        "expected winner row to have activebid1 class"
    # Amount in strong tag (first td)
    strong = row.select_one("strong")
    assert strong is not None
    amount_text = strong.get_text(strip=True).replace("`", "")
    assert float(amount_text) > 0


# ---------------------------------------------------------------------------
# app_bids — bidding phase (live countdown, no bidder table)
# ---------------------------------------------------------------------------

def test_app_bids_bidding_phase_has_countdown():
    s = soup("app_bids_681326.html")
    assert s.select_one("#app_bids") is not None
    assert s.select_one("#TenderCountdown") is not None, \
        "bidding-phase tender should have #TenderCountdown"
    # No completed bidder rows (no tr[id] in table)
    bidder_rows = s.select("#app_bids table.ktable tbody tr[id]")
    assert len(bidder_rows) == 0, "bidding phase should not have finalised bidder rows"


# ---------------------------------------------------------------------------
# agency_docs — results tab
# ---------------------------------------------------------------------------

def test_agency_docs_awarded_has_file_rows():
    s = soup("agency_docs_656756.html")
    assert s.select_one("#agency_docs") is not None
    rows = s.select("table#reports tbody tr[id]")
    assert len(rows) > 0, "awarded tender should have result file rows"
    # Row id format: <file_id>.<code>.<app_id>
    for tr in rows:
        parts = tr.get("id", "").split(".")
        assert len(parts) == 3, f"unexpected row id format: {tr.get('id')!r}"
    # All current-file rows have a files.php link with mode=app
    anchors = s.select("table#reports td.obsolete0 a")
    assert len(anchors) > 0
    for a in anchors:
        href = a.get("href", "")
        assert "mode=app" in href, f"expected mode=app in href: {href!r}"


def test_agency_docs_empty_state():
    s = soup("agency_docs_681326.html")
    assert s.select_one("#agency_docs") is not None
    text = s.get_text(" ", strip=True)
    assert "დოკუმენტაცია მიმაგრებული არ არის" in text, \
        "empty agency_docs should show 'no documentation attached' message"


# ---------------------------------------------------------------------------
# app_main — tender overview
# ---------------------------------------------------------------------------

def test_app_main_key_fields():
    s = soup("app_main_656756.html")
    assert s.select_one("#app_main") is not None
    text = s.get_text(" ", strip=True)
    assert "განცხადების ნომერი" in text, "NAT code label missing"
    assert "წინადადებების მიღება მთავრდება" in text, "bid deadline label missing"
    # NAT code is in a <strong> tag
    nat_strong = s.select_one("#print_area strong")
    assert nat_strong is not None
    nat = nat_strong.get_text(strip=True)
    assert nat.startswith(("NAT", "B2B", "SPA", "CON")), f"unexpected NAT code: {nat!r}"


def test_app_main_buyer_has_show_profile():
    s = soup("app_main_656756.html")
    # Buyer link has ShowProfile(org_id) in onclick
    links = s.select("#app_main a[onclick*='ShowProfile']")
    assert len(links) >= 1, "expected ShowProfile link for buyer"
    onclick = links[0].get("onclick", "")
    m = re.search(r"ShowProfile\((\d+)\)", onclick)
    assert m is not None
    assert int(m.group(1)) > 0


# ---------------------------------------------------------------------------
# lastevents feed
# ---------------------------------------------------------------------------

def test_lastevents_has_five_rows():
    s = soup("lastevents.html")
    rows = s.select("table#lastevents tbody tr")
    assert len(rows) == 5, f"expected 5 lastevents rows, got {len(rows)}"


def test_lastevents_row_structure():
    s = soup("lastevents.html")
    rows = s.select("table#lastevents tbody tr")
    for tr in rows:
        onclick = tr.get("onclick", "")
        m = re.search(r"ShowApp\((\d+)", onclick)
        assert m is not None, f"missing ShowApp in onclick: {onclick!r}"
        assert int(m.group(1)) > 0
        # NAT code
        strong = tr.select_one("strong")
        assert strong is not None
        assert strong.get_text(strip=True).startswith("NAT"), \
            f"expected NAT code: {strong.get_text(strip=True)!r}"
        # Status text
        status_p = tr.select_one("p.status")
        assert status_p is not None
        timestamp = status_p.select_one("span.color-1")
        assert timestamp is not None


# ---------------------------------------------------------------------------
# profile (action=profile) — endpoints added 2026-05-29
# ---------------------------------------------------------------------------

def _read(fn: str) -> str:
    return (DISC / fn).read_text(encoding="utf-8")


def test_profile_buyer_fields():
    prof = ProcurementClient._parse_profile(_read("profile_buyer.html"), 42485)
    assert prof.role == "შემსყიდველი"
    assert prof.is_buyer is True
    assert prof.name and len(prof.name) > 3
    assert prof.id_code and prof.id_code.isdigit()
    assert prof.email and "@" in prof.email


def test_profile_supplier_role():
    prof = ProcurementClient._parse_profile(_read("profile_supplier.html"), 32327)
    assert prof.role == "მიმწოდებელი"
    assert prof.is_buyer is False


# ---------------------------------------------------------------------------
# app_statushistory (action=app_statushistory)
# ---------------------------------------------------------------------------

def test_status_history_rows():
    events = ProcurementClient._parse_status_history(_read("app_statushistory_656756.html"))
    assert len(events) >= 2
    # newest first; each row has a DD.MM.YYYY HH:MM timestamp + non-empty status
    assert re.match(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", events[0].timestamp)
    assert all(e.status for e in events)
    # contains a status that is NOT in the 11-value app_status search enum
    labels = {e.status for e in events}
    assert "დამატებითი რაუნდები დასრულებულია" in labels


# ---------------------------------------------------------------------------
# app_tdocs (action=app_tdocs)
# ---------------------------------------------------------------------------

def test_tech_docs_rows_use_tdoc_mode():
    docs = ProcurementClient._parse_tech_docs(_read("app_tdocs_656756.html"))
    assert len(docs) >= 1
    hrefs = [d.href for d in docs if d.href]
    assert hrefs and all("mode=tdoc" in h for h in hrefs)
    assert all(d.bidder for d in docs)


# ---------------------------------------------------------------------------
# view_bid (action=view_bid)
# ---------------------------------------------------------------------------

def test_bid_history_amount_parses():
    entries = ProcurementClient._parse_bid_history(_read("view_bid_656756_759455.html"))
    assert len(entries) >= 1
    assert entries[0].amount_float and entries[0].amount_float > 0
    assert re.match(r"\d{2}\.\d{2}\.\d{4}", entries[0].datetime)


# ---------------------------------------------------------------------------
# today_bids (action=today_bids)
# ---------------------------------------------------------------------------

def test_today_bids_rows():
    rows = ProcurementClient._parse_showapp_rows(_read("today_bids.html"), "#today_bids")
    assert len(rows) > 5, "today_bids should be a full list, not capped at 5"
    r = rows[0]
    assert isinstance(r.app_id, int) and r.app_id > 0
    assert r.nat_code  # first <strong> = tender code
    buyers = [x.buyer for x in rows if x.buyer]
    assert len(buyers) > 0


# ---------------------------------------------------------------------------
# files.php mode handling (session helper)
# ---------------------------------------------------------------------------

def test_file_url_modes():
    s = PortalSession.__new__(PortalSession)  # no network init
    assert "mode=que" in PortalSession.file_url(s, "111", "222")
    assert PortalSession.file_url(s, "111", "222", mode="tdoc").endswith("mode=tdoc&file=111&code=222")
    # contract omits the code param
    url = PortalSession.file_url(s, "638284", None, mode="contract")
    assert url.endswith("mode=contract&file=638284")
    assert "code=" not in url


def test_permalink():
    assert PortalSession.permalink(656756) == \
        "https://tenders.procurement.gov.ge/public/?go=656756&lang=ge"


# ---------------------------------------------------------------------------
# show_qa (action=show_qa) — clarification Q&A thread
# ---------------------------------------------------------------------------

def test_show_qa_empty_state():
    html = _read("show_qa_656756_23295158.html")
    assert ProcurementClient.qa_is_empty(html) is True


def test_show_qa_empty_detector_negative():
    # a thread with content should NOT be flagged empty
    assert ProcurementClient.qa_is_empty("<p>ვ. გიორგაძე: პასუხი აქ</p>") is False


def test_show_qa_populated_thread():
    html = _read("show_qa_125688_25710.html")
    assert ProcurementClient.qa_is_empty(html) is False
    # populated answer block: A type3 with author + message
    s = BeautifulSoup(html, "lxml")
    assert s.select_one("p.author") is not None
    assert s.select_one("p.chatmessgase") is not None


# ---------------------------------------------------------------------------
# app_docs — TWO layouts (sectioned modern vs flat legacy/non-NAT-SPA-CON)
# ---------------------------------------------------------------------------

def test_app_docs_sectioned_layout():
    d = ProcurementClient._parse_docs(_read("app_docs_612033_sectioned.html"), 612033)
    assert d.layout == "sectioned"
    assert len(d.files) > 0
    # sectioned files use mode=que and carry a section id
    assert all(f.mode == "que" for f in d.files if f.mode)
    assert any(f.section_id == "que150" for f in d.files)
    # cost estimates come from section 1.3
    assert len(d.cost_estimate_files) >= 1


def test_app_docs_flat_layout_legacy():
    d = ProcurementClient._parse_docs(_read("app_docs_125688_flat.html"), 125688)
    assert d.layout == "flat"
    assert len(d.files) > 0
    # flat files use mode=app and have NO section id
    assert all(f.mode == "app" for f in d.files if f.mode)
    assert all(f.section_id is None for f in d.files)
    # a cost-estimate xlsx is still discoverable in the flat list
    assert len(d.cost_estimate_files) >= 1
    # flat layout respects currentness: the fixture has an obsolete1 row that must
    # be flagged is_current=False (regression guard — it used to default to True)
    assert any(not f.is_current for f in d.files), "obsolete1 file not flagged"
    assert any(f.is_current for f in d.files)


def test_app_docs_flat_layout_b2b_cost_estimate():
    d = ProcurementClient._parse_docs(_read("app_docs_687393_flat_b2b.html"), 687393)
    assert d.layout == "flat"
    # B2B price table is named "ფასების ცხრილი" (not "ხარჯთაღრიცხვა") — heuristic must still catch it
    ce = d.cost_estimate_files
    assert any((f.filename or "").lower().endswith(".xlsx") for f in ce)


# ---------------------------------------------------------------------------
# authoritative scraped filter map (docs/search_filters.json) + category map
# ---------------------------------------------------------------------------

def test_search_filters_artifact_invariants():
    import json
    p = ROOT / "docs" / "search_filters.json"
    if not p.exists():
        pytest.skip("search_filters.json not generated")
    filters = {f["param"]: f for f in json.loads(p.read_text(encoding="utf-8"))["filters"]}
    # all 22 documented params present, with Georgian labels on the non-hidden ones
    assert filters["app_status"]["label"] == "შესყიდვის სტატუსი"
    assert filters["app_basecode"]["label"] == "შესყიდვის კატეგორია"
    # option maps carry internal id + georgian name
    statuses = {o["id"]: o["name"] for o in filters["app_status"]["options"]}
    assert statuses["140"] == "ხელშეკრულება დადებულია"
    assert statuses["130"] == "მიმდინარეობს ხელშეკრულების მომზადება"


def test_cpv_basecode_map_artifact():
    import json
    p = ROOT / "docs" / "cpv_basecode_map.json"
    if not p.exists():
        pytest.skip("cpv_basecode_map.json not generated")
    m = json.loads(p.read_text(encoding="utf-8"))
    # 45200000 (broad construction category) resolves to internal id 19003
    rev = {v["cpv"]: k for k, v in m.items()}
    assert rev.get("45200000") == "19003"
