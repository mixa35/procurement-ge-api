# Changelog

All notable changes to this project are documented here.

## [1.1.0] — 2026-06-12

Deep-audit release: failures are now loud, every core tab parses into structured
data, and the docs reflect three newly verified facts about the portal's world
(OCDS freeze, robots.txt, the lang=en trap). No breaking changes — all raw-HTML
getters remain; parsed variants are new methods.

### Added
- **Exceptions** (`tenders_client.errors`): `TenderNotFoundError` (bad app_id),
  `SessionExpiredError` (stale lang session, after one automatic re-init),
  `ParseError` (expected wrapper markup missing — drift detector). The client
  never silently returns empty data anymore.
- **Core-tab parsers**: `get_main_info()` → `TenderMain` (full label map +
  status_code from stat icon + buyer org_id), `get_bids_info()` → `BidsTab`/`Bid`
  (open/listed/empty states, bidder_id ready for `get_bid_history`, winner via
  activebid1), `get_result_files()` (table#reports), `get_contract_info()` →
  `Contract`/`Payment` (summary card, document list, payment history, paid %).
- **`get_lastevents()`** — the documented feed finally has a client method.
- **`iter_search(max_rows=None, **filters)`** — generator across result pages.
- **Q&A end-to-end**: `DocsTab.qa_threads` (chat ids from both layouts) +
  `parse_qa()` → `QaMessage`; `get_qa()` is now usable without manual HTML digging.
- **`PortalSession.download()`** — throttled file download, filename from
  Content-Disposition.
- **Typed values** (`tenders_client.parsing`): `parse_amount` (backtick/currency/
  funding-source tolerant), `parse_date` (DD.MM.YYYY[ HH:MM]); `_dt`/`_amount`
  properties across models. `OrgProfile.reg_code` promoted as the stable NAPR
  join key (matches OCDS `GE-NAPR-<regcode>`).
- **`python -m tenders_client.healthcheck`** — ~8 throttled live asserts against
  the catalog's selectors; run before scraping campaigns to catch portal drift.
- HTTP retries with backoff (3x, 500/502/503/504) + `raise_for_status`; module
  logging (`logging.getLogger("tenders_client")`).

### Changed
- Session init now **verifies the Georgian UI** — `lang=en` exists and returns
  fully English fragments, which would silently break every label-keyed parser.
- `next_page()`/`goto_page()` raise before a search (server-side result-set state).
- `search_tenders` rejects malformed date params (portal silently ignores them).
- User-Agent: `procurement-ge-api/<version>`.

### Docs
- README "no public API" corrected: the official OCDS API (odapi.spa.ge) exists
  but its **data ends 2019-06-25** (verified 2026-06-12) — this project is the
  only machine-readable source of current data. New `docs/ocds_mapping.md` with
  the full OCDS↔project field mapping and shared-backend proof.
- Recorded `robots.txt: Disallow: /` (crawling-policy note); Language section in
  api_reference; error-signature → exception table; `fblogin/fblogout.php` added
  to the out-of-scope entry-point map.

### Tests
- 60 passing (was 27): negative tests for every error signature and drift guard,
  core-tab parser tests (new fixtures: `agr_docs_656756/577557`,
  `application_656756`), iter_search paging, value parsing, alias mapping,
  `lookup_company`, `get_tabs`. Fixture-missing now FAILS instead of skipping.

## [1.0.1] — 2026-06-02

Bug fixes from an accuracy audit (parser/model gaps + packaging placeholders).

### Fixed
- **Search rows now populate `category` and `estimated_value`.** `TenderRow` promised
  both and the search HTML carries them, but `_enrich_row()` only extracted NAT
  code/buyer/status. Both fields are now parsed.
- **Flat-layout docs respect currentness.** `_parse_docs` (flat) now sets
  `DocFile.is_current` from the file cell's `obsolete0`/`obsolete1` class instead of
  defaulting every flat file to `True` (matching the sectioned layout's behavior).
- **Packaging URLs** in `pyproject.toml` and the README install command pointed at a
  placeholder org (`REPLACE_ME`); corrected to `mixa35`.
- **Docs:** `api_reference.md` no longer cites `cpv_dialog2.html` / `stat_icon_mapping.txt`
  as shipped fixtures — they are `data/discovery/` provenance captures (not in `tests/fixtures/`).

### Tests
- Added regression assertions for search `category`/`estimated_value` and flat-layout
  obsolete handling. 27 passing.

## [1.0.0] — 2026-05-30

First packaged release. The public Procurement (შესყიდვები) surface of
tenders.procurement.gov.ge is fully documented and verified against the live site.

### Documented endpoints (20)
Company lookup, search (`search_app`), tender container + the 5 detail tabs
(`app_main`, `app_docs`, `app_bids`, `agency_docs`, `agr_docs`), `lastevents`,
`app_statushistory`, `app_tdocs`, `profile`, `today_bids`, `view_bid`, `show_qa`,
CPV tree picker (`cpv/dialog2.php`), CPV autocomplete (confirmed empty even live),
`files.php` (modes que/app/tdoc/contract), tender permalink (`/?go=`), and
`who.php`. Out-of-scope modules (CMR/CON/SMP/ePLAN/MRS) mapped as entry points only.

### Verified behaviors
- Tab set is **state-dependent**: `agr_docs` (contract) appears only at
  `app_status=140` (signed). Validated across 16 tenders (status 10/130/140).
- `app_docs` has **two layouts** (sectioned vs flat), type/era driven;
  `get_doc_files()` auto-detects.
- Category filter `app_basecode` (internal id, broad category) ≠ `app_codes`
  (exact CPV); 273-category CPV→id map shipped.
- `stat<N>.png` icon == `app_status` value (1:1).

### Packaging
- `tenders_client` is `pip install`-able and copy-friendly; reads no files from
  disk at runtime (the category map is fetched live).
- 27 fixture-backed parser tests, green on a fresh clone.
- Discovery/re-verification scripts retained under `provenance/`.
