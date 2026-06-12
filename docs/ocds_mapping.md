# The official OCDS open-data API vs. this project

**Investigated & verified live: 2026-06-12.**

The State Procurement Agency operates an official OCDS 1.1 open-data API at
**`https://odapi.spa.ge`** (CC0 license, Swagger at `/api/swagger.ui`). Two facts matter:

1. **The API machinery works perfectly** — all four documented endpoints respond as
   documented (`/api/releases.json` & `/api/records.json` with `page`, `ordering=asc|desc`,
   `idsOnly`; `/api/release.json?releaseID=`; `/api/record.json?ocid=`), and the backing
   **Elasticsearch is openly queryable** at `/search` (index `releases`, type `Tender`,
   full query DSL — 275,641 documents).
2. **The data is frozen at 2019-06-25.** The newest release across the entire corpus
   (checked both via `ordering=desc` and an ES sort on `ocds.date` over all 275,641 docs)
   is `2019-06-25T23:44`. The publication policy still says "nightly refresh"; the
   pipeline stopped in 2019. The live portal holds ~496k records — the missing ~220k are
   everything after mid-2019. **For current data, this project's scraper is the only
   machine-readable source.**

Caveats: the host serves an incomplete TLS chain (pin the intermediate cert or relax
verification); `ocid` format is `ocds-3z43pn-<tender_code>` (e.g. `ocds-3z43pn-NAT180015582`).

## Proof of shared backend

The OCDS record's `awards[].documents[].url` is literally this portal's documented
permalink format — `https://tenders.procurement.gov.ge/public/?go=<app_id>&lang=en` —
and `tender.id` is the NAT code. The OCDS export was a downstream nightly summary of the
same database this project scrapes.

## Field mapping (OCDS `compiledRelease` ↔ this project)

Derived by enumerating all 62 field paths of a contract-stage record
(`ocds-3z43pn-NAT180015582`) and mapping each onto the documented portal surface.
**No OCDS field revealed a portal element this project had missed.**

| OCDS field | This project | Notes |
|---|---|---|
| `tender.id` (`NAT180015582`) | `nat_code` (app_main, search rows) | identical format |
| `ocid` = `ocds-3z43pn-<code>` | derivable | fixed prefix |
| `buyer.name` / `tender.procuringEntity` | `TenderMain.buyer_name` | |
| `buyer.id` = `GE-NAPR-<regcode>` | `OrgProfile.reg_code` (საიდენტიფიკაციო კოდი) | **the stable cross-dataset join key**; the portal's internal `org_id` exists only here |
| `tender.value.amount/currency` | `TenderMain.estimated_value(_amount)` | |
| `tender.items[].classification` (CPV) | category / `app_basecode`/`app_codes` | OCDS adds sub-codes via `additionalClassifications` |
| `tender.tenderPeriod.startDate/endDate` | `TenderMain.announce_date / bid_deadline` | ISO vs DD.MM.YYYY |
| `tender.status` (`complete`/`active`…) | `app_status` enum (10…140) | different vocabularies, same lifecycle |
| `tender.procurementMethod`/`submissionMethod`/`awardCriteria` | derivable from `app_type` | OCDS normalizes |
| `tender.tenderers[]` | `BidsTab.bids` | OCDS = names only |
| `awards[].suppliers[]` + `value` | `BidsTab.winner` + amount | |
| `awards[].contractPeriod` | `Contract.valid_from/valid_to` | |
| `contracts[].dateSigned/title/status` | `Contract.contract_date/number_raw/status_text` | |
| `parties[].address/contactPoint` | `OrgProfile` fields | |

## What ONLY this project has (never exported to OCDS, even pre-2019)

- per-bidder **bid trails** with timestamps (`view_bid`) — OCDS keeps only the final award
- the actual **documentation files** (cost-estimate XLSX etc.; `app_docs`/`files.php`)
- **clarification Q&A threads** (`show_qa`), **payment history** (`agr_docs`),
  **full status timeline** (`app_statushistory`), **technical docs per bidder** (`app_tdocs`)
- live states (countdowns, `today_bids`, `lastevents`) and the portal's internal ids
- **everything after 2019-06-25**

## When to use which

- **History ≤ June 2019, in bulk:** use OCDS / its open Elasticsearch — free, clean JSON,
  no scraping, no throttle.
- **Anything current:** this project. For bulk-current needs, prefer incremental sync
  (status-change-date filtered searches + `lastevents`/`today_bids` feeds) over brute
  pagination — see README scaling note.
