# Procurement GE API

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![tests](https://github.com/mixa35/procurement-ge-api/actions/workflows/tests.yml/badge.svg)](https://github.com/mixa35/procurement-ge-api/actions/workflows/tests.yml)
[![Portal verified](https://img.shields.io/badge/portal%20verified-2026--06--12-informational.svg)](docs/api_reference.md)

A complete, reverse-engineered **API layer + documentation** for the Georgian
e-Procurement portal — **[tenders.procurement.gov.ge](https://tenders.procurement.gov.ge/public/?lang=ge)**.

The portal itself has **no API**. It is a single-page app whose backend
(`library/controller.php`) returns **HTML fragments**, not JSON. An official OCDS
open-data API exists at `odapi.spa.ge`, **but its data ends 2019-06-25** (verified
2026-06-12 — see [docs/ocds_mapping.md](docs/ocds_mapping.md)), which makes this
repository the **only machine-readable source of current Georgian procurement
data**. It documents every public endpoint, every UI state, and every HTML
response shape — and ships a clean Python client (`tenders_client`) that turns
those fragments into structured data.

> **Status:** the public Procurement (შესყიდვები) surface is fully documented and
> verified against the live site (last verified **2026-05-29**, 16-tender visual
> validation). Other portal modules (CMR/CON/SMP/ePLAN/MRS) are intentionally
> **out of scope** and mapped only as entry points — see the catalog.

---

## What's inside

| Path | What it is |
|---|---|
| **[docs/api_reference.md](docs/api_reference.md)** | Prose reference: every endpoint, params, response shape, edge cases. |
| **[docs/endpoint_catalog.yaml](docs/endpoint_catalog.yaml)** | **Machine-readable source of truth** — the inventory every other doc derives from. |
| **[docs/search_filters.md](docs/search_filters.md)** / `.json` | Authoritative map of **every search filter**: Georgian label ↔ backend param ↔ internal-id/value enums. |
| **[docs/cpv_basecode_map.json](docs/cpv_basecode_map.json)** | 273 procurement categories: CPV number → `app_basecode` internal id. |
| **[docs/html_structure.md](docs/html_structure.md)** | Annotated HTML examples for each tab/endpoint (what the parsers key off). |
| **[docs/gallery.html](docs/gallery.html)** | Visual proof: 16 real tenders across the lifecycle, screenshotted and validated. |
| **[docs/ocds_mapping.md](docs/ocds_mapping.md)** | The official OCDS open-data API (frozen 2019-06-25): field mapping, what only this project has, when to use which. |
| **[tenders_client/](tenders_client/)** | The Python client (session + parsers + dataclasses). |
| **[examples/](examples/)** | Runnable scripts (start here). |
| **[tests/](tests/)** | 60 fixture-backed tests (27 of them parser tests) — no live portal calls, run in CI on Python 3.10–3.13. |
| **[provenance/discovery/](provenance/discovery/)** | The scripts used to discover & re-verify the endpoints (how the docs were derived). |
| **[AGENTS.md](AGENTS.md)** | Entry point for AI agents (Claude Code etc.) — read this first if you're an LLM. |

---

## Install

**Option A — pip install (recommended):**

```bash
pip install .
# or, straight from GitHub:
# pip install git+https://github.com/mixa35/procurement-ge-api.git
```

Then, from anywhere:

```python
from tenders_client import ProcurementClient
```

**Option B — copy the folder:** the `tenders_client/` package is self-contained
(no on-disk data files; it fetches everything live). Drop it into your project and
`pip install requests beautifulsoup4 lxml`.

Runtime requires **Python ≥ 3.10** and only `requests`, `beautifulsoup4`, `lxml`.
(The extra packages in `requirements.txt` are for the `provenance/discovery/`
scripts, not for using the client.)

---

## Quickstart

```python
from tenders_client import ProcurementClient

client = ProcurementClient()          # acquires the SPALITE session cookie for you

# 1) Search by procurement category (the "შესყიდვის კატეგორია" dropdown)
page = client.search_by_category(45200000, app_status=50, app_amount_from=150000)
print(page.total_records, "tenders")
for row in page.rows:
    print(row.app_id, row.nat_code, row.buyer, row.estimated_value_amount)

# ...or iterate across pages without manual pagination:
for row in client.iter_search(max_rows=20, app_status=140):
    print(row.app_id, row.nat_code)

# 2) Open one tender — parsed, not raw HTML
app_id = page.rows[0].app_id
tabs = client.get_tabs(app_id)         # which tabs exist (state-dependent)
main = client.get_main_info(app_id)    # TenderMain: deadline, value, buyer, status...
print(main.nat_code, main.status_text, main.buyer_name, main.bid_deadline_dt)

bids = client.get_bids_info(app_id)    # BidsTab: state + bidders
if bids.winner:
    print("winner:", bids.winner.bidder_name, bids.winner.last_amount_value)

# 3) Documentation files (handles both layouts automatically) + Q&A threads
docs = client.get_doc_files(app_id)
for f in docs.files:
    print(f.filename, "→", client.s.file_url(f.file_id, f.code, f.mode))
for t in docs.qa_threads:
    print("Q&A thread", t.chat_id, client.parse_qa(client.get_qa(app_id, t.chat_id)))

# 4) Contract + payments (tenders at app_status=140 only)
if tabs.has_contract:
    c = client.get_contract_info(app_id)
    print(c.supplier_name, c.amount_value, c.currency, c.paid_pct, "% paid")

# 5) Download an attachment (throttled, cookie-bearing)
if docs.files:
    f = docs.files[0]
    client.s.download(f.file_id, f.code, f.mode, dest_dir="downloads")
```

Failures are **loud**: a bad `app_id` raises `TenderNotFoundError`, a dead session
raises `SessionExpiredError` (after one automatic re-init), and markup drift raises
`ParseError` — the client never silently returns empty data (see
[docs/api_reference.md](docs/api_reference.md) "Error signatures").

The client throttles every portal request to **1.5s** by default
(`THROTTLE_S` env var, or `make_session(throttle_s=...)`). **Please keep it
throttled — do not hammer the portal.**

### Crawling policy note

The portal's `robots.txt` is `User-agent: * / Disallow: /` (recorded 2026-06-12) —
it formally disallows automated crawling, though nothing enforces it technically.
This client exists for low-volume, throttled, targeted reading of public data;
whether and how to use it is the operator's call. Bulk-historical needs should go
to the official OCDS open data instead (≤ 2019-06 only — see
[docs/ocds_mapping.md](docs/ocds_mapping.md)).

---

## Two things that bite everyone (read these)

1. **Category filter ≠ exact code.** The "შესყიდვის კატეგორია" dropdown is the
   backend param **`app_basecode`**, and it wants an **internal id** (e.g. CPV
   `45200000` → `19003`), *not* the CPV number. It matches the **broad** category
   (all sub-codes). The separate **`app_codes`** param matches one **exact** code.
   They return different counts. Use `client.search_by_category(cpv)` for the
   dropdown behavior; pass `app_codes=` to `search_tenders()` for an exact code.

2. **Tabs are state-dependent.** A tender shows the contract tab (`agr_docs` /
   ხელშეკრულება) **only once a contract is signed** (`app_status=140`). Announced
   (10) and contract-being-prepared (130) tenders show 4 tabs, not 5.

Full filter/enum reference: **[docs/search_filters.md](docs/search_filters.md)**.

---

## License

**[MIT](LICENSE).** Use it, fork it, build on it.

Two requests that the license does not enforce but that matter:

1. **Keep the client throttled.** The portal is a public service run by a state
   agency and has no rate limiting of its own. The 1.5s default exists for a
   reason — please don't lower it for bulk work.
2. **Check `docs/ocds_mapping.md` first if you need history.** Bulk historical
   analysis belongs on the official OCDS open data, not on this client.

This repo documents only the **public** pages of the portal — no credentials, no
authenticated endpoints. The underlying procurement data is published by the
State Procurement Agency of Georgia under its own terms; the MIT license covers
this repository's code and documentation, not that data.
