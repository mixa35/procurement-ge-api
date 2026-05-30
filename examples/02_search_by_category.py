"""02 — Search by procurement CATEGORY (the 'შესყიდვის კატეგორია' dropdown).

Run:  python examples/02_search_by_category.py

This also doubles as the PORTABILITY TEST: run it from a directory OTHER than the
repo after `pip install`. If it resolves the CPV to an app_basecode id and returns
rows, the package is correctly self-contained (it reads no files from disk — the
category map is fetched live from the portal).

Reminder: the category dropdown is the backend param `app_basecode` and wants an
INTERNAL ID (e.g. 45200000 -> 19003), NOT the CPV number. For an EXACT code match
instead, use search_tenders(app_codes="45200000").
"""
import sys

from tenders_client import ProcurementClient

# Georgian output — make stdout UTF-8 even on a cp1252 Windows console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CPV = 45200000  # construction-works category (the "452..." group)


def main() -> None:
    client = ProcurementClient()

    basecode_id = client.resolve_basecode(CPV)
    print(f"CPV {CPV}  ->  app_basecode id {basecode_id}")

    # Category + "winner announced" (app_status=50) + minimum amount 150000 GEL.
    page = client.search_by_category(CPV, app_status=50, app_amount_from=150000)
    print(f"Matching tenders: {page.total_records}  (page {page.current_page}/{page.total_pages})")
    for row in page.rows:
        print(f"  {row.app_id}  {row.nat_code or '—':<14}  {row.buyer or ''}")


if __name__ == "__main__":
    main()
