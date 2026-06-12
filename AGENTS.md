# AGENTS.md — read this first (you are an LLM/agent)

This repo is a reverse-engineered API + docs for **tenders.procurement.gov.ge**
(Georgian e-Procurement). The site returns **HTML fragments, not JSON**. There is
no official API. Everything here is verified against the live site.

## Where truth lives (in priority order)

1. **`docs/endpoint_catalog.yaml`** — the **source of truth**. Machine-readable
   inventory of every endpoint: action, method, params, response selectors,
   `last_verified` date. When anything conflicts, this wins.
2. **`docs/search_filters.json` / `.md`** — authoritative filter map: every search
   field's Georgian label ↔ backend param ↔ allowed values (`{id, name}`). Scraped
   from the live form, not hand-written. Use this to translate a user's Georgian
   filter words into params.
3. **`docs/cpv_basecode_map.json`** — CPV number → `app_basecode` internal id.
4. **`docs/api_reference.md`** — prose + edge cases. **`docs/html_structure.md`** —
   the HTML shapes the parsers depend on.
5. **`tenders_client/`** — the client. Prefer calling it over re-scraping by hand.

**Do NOT** treat `graphify-out/` (if present) as truth — it is an auto-generated,
fuzzy *exploration* layer (edges tagged INFERRED/AMBIGUOUS). The YAML is canonical.

## Hard rules

- **Throttle.** Every portal request waits 1.5s (`THROTTLE_S`). Never bypass it.
- **Session.** `ProcurementClient()` GETs `/?lang=ge` to set the `SPALITE` cookie.
  Errors are exceptions now: stale session → auto re-init once, then
  `SessionExpiredError`; bad app_id → `TenderNotFoundError`; markup drift →
  `ParseError` (see `tenders_client/errors.py`).
- **lang=ge ONLY.** `lang=en` exists and returns English fragments — every parser
  keys on Georgian labels and the session verifies the Georgian UI at init.
- **Encoding** is UTF-8; thousands separator is a backtick (`7`500.00`); parse
  values with `tenders_client.parsing.parse_amount/parse_date`, don't regex ad hoc.
- **Scope:** only the Procurement (შესყიდვები) surface. CMR/CON/SMP/ePLAN/MRS are
  **out of scope** (entry-point map only in the catalog).
- **Historical bulk data (≤ 2019-06):** don't scrape it — the official OCDS API has
  it (frozen 2019-06-25, see `docs/ocds_mapping.md`). Current data: portal only.
- **Never** commit `.env`, `data/`, or live-scraped HTML (see `.gitignore`).

## Intent → action cheatsheet

| User wants | Do this | Param / note |
|---|---|---|
| Filter by procurement **category** ("კატეგორია", a CPV group like 452…) | `client.search_by_category(cpv)` | Resolves CPV → **`app_basecode`** internal id (broad: all sub-codes). **NOT `app_codes`.** |
| Filter by one **exact CPV code** | `client.search_tenders(app_codes="45200000")` | `app_codes` = exact match only. Different count than the category dropdown. |
| "winner announced / გამარჯვებული გამოვლენილია" | `app_status=50` | One status only. "Announced"=10, "contract being prepared"=130, "contract signed"=140. Full enum → `search_filters.md`. |
| Filter by amount | `app_amount_from=`, `app_amount_to=` | Currency defaults to GEL (`app_currency=2`). |
| Filter by a date | `app_date_type=<N>` + `app_date_from`/`app_date_tlll` | `app_date_type` picks WHICH date (e.g. 3 = status date). Dates are `DD.MM.YYYY`. |
| Open a tender (parsed) | `client.get_tabs(app_id)` then `get_main_info/get_doc_files/get_bids_info/get_result_files/get_contract_info` | Tabs are **state-dependent**: contract tab (`agr_docs`) exists only at `app_status=140`. Raw-HTML variants (`get_main/get_bids/...`) still exist. |
| Iterate many results | `client.iter_search(max_rows=N, **filters)` | Generator across pages; ~6 requests per 24 rows at 1.5s throttle. |
| Winner / bid amounts | `client.get_bids_info(app_id).winner` | `Bid.bidder_id` feeds `get_bid_history`; `Bid.org_id` feeds `get_profile`. |
| Contract + payments | `client.get_contract_info(app_id)` | `Contract.paid_pct`, `payments[].amount_value`, contract file id. |
| Q&A clarifications | `client.get_doc_files(app_id).qa_threads` → `client.parse_qa(client.get_qa(app_id, chat_id))` | chat ids come from app_docs (both layouts). |
| Company profile | `client.get_profile(org_id)` | Works for buyer or supplier orgs. `OrgProfile.reg_code` = NAPR join key. |
| Status timeline | `client.get_status_history(app_id)` | Finer-grained than the search-filter status enum. |
| Latest status changes | `client.get_lastevents()` | Homepage feed, 5 rows. |
| Download a file | `client.s.download(file_id, code, mode, dest_dir)` | Throttled; filename from Content-Disposition. `mode=contract` omits `code`. |
| Permalink to a tender | `PortalSession.permalink(app_id)` | `…/?go=<id>&lang=ge`. |

## The mistake to never repeat

The **category dropdown is `app_basecode` (internal id), not `app_codes` (CPV
number)**. They return different result counts. If a user gives a Georgian
category/CPV and your count looks wrong, you almost certainly used the wrong param.
Resolve via `cpv_basecode_map.json` / `client.resolve_basecode()`.

## Search param defaults

The full POST body and every default value is `SEARCH_DEFAULTS` in
`tenders_client/client.py`. `search_tenders(**filters)` validates keys against it
and raises on unknown params — so a typo'd filter fails loud, not silent.
