# API Reference — tenders.procurement.gov.ge

## Base URL
https://tenders.procurement.gov.ge/public/library/controller.php

## Session / Cookie requirement

All controller.php requests require a live `SPALITE` session cookie **plus server-side
`lang` state**. Both are established by a single GET to the homepage:

```
GET https://tenders.procurement.gov.ge/public/?lang=ge
← Set-Cookie: SPALITE=<random_session_id>; path=/
← (server also stores lang=ge in the PHP session)
```

**What SPALITE is:** A standard PHP session cookie (`PHPSESSID`-equivalent) set in a
`Set-Cookie` response header. It is **not** injected by JavaScript. A plain `requests`
session (or `curl --cookie-jar`) captures it automatically by following the redirect and
accepting cookies. No JavaScript execution is needed.

**Reproducing in curl:**
```bash
curl -c /tmp/cookies.txt \
     "https://tenders.procurement.gov.ge/public/?lang=ge"
# cookies.txt now holds SPALITE; reuse for subsequent calls:
curl -b /tmp/cookies.txt \
     "https://tenders.procurement.gov.ge/public/library/controller.php?action=lastevents"
```

**Session lifetime:** Not formally documented by the portal. Empirically, the session
survives the duration of a scraping run (minutes to hours). A stale or missing SPALITE
produces the PHP error `Undefined index: lang` at controller.php line 8 — not an HTTP
4xx. When this occurs, re-initialize by repeating the GET `/?lang=ge` to obtain a fresh
cookie.

**Auth requirement:** All endpoints documented here are reachable **anonymously** — no
login, no credentials. The SPALITE cookie is a session-state carrier, not an auth token.
Confirmed by: fresh `requests.Session()` with only the homepage GET producing valid data
from every documented endpoint (search, tabs, contract, lastevents).

**Rate limiting / throttling:** The portal does not return explicit 429 responses. The
project uses a conservative 1.5-second inter-request delay (configurable via `THROTTLE_S`
env var). Bot-detection behavior at faster rates is unknown — do not reduce below 1.0s
without testing.

## Tender detail tab structure

A full tender loads via:
```
GET library/controller.php?action=application&app_id=<ID>&app_reg=&key=
```
The response contains a jQuery UI tabs widget (`#application_tabs`). **The tab set is
state-dependent** (confirmed 2026-05-28 against live tenders):

| Tab label | action= | Presence | Contains |
|---|---|---|---|
| NAT... (main) | `app_main` | always | Tender overview, procurement info |
| **დოკუმენტაცია** | **`app_docs`** | always | Buyer-side procurement documentation incl. cost-estimate xlsx |
| შეთავაზებები | `app_bids` | always | Bids / offers submitted by suppliers |
| შედეგები | `agency_docs` | always | Results / winner announcement |
| ხელშეკრულება | `agr_docs` | only after contract signed | Contract info + payments |

**Verification:** a bidding-phase tender (app_id 681326) renders 4 tabs (no `agr_docs`);
awarded tenders (636666, 656756, 678938) render all 5. The `key` query param is sent by the
site's JS literally as `key=undefined`; an empty `key=` works identically.

**History correction:** earlier revisions of this file mislabelled `agency_docs` as
"submitted bids ... no longer used" and omitted `app_bids`. In fact `app_bids` is the bids
tab and `agency_docs` is the results tab. The cost-estimate xlsx target remains `app_docs`
section 1.3.

## Endpoint 1: Search Tenders (შესყიდვები filter form)

**Method:** POST
**URL:** https://tenders.procurement.gov.ge/public/library/controller.php
**Content-Type:** application/x-www-form-urlencoded

This is the form behind the `#search_btn` (ძებნა) button on the შესყიდვები tab. Full field
inventory captured live 2026-05-28. **All 22 params are always sent**, even when empty.

> **📌 Authoritative filter & value reference: [`search_filters.md`](search_filters.md) / [`search_filters.json`](search_filters.json)**
> Every filter (Georgian label ↔ backend param) and every dropdown option (internal id ↔
> Georgian name) is **scraped directly from the live `#search_frm`** by
> `provenance/discovery/extract_filters.py` — regenerate any time. The enum tables below were
> **verified against that scrape on 2026-05-29**. If they ever disagree, the scrape wins.
> Remember: `<select>` values are **internal ids**, not the visible numbers (esp. `app_basecode`).

### Exact default POST body (no filters)
```
action=search_app&app_t=0&search=&app_reg_id=&app_shems_id=0&org_a=&app_monac_id=0&org_b=
&app_particip_status_id=0&app_donor_id=0&app_status=0&app_agr_status=0&app_type=0
&app_basecode=0&app_codes=&app_date_type=1&app_date_from=&app_date_tlll=
&app_amount_from=&app_amount_to=&app_currency=2&app_pricelist=0
```

### Request Body Parameters

| Parameter              | UI label (შესყიდვები) | Default | Notes |
|------------------------|------------------------|---------|-------|
| action                 | —                      | search_app | fixed |
| app_t                  | —                      | 0       | fixed |
| search                 | —                      | (empty) | hidden; free-text, normally empty |
| app_reg_id             | განცხადების ნომერი     | (empty) | tender announcement number (e.g. NAT260006121) |
| app_shems_id           | (hidden, set by org_a) | 0       | **buyer** internal id; populated when you pick a suggestion in `org_a` |
| org_a                  | შემსყიდველი            | (empty) | **buyer** name search box (min 3 chars); autocomplete fills `app_shems_id` |
| app_monac_id           | (hidden, set by org_b) | 0       | **supplier** internal id; resolve via `list_org.php?q=<reg_code>&orgtype=1` |
| org_b                  | მიმწოდებელი            | (empty) | **supplier** name search box (min 3 chars); autocomplete fills `app_monac_id`. (Earlier docs wrongly called this "unused".) |
| app_particip_status_id | მიმწოდებლის სტატუსი     | 0       | supplier status — see enum below |
| app_donor_id           | დონორი                 | 0       | donor — see enum below (16 values) |
| app_status             | შესყიდვის სტატუსი       | 0       | procurement status — see enum below (11 values) |
| app_agr_status         | ხელშეკრულების სტატუსი   | 0       | contract status — see enum below |
| app_type               | შესყიდვის ტიპი          | 0       | procurement type — see enum below (16 values) |
| app_basecode           | შესყიდვის კატეგორია     | 0       | CPV category; value = internal id (not the CPV number). 274 `<option>`s = 273 categories + the `0`=all default. |
| app_codes              | (CPV codes textarea)   | (empty) | comma-separated raw CPV codes; alternative to `app_basecode` |
| app_date_type          | თარიღი (type)          | 1       | 1=registration, 2=trade, 3=status date |
| app_date_from          | -დან                   | (empty) | DD.MM.YYYY, day first. Server-side filter. |
| app_date_tlll          | -მდე                   | (empty) | DD.MM.YYYY till. **NOTE: triple-L typo in field name** (`tlll`); input id is `app_date_till` |
| app_amount_from        | თანხით -დან            | (empty) | numeric |
| app_amount_to          | თანხით -მდე            | (empty) | numeric |
| app_currency           | (hidden)               | 2       | currency; 2 observed |
| app_pricelist          | პრეისკურანტი           | 0       | 0=all, 1=with pricelist, 2=without |

### Enum: app_status (შესყიდვის სტატუსი — procurement status)
| Value | Label |
|---|---|
| 0 | (all) |
| 10 | გამოცხადებულია (announced) |
| 20 | წინადადებების მიღება დაწყებულია (bid intake started) |
| 30 | წინადადებების მიღება დასრულებულია (bid intake ended) |
| 40 | შერჩევა/შეფასება (selection/evaluation) |
| 50 | გამარჯვებული გამოვლენილია (winner revealed) |
| 100 | დასრულებულია უარყოფითი შედეგით (ended, negative result) |
| 110 | არ შედგა (did not take place) |
| 120 | შეწყვეტილია (terminated) |
| 130 | მიმდინარეობს ხელშეკრულების მომზადება (contract being prepared) |
| 140 | ხელშეკრულება დადებულია (contract signed) |

### Enum: app_particip_status_id (მიმწოდებლის სტატუსი — supplier status)
| 0 = (all) | 200 = ხელშეკრულება დადებული (contract awarded) | 100 = დისკვალიფიცირებული (disqualified) |

### Enum: app_agr_status (ხელშეკრულების სტატუსი — contract status)
| 0 = (all) | 10 = active | 20 = completed | 30 = failed | 40 = active, warranty period |

### Enum: app_type (შესყიდვის ტიპი — procurement type)
| Value | Code | Value | Code |
|---|---|---|---|
| 9 | NAT (e-tender, no auction) | 3 | GEO (e-procedure) |
| 2 | SPA (e-tender, reverse auction) | 5 | DEP (e-procedure, donor funds) |
| 4 | CON (consolidated tender) | 7 | GRA (grant competition) |
| 6 | CNT (contest) | 22 | PPP (public-private/concession) |
| 11 | MEP (two-stage e-tender) | 20 | B2B (private procurement) |
| 15 | DAP (e-tender, different rules) | 8 | NAT simplified |
| 16 | TEP (e-tender w/ prequalification) | 1 | SPA simplified |
| | | 10 | MEP simplified |
| | | 14 | DAP simplified |

### Enum: app_donor_id (დონორი — donor), 16 values
0=(all), 100=World Bank, 110=EBRD, 120=EIB, 130=ADB, 140=AIIB, 150=KfW,
160=MCC-Georgia, 170=JICA, 180=UNHCR, 190=EU, 195=IFAD, 200=CEB, 205=NEFCO,
206=AFD (French Dev. Agency), 2000=donor rules with govt consent.

### Pagination
After a search, the result set is held **server-side in the session**. Navigation is a **GET**:
```
GET controller.php?action=search_app&page=<next|prev|N>
```
- `btn_next` → `page=next`, `btn_prev` → `page=prev`
- `btn_last` → numeric last-page index (e.g. `page=123707`); `page=<N>` jumps to page N
- 4 rows per page
- Total indicator: a button's text `"<N> ჩანაწერი (გვერდი: <cur>/<total>)"` — regex the digits after `/`
- Pagination buttons: `btn_first`, `btn_prev`, `btn_next`, `btn_last`

### Response
HTML fragment containing:
- `<table id="list_apps_by_subject">` with `<tbody>` result rows
- Each result row: `<tr id="A<NUMERIC_ID>">` — strip leading "A" → app_id for the next call
  (rows also carry `onclick="ShowApp(<app_id>,'',0)"`)
- When no results: single row with text "ჩანაწერები არ არის"

### Extracting tender IDs from response
Select all `tr[id]` inside `#list_apps_by_subject tbody`; strip the leading "A".

---

## Endpoint 2: Get Buyer-Side Cost Estimates (TARGET)

**Method:** GET
**URL:** https://tenders.procurement.gov.ge/public/library/controller.php?action=app_docs&app_id=<NUMERIC_ID>&key=

> ### ⚠️ `app_docs` has TWO response layouts — driven by tender TYPE (+ era)
> Confirmed 2026-05-29 by sampling every type. **Detect the layout structurally; never assume by type.**
>
> | Layout | Tender types | Files | Cost estimate |
> |---|---|---|---|
> | **Sectioned** (below) | **NAT, SPA, CON** | `mode=que` | section `#que150` (1.3) |
> | **Flat** | GEO, DEP, MEP, DAP, TEP, CNT, GRA, B2B | `mode=app` | an `.xlsx` row named `ხარჯთაღრიცხვა`/`ფასების ცხრილი` |
>
> **Era caveat:** old tenders are flat even for NAT/SPA/CON (e.g. `SPA140022279` from 2014 is flat;
> recent SPA is sectioned). **Flat layout** = `<div class="pad4px"><table id="tender_docs">` of attached
> files (cols: file `<a>` | თარიღი/ავტორი), plus an exception-document block and a `<div id="chat">`
> Q&A section. The client's `get_doc_files(app_id)` returns a `DocsTab(layout, files)` that handles both,
> and `.cost_estimate_files` selects the estimate across layouts. Fixtures: `app_docs_612033_sectioned.html`,
> `app_docs_125688_flat.html`, `app_docs_687393_flat_b2b.html`.

### Response Structure (sectioned layout — NAT/SPA/CON)
HTML fragment. Top-level wrapper: `<div id="app_docs">`. Inside, a series of `<section class="question level1">` blocks, one per labelled paragraph of the announcement:

- `#que100` — 1.1 (object name)
- `#que101` — 1.2 (technical specification)
- **`#que150` — 1.3 ფასების ცხრილი/ხარჯთაღრიცხვა ← cost-estimate xlsx files live here**
- `#que200` — 1.4 (delivery deadline)
- …

### Section 1.3 row structure

```html
<section id="que150" class="question level1">
  <p class="q"><span>1.3 ფასების ცხრილი/ხარჯთაღრიცხვა</span></p>
  <div class="answ-file">
    <section>
      <div class="obsolete0">
        <a target="blank" href="https://.../library/files.php?mode=que&file=<FILE_ID>&code=<CODE>">
          <span><img src=".../excel.png"></span>
          <FILENAME>.xlsx
        </a>
      </div>
    </section>
    ... (one <section> per file; observed 14 in a single tender)
  </div>
</section>
```

**`obsolete` flag** (on the inner `<div>`):
- `obsolete0` = current version (keep)
- `obsolete1` = superseded by a newer upload (skip)

**No upload-date column.** Section 1.3 does not show per-file upload timestamps — `document_uploaded_at` is NULL for this path.

**`target="blank"`** (no underscore — quirk of the source markup; ignore).

### Document selection rule
Take every `obsolete0` `.xlsx` anchor under `section#que150 div.answ-file`. No AI selection, no keyword filter — section 1.3 is by definition the cost-estimate list. Empty section → "no estimate found", skip tender.

### File Download URL
```
GET https://tenders.procurement.gov.ge/public/library/files.php?mode=que&file=<FILE_ID>&code=<CODE>
```
- Note `mode=que` (not `mode=app` like the legacy `agency_docs` path). The `mode` value is parsed straight from the anchor's `href` query string.
- `file` and `code` are parsed from the `href` query string.
- Session cookie required (same SPALITE session).
- Returns the binary file directly with correct Content-Type.
- Confirmed working for `.xlsx` (MIME: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).

### Observed XLSX file structure (cost estimates)
Confirmed from tender app_id=636666, file_id=6665929:
- **Multiple sheets:** one summary sheet (კრებსითი) + one sheet per work section (room/area)
- **Summary sheet:** lists totals per section with `=SUM(...)` cross-sheet formulas
- **Work sheets (TARGET):** 2-row merged header at rows 3-4; data rows start at row 5+
  - Col A: item number (N)
  - Col B: work/material name (სამუშაოს დასახელება)
  - Col C: unit of measurement (განზომილება)
  - Col D: norm (ნორმა)
  - Col E: quantity (რაოდენობა)
  - Cols F-G: material unit price + total (მასალა)
  - Cols H-I: labor unit price + total (ხელფასი)
  - Cols J-K: machinery unit price + total (მანქანა-მექანიზმები)
  - Cols L-M: row total (ჯამი)
- **Sub-items:** main item row has work name + quantity; sub-rows (შრომის დანახარჯი, სხვა მანქანები) break it down into labor/machinery components
- **Formulas everywhere:** load with `openpyxl` using `data_only=True` to get cached values; if cache is empty (file never opened in Excel), values will be None — fall back to LLM extraction from PDF version
- **Encoding:** all Georgian text, UTF-8 throughout

---

## Endpoint 2b: Bids tab (შეთავაზებები)

**Method:** GET
**URL:** `...controller.php?action=app_bids&app_id=<ID>&key=`
Fixtures: `tests/fixtures/app_bids_656756.html` (awarded), `app_bids_681326.html` (bidding).

Wrapper `<div id="app_bids">`. Two shapes by tender state:
- **Bid intake open:** a live `#TenderCountdown` widget + `RefreshBids()` auto-refresh
  (`ShowApp(<id>,'',2)`). No bidder amounts shown publicly while open.
- **Awarded / closed:** a `ktable` bidders table — columns პრეტენდენტი (bidder) /
  ბოლო შეთავაზება თანხა/დრო (last bid amount+time) / პირველი შეთავაზება (first bid) /
  შეთავაზებები (count). Rows `id="B<app_id><n>"`. Buttons: `#refrsh`, `#showtdocs`
  (loads technical docs into `#app_tdocs`).

## Endpoint 2c: Results tab (შედეგები)

**Method:** GET
**URL:** `...controller.php?action=agency_docs&app_id=<ID>&key=`
Fixtures: `tests/fixtures/agency_docs_656756.html` (full), `agency_docs_681326.html` (empty).

**Quirk:** the response wrapper is `<div id="agency_docs">` — the **same id used by the
contract tab** (`agr_docs`, Endpoint 3). Distinguish by content, not by wrapper id.

Content is a documents table `<table id="reports" class="ktable">`:
- Columns: `[lock icon]` | document `<a>` | თარიღი/ავტორი (date/author)
- File anchors: `files.php?mode=app&file=<id>&code=<code>` — note **`mode=app`** here
  (the cost-estimate files in `app_docs` 1.3 use `mode=que`).
- Row id pattern: `"<file_id>.<code>.<app_id>"`; classes `doctype<NN>`, `obsolete0/1`;
  icon `file_lock<0|1>.png`.
- **Empty state:** single row "დოკუმენტაცია მიმაგრებული არ არის".

---

## Endpoint 3: Get Contract & Payment Data for a Tender

**Method:** GET  
**URL:** https://tenders.procurement.gov.ge/public/library/controller.php?action=agr_docs&app_id=<NUMERIC_ID>

**Session note:** works in any lang-initialized session (`GET /?lang=ge` first); no
per-tender priming needed (verified headless 2026-05-28). A PHP `Undefined index: lang`
error (line 8) only appears when the session lang state is missing — re-init the session.
The site sends **no `key` param** for this action (other tabs send `key=undefined`).

### Response Structure
HTML fragment. The wrapper `<div id="agency_docs">` (**same id as the results tab** —
distinguish by content) contains 3 child divs:

**Child div 0** (class: ui-state-highlight) — Contract summary:
- Winner company name
- Contract number + signing date + value (format varies, e.g. "N56 30.03.2026 / 19540.8 ლარი")
- Contract validity period

**Child div 1** (class: pad4px) — Documents list:
- `<table id="last_docs">` listing uploaded PDF documents

**Child div 2** (class: ui-state-highlight) — PAYMENT TABLE (this is "div:last-of-type"):
- Contains the payments table

### Payment Table Structure
CSS selector: `#agency_docs > div:last-of-type > table`

Row 0 (header, uses `<td>` not `<th>`):
| Col 0  | Col 1 | Col 2    | Col 3            | Col 4           |
|--------|-------|----------|------------------|-----------------|
| თანხა  | წელი  | კვარტალი | გადახდის თარიღი  | თარიღი/ავტორი   |
| Amount | Year  | Quarter  | Payment Date     | Date/Author     |

Row 1+ (data rows, one per payment received):
| Col 0                          | Col 1 | Col 2 | Col 3      | Col 4              |
|--------------------------------|-------|-------|------------|--------------------|
| "7`500.00 ლარი" + funding src  | 2026  | 1     | 12.03.2026 | 12.03.2026–author  |

**When no payments exist:**
Table has 2 rows: header row + single row with one cell containing "ჩანაწერები არ არის"

**When payments exist:**
Table has header row + N data rows (one per payment).
The LAST data row = most recent payment.
Target: `tbody > tr:nth-last-child(1)` or just the last `<tr>` in the table.

### Parsing the amount (Col 0)
- Full textContent includes Georgian funding source label appended without separator
- The text NODE value (direct text node, not children) = clean amount string: "7`500.00 ლარი"
- Alternatively: extract via regex up to "ლარი"
- To convert to number: remove backtick ` (thousands separator), remove " ლარი", parse as float

### Parsing the payment date (Col 3)
- Format: DD.MM.YYYY (e.g. "12.03.2026")
- Col 4 also contains the date at the start if col 3 parsing fails

---

# Endpoints discovered in the 2026-05-29 audit pass

All of the below were enumerated from the SPA's frontend JS (`library/spa.js` and the inline
JS inside the tab fragments) and confirmed with live `controller.php` calls. They were either
previously `not_discovered` or entirely undocumented.

## Endpoint 4: Company / Org Profile (`action=profile`)

**Method:** GET
**URL:** `controller.php?action=profile&org_id=<ORG_ID>&isdialog=`

Fired by `ShowProfile(org_id)` (spa.js). `org_id` comes from `onclick="ShowProfile(<id>)"`
on the buyer link in `app_main`, on bidder links in `app_bids`, and in the contract summary.

**Response:** HTML fragment, wrapper `<div id="profile_dialog">`, containing a
`table.ktable.with-label` of label/value rows:

| Label (Georgian) | Meaning |
|---|---|
| `შემსყიდველი` **or** `მიმწოდებელი` | role + legal form + `<strong>`org name`</strong>` (the label itself tells you buyer vs supplier) |
| `საიდენტიფიკაციო კოდი` | ID / tax code |
| `ქვეყანა` | country |
| `ქალაქი/დაბა/სოფელი` | city/town/village |
| `მისამართი` | address |
| `ტელეფონი` / `ფაქსი` | phone / fax |
| `ელ-ფოსტა` | email (`mailto:` anchor) |
| `ვებ-გვერდი` | website |

Same shape for buyers and suppliers; the first row's label distinguishes the role.
Fixtures: `profile_buyer.html` (org 42485), `profile_supplier.html` (org 32327).

## Endpoint 5: Status History / Timeline (`action=app_statushistory`)

**Method:** GET — **URL:** `controller.php?action=app_statushistory&app_id=<ID>`

Fired by the `#btn_appstatushistory` ("ქრონოლოგია") button in `app_main`. Wrapper
`<div id="z">`; a `table.with-free-label-history` of `(timestamp DD.MM.YYYY HH:MM, status label)`
rows, **newest first**.

> **Correction to the status model:** this timeline exposes finer-grained statuses than the
> 11-value `app_status` **search** enum — e.g. `დამატებითი რაუნდები დასრულებულია`
> ("additional rounds ended"), which has no `app_status` filter value. Treat the `app_status`
> enum as a *search filter vocabulary*, not the complete tender lifecycle. Fixture:
> `app_statushistory_656756.html`.

## Endpoint 6: Technical Documentation (`action=app_tdocs`)

**Method:** GET — **URL:** `controller.php?action=app_tdocs&app_id=<ID>`

Fired by the `#showtdocs` button in `app_bids`. Wrapper `<div id="tdocs_div">`;
`table#tdocs.ktable` with columns პრეტენდენტი (bidder) / ფაილი (file) / თარიღი (date).
File anchors use **`files.php?mode=tdoc&file=<id>&code=<code>`** — a third `mode` value.
Fixture: `app_tdocs_656756.html`.

## Endpoint 7: Bid History for one bidder (`action=view_bid`)

**Method:** GET — **URL:** `controller.php?action=view_bid&app_id=<ID>&bid_id=<BIDDER_ID>`

Fired by `ShowBidHistory(app_id, bidder_id)` (the "ნახვა" link in the `app_bids` count column).
**Param naming gotcha:** the JS calls `ShowBidHistory(app_id, bidder_id)` then sends
`app_id=<app_id>` and **`bid_id=<bidder_id>`** — `bid_id` is the *bidder's* internal id (the
same id embedded in the bidder row id `B<app_id><bidder_id>`), not a per-bid id.

**Response:** `table.ktable` with columns თანხა (amount, in `<strong>`, backtick thousands) /
თარიღი (datetime). One row per bid that bidder placed. Fixture:
`view_bid_656756_759455.html`.

## Endpoint 8: "Today" feed (`action=today_bids`)

**Method:** GET — **URL:** `controller.php?action=today_bids` (no other params)

Fired by `GoToday()` (spa.js). Header banner
`შესყიდვები, სადაც წინადადებების მიღების ვადა დღეს იწურება ან ამოწურულია (<N>)` =
"procurements whose bid-submission deadline expires today or has expired". Then
`table#today_bids.ktable` with rows `tr[onclick="ShowApp(<app_id>,'',0)"]` in the **same
markup as search results**. **Full list** (158 rows observed) — not capped at 5, not paginated.
Anonymous despite the FB-login gate in the UI. Fixture: `today_bids.html`.

## Endpoint 9: Clarification Q&A thread (`action=show_qa`)

**Method:** GET — **URL:** `controller.php?action=show_qa&app_id=<ID>&chat_id=<CHAT_ID>`

Each documentation section in `app_docs` carries a `<div class="hst-blk" id="hst-<chat_id>">`
and a `.show_reply` toggle button (id `<x>_<app_id>_<chat_id>`). Clicking it fires
`$.get(controller.php, {action:'show_qa', app_id, chat_id})` and fills `#ANS<chat_id>` with the
reply thread for that clarification question. `chat_id` is the numeric part of the `hst-<id>`.

**Empty state:** `<p class="color-2"><hr/>პასუხები არ არის</p>` ("no answers").
**Populated** (captured from legacy tender 125688): one or more answer blocks
`<div class="ui-widget-content ... A type3"><p class="author color-1"><span class="date">…</span>
<buyer org> :: <person></p><p class="chatmessgase activebid1"><answer text></p></div>` — `A type3` =
answer (the question block in `app_docs` `#chat` is `Q type1`). Fixtures:
`show_qa_656756_23295158.html` (empty), `show_qa_125688_25710.html` (populated). Stale session →
`Undefined index: lang` (re-init).

## CPV helper endpoints (back the `app_codes` / `app_basecode` search inputs)

- **`library/cpv/dialog2.php`** (POST `input_id`, `code_str`, optional `cpvlang=2` for English) —
  returns the CPV tree-picker dialog (`<div id="cpv_dialog">` + a dynatree `<div id="tree">`).
  The tree lazy-loads child nodes from `library/cpv/lazy_node.php`. Fixture: `cpv_dialog2.html`.
- **`library/cpv/cpv_search.php`** (GET `q`, `limit`, `timestamp`) — the autocomplete backend for
  the CPV codes text field (pipe/newline rows `code|label`). **Confirmed empty 2026-05-29:** returns
  HTTP 200 / 0-byte body for every query, not only to curl but also when fetched from the live page
  via Playwright (correct cookies + Referer + `X-Requested-With`). The autocomplete fires but yields
  no rows — effectively dead server-side. Use the tree picker for CPV selection.

## File download endpoint (`files.php`) — complete `mode` table

**URL:** `library/files.php?mode=<MODE>&file=<FILE_ID>&code=<CODE>` — returns the binary file
(correct Content-Type) within the SPALITE session. Always parse `mode`/`file`/`code` straight
from the anchor's `href`; never hardcode `mode`.

| mode | Used by | Notes |
|---|---|---|
| `que` | `app_docs` section files (e.g. 1.3 cost-estimate xlsx) | |
| `app` | `agency_docs` (results) files; `agr_docs` supplementary docs | |
| `tdoc` | `app_tdocs` technical-documentation files | discovered 2026-05-29 |
| `contract` | `agr_docs` contract file (`table#last_docs`) | **omits `code`** — href is `mode=contract&file=<id>` only |

## Tender permalink

`https://tenders.procurement.gov.ge/public/?go=<app_id>&lang=ge` — direct deep link to a tender
(shown in `app_main` as "შესყიდვის ბმული"). Equivalent to `ShowApp(app_id)`; underlying data
still flows through `action=application` + the tab endpoints.

## Presence counter (`who.php`)

`library/who.php` → JSON `{osess, guests}` (logged-in sessions / guests). Site-wide presence,
not tender data — documented for completeness.

---

# Out-of-scope module map (boundary)

Per project scope (see README.md / AGENTS.md), the CMR/CON/SMP/ePLAN/MRS/Market-Research modules are **not**
reverse-engineered. For completeness, here is every other entry point the SPA exposes, so the
Procurement-section coverage above is provably exhaustive:

| Module | List entry point | Detail controller |
|---|---|---|
| SSP | `controller.php?action=ssp&org_id=0` → `#dialog` | `library/ssp/ssp_controller.php?action=view&ssp_id=` |
| SMP | `controller.php?action=smp&org_id=0` → `#dialog` | `library/smp/smp_controller.php?action=view&smp_id=` |
| CON | `controller.php?action=con&org_id=0` → `#dialog` | `library/con/con_controller.php?action=application&con_agr_id=` |
| SPLAN | `controller.php?action=splan&org_id=0` → `#dialog` | — |
| QEP / MRS (Market Research) | `qep/qep_controller.php?action=search_qep&search=` → `#app_list` | `library/qep/qep_controller.php?action=application&app_id=` |

## Filtering by procurement category (`app_basecode` vs `app_codes`)

The "შესყიდვის კატეგორია" dropdown is **`app_basecode`**, and its value is an **internal id,
not the CPV number**. There are two different ways to filter by CPV, and they return
**different counts** (verified 2026-05-29):

| Field | Meaning | Example (+ `app_status=130`) |
|---|---|---|
| `app_basecode=<id>` | the dropdown — a **broad category** (all sub-codes of that CPV group) | `45200000` → id `19003` → **182** results |
| `app_codes=45200000` | an **exact** raw CPV code | **77** results |

To mirror the UI dropdown, resolve the CPV number to its `app_basecode` id. The full map of
all 273 categories is in **`docs/cpv_basecode_map.json`** (`{id: {cpv, name}}`), and the client
provides it live: `client.cpv_categories()`, `client.resolve_basecode(45200000)` → `'19003'`,
and `client.search_by_category(45200000, app_status=130)`. Rebuild the map any time from the
homepage `<select id="app_basecode">`.

## Correction: `app_reg_id` search matches the number, not the prefix

`POST search_app` with `app_reg_id=NAT250000613` returns **all** tenders numbered `250000613` —
`GEO250000613`, `CON250000613`, `SPA250000613`, **and** `NAT250000613` — because the filter matches
the numeric part and ignores the `NAT/SPA/…` type prefix. To resolve a specific announcement, filter
the result rows by exact `nat_code`. (Discovered 2026-05-29 while resolving the two sample tenders.)

## Correction: `list_org.php` orgtype used by the UI

The live search form's **buyer** autocomplete (`#org_a`, fills `app_shems_id`) calls
`list_org.php?orgtype=3`; the **supplier** autocomplete (`#org_b`, fills `app_monac_id`) uses
`orgtype=1`. Although `orgtype=2` is the buyer-role registry, the site itself uses **3 for
buyer / 1 for supplier**. To mirror the UI exactly, use those values.

## Resolved: status icon → status value mapping

`stat<N>.png` icon numbers are **identical** to the `app_status` value (1:1): filtering search by
`app_status=10` yields `stat10.png`, `20`→`stat20.png`, … `140`→`stat140.png`. No separate
lookup table needed. Fixture: `stat_icon_mapping.txt`.
