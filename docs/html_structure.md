# HTML Response Structures

## Documentation Tab (`action=app_docs`) — Section 1.3 (TARGET)

Captured 2026-05-12 from tender app_id=656756 during discovery. A representative
sectioned-layout fixture ships at `tests/fixtures/app_docs_612033_sectioned.html`.

```html
<div id="app_docs">
  <div class="ui-tabs-panel">
    <div id="application_tabs" class="ui-tabs">

      <!-- ... earlier sections (1.1, 1.2) ... -->

      <section id="que150" class="question level1">
        <p class="q"><span>1.3 ფასების ცხრილი/ხარჯთაღრიცხვა</span></p>
        <div class="a"><div id="hst-..." class="hst-blk"></div></div>

        <div class="answ-file">

          <!-- One <section> per file. Observed up to 14 in a single tender. -->
          <section>
            <div class="obsolete0">                          <!-- obsolete1 = superseded, skip -->
              <a target="blank"                              <!-- note: "blank" not "_blank" -->
                 href="https://.../library/files.php?mode=que&file=1389067&code=1676913782">
                <span><img src=".../excel.png"></span>
                დანართი #2.xlsx
              </a>
            </div>
          </section>

          <section>
            <div class="obsolete0">
              <a target="blank"
                 href="https://.../library/files.php?mode=que&file=1389068&code=1676913786">
                <span><img src=".../excel.png"></span>
                დანართი #2 - ხარჯთაღრიცხვა #1 - ბორდიურები.xlsx
              </a>
            </div>
          </section>

          <!-- ... -->
        </div>
      </section>

      <!-- ... later sections (1.4 ...) ... -->

    </div>
  </div>
</div>
```

**Parser selector:** `section#que150 div.answ-file > section > div[class^="obsolete"] > a`. Skip anchors whose parent div lacks class `obsolete0`. Extract `mode`/`file`/`code` from the anchor's `href` query string. Filename is the anchor's `get_text(strip=True)`.

**No upload-date column.** Unlike `agency_docs` `<table id="reports">`, section 1.3 has no timestamp per file — `document_uploaded_at` stays NULL on insert.

**§1.3 is one section of many — the sectioned form is large.** Verified live (NAT260011223,
announced): a sectioned `app_docs` is a full structured questionnaire — §1.1 object name,
**§1.2** technical-spec block (carries the buyer's project/geology/structural-assessment PDFs),
**§1.3** the cost estimate (usually 1 `.xlsx`, sometimes several), then annex-template sections
(დანართი N3 გამოცდილება, N4 ამხანაგობა, N6 გრაფიკი), §4.1.x price-adequacy rules, §7.1.1 advance
terms, a **draft contract** (`ხელშეკრულების პროექტი.pdf`), §9.1 contact person, and **§11.1 the
commission ოქმი** approving the conditions. So: files of real value live in sections *other than*
1.3, and `ოქმი`/contract drafts appear here too — not only in Results. The client targets §1.3 for
the estimate; widen the selector if you want the full buyer package.

> The `"დოკუმენტაცია მიმაგრებული არ არის"` string also appears here as the empty-state of the
> per-section **Q&A / clarification** blocks (`hst-blk`), even when documents *are* attached
> elsewhere on the tab. Don't treat that string as "tab has no documents".

### ⚠️ Second layout — FLAT (GEO/DEP/MEP/DAP/TEP/CNT/GRA/B2B, and all legacy tenders)

`app_docs` returns a completely different shape for non-(NAT/SPA/CON) types and for older tenders.
No `#que###` sections — a flat attached-files table + a Q&A block. Captured from `SPA140022279`
(app_id 125688, 2014) and `B2B260000082` (app_id 687393). Files use **`mode=app`** (not `que`).

```html
<div id="app_docs">
  <p><strong>დოკუმენტაცია</strong></p>

  <div class="pad4px">
    <table id="tender_docs" class="ktable">
      <thead><tr><td>მიმაგრებული ფაილები</td><td>თარიღი/ავტორი</td></tr></thead>
      <tbody>
        <tr>
          <td><img ...></td>
          <td><a href="library/files.php?mode=app&file=898066&code=1411412438">
                _ტექნიკური დავალება - ხარჯთაღრიცხვა_asfalti...xlsx</a></td>   <!-- cost estimate lives HERE -->
          <td>22.09.2014 19:00 :: რუსუდან ჩინჩალაძე</td>
        </tr>
        <!-- ... more file rows ... -->
      </tbody>
    </table>
  </div>

  <!-- exception-document block (often empty) -->
  <div><p><strong>გამონაკლისის/გამოცხადების დამადასტურებელი დოკუმენტი</strong></p>
       <p class="color-1">დოკუმენტაცია მიმაგრებული არ არის</p></div>

  <!-- Q&A: supplier questions; answers lazy-load via action=show_qa into #ANS<chat_id> -->
  <div id="chat">
    <p>კითხვის დასმა</p>
    <div class="ui-widget-content ... Q type1">
      <p class="author color-1">23.09.2014 16:39 შპს ... :: ...</p>
      <p class="chatmessgase activebid1">გთხოვთ ატვირთოთ ... (the question text)</p>
      <div id="ANS25687"></div>           <!-- filled by show_qa(app_id, chat_id=25687) -->
    </div>
    <!-- "გამოხმაურება (N)" = N responses -->
  </div>
</div>
```

**Parser notes (flat):** `table#tender_docs tbody tr` with an `a[href*='files.php']` → `(filename, mode=app, date/author)`. The cost-estimate xlsx is a normal row — match by name (`ხარჯთაღრიცხვა` or `ფასების ცხრილი`). `get_doc_files()` auto-detects layout; `DocsTab.cost_estimate_files` works for both.

## Main Tab (`action=app_main`) — Tender Overview

Captured 2026-05-29 from tender app_id=656756 (awarded state).

```html
<div id="app_main">
  <div id="print_area">
    <table class="ktable with-label">
      <tbody>
        <!-- Key-value rows — td[0]=label, td[1]=value -->
        <tr>
          <td>შესყიდვის ტიპი</td>
          <td>ელექტრონული ტენდერი აუქციონის გარეშე(NAT)</td>
        </tr>
        <tr>
          <td>განცხადების ნომერი</td>
          <td><strong>NAT250021073</strong></td>
        </tr>
        <tr>
          <td>შესყიდვის სტატუსი</td>
          <td><img src="images/statuses/stat140.png"> ხელშეკრულება დადებულია</td>
        </tr>
        <tr>
          <td>შემსყიდველი</td>
          <!-- ShowProfile(org_id) — buyer name + org_id for profile lookup -->
          <td><a href="javascript:void(0)" onclick="ShowProfile(42485)">
            <img src="images/profile24.png"> თვითმმართველი ქალაქი ქალაქ რუსთავის მუნიციპალიტეტი
          </a></td>
        </tr>
        <tr>
          <td>შესყიდვის გამოცხადების თარიღი</td>
          <td>24.11.2025 12:38</td>
        </tr>
        <tr>
          <td>წინადადებების მიღება იწყება</td>
          <td>02.12.2025 00:03</td>
        </tr>
        <tr>
          <td>წინადადებების მიღება მთავრდება</td>  <!-- bid deadline -->
          <td>05.12.2025 12:30</td>
        </tr>
        <tr>
          <td>შესყიდვის სავარაუდო ღირებულება</td>
          <td><span>132`439.00 GEL</span>          <!-- backtick thousands sep -->
        </tr>
        <tr>
          <td>შესყიდვის კატეგორია</td>
          <td class="subject_name"><strong></strong> 45100000-სამშენებლო უბნის მოსამზადებელი სამუშაოები</td>
        </tr>
        <!-- colspan=2 row: description text -->
        <tr>
          <td colspan="2">
            <div class="blabla">ქალაქ რუსთავში, შარტავას გამზირზე ... (free text description)</div>
          </td>
        </tr>
        <!-- ... more rows (delivery deadline, guarantee amount, etc.) ... -->
      </tbody>
    </table>
  </div>

  <!-- Created / last-modified timestamps -->
  <ul class="date">
    <li>განცხადების ჩაწერა: Author Name :: DD.MM.YYYY HH:MM</li>
    <li>ბოლო შესწორება: Author Name :: DD.MM.YYYY HH:MM</li>
  </ul>

  <!-- History button fires action=app_statushistory -> fills div#history -->
  <div class="pad4px">
    <button id="btn_appstatushistory">ქრონოლოგია</button>
  </div>
  <div id="history"></div>   <!-- filled lazily by $.get(app_statushistory) -->
</div>
```

**Parser notes:**
- Iterate `table.ktable.with-label tbody tr` and match by `td[0].text.strip()`.
- Status icon is `td[1] img[src]` → `stat<N>.png`; N maps to `app_status` enum value.
- Buyer `org_id` is in `onclick="ShowProfile(<id>)"` — useful for profile lookups.
- Estimated value: strip backtick, strip ` GEL`/` ლარი`, parse as float.
- **Currency label is inconsistent** — the same field renders `GEL` on some views/tenders and
  `ლარი` on others (e.g. the contract tab). Strip *either* suffix; don't assume one.
- **Additional rows seen live** (present per tender, match by label — don't assume a fixed set):
  წინადადება წარმოდგენილი უნდა იყოს (VAT basis: დღგ-ს გათვალისწინებით / გარეშე),
  კლასიფიკატორის კოდები (CPV code list), მოწოდების ვადა (delivery term),
  შესყიდვის რაოდენობა ან მოცულობა (quantity/volume), დამატებითი ინფორმაცია (free text),
  **შეთავაზების ფასის კლების ბიჯი** (price-reduction step), **გარანტიის ოდენობა** (bid-guarantee
  amount) and **გარანტიის მოქმედების ვადა** (guarantee validity, days). Treat the table as an
  open-ended label→value map, not a fixed schema.
- **The label set itself varies by tender TYPE (verified live) — do not hardcode `შემსყიდველი`
  or `შესყიდვის სავარაუდო ღირებულება`:**
  - **Grant (GRA) / donor (DEP)** add `დონორი` (donor), `პროგრამის დასახელება` (program),
    `ლოტის დასახალება / N:` (lot), `პროექტის ხანგრძლივობა` (project duration). **GRA replaces the
    buyer row `შემსყიდველი` with `ადმინისტრირებას უწევს` (administered by)** — a buyer lookup keyed
    on `შემსყიდველი` returns nothing for GRA. GRA also omits category/CPV, guarantee and bid-step.
  - **Price-list (პრეისკურანტი) tenders** rename the value row to
    **`პრეისკურანტის სავარაუდო ღირებულება`** and add **`შესყიდვის ობიექტის სახელშეკრულებო ღირებულება`**
    — an exact match on `შესყიდვის სავარაუდო ღირებულება` misses the estimate here.
  - **B2B** omits the guarantee rows (shorter table); keeps `შემსყიდველი`, category, bid-step.

---

## Bids Tab (`action=app_bids`) — Awarded / Closed State

Captured 2026-05-29 from tender app_id=656756. For the live-bidding state see fixture `app_bids_681326.html` (shows `#TenderCountdown` instead of the table below).

```html
<div id="app_bids">
  <p align="right">
    <button id="refrsh">გვერდის განახლება</button>      <!-- refreshes tab -->
    <button id="showtdocs">ტექნიკური დოკუმენტაცია</button>  <!-- fires action=app_tdocs -->
  </p>
  <div id="app_tdocs" style="margin-top:3em;"></div>   <!-- filled lazily -->

  <table class="ktable">
    <thead>
      <tr class="ui-widget-header">
        <td>პრეტენდენტი</td>                  <!-- bidder -->
        <td>ბოლო შეთავაზება<br/>თანხა/დრო</td> <!-- last bid: amount / datetime -->
        <td>პირველი შეთავაზება<br/>თანხა/დრო</td><!-- first bid: amount / datetime -->
        <td>შეთავაზებები</td>                  <!-- bid count -->
      </tr>
    </thead>
    <tbody>
      <!-- Row id = B<app_id><bidder_internal_id> -->
      <tr id="B656756759455">
        <td class="activebid1">
          <a href="#" onclick="ShowProfile(32327)"><img src="images/profile24.png"></a>
          <span class="color-1">შპს სამება</span>  <!-- winner marked activebid1 -->
        </td>
        <td class="activebid1">
          <strong>130`439.00</strong>&nbsp;<br/>
          <span class="date">04.12.2025 14:28</span>
        </td>
        <td class="activebid1">
          130`439.00&nbsp;<br/>
          <span class="date">04.12.2025 14:28</span>
        </td>
        <td>
          [1] &nbsp;
          <a onclick="ShowBidHistory(656756, 759455)">ნახვა</a>  <!-- bid count + history link -->
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

**Parser notes:**
- Row `id` format: `B<app_id><bidder_id>` — strip leading `B<app_id>` to get bidder internal id.
- Winner row has `class="activebid1"` on its cells.
- Amount: `strong` text — strip backtick thousands sep.
- Bid history: `ShowBidHistory(app_id, bidder_id)` → `action=view_bid` (documented below).
- Live-bidding state: `#TenderCountdown` widget replaces the table; `RefreshBids()` auto-polls.
- **Bidders show from selection/evaluation onward (status 40+), not only when awarded** —
  verified live on a B2B at `შერჩევა/შეფასება` with 6 bidders already listed.
- **Type variants (verified live):**
  - **Donor tenders (DEP)** render an *extra* simple table — `პრეტენდენტი | შეთავაზებული თანხა |
    თარიღი` (single submitted offer, no auction rounds) — **before** the standard table. Both
    list the same bidders. Parse the standard (`tr[id^="B"]`) table; the extra one is a no-rounds
    summary.
  - **Grant tenders (GRA)** use the header `განმცხადებელი` (applicant) instead of `პრეტენდენტი`.
    Don't match the bidder column by that exact header text.
- **Three distinct states** (verified live): (1) *announced but bidding not yet open* → the
  bidders table renders with its header and an **empty body** (no countdown, no rows); (2)
  *bidding open* → `#TenderCountdown`; (3) *closed* → the populated table above. So an empty
  bids table does not mean "no bids" — check the tender status first.
- The `ტექნიკური დოკუმენტაცია` button (`#showtdocs`) and `გვერდის განახლება` (`#refrsh`) are
  always present regardless of state.

---

## Results Tab (`action=agency_docs`) — Documents Table

Captured 2026-05-29 from tender app_id=656756 (awarded, multiple result files).

```html
<div id="agency_docs">   <!-- SAME wrapper id as agr_docs — distinguish by content -->
  <div class="pad4px">
    <table id="reports" class="ktable">
      <colgroup>
        <col width="24">  <!-- lock icon -->
        <col>             <!-- filename link -->
        <col width="30%"> <!-- date/author -->
      </colgroup>
      <thead>
        <tr class="ui-widget-header">
          <td colspan="2">დოკუმენტი</td>
          <td>თარიღი/ავტორი</td>
        </tr>
      </thead>
      <tbody>
        <!-- Row id = "<file_id>.<code>.<app_id>" -->
        <tr id="6777933.1765299560.656756">
          <td><img src="images/file_lock0.png"></td>  <!-- lock0=public, lock1=locked -->
          <!-- td class: doctype<NN> obsolete<0|1>; obsolete0=current, obsolete1=superseded -->
          <td class="doctype30 obsolete0">
            <a target="blank" href="library/files.php?mode=app&file=6777933&code=1765299560">
              NAT250021073_ინტერესთა კონფლიქტი.pdf
            </a>
          </td>
          <td class="date">09.12.2025 16:59 :: ლელა ღუბიანური</td>
        </tr>
        <!-- ... more rows ... -->

        <!-- Empty state (no results uploaded): -->
        <tr>
          <td colspan="3">დოკუმენტაცია მიმაგრებული არ არის</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

**Parser notes:**
- Row `id` format: `<file_id>.<code>.<app_id>` — split on `.` to extract components.
- Skip rows with `obsolete1` class (superseded versions).
- Download URL: `files.php?mode=app&file=<file_id>&code=<code>` — note `mode=app` (not `mode=que`).
- `doctype<NN>` class encodes a coarse document group. Sampled live across 7 tenders
  (2018→2026), only three values seen:
  - **`doctype30`** — procedural / agency decisions: ინტერესთა კონფლიქტი (conflict of
    interest), ოქმი (commission minutes), წერილი (letters), შეტყობინება (notifications).
  - **`doctype40`** — a single commission letter/protocol (typically 1 per tender).
  - **`doctype50`** — agency decision/closure protocols, e.g. `შესყიდვის შეწყვეტის ოქმი`
    (termination protocol, on terminated tenders) and TEP/prequalification result protocols.
  - **`doctype100`** — contract-stage / contractor-submitted bundle: ხელშეკრულება
    (the signed contract), the awarded **ხარჯთაღრიცხვა / ფასების ცხრილი** (cost estimate /
    price schedule), გეგმა-გრაფიკი (work schedule), გამოცდილება, პერსონალი, მინდობილობა,
    დანართი N1/N3/N5, drawings, etc.
  - **`doctype` is NOT a reliable cost-estimate filter** — `doctype100` mixes the price
    sheet with everything else contractual. Treat it as a hint, not a selector.

### Finding the awarded contractor's cost estimate (ხარჯთაღრიცხვა / ფასების ცხრილი)

This is the **highest-value file in the whole tender**: the **awarded contractor's** price
schedule, surfaced in the Results tab (usually `.xlsx`, often with a `-signed.pdf` countersigned
copy alongside). Unlike the buyer's `app_docs` §1.3 estimate — which lists required materials but
frequently omits prices or carries placeholder/inaccurate ones — this file contains the
contractor's real per-material pricing.

> Note: the *content* is the contractor's pricing, but the row author/uploader is often an
> agency officer who publishes the whole result package (the same person frequently uploads the
> commission ოქმი in the same batch). Treat the file as "the contractor's cost estimate as
> published in Results", not as proof of who clicked upload.

**It appears only late in the lifecycle.** Verified live across states: at status 130
(*contract being prepared*) the Results tab carries **only procedural docs** (ინტერესთა
კონფლიქტი, ოქმი, მიმართვა) — **no contractor cost sheet yet**. The cost estimate and the rest
of the contractor bundle (personnel, power-of-attorney, experience, schedule, extracts) appear
only once the contract is concluded (**status 140**). On a freshly announced tender (status 10)
Results is empty (`დოკუმენტაცია მიმაგრებული არ არის`).

**It is not always present, and the filename is unreliable.** Sampled live:
- Sometimes the keyword is in the name: `ხარჯთაღრიცხვა მინი მოედანი.xlsx`,
  `ხარჯთაღრიცხვა (დანართი N1).xlsx`.
- Often it is **not**: the cost sheet is named by location or annex number with no keyword
  at all — e.g. `ფონიჭალა 3 N26 ფეხბურთის მოედანი.xlsx`, `ვასაძის ქუჩა - boloi.xlsx`,
  `დანართი N3- bolo.xlsx`, `... დამუშავებული ასატვირთი - 3.xlsx`.
- **Spelling is not safe to rely on either** — a real live file is named
  `ხარჯთაღრიხცვა საბავშვო მოედანი.xlsx` (note the transposed letters `ხც` vs `ცხ`), which an
  exact `ხარჯთაღრიცხვა` match silently drops.
- Multiple cost sheets per tender are common (one `.xlsx` per object/lot, often each paired
  with a countersigned `-signed.pdf`).
- Some tenders ship no contractor cost sheet in Results at all (only contracts/protocols).

**So we cannot identify it in advance by name or doctype.** Recommended approach:
1. **Cheap pre-filter** — keep `doctype100` rows ending in `.xls`/`.xlsx` (and any name
   matching `ხარჯთაღრიცხვა` / `ფასების ცხრილი`) as strong candidates.
2. **AI/content classification for the rest** — download the candidate spreadsheets and let
   a model inspect the sheet (column headers like ერთე. ფასი / ღირებულება / რაოდენობა,
   line-item structure) to decide whether it is a price schedule. This is the only robust
   way to catch the location-named / `bolo` / `დანართი N#` cases that carry no keyword.

> ⚠️ A pure name-keyword match will silently miss a large share of real cost estimates.
> Content inspection (AI) is required for complete coverage.

---

## Last Events Feed (`action=lastevents`)

Captured 2026-05-29. Always returns exactly 5 most-recent status-change events.

```html
<!-- Title banner -->
<div class="ui-state-highlight ui-corner-all">
  განცხადებების სტატუსების ბოლო 5 ცვლილება
</div>

<table id="lastevents" class="ktable">
  <tbody>
    <!-- Each row is a status-change event; onclick opens the tender -->
    <tr onclick="$('#app_list').hide();ShowApp(685929,'',0)">
      <td>
        <p class="status">
          წინადადებების მიღება დაწყებულია
          <span class="color-1">29.05.2026 00:06</span>   <!-- event timestamp -->
        </p>
        <img src="images/statuses/stat20.png">&nbsp;
        <strong>NAT260009861</strong><br/><br/>
        შემსყიდველი: <strong>ჩოხატაურის მუნიციპალიტეტი</strong><br/>
        კატეგორია: <span class="color-2">45200000</span>
      </td>
    </tr>
    <!-- ... 4 more rows ... -->
  </tbody>
</table>
```

**Parser notes:**
- `app_id` is in the `onclick` attribute: `ShowApp(<app_id>,'',0)`.
- Status text is `p.status` text node (before the `span.color-1`).
- Timestamp is `p.status span.color-1` text: `DD.MM.YYYY HH:MM`.
- Stat icon: `img[src]` → `statuses/stat<N>.png`.
- NAT code: `strong` (first one in the td).
- Buyer: text after `შემსყიდველი:` label → inner `strong`.
- CPV: `span.color-2` text.

---

## Search Results Page HTML

```html
<!-- Pagination buttons + info (returned as part of the HTML fragment) -->
<button id="btn_first"><span>...</span></button>
<button id="btn_prev"><span>...</span></button>
<button><span>45873 ჩანაწერი (გვერდი: 1/11469)</span></button>
<button id="btn_next"><span>...</span></button>
<button id="btn_last"><span>...</span></button>

<!-- Results table -->
<table id="list_apps_by_subject" class="ktable">
  <tbody>
    <tr id="A678938">
      <td valign="top">
        <img src="images/statuses/stat10.png">
      </td>
      <td>
        <p class="status">ხელშეკრულება დადებულია<br>
          მიმდინარე ხელშეკრულება
          გამარჯვებული: ზოდი პლიუსი
          მონაწილეთა რაოდენობა - 1
        </p>
        <p class="lbl color-1">კერძო შესყიდვა(B2B)</p>
        <p>განცხადების ნომერი: <strong>B2B260000023</strong></p>
        <p>შესყიდვის გამოცხადების თარიღი: 20.03.2026</p>
        <p>წინადადებების მიღების ვადა: 26.03.2026</p>
        <p>შემსყიდველი: <strong>შპს დელტა მშენებელი</strong></p>
        <p>შესყიდვის კატეგორია: <span class="color-2"><strong></strong> 44900000-...</span></p>
        <p>შესყიდვის სავარაუდო ღირებულება: <span class="color-1"><strong>24`364.00</strong> ლარი</span></p>
      </td>
    </tr>
    <!-- more tr rows... -->
  </tbody>
</table>
```

## Contract/Payment Page HTML

```html
<div id="agency_docs">

  <!-- DIV 0: Contract summary -->
  <div class="ui-state-highlight ui-corner-all">
    <!-- Contract status label + author/date, then a days-to-expiry countdown -->
    მიმდინარე ხელშეკრულება        <!-- contract status (current / executed / unfulfilled / ...) -->
    Author Name :: 30.04.2026
    <strong>91</strong> დღე ხელშეკრულების მოქმედების ვადის ამოწურვამდე  <!-- days until expiry -->
    <!-- Winner name, contract number/amount, validity dates, contract date -->
    ზოდი პლიუსი
    ნომერი/თანხა: N56 30.03.2026 / 19540.8 ლარი
    ხელშეკრულება ძალაშია: 30.03.2026 - 31.05.2026
  </div>

  <!-- DIV 1: Documents list -->
  <div class="pad4px">
    <table id="last_docs">
      <tbody>
        <tr>
          <td>დოკუმენტი</td>
          <td>თარიღი/ავტორი</td>
        </tr>
        <tr>
          <td>1.</td>
          <td></td>
          <td>filename.pdf</td>
          <td>26.03.2026 14:35 :: Author Name</td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- DIV 2: Payment table (div:last-of-type) — TARGET -->
  <div class="ui-state-highlight ui-corner-all">
    <table>
      <tbody>
        <!-- Header row (uses td, not th) -->
        <tr>
          <td>თანხა</td>
          <td>წელი</td>
          <td>კვარტალი</td>
          <td>გადახდის თარიღი</td>
          <td>თარიღი/ავტორი</td>
        </tr>
        <!-- Data row (one per payment) — may be multiple -->
        <tr>
          <td>7`500.00 ლარისაკუთარი შემოსავლები</td>  <!-- col 0: amount + funding (no separator) -->
          <td>2026</td>                                  <!-- col 1: year -->
          <td>1</td>                                     <!-- col 2: quarter -->
          <td>12.03.2026</td>                            <!-- col 3: payment date DD.MM.YYYY -->
          <td>12.03.2026–Author Name</td>                <!-- col 4: date + author -->
        </tr>
        <!-- OR if no payments: -->
        <tr>
          <td colspan="...">ჩანაწერები არ არის</td>
        </tr>
      </tbody>
    </table>
  </div>

</div>
```

**Contract document link (`table#last_docs`)** uses `files.php?mode=contract&file=<id>` — note
**no `code` param** (unlike `mode=que`/`app`/`tdoc`, which all carry `code`). Files *inside* the
documents list still use `mode=app&file=&code=` (e.g. `ავანსი.pdf`).

**Payment block header (above the payment table)** carries a `ფაქტობრივი გადახდები` heading and a
summary line: `ხელშეკრულების თანხა: <amount>` and `გადახდილი თანხა: <amount> (<pct>%)` — a quick
contract-amount-vs-paid figure without summing the rows. Each payment row's amount cell also
embeds the funding source (e.g. `ადგილობრივი თვითმართველი ერთეულის ბიუჯეტი`, `საკუთარი შემოსავლები`)
and may be tagged `(ავანსი)` for advances.

---

## Org Profile (`action=profile`) — captured 2026-05-29

Buyer fixture `profile_buyer.html` (org 42485); supplier `profile_supplier.html` (org 32327).

```html
<div id="profile_dialog" title="<img src='images/profile24.png'> პროფილი">
  <table class="ktable with-label">
    <!-- First row label = role: 'შემსყიდველი' (buyer) or 'მიმწოდებელი' (supplier) -->
    <tr><td><strong>შემსყიდველი</strong></td>
        <td><label>საჯარო სამართლის იურიდიული პირი (სსიპ)</label><br/>
            <strong>თვითმმართველი ქალაქი ქალაქ რუსთავის მუნიციპალიტეტი</strong></td></tr>
    <tr><td>საიდენტიფიკაციო კოდი</td><td>216433287</td></tr>
    <tr><td>ქვეყანა</td><td>საქართველო</td></tr>
    <tr><td>ქალაქი/დაბა/სოფელი</td><td>ქალაქი რუსთავი</td></tr>
    <tr><td>მისამართი</td><td>ქ.რუსთავი კოსტავას გამზ. N20</td></tr>
    <tr><td>ტელეფონი</td><td>+995341255231</td></tr>
    <tr><td>ფაქსი</td><td></td></tr>
    <tr><td>ელ-ფოსტა</td><td><a href="mailto:rustavicity@procurement.gov.ge">...</a></td></tr>
    <tr><td>ვებ-გვერდი</td><td>www.rustavi.gov.ge</td></tr>
  </table>
</div>
```

**Parser notes:** iterate `#profile_dialog table tr`, two-`td` rows → `{label: value}`. The first
row's label (`შემსყიდველი` vs `მიმწოდებელი`) gives the org role.

---

## Status History (`action=app_statushistory`) — captured 2026-05-29

Fixture `app_statushistory_656756.html`.

```html
<div class="ui-widget-content ui-corner-all pad4px" id="z">
  <p class="paratitle">ქრონოლოგია <button id="nohist"></button></p>
  <table class="with-free-label-history">
    <tbody>
      <tr><td width="140">17.12.2025 15:58</td><td>ხელშეკრულება დადებულია</td></tr>
      <tr><td width="140">11.12.2025 17:47</td><td>მიმდინარეობს ხელშეკრულების მომზადება</td></tr>
      <tr><td width="140">05.12.2025 12:30</td><td>დამატებითი რაუნდები დასრულებულია</td></tr>
      <!-- ... newest-first; note statuses absent from the app_status search enum ... -->
      <tr><td width="140">24.11.2025 12:38</td><td>გამოცხადებულია</td></tr>
    </tbody>
  </table>
</div>
```

**Parser notes:** `#z table tbody tr` → `(td[0]=timestamp, td[1]=status)`, newest first. This is
the authoritative lifecycle; it includes intermediate statuses the search filter enum omits.

---

## Technical Documentation (`action=app_tdocs`) — captured 2026-05-29

Fixture `app_tdocs_656756.html`.

```html
<div class="ui-widget-content ui-corner-all pad4px" id="tdocs_div">
  <p class="paratitle">ტექნიკური დოკუმენტაცია <button id="hidetdocs"></button></p>
  <table class="ktable" id="tdocs">
    <thead><tr class="ui-widget-header">
      <td>პრეტენდენტი</td><td>ფაილი</td><td>თარიღი</td>
    </tr></thead>
    <tbody>
      <tr>
        <td>შპს სამება</td>
        <td><a href="library/files.php?mode=tdoc&file=3587019&code=1764796805">file.pdf</a></td>
        <td>...</td>
      </tr>
      <!-- ... one row per bidder file ... -->
    </tbody>
  </table>
</div>
```

**Parser notes:** `#tdocs tbody tr` → bidder / file anchor (`mode=tdoc`) / date.

**This is a primary BID-STAGE pricing source (verified live).** The files here are the bidders'
own priced submissions, keyed by bidder:
- **Price-list (პრეისკურანტი) tenders** — the bidder's unit-price catalog lives here as a
  `... პრეისკურანტი .xlsx` (e.g. `მომსახურების პრეისკურანტი.xlsx`). It is **not** in the bids table
  or `view_bid` (which only show a single sum + date) — `app_tdocs` is the only place to get the
  per-line prices.
- **MEP / works tenders** — bidders attach their `ხარჯთაღრიცხვა-signed.pdf` and a `წინადადება .xlsx`
  (priced proposal) here.

So `app_tdocs` is the bid-time analogue of the awarded contractor cost estimate in `agency_docs`:
same caveats apply (filename unreliable, spelling varies) → use content/AI classification, not a
name match, to find the priced sheet.

---

## Bid History (`action=view_bid`) — captured 2026-05-29

Fixture `view_bid_656756_759455.html`. Returned by `ShowBidHistory(app_id, bidder_id)` →
`controller.php?action=view_bid&app_id=<app_id>&bid_id=<bidder_id>`.

```html
<div class="pad4px">
  <table class="ktable">
    <thead><tr class="ui-widget-header"><td>თანხა</td><td>თარიღი</td></tr></thead>
    <tbody>
      <tr><td><strong>130`439.00</strong></td><td class="date">04.12.2025 14:28</td></tr>
      <!-- one row per bid this bidder placed -->
    </tbody>
  </table>
</div>
```

**Parser notes:** rows = `(amount strong, datetime)`. `bid_id` in the URL is the **bidder's**
internal id (the `<bidder_id>` part of the `B<app_id><bidder_id>` row id in `app_bids`).

---

## "Today" feed (`action=today_bids`) — captured 2026-05-29

Fixture `today_bids.html`. Full list (158 rows) of tenders whose bid deadline expires today.

```html
<div class="ui-state-highlight ui-corner-all">
  შესყიდვები, სადაც წინადადებების მიღების ვადა დღეს იწურება ან ამოწურულია (<strong>158</strong>)
</div>
<table id="today_bids" class="ktable">
  <tbody>
    <tr onclick="$('#app_list').hide();ShowApp(685705,'',0)">
      <td valign="top"><img src="images/statuses/stat20.png"></td>
      <td>
        <p class="color-1"><strong>SPA260000449</strong></p>
        <p class="lbl color-1">ელექტრონული ტენდერი(SPA)</p>
        <p>შემსყიდველი: <strong>სს "საქართველოს სახელმწიფო ელექტროსისტემა"</strong></p>
        <p>შესყიდვის კატეგორია: <span class="color-2">44100000-...</span></p>
        <p>წინადადებების მიღების ვადა: <strong>29.05.2026 12:00</strong></p>
        <p>შესყიდვის სავარაუდო ღირებულება: <span class="color-1"><strong>12584</strong> ლარი</span></p>
      </td>
    </tr>
    <!-- ... ~158 rows; same markup as search results ... -->
  </tbody>
</table>
```

**Parser notes:** `table#today_bids tbody tr[onclick]` — reuse the search-row parser
(`app_id` from `ShowApp(...)`, NAT code in first `strong`, buyer after `შემსყიდველი:`, etc.).
The banner `<strong>` holds the total count.

---

## CPV tree picker (`cpv/dialog2.php`) — captured 2026-05-29

Fixture `cpv_dialog2.html` (POST `input_id=cpv_codes_search&code_str=`; add `cpvlang=2` for English).

```html
<div id="cpv_dialog" title="...">
  <div id="tree"></div>   <!-- dynatree; lazy-loads nodes -->
  <script>
    $("#tree").dynatree({ initAjax: { url: "library/cpv/lazy_node.php" }, ... });
  </script>
</div>
```

The autocomplete sibling `cpv/cpv_search.php?q=&limit=` returned an empty body to direct requests
(2026-05-29) — see api_reference.md note; prefer the tree picker.
