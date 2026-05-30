"""01 — Quickstart: open a session and run a plain search.

Run:  python examples/01_quickstart.py

The client acquires the SPALITE session cookie automatically and throttles every
request to 1.5s. No credentials needed — this is all public data.
"""
import sys

from tenders_client import ProcurementClient

# Georgian output — make stdout UTF-8 even on a cp1252 Windows console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    client = ProcurementClient()

    # A default search (no filters) — most recent tenders, 4 rows per page.
    page = client.search_tenders()
    print(f"Total records: {page.total_records}  (page {page.current_page}/{page.total_pages})")
    for row in page.rows:
        print(f"  {row.app_id}  {row.nat_code or '—':<14}  {row.buyer or ''}")


if __name__ == "__main__":
    main()
