# Changelog

All notable changes to this project are documented here.

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
