"""Fixture-backed tests for the core-tab parsers added in the 2026-06-12 audit pass:
app_main, app_bids, agency_docs (result files), agr_docs (contract+payments),
QA-thread collection, parse_qa, and iter_search paging logic. No network calls.
"""
from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DISC = pathlib.Path(__file__).resolve().parent / "fixtures"

sys_import = __import__("sys")
sys_import.path.insert(0, str(ROOT))

from tenders_client.client import ProcurementClient  # noqa: E402
from tenders_client.models import SearchPage, TenderRow  # noqa: E402


def _read(fn: str) -> str:
    return (DISC / fn).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# app_main -> TenderMain
# ---------------------------------------------------------------------------

def test_parse_main_core_fields():
    tm = ProcurementClient._parse_main(_read("app_main_656756.html"), 656756)
    assert tm.nat_code and tm.nat_code.startswith(("NAT", "SPA", "CON", "B2B"))
    assert tm.tender_type and "(" in tm.tender_type      # e.g. ...(NAT)
    assert tm.status_text
    assert tm.status_code in range(10, 150)              # stat<N>.png identity mapping
    assert tm.buyer_name and len(tm.buyer_name) > 3
    assert tm.buyer_org_id and tm.buyer_org_id > 0
    assert tm.bid_deadline and "." in tm.bid_deadline    # DD.MM.YYYY HH:MM
    assert tm.estimated_value and any(ch.isdigit() for ch in tm.estimated_value)
    assert tm.category
    # full label map is preserved (open-ended schema per html_structure.md)
    assert len(tm.fields) >= 8
    assert tm.permalink.endswith("?go=656756&lang=ge")


# ---------------------------------------------------------------------------
# app_bids -> BidsTab
# ---------------------------------------------------------------------------

def test_parse_bids_awarded():
    bt = ProcurementClient._parse_bids(_read("app_bids_656756.html"), 656756)
    assert bt.state == "listed"
    assert len(bt.bids) >= 1
    b = bt.bids[0]
    assert b.bidder_id == 759455            # from ShowBidHistory(656756, 759455)
    assert b.bidder_name == "შპს სამება"
    assert b.org_id == 32327                # ShowProfile
    assert b.last_amount and any(ch.isdigit() for ch in b.last_amount)
    assert b.last_time and "." in b.last_time
    assert b.bid_count == 1
    assert bt.winner is not None and bt.winner.is_winner


def test_parse_bids_open_countdown():
    bt = ProcurementClient._parse_bids(_read("app_bids_681326.html"), 681326)
    assert bt.state == "open"
    assert bt.bids == []


# ---------------------------------------------------------------------------
# agency_docs -> result files
# ---------------------------------------------------------------------------

def test_parse_result_files_awarded():
    files = ProcurementClient._parse_result_files(_read("agency_docs_656756.html"))
    assert len(files) >= 1
    for f in files:
        assert f.mode == "app"
        assert f.file_id and f.file_id.isdigit()
        assert f.filename


def test_parse_result_files_empty_state():
    # empty-state table renders with the 'no documentation' row -> [] (not an error)
    files = ProcurementClient._parse_result_files(_read("agency_docs_681326.html"))
    assert files == []


# ---------------------------------------------------------------------------
# agr_docs -> Contract
# ---------------------------------------------------------------------------

def test_parse_contract_summary():
    c = ProcurementClient._parse_contract(_read("agr_docs_656756.html"), 656756)
    assert c.status_text == "მიმდინარე ხელშეკრულება"
    assert c.supplier_name == "შპს სამება"
    assert c.supplier_org_id == 32327
    assert c.amount_value == 130439.0       # from span.convertme id
    assert c.currency == "GEL"
    assert c.valid_from == "17.12.2025" and c.valid_to == "30.04.2026"
    assert c.contract_date == "17.12.2025"
    assert c.contract_file_id == "638284"   # files.php?mode=contract (no code)
    assert len(c.files) >= 2                # table#last_docs rows
    assert all(f.mode == "app" for f in c.files)


def test_parse_contract_payments():
    c = ProcurementClient._parse_contract(_read("agr_docs_656756.html"), 656756)
    assert c.contract_value_total and "130`439.00" in c.contract_value_total
    assert c.paid_pct == 98
    assert len(c.payments) == 1
    p = c.payments[0]
    assert p.year == "2025" and p.quarter == "4"
    assert p.pay_date == "31.12.2025"
    assert "127`178.03" in p.amount

    # second fixture: multiple payments, older era (no ხელშეკრულების თარიღი is OK there)
    c2 = ProcurementClient._parse_contract(_read("agr_docs_577557.html"), 577557)
    assert len(c2.payments) >= 4
    assert c2.paid_pct == 84
    assert c2.supplier_name == "შპს გეგუ"


# ---------------------------------------------------------------------------
# QA threads in app_docs + parse_qa
# ---------------------------------------------------------------------------

def test_docs_qa_threads_sectioned():
    d = ProcurementClient._parse_docs(_read("app_docs_612033_sectioned.html"), 612033)
    assert len(d.qa_threads) >= 10          # one hst-blk per section (31 in fixture)
    t = d.qa_threads[0]
    assert isinstance(t.chat_id, int) and t.chat_id > 0
    assert any(t.section_id for t in d.qa_threads)


def test_docs_qa_threads_flat_with_questions():
    d = ProcurementClient._parse_docs(_read("app_docs_125688_flat.html"), 125688)
    ids = {t.chat_id for t in d.qa_threads}
    assert {25932, 25710, 25709, 25687} <= ids   # ANS<chat_id> divs in fixture
    with_q = [t for t in d.qa_threads if t.question]
    assert len(with_q) >= 1                      # flat layout carries question text


def test_parse_qa_populated_and_empty():
    msgs = ProcurementClient.parse_qa(_read("show_qa_125688_25710.html"))
    assert len(msgs) >= 1
    assert msgs[0].author and msgs[0].message
    assert ProcurementClient.parse_qa(_read("show_qa_656756_23295158.html")) == []


# ---------------------------------------------------------------------------
# iter_search paging logic (stubbed pages, no network)
# ---------------------------------------------------------------------------

def _page(rows, cur, total):
    return SearchPage(rows=[TenderRow(app_id=r) for r in rows],
                      current_page=cur, total_pages=total, total_records=len(rows))


def test_iter_search_stops_at_last_page():
    c = ProcurementClient.__new__(ProcurementClient)
    pages = [_page([1, 2], 1, 2), _page([3, 4], 2, 2)]
    c.search_tenders = lambda **f: pages[0]
    c.next_page = lambda: pages[1]
    got = [r.app_id for r in c.iter_search()]
    assert got == [1, 2, 3, 4]


def test_iter_search_respects_max_rows():
    c = ProcurementClient.__new__(ProcurementClient)
    c.search_tenders = lambda **f: _page([1, 2, 3, 4], 1, 99)
    c.next_page = lambda: (_ for _ in ()).throw(AssertionError("must not page"))
    got = [r.app_id for r in c.iter_search(max_rows=3)]
    assert got == [1, 2, 3]


def test_iter_search_single_page():
    c = ProcurementClient.__new__(ProcurementClient)
    c.search_tenders = lambda **f: _page([7], 1, 1)
    got = [r.app_id for r in c.iter_search()]
    assert got == [7]
