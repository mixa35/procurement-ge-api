"""03 — Drill into one tender: tabs, main page, documentation files.

Run:  python examples/03_full_tender.py [app_id]

Shows that the visible tab set is STATE-DEPENDENT (the contract tab `agr_docs`
appears only once a contract is signed, app_status=140) and that get_doc_files()
transparently handles both the 'sectioned' and 'flat' documentation layouts.
"""
import sys

from tenders_client import ProcurementClient

# Georgian output — make stdout UTF-8 even on a cp1252 Windows console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    client = ProcurementClient()

    if len(sys.argv) > 1:
        app_id = int(sys.argv[1])
    else:
        # No id given — take the first row of a default search.
        app_id = client.search_tenders().rows[0].app_id
    print(f"Tender app_id = {app_id}")
    print(f"Permalink     = {client.s.permalink(app_id)}")

    tabs = client.get_tabs(app_id)
    print(f"Tabs present  = {tabs.actions}  ({len(tabs.actions)} tabs)")

    docs = client.get_doc_files(app_id)
    print(f"Docs layout   = {docs.layout}  ({len(docs.files)} file(s))")
    for f in docs.files[:10]:
        print(f"   - {f.filename}  ->  {client.s.file_url(f.file_id, f.code, f.mode)}")


if __name__ == "__main__":
    main()
