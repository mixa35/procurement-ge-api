"""Low-level portal session: cookie acquisition, UTF-8, throttling, raw requests.

Confirmed during discovery (2026-05-28): controller.php needs a live SPALITE session
cookie + lang state, both set by first visiting `/?lang=ge`. Once initialized this way,
every documented action (including agr_docs) works directly — no per-tender priming is
needed. (A "Undefined index: lang" PHP error only appears when the session lang state is
missing, e.g. a stale/rotated cookie.)
"""
from __future__ import annotations

import time
import os

import requests

BASE = "https://tenders.procurement.gov.ge/public"
CONTROLLER = f"{BASE}/library/controller.php"
LIST_ORG = f"{BASE}/library/list_org.php"
FILES = f"{BASE}/library/files.php"
HOME = f"{BASE}/?lang=ge"


class PortalSession:
    """A throttled requests.Session pre-seeded with the SPALITE cookie."""

    def __init__(self, throttle_s: float | None = None, user_agent: str | None = None):
        self.throttle_s = (
            throttle_s if throttle_s is not None else float(os.getenv("THROTTLE_S", "1.5"))
        )
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": user_agent or "TendersDiscovery/0.1 (+docs project)"}
        )
        # Acquire SPALITE cookie + lang session state.
        self._raw_get(HOME)

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.throttle_s:
            time.sleep(self.throttle_s - elapsed)

    def _raw_get(self, url: str, params: dict | None = None) -> requests.Response:
        self._wait()
        resp = self.session.get(url, params=params, timeout=30)
        resp.encoding = "utf-8"
        self._last_request = time.monotonic()
        return resp

    # --- public helpers -------------------------------------------------

    def get(self, action: str, **params) -> str:
        """GET controller.php?action=<action>&... and return decoded text."""
        params = {"action": action, **params}
        return self._raw_get(CONTROLLER, params).text

    def post_search(self, body: dict) -> str:
        self._wait()
        resp = self.session.post(CONTROLLER, data=body, timeout=30)
        resp.encoding = "utf-8"
        self._last_request = time.monotonic()
        return resp.text

    def page(self, value: str | int) -> str:
        """Navigate the server-side-held search result set (page=next|prev|<N>)."""
        return self.get("search_app", page=value)

    def open_tender(self, app_id: int) -> str:
        """Fetch the tender container (action=application) — used to read the tab strip."""
        return self.get("application", app_id=app_id, app_reg="", key="")

    def tab(self, action: str, app_id: int) -> str:
        """Fetch a tender detail tab. A lang-initialized session is sufficient for all tabs."""
        return self.get(action, app_id=app_id, key="")

    def list_org(self, q: str, orgtype: int = 1) -> str:
        return self._raw_get(LIST_ORG, {"q": q, "orgtype": orgtype}).text

    def file_url(self, file_id: str, code: str | None = None, mode: str = "que") -> str:
        """Build a files.php download URL.

        mode values: que (app_docs), app (agency_docs/agr_docs), tdoc (app_tdocs),
        contract (agr_docs contract file — omits `code`). Always parse mode/file/code
        straight from the anchor href rather than hardcoding.
        """
        if mode == "contract" or code is None:
            return f"{FILES}?mode={mode}&file={file_id}"
        return f"{FILES}?mode={mode}&file={file_id}&code={code}"

    @staticmethod
    def permalink(app_id: int) -> str:
        """Direct deep link to a tender (shown in app_main as 'შესყიდვის ბმული')."""
        return f"{BASE}/?go={app_id}&lang=ge"


def make_session(**kwargs) -> PortalSession:
    return PortalSession(**kwargs)
