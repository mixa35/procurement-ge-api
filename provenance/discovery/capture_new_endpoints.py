"""Capture fixtures for the endpoints discovered in the 2026-05-29 audit pass.

New / newly-shaped endpoints:
  today_bids, profile, app_statushistory, app_tdocs, view_bid, cpv_search.

Also re-runs the stat<N>.png -> app_status icon mapping (medium-priority handoff
item) by searching once per app_status value and recording the icon shown.

All requests go through PortalSession (throttled 1.5s, SPALITE cookie, UTF-8).

Run:  python provenance/discovery/capture_new_endpoints.py
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tenders_client import ProcurementClient  # noqa: E402
from tenders_client.client import SEARCH_DEFAULTS  # noqa: E402
from tenders_client.session import BASE  # noqa: E402

FIXTURES = ROOT / "data" / "discovery"

# Sample tender + actors (from existing fixtures / app_bids winner).
APP_ID = 656756
BUYER_ORG_ID = 42485      # ShowProfile(42485) in app_main_656756
SUPPLIER_ORG_ID = 32327   # ShowProfile(32327) in app_bids_656756 (winner)
BIDDER_ID = 759455        # B656756759455 winner bidder id

APP_STATUS_VALUES = [10, 20, 30, 40, 50, 100, 110, 120, 130, 140]


def save(name: str, html: str) -> pathlib.Path:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    p = FIXTURES / name
    p.write_text(html, encoding="utf-8")
    print(f"  saved {p.name:<40} {len(html):>8} bytes")
    return p


def main() -> int:
    c = ProcurementClient()

    print("=" * 64)
    print("CAPTURE: newly discovered endpoints")
    print("=" * 64)

    # 1. today_bids (no params)
    save("today_bids.html", c.s.get("today_bids"))

    # 2. profile — buyer and supplier
    save("profile_buyer.html", c.s.get("profile", org_id=BUYER_ORG_ID, isdialog=""))
    save("profile_supplier.html", c.s.get("profile", org_id=SUPPLIER_ORG_ID, isdialog=""))

    # 3. app_statushistory
    save(f"app_statushistory_{APP_ID}.html",
         c.s.get("app_statushistory", app_id=APP_ID))

    # 4. app_tdocs
    save(f"app_tdocs_{APP_ID}.html", c.s.get("app_tdocs", app_id=APP_ID))

    # 5. view_bid (bid history for a bidder)
    save(f"view_bid_{APP_ID}_{BIDDER_ID}.html",
         c.s.get("view_bid", app_id=APP_ID, bid_id=BIDDER_ID))

    # 6. cpv_search.php autocomplete (different path, not controller.php)
    cpv_url = f"{BASE}/library/cpv/cpv_search.php"
    cpv_html = c.s._raw_get(cpv_url, {"q": "45000000"}).text
    save("cpv_search_sample.html", cpv_html)

    # --- stat<N>.png -> app_status icon mapping --------------------------
    print()
    print("=" * 64)
    print("MAP: stat<N>.png icon -> app_status filter value")
    print("=" * 64)
    icon_re = re.compile(r"statuses/stat(\d+)\.png")
    mapping: dict[int, list[str]] = {}
    for status in APP_STATUS_VALUES:
        body = dict(SEARCH_DEFAULTS)
        body["app_status"] = str(status)
        html = c.s.post_search(body)
        icons = sorted(set(icon_re.findall(html)))
        mapping[status] = icons
        print(f"  app_status={status:<4} -> stat icons seen: {icons}")
    save("stat_icon_mapping.txt",
         "\n".join(f"app_status={k}\tstat_icons={v}" for k, v in mapping.items()))

    print("\nDONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
