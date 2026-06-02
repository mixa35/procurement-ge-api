# Changelog

All notable changes to this project are documented here.

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
