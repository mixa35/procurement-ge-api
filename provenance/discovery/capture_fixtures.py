"""Headless discovery capture: replays every documented endpoint via tenders_client,
saves raw HTML fixtures to data/discovery/, seeds sample rows into data/discovery.duckdb,
and asserts the agr_docs priming rule works without a browser.

Run:  python provenance/discovery/capture_fixtures.py
"""
from __future__ import annotations

import pathlib
import sys

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tenders_client import ProcurementClient  # noqa: E402
from tenders_client.client import SEARCH_DEFAULTS  # noqa: E402

FIXTURES = ROOT / "data" / "discovery"
DB_PATH = ROOT / "data" / "discovery.duckdb"

# Sample tenders spanning states (override later from user input if needed).
SAMPLES = {"awarded": 656756, "bidding_phase": 681326}
TABS = ["app_main", "app_docs", "app_bids", "agency_docs", "agr_docs"]


def save(name: str, html: str) -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / name
    path.write_text(html, encoding="utf-8")
    return len(html)


def main() -> int:
    client = ProcurementClient()
    log: list[tuple] = []

    # 1. Company lookup (orgtype=1 supplier registry).
    companies = client.lookup_company("თბილისის მუნიციპალიტეტი", orgtype=1)
    print(f"[company_lookup] orgtype=1 -> {len(companies)} rows")

    # 2. Default search (page 1) — capture raw HTML, then parse.
    search_html = client.s.post_search(dict(SEARCH_DEFAULTS))
    save("search_app_default_p1.html", search_html)
    page = client._parse_search(search_html)
    print(f"[search_app] page {page.current_page}/{page.total_pages}, "
          f"{page.total_records} records, {len(page.rows)} rows on page")

    # 3. Each detail tab for each sample tender.
    for label, app_id in SAMPLES.items():
        tabs = client.get_tabs(app_id)
        save(f"application_{app_id}.html", client.s.open_tender(app_id))
        print(f"[{label} {app_id}] tabs: {tabs.actions} (contract={tabs.has_contract})")
        for action in TABS:
            if action == "agr_docs" and not tabs.has_contract:
                continue
            html = client.s.tab(action, app_id)
            n = save(f"{action}_{app_id}.html", html)
            is_lang_err = "Undefined index: lang" in html
            log.append((label, app_id, action, n, is_lang_err))
            flag = " !! LANG ERROR" if is_lang_err else ""
            print(f"    {action:<12} {n:>6} bytes{flag}")

    # 4. Verify agr_docs replays headless with only a lang-initialized session (no priming).
    agr_rows = [r for r in log if r[2] == "agr_docs"]
    assert agr_rows, "no agr_docs captured (need an awarded sample)"
    assert all(not r[4] for r in agr_rows), "agr_docs returned 'Undefined index: lang' -> session not lang-initialized"
    print("[verify] agr_docs replayed headless (lang-initialized session, no priming) -> OK")

    # 5. Seed DuckDB sample tables.
    con = duckdb.connect(str(DB_PATH))
    con.execute("""CREATE TABLE IF NOT EXISTS sample_tenders(
        app_id INTEGER PRIMARY KEY, nat_code TEXT, buyer TEXT, status_text TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS capture_log(
        label TEXT, app_id INTEGER, action TEXT, bytes INTEGER, lang_error BOOLEAN)""")
    for r in page.rows:
        con.execute("INSERT OR REPLACE INTO sample_tenders VALUES (?,?,?,?)",
                    [r.app_id, r.nat_code, r.buyer, r.status_text])
    con.execute("DELETE FROM capture_log")
    con.executemany("INSERT INTO capture_log VALUES (?,?,?,?,?)", log)
    n_tenders = con.execute("SELECT count(*) FROM sample_tenders").fetchone()[0]
    con.close()
    print(f"[duckdb] {DB_PATH.name}: {n_tenders} sample_tenders, {len(log)} capture_log rows")
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
