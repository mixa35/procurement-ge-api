"""Value-parsing helpers for the portal's Georgian-formatted strings.

The portal renders amounts with a BACKTICK thousands separator (7`500.00) and an
inconsistent currency suffix (GEL on some views, ლარი on others — see
docs/html_structure.md). Dates are DD.MM.YYYY with an optional HH:MM.
"""
from __future__ import annotations

import re
from datetime import datetime

_AMOUNT_RE = re.compile(r"(\d[\d` ]*(?:\.\d+)?)")
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{2}):(\d{2}))?")


def parse_amount(s: str | None) -> float | None:
    """First numeric amount in a portal string -> float (backticks stripped).

    Works on '132`439.00 GEL', '7`500.00 ლარი', '127`178.03 ლარი საკუთარი …'
    (payment cells embed the funding source after the amount).
    """
    if not s:
        return None
    m = _AMOUNT_RE.search(s)
    if not m:
        return None
    try:
        return float(m.group(1).replace("`", "").replace(" ", ""))
    except ValueError:
        return None


def parse_date(s: str | None) -> datetime | None:
    """First DD.MM.YYYY[ HH:MM] in a portal string -> datetime (naive, portal-local)."""
    if not s:
        return None
    m = _DATE_RE.search(s)
    if not m:
        return None
    d, mo, y, hh, mm = m.groups()
    try:
        return datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0))
    except ValueError:
        return None
