# Procurement GE API

A complete, reverse-engineered **API layer + documentation** for the Georgian
e-Procurement portal — **[tenders.procurement.gov.ge](https://tenders.procurement.gov.ge/public/?lang=ge)**.

The site has **no public API**. It is a single-page app whose backend
(`library/controller.php`) returns **HTML fragments**, not JSON. This repository
documents every public endpoint, every UI state, and every HTML response shape —
and ships a clean Python client (`tenders_client`) that turns those fragments
into structured data.

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
| **[tenders_client/](tenders_client/)** | The Python client (session + parsers + dataclasses). |
| **[examples/](examples/)** | Runnable scripts (start here). |
| **[tests/](tests/)** | 27 fixture-backed parser tests — green on a fresh clone. |
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
    print(row.app_id, row.nat_code, row.buyer)

# 2) Open one tender's tabs and read its main page
tabs = client.get_tabs(page.rows[0].app_id)   # which tabs exist (state-dependent)
main_html = client.get_main(page.rows[0].app_id)

# 3) Documentation files (handles both layouts automatically)
docs = client.get_doc_files(page.rows[0].app_id)
for f in docs.files:
    print(f.filename, "→", client.s.file_url(f.file_id, f.code, f.mode))
```

The client throttles every portal request to **1.5s** by default
(`THROTTLE_S` env var, or `make_session(throttle_s=...)`). **Please keep it
throttled — do not hammer the portal.**

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

**Proprietary — all rights reserved.** This is *not* open source. See
[LICENSE](LICENSE). To obtain a license to use this work, contact
**mishogongadze7@gmail.com**.

This repo documents only the **public** pages of the portal — no credentials, no
authenticated endpoints. The underlying procurement data is published by the
State Procurement Agency of Georgia under its own terms.
