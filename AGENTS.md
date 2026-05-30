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
  A stale cookie → PHP `Undefined index: lang` (line 8). Re-init the client to fix.
- **Encoding** is UTF-8; thousands separator is a backtick (`7`500.00`).
- **Scope:** only the Procurement (შესყიდვები) surface. CMR/CON/SMP/ePLAN/MRS are
  **out of scope** (entry-point map only in the catalog).
- **Never** commit `.env`, `data/`, or live-scraped HTML (see `.gitignore`).

## Intent → action cheatsheet

| User wants | Do this | Param / note |
|---|---|---|
| Filter by procurement **category** ("კატეგორია", a CPV group like 452…) | `client.search_by_category(cpv)` | Resolves CPV → **`app_basecode`** internal id (broad: all sub-codes). **NOT `app_codes`.** |
| Filter by one **exact CPV code** | `client.search_tenders(app_codes="45200000")` | `app_codes` = exact match only. Different count than the category dropdown. |
| "winner announced / გამარჯვებული გამოვლენილია" | `app_status=50` | One status only. "Announced"=10, "contract being prepared"=130, "contract signed"=140. Full enum → `search_filters.md`. |
| Filter by amount | `app_amount_from=`, `app_amount_to=` | Currency defaults to GEL (`app_currency=2`). |
| Filter by a date | `app_date_type=<N>` + `app_date_from`/`app_date_tlll` | `app_date_type` picks WHICH date (e.g. 3 = status date). Dates are `DD.MM.YYYY`. |
| Open a tender | `client.get_tabs(app_id)` then `get_main/get_doc_files/get_bids/get_results/get_contract` | Tabs are **state-dependent**: contract tab (`agr_docs`) exists only at `app_status=140`. |
| Company profile | `client.get_profile(org_id)` | Works for buyer or supplier orgs. |
| Status timeline | `client.get_status_history(app_id)` | Finer-grained than the search-filter status enum. |
| Build a file download URL | `client.s.file_url(file_id, code, mode)` | Parse `mode/file/code` from the anchor href; `mode=contract` omits `code`. |
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
