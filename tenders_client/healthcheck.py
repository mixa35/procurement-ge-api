"""Live drift detector: ~8 throttled portal requests asserting the catalog's selectors.

Run before any scraping campaign (or monthly):

    python -m tenders_client.healthcheck

Exit 0 = portal still matches docs/endpoint_catalog.yaml; exit 1 = something drifted
(rerun the provenance/discovery scripts and update the docs before trusting output).
Not collected by pytest — this hits the live portal on purpose.
"""
from __future__ import annotations

import sys

from bs4 import BeautifulSoup

from .client import ProcurementClient
from .errors import TenderNotFoundError
from .session import HOME

# the 22 documented search params (docs/search_filters.md)
EXPECTED_PARAMS = {
    "action", "app_agr_status", "app_amount_from", "app_amount_to", "app_basecode",
    "app_codes", "app_currency", "app_date_from", "app_date_tlll", "app_date_type",
    "app_donor_id", "app_monac_id", "app_particip_status_id", "app_pricelist",
    "app_reg_id", "app_shems_id", "app_status", "app_t", "app_type",
    "org_a", "org_b", "search",
}


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn):
        try:
            value = fn()
            results.append((name, True, ""))
            return value
        except Exception as exc:  # noqa: BLE001 — report every failure kind
            results.append((name, False, f"{type(exc).__name__}: {exc}"))
            return None

    # 1) session init (Georgian marker verified inside the constructor)
    client = check("session init (lang=ge, SPALITE)", ProcurementClient)
    if client is None:
        return _report(results)

    # 2) search form still has exactly the documented params
    def check_form():
        html = client.s._raw_get(HOME).text
        frm = BeautifulSoup(html, "lxml").select_one("#search_frm")
        assert frm is not None, "#search_frm missing"
        names = {el.get("name") for el in frm.select("[name]")}
        missing = EXPECTED_PARAMS - names
        extra = names - EXPECTED_PARAMS
        assert not missing, f"params missing: {missing}"
        assert not extra, f"NEW params appeared: {extra}"
    check("search form: 22 documented params", check_form)

    # 3) default search parses (table + page indicator + rows)
    def check_search():
        page = client.search_tenders()
        assert page.rows, "no rows parsed"
        assert page.total_records and page.total_pages, "page indicator missing"
        return page
    page = check("search_app parses (rows + indicator)", check_search)
    app_id = page.rows[0].app_id if page else None

    if app_id:
        def check_tabs():
            tabs = client.get_tabs(app_id)
            assert tabs.actions, "no tab actions found"
        check(f"get_tabs({app_id})", check_tabs)

        def check_main():
            tm = client.get_main_info(app_id)
            assert tm.nat_code, "nat_code missing"
            assert tm.status_text, "status_text missing"
            assert tm.fields, "label map empty"
        check(f"get_main_info({app_id})", check_main)

        def check_docs():
            d = client.get_doc_files(app_id)
            assert d.layout in ("sectioned", "flat", "empty"), f"layout={d.layout!r}"
        check(f"get_doc_files({app_id})", check_docs)

    def check_lastevents():
        rows = client.get_lastevents()
        assert len(rows) == 5, f"expected 5 rows, got {len(rows)}"
    check("get_lastevents() == 5 rows", check_lastevents)

    def check_notfound():
        try:
            client.get_main(999999999)
        except TenderNotFoundError:
            return
        raise AssertionError("expected TenderNotFoundError")
    check("invalid app_id -> TenderNotFoundError", check_notfound)

    return _report(results)


def _report(results) -> int:
    failed = [r for r in results if not r[1]]
    for name, ok, msg in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {msg}" if msg else ""))
    print(f"\nhealthcheck: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("PORTAL DRIFT SUSPECTED — re-verify with provenance/discovery scripts "
              "before trusting scraped output.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
