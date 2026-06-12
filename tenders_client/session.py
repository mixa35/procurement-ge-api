"""Low-level portal session: cookie acquisition, UTF-8, throttling, raw requests.

Confirmed during discovery (2026-05-28): controller.php needs a live SPALITE session
cookie + lang state, both set by first visiting `/?lang=ge`. Once initialized this way,
every documented action (including agr_docs) works directly — no per-tender priming is
needed.

The portal signals application-level failures as HTTP 200 + a PHP notice in the body
(see docs/endpoint_catalog.yaml). `_detect_error()` sniffs those signatures so callers
get exceptions (errors.py) instead of silently parsing an error page.

NOTE: the portal must be used with lang=ge — `lang=en` exists and returns fully
English fragments, which breaks every Georgian-label-keyed parser. The constructor
verifies the session landed on the Georgian UI.

Concurrency: one PortalSession = one server-side PHP session, which also holds the
active search result set used by pagination. Do not share a session across threads.
"""
from __future__ import annotations

import logging
import time
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ._version import __version__
from .errors import SessionExpiredError, TenderNotFoundError

logger = logging.getLogger("tenders_client")

BASE = "https://tenders.procurement.gov.ge/public"
CONTROLLER = f"{BASE}/library/controller.php"
LIST_ORG = f"{BASE}/library/list_org.php"
FILES = f"{BASE}/library/files.php"
HOME = f"{BASE}/?lang=ge"

# A label that is always present on the Georgian homepage search form and never on
# the English one — used to verify the session is in the supported language.
_GE_MARKER = "შესყიდვის სტატუსი"


class PortalSession:
    """A throttled requests.Session pre-seeded with the SPALITE cookie."""

    def __init__(self, throttle_s: float | None = None, user_agent: str | None = None):
        self.throttle_s = (
            throttle_s if throttle_s is not None else float(os.getenv("THROTTLE_S", "1.5"))
        )
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": user_agent or f"procurement-ge-api/{__version__} (+docs project)"}
        )
        retry = Retry(
            total=3, backoff_factor=2,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._init_lang()

    def _init_lang(self) -> None:
        """Acquire SPALITE cookie + Georgian lang state, and verify both."""
        resp = self._raw_get(HOME)
        if "SPALITE" not in self.session.cookies:
            raise SessionExpiredError("portal did not set the SPALITE session cookie")
        if _GE_MARKER not in resp.text:
            raise SessionExpiredError(
                "portal session is not on the Georgian UI (lang=ge) — "
                "the parsers key on Georgian labels and would silently fail"
            )

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.throttle_s:
            time.sleep(self.throttle_s - elapsed)

    def _raw_get(self, url: str, params: dict | None = None) -> requests.Response:
        self._wait()
        t0 = time.monotonic()
        resp = self.session.get(url, params=params, timeout=30)
        resp.encoding = "utf-8"
        self._last_request = time.monotonic()
        logger.debug("GET %s params=%s -> %s (%.2fs)",
                     url, params, resp.status_code, self._last_request - t0)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _detect_error(text: str) -> str | None:
        """Classify a controller.php response body.

        Returns 'stale' (lang session lost), 'notfound' (bad id), or None (ok).
        Signatures are documented in docs/endpoint_catalog.yaml; both appear as
        HTTP 200 PHP notices that name controller.php.
        """
        head = text[:600]
        if "Undefined index: lang" in head and "controller.php" in head:
            return "stale"
        if "Undefined offset" in head and "controller.php" in head:
            return "notfound"
        return None

    def _checked(self, text: str, describe: str, retry) -> str:
        """Raise on error signatures; transparently re-init + retry once on staleness."""
        kind = self._detect_error(text)
        if kind is None:
            return text
        if kind == "notfound":
            raise TenderNotFoundError(f"portal returned 'Undefined offset' for {describe}")
        # stale lang session: re-init once, retry the original request
        logger.warning("stale portal session detected (%s) — re-initializing", describe)
        self._init_lang()
        text2 = retry()
        if self._detect_error(text2) == "stale":
            raise SessionExpiredError(f"session still stale after re-init ({describe})")
        if self._detect_error(text2) == "notfound":
            raise TenderNotFoundError(f"portal returned 'Undefined offset' for {describe}")
        return text2

    # --- public helpers -------------------------------------------------

    def get(self, action: str, **params) -> str:
        """GET controller.php?action=<action>&... and return decoded text."""
        params = {"action": action, **params}
        text = self._raw_get(CONTROLLER, params).text
        return self._checked(
            text, f"action={action} {params}",
            retry=lambda: self._raw_get(CONTROLLER, params).text,
        )

    def post_search(self, body: dict) -> str:
        def _do() -> str:
            self._wait()
            t0 = time.monotonic()
            resp = self.session.post(CONTROLLER, data=body, timeout=30)
            resp.encoding = "utf-8"
            self._last_request = time.monotonic()
            logger.debug("POST %s action=%s -> %s (%.2fs)",
                         CONTROLLER, body.get("action"), resp.status_code,
                         self._last_request - t0)
            resp.raise_for_status()
            return resp.text
        return self._checked(_do(), f"POST action={body.get('action')}", retry=_do)

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

    def download(self, file_id: str, code: str | None = None, mode: str = "que",
                 dest_dir: str = ".", filename: str | None = None) -> str:
        """Download a files.php attachment to dest_dir; returns the saved path.

        Filename comes from the Content-Disposition header when the caller does not
        supply one (fallback: the file_id). Throttled like every portal request.
        """
        import pathlib
        import re as _re
        from urllib.parse import unquote

        self._wait()
        resp = self.session.get(self.file_url(file_id, code, mode), timeout=60, stream=True)
        self._last_request = time.monotonic()
        resp.raise_for_status()
        if filename is None:
            cd = resp.headers.get("Content-Disposition", "")
            m = (_re.search(r"filename\*=(?:UTF-8'')?([^;]+)", cd)
                 or _re.search(r'filename="?([^";]+)"?', cd))
            filename = unquote(m.group(1).strip()) if m else str(file_id)
            try:
                # the portal sends raw UTF-8 bytes in a plain filename= header,
                # which the HTTP layer decodes as latin-1 — undo that mojibake
                filename = filename.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        dest = pathlib.Path(dest_dir) / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                fh.write(chunk)
        logger.debug("downloaded %s (%s bytes) -> %s",
                     filename, resp.headers.get("Content-Length", "?"), dest)
        return str(dest)

    @staticmethod
    def permalink(app_id: int) -> str:
        """Direct deep link to a tender (shown in app_main as 'შესყიდვის ბმული')."""
        return f"{BASE}/?go={app_id}&lang=ge"


def make_session(**kwargs) -> PortalSession:
    return PortalSession(**kwargs)
