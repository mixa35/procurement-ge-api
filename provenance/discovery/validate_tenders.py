"""Validate 10 specific tenders against the documented rules (adversarial).

For each tender it records PREDICTED vs ACTUAL behaviour and diffs them, so real
exceptions surface instead of being rubber-stamped. Outputs:
  - docs/gallery/validation_results.json   (one source of truth for the gallery)
  - data/discovery/<action>_<app_id>.html   (raw fixtures)
and prints a per-tender + per-type summary.

Rules checked (from docs/endpoint_catalog.yaml + api_reference.md):
  * app_docs layout: type prefix NAT/SPA/CON -> sectioned (mode=que), else flat (mode=app).
    Era caveat: OLD NAT/SPA/CON may be flat -> not an exception, flagged with reg date.
  * agr_docs tab present  <=>  a contract was ever signed (status reaches 130/140).
  * stat<N>.png icon number == app_status enum value (1:1).
  * agency_docs uses mode=app; empty state string.
Run:  python provenance/discovery/validate_tenders.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup  # noqa: E402

from tenders_client import ProcurementClient  # noqa: E402

APP_IDS = [
    # 10 awarded / active-contract (app_status=140) — span 2018-2026; 5 tabs incl. agr_docs
    577557, 596328, 399052, 302010, 274057, 678297, 604900, 642243, 409776, 464772,
    # 3 contract-being-prepared (app_status=130) — 4 tabs, NO agr_docs yet
    686258, 687576, 687581,
    # 3 announced (app_status=10) — earliest stage, 4 tabs, NO agr_docs (no contract yet)
    688985, 688150, 688168,
]

SECTIONED_TYPES = {"NAT", "SPA", "CON"}
GALLERY = ROOT / "docs" / "gallery"
FIX = ROOT / "data" / "discovery"

# app_status enum (value -> Georgian label) from api_reference.md
STATUS_ENUM = {
    10: "გამოცხადებულია", 20: "წინადადებების მიღება დაწყებულია",
    30: "წინადადებების მიღება დასრულებულია", 40: "შერჩევა/შეფასება",
    50: "გამარჯვებული გამოვლენილია", 100: "დასრულებულია უარყოფითი შედეგით",
    110: "არ შედგა", 120: "შეწყვეტილია",
    130: "მიმდინარეობს ხელშეკრულების მომზადება", 140: "ხელშეკრულება დადებულია",
}


def save(action: str, app_id: int, html: str) -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / f"{action}_{app_id}.html").write_text(html, encoding="utf-8")


def parse_main(html: str) -> dict:
    s = BeautifulSoup(html, "lxml")
    out: dict = {"fields": {}}
    for tr in s.select("#print_area table tbody tr, #app_main table tbody tr"):
        tds = tr.find_all("td")
        if len(tds) == 2:
            out["fields"][tds[0].get_text(" ", strip=True)] = tds[1].get_text(" ", strip=True)
    strong = s.select_one("#print_area strong")
    out["nat_code"] = strong.get_text(strip=True) if strong else None
    icon = s.select_one("#app_main img[src*='stat'], #print_area img[src*='stat']")
    m = re.search(r"stat(\d+)\.png", icon.get("src", "")) if icon else None
    out["stat_icon"] = int(m.group(1)) if m else None
    out["reg_date"] = out["fields"].get("შესყიდვის გამოცხადების თარიღი")
    out["status_label"] = out["fields"].get("შესყიდვის სტატუსი")
    out["type_label"] = out["fields"].get("შესყიდვის ტიპი")
    return out


def main() -> int:
    c = ProcurementClient()
    results = []
    for app_id in APP_IDS:
        rec: dict = {"app_id": app_id, "checks": {}, "notes": []}
        # tabs
        tabs = c.get_tabs(app_id)
        rec["tabs"] = tabs.actions
        rec["has_contract_tab"] = tabs.has_contract

        # main
        main_html = c.s.tab("app_main", app_id); save("app_main", app_id, main_html)
        m = parse_main(main_html)
        prefix = re.match(r"[A-Z]+", m["nat_code"] or "")
        prefix = prefix.group(0) if prefix else "?"
        rec.update(nat_code=m["nat_code"], type_prefix=prefix, reg_date=m["reg_date"],
                   status_label=m["status_label"], stat_icon=m["stat_icon"],
                   type_label=m["type_label"])

        # docs — predicted vs actual
        docs = c.get_doc_files(app_id); save("app_docs", app_id, c.s.tab("app_docs", app_id))
        predicted = "sectioned" if prefix in SECTIONED_TYPES else "flat"
        actual = docs.layout
        modes = sorted({f.mode for f in docs.files if f.mode})
        rec["app_docs"] = {"predicted": predicted, "actual": actual,
                           "files": len(docs.files), "cost_est": len(docs.cost_estimate_files),
                           "modes": modes}
        if actual == predicted:
            rec["checks"]["docs_layout"] = "PASS"
        elif predicted == "sectioned" and actual == "flat":
            rec["checks"]["docs_layout"] = "ERA?"   # old NAT/SPA/CON -> flat (check reg_date)
            rec["notes"].append(f"layout flat though type={prefix} (reg {m['reg_date']}) — era case?")
        else:
            rec["checks"]["docs_layout"] = "EXCEPTION"
            rec["notes"].append(f"UNEXPECTED: type={prefix} predicted {predicted} but got {actual}")
        # mode invariant
        exp_mode = "que" if actual == "sectioned" else ("app" if actual == "flat" else None)
        rec["checks"]["docs_mode"] = "PASS" if (not modes or modes == [exp_mode]) else f"FAIL {modes}!={exp_mode}"

        # stat icon == enum value
        if m["stat_icon"] is not None:
            label_for_icon = STATUS_ENUM.get(m["stat_icon"])
            ok = label_for_icon and (m["status_label"] or "").startswith(label_for_icon)
            rec["checks"]["stat_icon"] = "PASS" if ok else f"CHECK icon={m['stat_icon']} label={m['status_label']!r}"

        # agency_docs (results)
        ag = c.s.tab("agency_docs", app_id); save("agency_docs", app_id, ag)
        ag_s = BeautifulSoup(ag, "lxml")
        ag_files = ag_s.select("table#reports tbody tr[id]")
        ag_empty = "დოკუმენტაცია მიმაგრებული არ არის" in ag
        ag_modes = sorted(set(re.findall(r"files\.php\?mode=(\w+)", ag)))
        rec["agency_docs"] = {"files": len(ag_files), "empty": ag_empty, "modes": ag_modes}
        if ag_files and ag_modes and ag_modes != ["app"]:
            rec["notes"].append(f"agency_docs modes {ag_modes} (expected app)")

        # contract tab consistency: documented rule = agr_docs present <=> a contract was SIGNED.
        # status 140 = signed; status 130 = being prepared (NOT yet signed) -> expect NO agr_docs.
        signed = (m["stat_icon"] == 140)
        rec["checks"]["contract_tab"] = (
            "PASS" if (rec["has_contract_tab"] == signed)
            else f"FINDING tab={rec['has_contract_tab']} status={m['stat_icon']}")
        if rec["has_contract_tab"]:
            agr = c.s.tab("agr_docs", app_id); save("agr_docs", app_id, agr)
            rec["agr_docs"] = {
                "has_payments": "ჩანაწერები არ არის" not in agr and "გადახდის თარიღი" in agr,
                "contract_file_mode": "contract" if "mode=contract" in agr else None,
            }

        # bids state (parse, don't string-match — attribute spacing varies)
        bids = c.s.tab("app_bids", app_id); save("app_bids", app_id, bids)
        bs = BeautifulSoup(bids, "lxml")
        if bs.select_one("#TenderCountdown"):
            rec["bids_state"] = "countdown"
        elif bs.select('tr[id^="B"]'):
            rec["bids_state"] = f"bidders({len(bs.select('tr[id^=\"B\"]'))})"
        else:
            rec["bids_state"] = "empty/other"

        results.append(rec)
        flag = "  ***" if any(v.startswith(("EXCEPTION", "FAIL")) for v in rec["checks"].values()) else ""
        print(f"{app_id}  {rec['nat_code']:<14} {prefix:<4} reg={rec['reg_date']}  "
              f"docs:{predicted}->{actual} {rec['checks']['docs_layout']:<9} "
              f"tabs={len(rec['tabs'])} status={rec['stat_icon']}{flag}")

    GALLERY.mkdir(parents=True, exist_ok=True)
    (GALLERY / "validation_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # per-type aggregation (refine era boundary)
    print("\n=== type -> layout (this run) ===")
    by_type: dict[str, list] = {}
    for r in results:
        by_type.setdefault(r["type_prefix"], []).append((r["app_docs"]["actual"], r["reg_date"]))
    for t, rows in sorted(by_type.items()):
        print(f"  {t}: {rows}")
    excs = [r["app_id"] for r in results if any(v.startswith(("EXCEPTION", "FAIL")) for v in r["checks"].values())]
    print(f"\nEXCEPTIONS/FAILS: {excs or 'none'}")
    print(f"results -> {GALLERY/'validation_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
