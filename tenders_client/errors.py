"""Exceptions raised by the client.

The portal never returns HTTP errors for application-level failures — it returns
HTTP 200 with a PHP notice in the body (documented in docs/endpoint_catalog.yaml).
The session layer sniffs those signatures and raises these instead of letting
parsers silently produce empty results.
"""
from __future__ import annotations


class PortalError(Exception):
    """Base class for all portal-related failures."""


class TenderNotFoundError(PortalError):
    """An app_id (or other id param) does not exist.

    Live signature: HTTP 200 body starting '[8] Undefined offset: 0 ... controller.php'
    (line 140 for app_main, 196 for app_docs, 390 for agr_docs).
    """


class SessionExpiredError(PortalError):
    """The SPALITE session lost its lang state and re-initialization failed.

    Live signature: '[8] Undefined index: lang ... controller.php - Line:8'.
    The session retries once with a fresh GET /?lang=ge before raising this.
    """


class ParseError(PortalError):
    """The response was not an error page, but the expected wrapper markup is
    missing — i.e. the portal's HTML has drifted from docs/html_structure.md."""
