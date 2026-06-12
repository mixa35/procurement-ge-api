"""Dataclasses returned by the client parsers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .parsing import parse_amount, parse_date


@dataclass
class Company:
    internal_id: str
    name: str
    reg_code: str


@dataclass
class TenderRow:
    """One row from the search results table."""
    app_id: int
    nat_code: str | None = None
    buyer: str | None = None
    status_text: str | None = None
    category: str | None = None
    estimated_value: str | None = None
    raw_text: str | None = None

    @property
    def estimated_value_amount(self) -> float | None:
        return parse_amount(self.estimated_value)


@dataclass
class SearchPage:
    rows: list[TenderRow] = field(default_factory=list)
    current_page: int | None = None
    total_pages: int | None = None
    total_records: int | None = None


@dataclass
class TenderTabs:
    """Which detail tabs a tender exposes (state-dependent)."""
    app_id: int
    actions: list[str] = field(default_factory=list)

    @property
    def has_contract(self) -> bool:
        return "agr_docs" in self.actions


@dataclass
class OrgProfile:
    """action=profile — company/org profile card."""
    org_id: int
    role: str | None = None          # 'შემსყიდველი' (buyer) | 'მიმწოდებელი' (supplier)
    name: str | None = None
    id_code: str | None = None       # საიდენტიფიკაციო კოდი
    country: str | None = None
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    fax: str | None = None
    email: str | None = None
    website: str | None = None
    fields: dict[str, str] = field(default_factory=dict)  # raw label->value

    @property
    def is_buyer(self) -> bool:
        return self.role == "შემსყიდველი"

    @property
    def reg_code(self) -> str | None:
        """NAPR registration code (საიდენტიფიკაციო კოდი) — the STABLE join key for
        cross-referencing other datasets (the official OCDS export keys orgs as
        GE-NAPR-<reg_code>; the portal's internal org_id exists nowhere else)."""
        return self.id_code


@dataclass
class StatusEvent:
    """One row of action=app_statushistory (newest first)."""
    timestamp: str   # DD.MM.YYYY HH:MM
    status: str

    @property
    def timestamp_dt(self) -> datetime | None:
        return parse_date(self.timestamp)


@dataclass
class TechDoc:
    """One row of action=app_tdocs."""
    bidder: str | None
    filename: str | None
    href: str | None
    date: str | None = None


@dataclass
class DocFile:
    """One file from the documentation tab (action=app_docs), either layout."""
    filename: str
    href: str | None
    mode: str | None = None          # que (sectioned) | app (legacy flat)
    file_id: str | None = None
    code: str | None = None
    section_id: str | None = None    # e.g. 'que150' (1.3) — sectioned layout only
    is_current: bool = True          # obsolete0 → True, obsolete1 → False
    date_author: str | None = None   # legacy flat layout only


@dataclass
class DocsTab:
    """Parsed action=app_docs result, layout-agnostic."""
    app_id: int
    layout: str                      # 'sectioned' | 'flat' | 'empty'
    files: list[DocFile] = field(default_factory=list)
    qa_threads: list["QaThread"] = field(default_factory=list)  # feed get_qa()

    # 1.3 section label is "ფასების ცხრილი/ხარჯთაღრიცხვა" — match either term in flat layout.
    _COST_TERMS = ("ხარჯთაღრიცხვა", "ფასების ცხრილი")

    @property
    def cost_estimate_files(self) -> list[DocFile]:
        """Best-effort cost-estimate selection across both layouts.

        Sectioned: current files under section 1.3 (#que150). Flat: .xlsx whose name
        mentions a cost-estimate term (ხარჯთაღრიცხვა / ფასების ცხრილი), else all .xlsx
        as a fallback.
        """
        if self.layout == "sectioned":
            return [f for f in self.files if f.section_id == "que150" and f.is_current]
        xlsx = [f for f in self.files if (f.filename or "").lower().endswith(".xlsx")]
        named = [f for f in xlsx if any(t in (f.filename or "") for t in self._COST_TERMS)]
        return named or xlsx


@dataclass
class TenderMain:
    """Parsed action=app_main (tender overview).

    The label set varies by tender type (see docs/html_structure.md) — `fields`
    always carries the FULL label->value map; the named attributes are the
    common ones, populated when their label (or a known variant) is present.
    """
    app_id: int
    nat_code: str | None = None
    tender_type: str | None = None       # შესყიდვის ტიპი
    status_text: str | None = None
    status_code: int | None = None       # from stat<N>.png icon (identity mapping)
    buyer_name: str | None = None        # შემსყიდველი (GRA: ადმინისტრირებას უწევს)
    buyer_org_id: int | None = None      # ShowProfile(<id>)
    announce_date: str | None = None     # შესყიდვის გამოცხადების თარიღი
    bids_open: str | None = None         # წინადადებების მიღება იწყება
    bid_deadline: str | None = None      # წინადადებების მიღება მთავრდება
    estimated_value: str | None = None   # …სავარაუდო ღირებულება (incl. პრეისკურანტის variant)
    category: str | None = None          # შესყიდვის კატეგორია
    description: str | None = None       # div.blabla free text
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def permalink(self) -> str:
        return f"https://tenders.procurement.gov.ge/public/?go={self.app_id}&lang=ge"

    @property
    def estimated_value_amount(self) -> float | None:
        return parse_amount(self.estimated_value)

    @property
    def bid_deadline_dt(self) -> datetime | None:
        return parse_date(self.bid_deadline)

    @property
    def announce_date_dt(self) -> datetime | None:
        return parse_date(self.announce_date)


@dataclass
class Bid:
    """One bidder row from action=app_bids (closed/listed state)."""
    bidder_id: int | None        # ShowBidHistory(app_id, <bidder_id>) — feed to get_bid_history
    bidder_name: str | None
    org_id: int | None = None    # ShowProfile(<id>) — feed to get_profile
    last_amount: str | None = None
    last_time: str | None = None
    first_amount: str | None = None
    first_time: str | None = None
    bid_count: int | None = None
    is_winner: bool = False      # activebid1 cells

    @property
    def last_amount_value(self) -> float | None:
        return parse_amount(self.last_amount)


@dataclass
class BidsTab:
    """Parsed action=app_bids. state: 'open' (live countdown, no rows yet),
    'listed' (bidders table populated), 'empty' (table rendered, no rows —
    announced but bidding not started; check tender status)."""
    app_id: int
    state: str
    bids: list[Bid] = field(default_factory=list)

    @property
    def winner(self) -> Bid | None:
        return next((b for b in self.bids if b.is_winner), None)


@dataclass
class Payment:
    """One row of the agr_docs payment table (ფაქტობრივი გადახდები)."""
    amount: str                  # raw; includes funding source text, may tag (ავანსი)
    year: str | None = None
    quarter: str | None = None
    pay_date: str | None = None  # გადახდის თარიღი DD.MM.YYYY
    date_author: str | None = None

    @property
    def amount_value(self) -> float | None:
        return parse_amount(self.amount)

    @property
    def pay_date_dt(self) -> datetime | None:
        return parse_date(self.pay_date)


@dataclass
class Contract:
    """Parsed action=agr_docs (contract tab; only exists at app_status=140)."""
    app_id: int
    status_text: str | None = None       # e.g. მიმდინარე ხელშეკრულება
    supplier_name: str | None = None
    supplier_org_id: int | None = None   # ShowProfile(<id>)
    number_raw: str | None = None        # ნომერი/თანხა left part (number+date concatenated)
    amount_value: float | None = None    # from span.convertme id "<amount>-<cur>-<date>"
    currency: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    contract_date: str | None = None     # ხელშეკრულების თარიღი (absent on old tenders)
    contract_file_id: str | None = None  # files.php?mode=contract&file=<id> (no code)
    files: list[DocFile] = field(default_factory=list)       # table#last_docs
    payments: list[Payment] = field(default_factory=list)
    contract_value_total: str | None = None  # ხელშეკრულების თანხა (payments block)
    paid_total: str | None = None            # გადახდილი თანხა
    paid_pct: int | None = None              # (NN%)


@dataclass
class QaThread:
    """A clarification Q&A thread reference found in app_docs.

    chat_id feeds get_qa(app_id, chat_id). Sectioned layout: from div.hst-blk
    id='hst-<chat_id>' (question text not shown inline). Flat layout: from
    div id='ANS<chat_id>' inside #chat, with the question text alongside.
    """
    chat_id: int
    section_id: str | None = None    # sectioned layout: enclosing section id
    question_author: str | None = None  # flat layout only
    question: str | None = None         # flat layout only


@dataclass
class QaMessage:
    """One answer/message of a show_qa thread."""
    author: str | None
    message: str | None


@dataclass
class BidHistoryEntry:
    """One row of action=view_bid (a single bid by one bidder)."""
    amount: str            # raw, backtick thousands sep preserved
    datetime: str

    @property
    def amount_float(self) -> float | None:
        try:
            return float(self.amount.replace("`", "").replace(" ", "").strip())
        except ValueError:
            return None
