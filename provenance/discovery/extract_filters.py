"""Authoritatively extract EVERY search filter + EVERY option from the live form.

Source of truth = the `#search_frm` HTML on the homepage. For each control it records the
backend param name, the Georgian label (the preceding `<li class="lbl">`), the input type,
and — for <select> — every option's internal id + Georgian name. No hand-written enums.

Outputs:
  docs/search_filters.json   (machine-readable: param -> {label, type, options:[{id,name}]})
  docs/search_filters.md     (human-readable tables)
Run:  python provenance/discovery/extract_filters.py
"""
from __future__ import annotations

import io
import json
import pathlib
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from bs4 import BeautifulSoup  # noqa: E402

from tenders_client import ProcurementClient  # noqa: E402
from tenders_client.session import HOME  # noqa: E402

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"


def main() -> int:
    c = ProcurementClient()
    soup = BeautifulSoup(c.s._raw_get(HOME).text, "lxml")
    frm = soup.find("form", id="search_frm")
    if not frm:
        print("ERROR: search_frm not found"); return 1

    filters = []
    for ctl in frm.find_all(["input", "select", "textarea"]):
        name = ctl.get("name")
        if not name:
            continue
        li = ctl.find_parent("li")
        lbl_li = li.find_previous_sibling("li", class_="lbl") if li else None
        if lbl_li is None:   # controls not wrapped in their own <li> (e.g. app_date_type in the date group)
            lbl_li = ctl.find_previous("li", class_="lbl")
        # strip the helper <label>(ძებნა მე-3...) hint from the label text
        label = None
        if lbl_li:
            for sub in lbl_li.find_all("label"):
                sub.extract()
            label = lbl_li.get_text(" ", strip=True) or None
        typ = ctl.get("type") if ctl.name == "input" else ctl.name
        entry = {"param": name, "label": label, "id": ctl.get("id"), "type": typ}
        if typ == "hidden":
            entry["default"] = ctl.get("value", "")
        if ctl.name == "select":
            opts = []
            for o in ctl.find_all("option"):
                opts.append({"id": o.get("value"), "name": o.get_text(strip=True)})
            entry["options"] = opts
        filters.append(entry)

    (DOCS / "search_filters.json").write_text(
        json.dumps({"source": HOME, "form": "#search_frm", "filters": filters},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    # human-readable markdown
    md = ["# Search filters — authoritative map (scraped from #search_frm)\n",
          f"Source: `{HOME}` · regenerate with `provenance/discovery/extract_filters.py`\n",
          "\n## Filters (Georgian label ↔ backend param)\n",
          "| Georgian label | param (backend) | type | #options |",
          "|---|---|---|---|"]
    for f in filters:
        nopt = len(f["options"]) if "options" in f else ""
        md.append(f"| {f['label'] or '(hidden)'} | `{f['param']}` | {f['type']} | {nopt} |")
    md.append("\n## Option value maps (internal id ↔ Georgian name)\n")
    for f in filters:
        if "options" not in f:
            continue
        md.append(f"\n### `{f['param']}` — {f['label'] or ''} ({len(f['options'])} options)\n")
        md.append("| id | name |")
        md.append("|---|---|")
        for o in f["options"]:
            if f["param"] == "app_basecode" and len(f["options"]) > 30:
                pass  # keep full list; it's the category map
            md.append(f"| `{o['id']}` | {o['name'] or '(all / empty)'} |")
    (DOCS / "search_filters.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # console summary for cross-checking the hand-written enums
    print(f"filters: {len(filters)}  ->  docs/search_filters.json + docs/search_filters.md\n")
    for f in filters:
        if "options" in f and f["param"] != "app_basecode":
            print(f"== {f['param']}  ({f['label']})  [{len(f['options'])} opts]")
            for o in f["options"]:
                print(f"     {o['id']:>5}  {o['name']}")
    bc = next(f for f in filters if f["param"] == "app_basecode")
    print(f"\n== app_basecode: {len(bc['options'])} options (full map in JSON/MD)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
