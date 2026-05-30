"""Re-verify app_main and app_docs fixtures; capture lastevents.

Saves fresh HTML to data/discovery/, prints a diff summary, and logs
verification results to data/discovery.duckdb.

Run:  python provenance/discovery/reverify_and_lastevents.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tenders_client import ProcurementClient  # noqa: E402

FIXTURES = ROOT / "data" / "discovery"

# All 4 sample app_ids across states.
SAMPLES = {
    "awarded":          656756,
    "bidding_phase":    681326,
    "failed_contract":  681857,
    "did_not_happen":   685227,
}
REVERIFY = ["app_main", "app_docs"]


def save(name: str, html: str) -> pathlib.Path:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    p = FIXTURES / name
    p.write_text(html, encoding="utf-8")
    return p


def check_html(html: str, checks: list[tuple[str, str]]) -> list[str]:
    """Return list of failed check descriptions."""
    fails = []
    for desc, needle in checks:
        if needle not in html:
            fails.append(f"  MISSING: {desc!r} (needle={needle!r})")
    return fails


def main() -> int:
    client = ProcurementClient()

    # --- 1. Re-verify app_main and app_docs --------------------------------
    print("=" * 60)
    print("RE-VERIFY: app_main and app_docs")
    print("=" * 60)

    app_main_checks = [
        ("NAT code label",          "განცხადების ნომერი"),
        ("bid deadline label",       "წინადადებების მიღება"),
        ("procurement type label",   "შესყიდვის ტიპი"),
    ]
    app_docs_checks = [
        ("app_docs wrapper",         'id="app_docs"'),
        ("section 1.3 estimate",     'id="que150"'),
        ("file anchor mode=que",     "mode=que"),
    ]

    all_ok = True
    for label, app_id in SAMPLES.items():
        print(f"\n[{label} / app_id={app_id}]")
        for action in REVERIFY:
            html = client.s.tab(action, app_id)
            p = save(f"{action}_{app_id}.html", html)
            checks = app_main_checks if action == "app_main" else app_docs_checks
            fails = check_html(html, checks)
            status = "OK" if not fails else "FAIL"
            print(f"  {action:<12} {len(html):>7} bytes  [{status}]  -> {p.name}")
            for f in fails:
                print(f)
                all_ok = False

    print()
    if all_ok:
        print("app_main + app_docs: all checks passed — ready to mark as documented.")
    else:
        print("Some checks FAILED — review failures above before marking as documented.")

    # --- 2. Capture lastevents ---------------------------------------------
    print()
    print("=" * 60)
    print("CAPTURE: lastevents")
    print("=" * 60)

    le_html = client.s.get("lastevents")
    p = save("lastevents.html", le_html)
    print(f"  lastevents  {len(le_html):>7} bytes  -> {p.name}")

    # Quick structural probe.
    probes = [
        ("NAT code present",        "NAT"),
        ("table or list present",   "<table"),
        ("empty state",             "ჩანაწერები არ არის"),
        ("date pattern",            ".202"),     # year suffix common to all dates
    ]
    print("\n  Structure probes:")
    for desc, needle in probes:
        found = needle in le_html
        print(f"    {'YES' if found else 'no ':3} — {desc}")

    # Print first 1200 chars so we can eyeball the shape.
    print("\n  --- first 1200 chars of response ---")
    print(le_html[:1200])
    print("  --- end preview ---")

    print("\nDONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
