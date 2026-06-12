"""High-level Procurement (შესყიდვები) client + HTML parsers.

Parsers are deliberately lenient: the portal returns HTML fragments whose exact
markup varies by tender state. Selectors are documented in docs/api_reference.md.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .errors import ParseError, PortalError
from .models import (
    Bid,
    BidHistoryEntry,
    BidsTab,
    Company,
    Contract,
    DocFile,
    DocsTab,
    OrgProfile,
    Payment,
    QaMessage,
    QaThread,
    SearchPage,
    StatusEvent,
    TechDoc,
    TenderMain,
    TenderRow,
    TenderTabs,
)
from .session import PortalSession, make_session

# Exact default search body (every key is always sent). Override per-search.
SEARCH_DEFAULTS: dict[str, str] = {
    "action": "search_app", "app_t": "0", "search": "", "app_reg_id": "",
    "app_shems_id": "0", "org_a": "", "app_monac_id": "0", "org_b": "",
    "app_particip_status_id": "0", "app_donor_id": "0", "app_status": "0",
    "app_agr_status": "0", "app_type": "0", "app_basecode": "0", "app_codes": "",
    "app_date_type": "1", "app_date_from": "", "app_date_tlll": "",
    "app_amount_from": "", "app_amount_to": "", "app_currency": "2", "app_pricelist": "0",
}

DETAIL_ACTIONS = ("app_main", "app_docs", "app_bids", "agency_docs", "agr_docs")
_PAGE_RE = re.compile(r"(\d+)\s*ჩანაწერი.*?გვერდი:\s*(\d+)\s*/\s*(\d+)")


class ProcurementClient:
    """One client = one portal session = ONE active server-side search result set.

    Pagination (next_page/goto_page) walks state held in the portal's PHP session,
    so interleaving two searches on one client corrupts paging — use one client per
    concurrent search. Do not share a client across threads.
    """

    def __init__(self, session: PortalSession | None = None):
        self.s = session or make_session()
        self._searched = False

    # --- company lookup -------------------------------------------------

    def lookup_company(self, q: str, orgtype: int = 1) -> list[Company]:
        text = self.s.list_org(q, orgtype=orgtype)
        out: list[Company] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                out.append(Company(internal_id=parts[0], name=parts[1], reg_code=parts[2]))
        return out

    # --- search ---------------------------------------------------------

    def search_tenders(self, **filters) -> SearchPage:
        """Run a search. Pass any search_app param as a keyword to override its default.

        Convenience aliases: supplier_id -> app_monac_id, buyer_id -> app_shems_id,
        date_from -> app_date_from, date_to -> app_date_tlll.
        """
        aliases = {
            "supplier_id": "app_monac_id", "buyer_id": "app_shems_id",
            "date_from": "app_date_from", "date_to": "app_date_tlll",
        }
        body = dict(SEARCH_DEFAULTS)
        for k, v in filters.items():
            key = aliases.get(k, k)
            if key not in SEARCH_DEFAULTS:
                raise KeyError(f"unknown search param: {k!r}")
            body[key] = str(v)
        page = self._parse_search(self.s.post_search(body))
        self._searched = True
        return page

    _cpv_cat_cache: dict | None = None

    def cpv_categories(self, refresh: bool = False) -> dict[str, dict]:
        """Map of the 'შესყიდვის კატეგორია' dropdown (app_basecode), fetched live.

        Returns {cpv_code: {"id": <app_basecode value>, "name": <Georgian label>}}.
        app_basecode wants this internal id, NOT the CPV number. Cached per client.
        """
        if self._cpv_cat_cache is not None and not refresh:
            return self._cpv_cat_cache
        from .session import HOME
        soup = BeautifulSoup(self.s._raw_get(HOME).text, "lxml")
        sel = soup.find("select", id="app_basecode")
        out: dict[str, dict] = {}
        for o in (sel.find_all("option") if sel else []):
            val, label = o.get("value"), o.get_text(strip=True)
            if not val or val == "0" or not label:
                continue
            m = re.match(r"(\d+)\s*-\s*(.*)", label)
            cpv = m.group(1) if m else label
            out[cpv] = {"id": val, "name": (m.group(2).strip() if m else label)}
        self._cpv_cat_cache = out
        return out

    def resolve_basecode(self, cpv_code: str | int) -> str | None:
        """CPV category number (e.g. 45200000) -> app_basecode internal id (e.g. '19003')."""
        cat = self.cpv_categories().get(str(cpv_code))
        return cat["id"] if cat else None

    def search_by_category(self, cpv_code: str | int, **filters) -> SearchPage:
        """Search using the 'შესყიდვის კატეგორია' dropdown (broad category, all sub-codes).

        Resolves the CPV number to its app_basecode id. For an EXACT code instead, pass
        app_codes=<code> to search_tenders().
        """
        bid = self.resolve_basecode(cpv_code)
        if bid is None:
            raise KeyError(f"no app_basecode category for CPV {cpv_code!r}")
        return self.search_tenders(app_basecode=bid, **filters)

    def next_page(self) -> SearchPage:
        self._require_search()
        return self._parse_search(self.s.page("next"))

    def goto_page(self, n: int) -> SearchPage:
        self._require_search()
        return self._parse_search(self.s.page(n))

    def _require_search(self) -> None:
        if not getattr(self, "_searched", False):
            raise PortalError(
                "no active search on this client — pagination walks server-side "
                "session state, so call search_tenders() first"
            )

    @staticmethod
    def _parse_search(html: str) -> SearchPage:
        soup = BeautifulSoup(html, "lxml")
        page = SearchPage()
        m = _PAGE_RE.search(soup.get_text(" ", strip=True))
        if m:
            page.total_records = int(m.group(1))
            page.current_page = int(m.group(2))
            page.total_pages = int(m.group(3))
        table = soup.select_one("#list_apps_by_subject")
        if table is None and m is None:
            # an empty result set still renders the table + indicator, so neither
            # being present means the markup is not what we know how to read
            raise ParseError("search response has no #list_apps_by_subject table "
                             "and no page indicator — markup drift?")
        if table:
            for tr in table.select("tbody tr[id]"):
                rid = tr.get("id", "")
                if not rid.startswith("A"):
                    continue
                try:
                    app_id = int(rid[1:])
                except ValueError:
                    continue
                row = TenderRow(app_id=app_id, raw_text=tr.get_text(" ", strip=True))
                _enrich_row(tr, row)
                page.rows.append(row)
        return page

    # --- tender detail --------------------------------------------------

    def get_tabs(self, app_id: int) -> TenderTabs:
        html = self.s.open_tender(app_id)
        soup = BeautifulSoup(html, "lxml")
        if soup.select_one("#application_tabs") is None:
            raise ParseError(f"action=application for app_id={app_id} has no "
                             "#application_tabs strip — markup drift?")
        actions = []
        for a in soup.select("#application_tabs a[href*='action=']"):
            mm = re.search(r"action=(\w+)", a.get("href", ""))
            if mm and mm.group(1) in DETAIL_ACTIONS and mm.group(1) not in actions:
                actions.append(mm.group(1))
        return TenderTabs(app_id=app_id, actions=actions)

    def get_main(self, app_id: int) -> str:
        return self.s.tab("app_main", app_id)

    def get_main_info(self, app_id: int) -> TenderMain:
        """action=app_main parsed into a TenderMain (full label map in .fields)."""
        return self._parse_main(self.s.tab("app_main", app_id), app_id)

    def get_docs(self, app_id: int) -> str:
        return self.s.tab("app_docs", app_id)

    def get_doc_files(self, app_id: int) -> DocsTab:
        """action=app_docs parsed into files, handling BOTH layouts.

        Two response shapes exist (confirmed 2026-05-29):
          * 'sectioned' — modern: section.question.level1 with #que150 (1.3) cost
            estimates; file anchors use files.php?mode=que.
          * 'flat' — legacy: a single table#tender_docs of attached files; anchors
            use files.php?mode=app. The cost-estimate xlsx is just one of these files.
        """
        return self._parse_docs(self.s.tab("app_docs", app_id), app_id)

    def get_bids(self, app_id: int) -> str:
        return self.s.tab("app_bids", app_id)

    def get_bids_info(self, app_id: int) -> BidsTab:
        """action=app_bids parsed: state ('open'/'listed'/'empty') + bidder rows.

        Bid.bidder_id feeds get_bid_history(); Bid.org_id feeds get_profile().
        """
        return self._parse_bids(self.s.tab("app_bids", app_id), app_id)

    def get_results(self, app_id: int) -> str:
        return self.s.tab("agency_docs", app_id)

    def get_result_files(self, app_id: int) -> list[DocFile]:
        """action=agency_docs parsed: result-document rows from table#reports."""
        return self._parse_result_files(self.s.tab("agency_docs", app_id))

    def get_contract(self, app_id: int) -> str:
        return self.s.tab("agr_docs", app_id)  # auto-primes

    def get_contract_info(self, app_id: int) -> Contract:
        """action=agr_docs parsed: contract summary + documents + payment history.

        Only meaningful once a contract is signed (app_status=140) — the tab does
        not exist before that (see get_tabs / TenderTabs.has_contract).
        """
        return self._parse_contract(self.s.tab("agr_docs", app_id), app_id)

    def get_lastevents(self) -> list[TenderRow]:
        """action=lastevents — homepage feed of the 5 most recent status changes."""
        return self._parse_showapp_rows(self.s.get("lastevents"), "#lastevents")

    def iter_search(self, max_rows: int | None = None, **filters):
        """Generator over search results across pages (throttled, 4 rows/page).

        Yields TenderRow until the result set is exhausted or max_rows is hit.
        Mind the math: ~6 portal requests per 24 rows at 1.5s throttle.
        """
        page = self.search_tenders(**filters)
        yielded = 0
        while True:
            for row in page.rows:
                yield row
                yielded += 1
                if max_rows is not None and yielded >= max_rows:
                    return
            if (not page.rows or page.current_page is None
                    or page.total_pages is None
                    or page.current_page >= page.total_pages):
                return
            page = self.next_page()

    # --- endpoints added in the 2026-05-29 audit pass -------------------

    def get_profile(self, org_id: int) -> OrgProfile:
        """action=profile — company/org profile card (buyer or supplier)."""
        html = self.s.get("profile", org_id=org_id, isdialog="")
        return self._parse_profile(html, org_id)

    def get_status_history(self, app_id: int) -> list[StatusEvent]:
        """action=app_statushistory — full status timeline (newest first)."""
        html = self.s.get("app_statushistory", app_id=app_id)
        return self._parse_status_history(html)

    def get_tech_docs(self, app_id: int) -> list[TechDoc]:
        """action=app_tdocs — technical-documentation files per bidder."""
        html = self.s.get("app_tdocs", app_id=app_id)
        return self._parse_tech_docs(html)

    def get_bid_history(self, app_id: int, bidder_id: int) -> list[BidHistoryEntry]:
        """action=view_bid — one bidder's bid trail.

        `bidder_id` is the bidder's internal id (the `<bidder_id>` part of the
        `B<app_id><bidder_id>` row id in app_bids), sent as the `bid_id` param.
        """
        html = self.s.get("view_bid", app_id=app_id, bid_id=bidder_id)
        return self._parse_bid_history(html)

    def get_today_bids(self) -> list[TenderRow]:
        """action=today_bids — tenders whose bid deadline expires today (full list)."""
        return self._parse_showapp_rows(self.s.get("today_bids"), "#today_bids")

    def get_qa(self, app_id: int, chat_id: int) -> str:
        """action=show_qa — clarification Q&A reply thread for a documentation section.

        `chat_id` is the numeric part of a `div.hst-blk id="hst-<chat_id>"` in app_docs.
        Returns the raw HTML thread; empty thread renders 'პასუხები არ არის'.
        """
        return self.s.get("show_qa", app_id=app_id, chat_id=chat_id)

    @staticmethod
    def qa_is_empty(html: str) -> bool:
        """True when a show_qa thread has no answers."""
        return "პასუხები არ არის" in html

    @staticmethod
    def _file_parts(href: str) -> tuple[str | None, str | None, str | None]:
        """Pull (mode, file_id, code) out of a files.php href query string."""
        q = dict(re.findall(r"[?&](\w+)=([^&]*)", href or ""))
        return q.get("mode"), q.get("file"), q.get("code") or None

    @staticmethod
    def _collect_qa_threads(soup) -> list[QaThread]:
        """Find Q&A thread ids in an app_docs response (both layouts).

        Sectioned: div.hst-blk id='hst-<chat_id>' (one per section, no inline text).
        Flat: div id='ANS<chat_id>' inside #chat, question text in sibling <p>s.
        """
        threads: list[QaThread] = []
        for d in soup.select("div.hst-blk[id]"):
            m = re.match(r"hst-(\d+)", d.get("id", ""))
            if not m:
                continue
            sec = d.find_parent("section")
            threads.append(QaThread(chat_id=int(m.group(1)),
                                    section_id=sec.get("id") if sec else None))
        for d in soup.select("div[id^='ANS']"):
            m = re.match(r"ANS(\d+)", d.get("id", ""))
            if not m:
                continue
            block = d.parent
            author_p = block.select_one("p.author") if block else None
            q_p = block.select_one("p.chatmessgase") if block else None
            threads.append(QaThread(
                chat_id=int(m.group(1)),
                question_author=author_p.get_text(" ", strip=True) if author_p else None,
                question=q_p.get_text(" ", strip=True) if q_p else None,
            ))
        return threads

    @classmethod
    def _parse_docs(cls, html: str, app_id: int) -> DocsTab:
        soup = BeautifulSoup(html, "lxml")
        qa_threads = cls._collect_qa_threads(soup)
        sections = soup.select("section.question.level1")
        if sections:
            files: list[DocFile] = []
            for sec in sections:
                sid = sec.get("id")
                for div in sec.select("div.answ-file div[class^='obsolete']"):
                    a = div.select_one("a[href]")
                    if not a:
                        continue
                    mode, fid, code = cls._file_parts(a.get("href", ""))
                    files.append(DocFile(
                        filename=a.get_text(" ", strip=True), href=a.get("href"),
                        mode=mode, file_id=fid, code=code, section_id=sid,
                        is_current="obsolete0" in (div.get("class") or []),
                    ))
            return DocsTab(app_id=app_id, layout="sectioned", files=files,
                           qa_threads=qa_threads)

        # legacy flat layout: a table of attached files (id often 'tender_docs')
        table = soup.select_one("table#tender_docs") or soup.select_one("#app_docs table")
        if table:
            files = []
            for tr in table.select("tbody tr, tr"):
                a = tr.select_one("a[href*='files.php']")
                if not a:
                    continue
                tds = tr.find_all("td")
                mode, fid, code = cls._file_parts(a.get("href", ""))
                cell = a.find_parent("td")
                cell_cls = (cell.get("class") or []) if cell else []
                files.append(DocFile(
                    filename=a.get_text(" ", strip=True), href=a.get("href"),
                    mode=mode, file_id=fid, code=code,
                    is_current="obsolete1" not in cell_cls,
                    date_author=tds[-1].get_text(" ", strip=True) if len(tds) >= 2 else None,
                ))
            if files:
                return DocsTab(app_id=app_id, layout="flat", files=files,
                               qa_threads=qa_threads)
        # no sections and no file table: only valid if the tab wrapper itself is
        # present (a genuinely empty docs tab); otherwise the markup has drifted
        if soup.select_one("#app_docs") is None:
            raise ParseError(f"app_docs for app_id={app_id} has neither sectioned "
                             "nor flat layout nor an #app_docs wrapper — markup drift?")
        return DocsTab(app_id=app_id, layout="empty", files=[], qa_threads=qa_threads)

    # --- core-tab parsers (added 2026-06-12 audit pass) ------------------

    @staticmethod
    def _parse_main(html: str, app_id: int) -> TenderMain:
        soup = BeautifulSoup(html, "lxml")
        if soup.select_one("#app_main") is None:
            raise ParseError(f"app_main for app_id={app_id} has no #app_main wrapper "
                             "— markup drift?")
        tm = TenderMain(app_id=app_id)
        table = (soup.select_one("#print_area table")
                 or soup.select_one("#app_main table.with-label"))
        if table is None:
            raise ParseError(f"app_main for app_id={app_id} has no overview table "
                             "— markup drift?")
        for tr in table.select("tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) == 2:
                label = tds[0].get_text(" ", strip=True)
                value = tds[1].get_text(" ", strip=True)
                if not label:
                    continue
                tm.fields[label] = value
                if label == "შესყიდვის ტიპი":
                    tm.tender_type = value
                elif label == "განცხადების ნომერი":
                    strong = tds[1].select_one("strong")
                    tm.nat_code = strong.get_text(strip=True) if strong else value
                elif label == "შესყიდვის სტატუსი":
                    tm.status_text = value
                    icon = tds[1].select_one("img[src*='stat']")
                    m = re.search(r"stat(\d+)\.png", icon.get("src", "")) if icon else None
                    tm.status_code = int(m.group(1)) if m else None
                elif label in ("შემსყიდველი", "ადმინისტრირებას უწევს"):  # GRA variant
                    tm.buyer_name = value
                    m = re.search(r"ShowProfile\((\d+)", str(tds[1]))
                    tm.buyer_org_id = int(m.group(1)) if m else None
                elif label == "შესყიდვის გამოცხადების თარიღი":
                    tm.announce_date = value
                elif label == "წინადადებების მიღება იწყება":
                    tm.bids_open = value
                elif label == "წინადადებების მიღება მთავრდება":
                    tm.bid_deadline = value
                elif "სავარაუდო ღირებულება" in label:  # incl. პრეისკურანტის… variant
                    tm.estimated_value = value
                elif label == "შესყიდვის კატეგორია":
                    tm.category = value
            elif len(tds) == 1 and tm.description is None:
                bla = tds[0].select_one("div.blabla")
                if bla:
                    tm.description = bla.get_text(" ", strip=True)
        return tm

    @staticmethod
    def _parse_bids(html: str, app_id: int) -> BidsTab:
        soup = BeautifulSoup(html, "lxml")
        if soup.select_one("#app_bids") is None:
            raise ParseError(f"app_bids for app_id={app_id} has no #app_bids wrapper "
                             "— markup drift?")
        if soup.select_one("#TenderCountdown") is not None:
            return BidsTab(app_id=app_id, state="open")
        bids: list[Bid] = []
        prefix = f"B{app_id}"
        for tr in soup.select("#app_bids table.ktable tbody tr[id]"):
            rid = tr.get("id", "")
            if not rid.startswith("B"):
                continue
            # bidder_id: prefer ShowBidHistory(app_id, <id>); fallback: strip B<app_id>
            m = re.search(r"ShowBidHistory\(\s*\d+\s*,\s*(\d+)", str(tr))
            if m:
                bidder_id = int(m.group(1))
            elif rid.startswith(prefix) and rid[len(prefix):].isdigit():
                bidder_id = int(rid[len(prefix):])
            else:
                bidder_id = None
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            name_el = tr.select_one("span.color-1")
            om = re.search(r"ShowProfile\((\d+)", str(tds[0]))
            cm = re.search(r"\[(\d+)\]", tds[-1].get_text(" ", strip=True))

            def _amount_time(td):
                if td is None:
                    return None, None
                date = td.select_one("span.date")
                t = date.get_text(strip=True) if date else None
                amt = td.get_text(" ", strip=True)
                if t:
                    amt = amt.replace(t, "").strip()
                return (amt or None), t

            last_amount, last_time = _amount_time(tds[1] if len(tds) > 1 else None)
            first_amount, first_time = _amount_time(tds[2] if len(tds) > 3 else None)
            bids.append(Bid(
                bidder_id=bidder_id,
                bidder_name=name_el.get_text(strip=True) if name_el
                            else tds[0].get_text(" ", strip=True) or None,
                org_id=int(om.group(1)) if om else None,
                last_amount=last_amount, last_time=last_time,
                first_amount=first_amount, first_time=first_time,
                bid_count=int(cm.group(1)) if cm else None,
                is_winner=any("activebid1" in (td.get("class") or []) for td in tds),
            ))
        return BidsTab(app_id=app_id, state="listed" if bids else "empty", bids=bids)

    @classmethod
    def _parse_result_files(cls, html: str) -> list[DocFile]:
        soup = BeautifulSoup(html, "lxml")
        table = soup.select_one("table#reports")
        if table is None:
            raise ParseError("agency_docs has no table#reports — markup drift?")
        files: list[DocFile] = []
        for tr in table.select("tbody tr[id]"):
            a = tr.select_one("a[href*='files.php']")
            if not a:
                continue
            tds = tr.find_all("td")
            mode, fid, code = cls._file_parts(a.get("href", ""))
            cell = a.find_parent("td")
            cell_cls = (cell.get("class") or []) if cell else []
            files.append(DocFile(
                filename=a.get_text(" ", strip=True), href=a.get("href"),
                mode=mode, file_id=fid, code=code,
                is_current="obsolete1" not in cell_cls,
                date_author=tds[-1].get_text(" ", strip=True) if len(tds) >= 2 else None,
            ))
        return files

    @classmethod
    def _parse_contract(cls, html: str, app_id: int) -> Contract:
        soup = BeautifulSoup(html, "lxml")
        wrap = soup.select_one("#agency_docs")  # agr_docs shares this wrapper id
        if wrap is None:
            raise ParseError(f"agr_docs for app_id={app_id} has no #agency_docs "
                             "wrapper — markup drift?")
        c = Contract(app_id=app_id)
        divs = wrap.find_all("div", recursive=False)
        if not divs:
            raise ParseError(f"agr_docs for app_id={app_id} has no content blocks "
                             "— markup drift?")

        # DIV 0 — contract summary card
        summary = divs[0]
        status = summary.select_one("span.agrfg10")
        c.status_text = status.get_text(strip=True) if status else None
        strong = summary.select_one("td strong")
        c.supplier_name = strong.get_text(strip=True) if strong else None
        m = re.search(r"ShowProfile\((\d+)", str(summary))
        c.supplier_org_id = int(m.group(1)) if m else None
        conv = summary.select_one("span.convertme")
        if conv:
            # id format: "<amount>-<currency>-<DD.MM.YYYY HH:MM>"
            parts = (conv.get("id") or "").split("-", 2)
            try:
                c.amount_value = float(parts[0])
            except (ValueError, IndexError):
                pass
            c.currency = parts[1] if len(parts) > 1 else None
        stext = summary.get_text(" ", strip=True)
        m = re.search(r"ნომერი/თანხა:\s*(.+?)\s*/", stext)
        c.number_raw = m.group(1).strip() if m else None
        m = re.search(r"ხელშეკრულება ძალაშია:\s*(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})", stext)
        if m:
            c.valid_from, c.valid_to = m.group(1), m.group(2)
        m = re.search(r"ხელშეკრულების თარიღი:\s*(\d{2}\.\d{2}\.\d{4})", stext)
        c.contract_date = m.group(1) if m else None
        a = summary.select_one("a[href*='mode=contract']")
        if a:
            _, c.contract_file_id, _ = cls._file_parts(a.get("href", ""))

        # documents list (table#last_docs)
        for tr in wrap.select("table#last_docs tr"):
            a = tr.select_one("a[href*='files.php']")
            if not a:
                continue
            tds = tr.find_all("td")
            mode, fid, code = cls._file_parts(a.get("href", ""))
            c.files.append(DocFile(
                filename=a.get_text(" ", strip=True), href=a.get("href"),
                mode=mode, file_id=fid, code=code,
                date_author=tds[-1].get_text(" ", strip=True) if len(tds) >= 2 else None,
            ))

        # payments block — the div carrying 'ფაქტობრივი გადახდები'
        pay_div = next((d for d in reversed(divs)
                        if "ფაქტობრივი გადახდები" in d.get_text()), None)
        if pay_div is not None:
            ptext = pay_div.get_text(" ", strip=True)
            m = re.search(r"ხელშეკრულების თანხა:\s*([\d`., ]+\S*)", ptext)
            c.contract_value_total = m.group(1).strip() if m else None
            m = re.search(r"გადახდილი თანხა:\s*([\d`., ]+\S*)\s*\((\d+)%\)", ptext)
            if m:
                c.paid_total, c.paid_pct = m.group(1).strip(), int(m.group(2))
            table = pay_div.find("table")
            for tr in (table.find_all("tr") if table else []):
                tds = tr.find_all("td")
                cells = [t.get_text(" ", strip=True) for t in tds]
                if len(cells) < 5 or cells[0] == "თანხა" or "ჩანაწერები არ არის" in cells[0]:
                    continue
                c.payments.append(Payment(
                    amount=cells[0], year=cells[1], quarter=cells[2],
                    pay_date=cells[3], date_author=cells[4],
                ))
        return c

    @staticmethod
    def parse_qa(html: str) -> list[QaMessage]:
        """Parse a show_qa thread into messages; [] when 'პასუხები არ არის'."""
        if "პასუხები არ არის" in html:
            return []
        soup = BeautifulSoup(html, "lxml")
        out: list[QaMessage] = []
        for author_p in soup.select("p.author"):
            msg_p = author_p.find_next_sibling("p", class_="chatmessgase")
            out.append(QaMessage(
                author=author_p.get_text(" ", strip=True),
                message=msg_p.get_text(" ", strip=True) if msg_p else None,
            ))
        return out

    # --- parsers for the above -----------------------------------------

    @staticmethod
    def _parse_profile(html: str, org_id: int) -> OrgProfile:
        soup = BeautifulSoup(html, "lxml")
        if soup.select_one("#profile_dialog") is None and soup.select_one("table.with-label") is None:
            raise ParseError(f"profile for org_id={org_id} has no #profile_dialog "
                             "or table.with-label — markup drift?")
        prof = OrgProfile(org_id=org_id)
        label_map = {
            "საიდენტიფიკაციო კოდი": "id_code", "ქვეყანა": "country",
            "ქალაქი/დაბა/სოფელი": "city", "მისამართი": "address",
            "ტელეფონი": "phone", "ფაქსი": "fax", "ელ-ფოსტა": "email",
            "ვებ-გვერდი": "website",
        }
        for tr in soup.select("#profile_dialog table tr, table.with-label tr"):
            tds = tr.find_all("td")
            if len(tds) != 2:
                continue
            label = tds[0].get_text(" ", strip=True)
            value = tds[1].get_text(" ", strip=True)
            prof.fields[label] = value
            if label in ("შემსყიდველი", "მიმწოდებელი"):
                prof.role = label
                strong = tds[1].select_one("strong")
                prof.name = strong.get_text(strip=True) if strong else value
            elif label in label_map:
                setattr(prof, label_map[label], value)
        return prof

    @staticmethod
    def _parse_status_history(html: str) -> list[StatusEvent]:
        soup = BeautifulSoup(html, "lxml")
        if soup.select_one("#z") is None and soup.select_one("table.with-free-label-history") is None:
            raise ParseError("app_statushistory has no #z wrapper or "
                             "table.with-free-label-history — markup drift?")
        out: list[StatusEvent] = []
        for tr in soup.select("#z table tbody tr, table.with-free-label-history tbody tr"):
            tds = tr.find_all("td")
            if len(tds) >= 2:
                out.append(StatusEvent(
                    timestamp=tds[0].get_text(" ", strip=True),
                    status=tds[1].get_text(" ", strip=True),
                ))
        return out

    @staticmethod
    def _parse_tech_docs(html: str) -> list[TechDoc]:
        soup = BeautifulSoup(html, "lxml")
        if soup.select_one("table#tdocs") is None:
            raise ParseError("app_tdocs has no table#tdocs — markup drift?")
        out: list[TechDoc] = []
        for tr in soup.select("table#tdocs tbody tr"):
            tds = tr.find_all("td")
            if not tds or "ui-widget-header" in (tr.get("class") or []):
                continue
            a = tr.select_one("a[href]")
            cells = [t.get_text(" ", strip=True) for t in tds]
            out.append(TechDoc(
                bidder=cells[0] if len(cells) > 0 else None,
                filename=a.get_text(" ", strip=True) if a else (cells[1] if len(cells) > 1 else None),
                href=a.get("href") if a else None,
                date=cells[-1] if len(cells) >= 3 else None,
            ))
        return out

    @staticmethod
    def _parse_bid_history(html: str) -> list[BidHistoryEntry]:
        soup = BeautifulSoup(html, "lxml")
        if soup.find("table") is None:
            raise ParseError("view_bid response has no table — markup drift?")
        out: list[BidHistoryEntry] = []
        for tr in soup.select("table tbody tr"):
            if "ui-widget-header" in (tr.get("class") or []):
                continue
            tds = tr.find_all("td")
            if len(tds) >= 2:
                out.append(BidHistoryEntry(
                    amount=tds[0].get_text(" ", strip=True),
                    datetime=tds[1].get_text(" ", strip=True),
                ))
        return out

    @staticmethod
    def _parse_showapp_rows(html: str, table_selector: str) -> list[TenderRow]:
        """Parse rows whose app_id lives in an onclick=ShowApp(<id>,...) attr
        (today_bids, lastevents). Row markup matches the search results body."""
        soup = BeautifulSoup(html, "lxml")
        out: list[TenderRow] = []
        scope = soup.select_one(table_selector)
        if scope is None:
            raise ParseError(f"response has no {table_selector!r} table — markup drift?")
        for tr in scope.select("tr[onclick]"):
            m = re.search(r"ShowApp\((\d+)", tr.get("onclick", ""))
            if not m:
                continue
            row = TenderRow(app_id=int(m.group(1)), raw_text=tr.get_text(" ", strip=True))
            strong = tr.select_one("strong")
            if strong:
                row.nat_code = strong.get_text(strip=True)
            cat = tr.select_one("span.color-2")
            if cat:
                row.category = cat.get_text(" ", strip=True)
            for p in tr.select("p"):
                t = p.get_text(" ", strip=True)
                if t.startswith("შემსყიდველი"):
                    row.buyer = t.split(":", 1)[-1].strip()
            out.append(row)
        return out


def _enrich_row(tr, row: TenderRow) -> None:
    for p in tr.select("p"):
        t = p.get_text(" ", strip=True)
        if "განცხადების ნომერი" in t:
            row.nat_code = t.split(":")[-1].strip()
        elif "შემსყიდველი" in t:
            row.buyer = t.split(":")[-1].strip()
        elif "შესყიდვის კატეგორია" in t:
            row.category = t.split(":", 1)[-1].strip()
        elif "შესყიდვის სავარაუდო ღირებულება" in t:
            row.estimated_value = t.split(":", 1)[-1].strip()
    sp = tr.select_one("p.status")
    if sp:
        row.status_text = sp.get_text(" ", strip=True)
