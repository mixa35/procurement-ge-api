"""04 — Feeds and company lookup.

Run:  python examples/04_feeds_and_lookup.py

  * today_bids — every tender whose bid deadline expires today.
  * company lookup — supplier/buyer autocomplete (orgtype: 1=supplier, 3=buyer).
"""
import sys

from tenders_client import ProcurementClient

# Georgian output — make stdout UTF-8 even on a cp1252 Windows console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    client = ProcurementClient()

    today = client.get_today_bids()
    print(f"Tenders closing today: {len(today)}")
    for row in today[:5]:
        print(f"  {row.app_id}  {row.nat_code or '—':<14}  {row.buyer or ''}")

    print()
    companies = client.lookup_company("შპს", orgtype=1)  # supplier registry
    print(f"Supplier matches for 'შპს': {len(companies)} (showing 5)")
    for c in companies[:5]:
        print(f"  {c.internal_id}  {c.reg_code:<12}  {c.name}")


if __name__ == "__main__":
    main()
