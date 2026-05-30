"""Dataclasses returned by the client parsers."""
from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass
class StatusEvent:
    """One row of action=app_statushistory (newest first)."""
    timestamp: str   # DD.MM.YYYY HH:MM
    status: str


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
