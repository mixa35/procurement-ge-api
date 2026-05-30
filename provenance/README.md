# provenance/

These are the **original discovery & re-verification scripts** used to reverse-
engineer the portal and produce the documentation in `docs/`. They are included as
evidence of *how* the endpoints were found and verified — not as part of the
runtime client (`tenders_client/`), which needs none of them.

| Script | What it captured |
|---|---|
| `discovery/capture_fixtures.py` | Core tab fixtures (app_main/app_docs/app_bids/agency_docs/agr_docs) + DuckDB inventory seed. |
| `discovery/capture_states.py` | State-variant samples (failed contract, did-not-happen). |
| `discovery/reverify_and_lastevents.py` | Re-verified app_main/app_docs; captured the `lastevents` feed. |
| `discovery/capture_new_endpoints.py` | profile / statushistory / tdocs / view_bid / today_bids / cpv + stat-icon mapping. |
| `discovery/validate_tenders.py` | Adversarial predicted-vs-actual validation across many tenders. |
| `discovery/build_gallery.py` | Built `docs/gallery.html` from the validation results + screenshots. |
| `discovery/extract_filters.py` | Scraped every filter + option from `#search_frm` → `docs/search_filters.{json,md}`. |

## Running them

They are meant to run **from the repo root**, against the live portal (throttled,
1.5s). They write captured HTML to `data/discovery/` (created on first run and
**git-ignored** — scraped pages are not redistributed). Extra dependencies these
scripts need (Playwright, DuckDB, openpyxl, python-dotenv) are listed in the root
`requirements.txt`; the client itself does not require them.

> A curated subset of the captured fixtures is committed under `tests/fixtures/`
> so the parser test suite is green on a fresh clone without re-scraping.
