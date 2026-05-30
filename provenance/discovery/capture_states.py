"""Capture tender fixtures for specific search-filter states.

Finds the first tender matching each filter, fetches every present detail tab, saves raw
HTML to data/discovery/, and appends to data/discovery.duckdb (sample_tenders + capture_log).

Run:  python provenance/discovery/capture_states.py
"""
from __future__ import annotations

import pathlib
import sys

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tenders_client import ProcurementClient  # noqa: E402

FIXTURES = ROOT / "data" / "discovery"
DB_PATH = ROOT / "data" / "discovery.duckdb"
TABS = ["app_main", "app_docs", "app_bids", "agency_docs", "agr_docs"]

# (label, search filters) — see api_reference.md enums.
STATES = [
    ("failed_contract", {"app_agr_status": 30}),   # შეუსრულებელი ხელშეკრულება
    ("did_not_happen", {"app_status": 110}),        # არ შედგა (no contract expected)
]


def save(name: str, html: str) -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / name).write_text(html, encoding="utf-8")
    return len(html)


def main() -> int:
    client = ProcurementClient()
    con = duckdb.connect(str(DB_PATH))
    con.execute("""CREATE TABLE IF NOT EXISTS sample_tenders(
        app_id INTEGER PRIMARY KEY, nat_code TEXT, buyer TEXT, status_text TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS capture_log(
        label TEXT, app_id INTEGER, action TEXT, bytes INTEGER, lang_error BOOLEAN)""")

    for label, filt in STATES:
        page = client.search_tenders(**filt)
        print(f"\n[{label}] filter={filt} -> {page.total_records} records, "
              f"{len(page.rows)} on page 1")
        if not page.rows:
            print(f"    no rows for {label}; skipping")
            continue
        row = page.rows[0]
        app_id = row.app_id
        con.execute("INSERT OR REPLACE INTO sample_tenders VALUES (?,?,?,?)",
                    [row.app_id, row.nat_code, row.buyer, row.status_text])
        tabs = client.get_tabs(app_id)
        save(f"application_{app_id}.html", client.s.open_tender(app_id))
        print(f"    app_id={app_id} nat={row.nat_code} tabs={tabs.actions} "
              f"(contract={tabs.has_contract})")
        con.execute("DELETE FROM capture_log WHERE label = ?", [label])
        for action in TABS:
            if action == "agr_docs" and not tabs.has_contract:
                continue
            html = client.s.tab(action, app_id)
            n = save(f"{action}_{app_id}.html", html)
            lang_err = "Undefined index: lang" in html
            con.execute("INSERT INTO capture_log VALUES (?,?,?,?,?)",
                        [label, app_id, action, n, lang_err])
            print(f"    {action:<12} {n:>6} bytes{' !! LANG ERROR' if lang_err else ''}")

    n_tenders = con.execute("SELECT count(*) FROM sample_tenders").fetchone()[0]
    n_log = con.execute("SELECT count(*) FROM capture_log").fetchone()[0]
    con.close()
    print(f"\n[duckdb] {DB_PATH.name}: {n_tenders} sample_tenders, {n_log} capture_log rows")
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
