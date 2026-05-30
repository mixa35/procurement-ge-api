"""Generate docs/gallery.html from docs/gallery/validation_results.json + screenshots.

Single source of truth: the JSON produced by validate_tenders.py. The gallery ties the
VISUAL proof (screenshots) to the HTML/Python findings (per-tender checks), so the three
layers stay consistent. Re-run after validate_tenders.py.

Run:  python provenance/discovery/build_gallery.py
"""
from __future__ import annotations

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
GALLERY = ROOT / "docs" / "gallery"
RESULTS = GALLERY / "validation_results.json"
OUT = ROOT / "docs" / "gallery.html"

BASE = "https://tenders.procurement.gov.ge/public/?go={}&lang=ge"


def badge(label: str, status: str) -> str:
    ok = status == "PASS"
    cls = "ok" if ok else ("era" if status.startswith("ERA") else "bad")
    return f'<span class="badge {cls}" title="{html.escape(status)}">{html.escape(label)}: {html.escape(status)}</span>'


def card(r: dict) -> str:
    aid = r["app_id"]
    ad = r["app_docs"]
    checks = r["checks"]
    rule = ("Sectioned layout (mode=que); cost estimate in section 1.3 (#que150)"
            if ad["actual"] == "sectioned"
            else "Flat layout (table#tender_docs, mode=app); cost estimate is a named .xlsx row")
    badges = "".join(badge(k, v) for k, v in checks.items())
    notes = "".join(f"<li>{html.escape(n)}</li>" for n in r.get("notes", []))
    notes_html = f'<ul class="notes">{notes}</ul>' if notes else ""
    agr = r.get("agr_docs", {})
    return f"""
  <section class="card">
    <h2>{html.escape(r['nat_code'] or '?')} <span class="aid">app_id {aid}</span></h2>
    <div class="meta">
      <b>Type:</b> {html.escape(r['type_prefix'])} &nbsp;|&nbsp;
      <b>Registered:</b> {html.escape(r['reg_date'] or '?')} &nbsp;|&nbsp;
      <b>Status:</b> {html.escape(str(r['status_label'] or ''))} (stat{r['stat_icon']}) &nbsp;|&nbsp;
      <b>Tabs:</b> {len(r['tabs'])} {html.escape(', '.join(r['tabs']))}
      &nbsp;|&nbsp; <a href="{BASE.format(aid)}" target="_blank">open live ↗</a>
    </div>
    <div class="badges">{badges}</div>
    <div class="facts">
      <b>app_docs:</b> predicted <code>{ad['predicted']}</code> → actual <code>{ad['actual']}</code>,
      {ad['files']} files, {ad['cost_est']} cost-estimate file(s), modes {ad['modes']}.<br>
      <b>Proves:</b> {html.escape(rule)}.<br>
      <b>Results (agency_docs):</b> {r['agency_docs']['files']} files (mode {r['agency_docs']['modes']}).
      &nbsp; <b>Bids:</b> {html.escape(r['bids_state'])}.
      {('&nbsp; <b>Contract:</b> payments=' + str(agr.get('has_payments')) + ', file mode=' + str(agr.get('contract_file_mode'))) if agr else ''}
    </div>
    {notes_html}
    <div class="shots">
      <figure><figcaption>Main tab</figcaption><a href="gallery/{aid}_main.png" target="_blank"><img src="gallery/{aid}_main.png" loading="lazy"></a></figure>
      <figure><figcaption>Documentation tab (proof of layout)</figcaption><a href="gallery/{aid}_docs.png" target="_blank"><img src="gallery/{aid}_docs.png" loading="lazy"></a></figure>
    </div>
  </section>"""


def main() -> int:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    # show the lifecycle progression: announced (10) -> preparing (130) -> signed (140)
    data.sort(key=lambda r: (r.get("stat_icon") or 0, r["app_id"]))
    total = len(data)
    passed = sum(1 for r in data if all(v == "PASS" or v.startswith("ERA") for v in r["checks"].values()))
    by_type: dict[str, set] = {}
    for r in data:
        by_type.setdefault(r["type_prefix"], set()).add(r["app_docs"]["actual"])
    type_summary = ", ".join(f"{t}→{'/'.join(sorted(v))}" for t, v in sorted(by_type.items()))
    cards = "\n".join(card(r) for r in data)
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Tender Validation Gallery — tenders.procurement.gov.ge</title>
<style>
  body{{font:14px/1.5 system-ui,Segoe UI,sans-serif;margin:0;background:#f4f5f7;color:#1a1a1a}}
  header{{background:#0b5; background:linear-gradient(90deg,#0a5,#078);color:#fff;padding:20px 28px}}
  header h1{{margin:0 0 6px;font-size:20px}} header p{{margin:2px 0;opacity:.95}}
  main{{max-width:1100px;margin:18px auto;padding:0 16px}}
  .card{{background:#fff;border:1px solid #dde;border-radius:10px;padding:16px 18px;margin:0 0 18px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
  .card h2{{margin:0 0 4px;font-size:17px}} .aid{{color:#789;font-weight:400;font-size:13px}}
  .meta,.facts{{color:#334;font-size:13px;margin:4px 0}} .facts code{{background:#eef;padding:1px 5px;border-radius:4px}}
  .badges{{margin:8px 0}}
  .badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;color:#fff}}
  .badge.ok{{background:#2a9d3a}} .badge.bad{{background:#c0392b}} .badge.era{{background:#d68910}}
  .notes{{color:#a15;font-size:13px;margin:6px 0 0 18px}}
  .shots{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}}
  .shots img{{width:100%;border:1px solid #ccd;border-radius:6px}}
  figcaption{{font-size:12px;color:#567;margin-bottom:4px}}
  a{{color:#067}}
</style></head>
<body>
<header>
  <h1>Tender Validation Gallery</h1>
  <p>{passed}/{total} tenders pass every documented rule (layout · file mode · stat-icon=status · contract-tab).
     Visual + HTML + Python cross-checked. Generated from <code>docs/gallery/validation_results.json</code>.</p>
  <p>Type → layout observed: <b>{html.escape(type_summary)}</b>.
     Era note: NAT sectioned confirmed back to 2018; older tenders (e.g. 2014 SPA) are flat.</p>
  <p><b>Lifecycle coverage (state-dependent tabs):</b> status 10 <i>გამოცხადებულია</i> (4 tabs, no contract)
     → 130 <i>მიმდინარეობს ხელშეკრულების მომზადება</i> (4 tabs, no contract)
     → 140 <i>ხელშეკრულება დადებულია</i> (5 tabs, <code>agr_docs</code> appears). Confirms: the contract tab
     shows up only once a contract is <b>signed</b>, not while it is being prepared.</p>
</header>
<main>
{cards}
</main>
</body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT}  ({passed}/{total} pass; types: {type_summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
