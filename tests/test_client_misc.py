"""Client plumbing tests with stubbed sessions: lookup_company, get_tabs,
search alias mapping. No network calls."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DISC = pathlib.Path(__file__).resolve().parent / "fixtures"

sys_import = __import__("sys")
sys_import.path.insert(0, str(ROOT))

from tenders_client.client import ProcurementClient  # noqa: E402


class _StubSession:
    """Captures calls; returns canned responses."""

    def __init__(self, **responses):
        self.responses = responses
        self.calls: list[tuple] = []

    def list_org(self, q, orgtype=1):
        self.calls.append(("list_org", q, orgtype))
        return self.responses["list_org"]

    def open_tender(self, app_id):
        self.calls.append(("open_tender", app_id))
        return self.responses["open_tender"]

    def post_search(self, body):
        self.calls.append(("post_search", dict(body)))
        return self.responses["post_search"]


def _client(**responses) -> ProcurementClient:
    c = ProcurementClient.__new__(ProcurementClient)
    c.s = _StubSession(**responses)
    c._searched = False
    return c


# ---------------------------------------------------------------------------
# lookup_company — pipe-delimited list_org.php payload
# ---------------------------------------------------------------------------

LIST_ORG_SAMPLE = (
    "32327|შპს სამება|204876606|\n"
    "42485|ქალაქ რუსთავის მუნიციპალიტეტი|216293664|\n"
    "\n"            # blank line must be skipped
    "bad-line\n"    # malformed line must be skipped
)


def test_lookup_company_parses_pipe_rows():
    c = _client(list_org=LIST_ORG_SAMPLE)
    out = c.lookup_company("სამება", orgtype=1)
    assert len(out) == 2
    assert out[0].internal_id == "32327"
    assert out[0].name == "შპს სამება"
    assert out[0].reg_code == "204876606"
    assert c.s.calls == [("list_org", "სამება", 1)]


# ---------------------------------------------------------------------------
# get_tabs — real captured container fixture (5 tabs, awarded tender)
# ---------------------------------------------------------------------------

def test_get_tabs_awarded_five_tabs():
    html = (DISC / "application_656756.html").read_text(encoding="utf-8")
    c = _client(open_tender=html)
    tabs = c.get_tabs(656756)
    assert tabs.actions[0] == "app_main"
    assert "agr_docs" in tabs.actions       # awarded -> contract tab present
    assert tabs.has_contract is True
    assert len(tabs.actions) == 5


# ---------------------------------------------------------------------------
# search alias mapping — supplier_id/buyer_id/date_from/date_to translate
# ---------------------------------------------------------------------------

SEARCH_OK = ('<div>5 ჩანაწერი (გვერდი: 1/2)</div>'
             '<table id="list_apps_by_subject"><tbody></tbody></table>')


def test_search_aliases_map_to_portal_params():
    c = _client(post_search=SEARCH_OK)
    c.search_tenders(supplier_id=111, buyer_id=222,
                     date_from="01.01.2026", date_to="31.01.2026")
    _, body = c.s.calls[0]
    assert body["app_monac_id"] == "111"
    assert body["app_shems_id"] == "222"
    assert body["app_date_from"] == "01.01.2026"
    assert body["app_date_tlll"] == "31.01.2026"
    assert body["action"] == "search_app"
    assert c._searched is True              # pagination unlocked after a search
