"""Reverse-engineered client for the შესყიდვები (Procurement) section of
tenders.procurement.gov.ge. See docs/api_reference.md and docs/endpoint_catalog.yaml."""

from ._version import __version__
from .errors import ParseError, PortalError, SessionExpiredError, TenderNotFoundError
from .session import PortalSession, make_session
from .client import ProcurementClient
from .models import (
    BidHistoryEntry,
    Company,
    DocFile,
    DocsTab,
    OrgProfile,
    SearchPage,
    StatusEvent,
    TechDoc,
    TenderRow,
    TenderTabs,
)

__all__ = [
    "__version__",
    "PortalSession", "make_session", "ProcurementClient",
    "PortalError", "TenderNotFoundError", "SessionExpiredError", "ParseError",
    "Company", "TenderRow", "SearchPage", "TenderTabs",
    "OrgProfile", "StatusEvent", "TechDoc", "BidHistoryEntry",
    "DocFile", "DocsTab",
]
