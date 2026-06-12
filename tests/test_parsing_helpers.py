"""Tests for parsing.py value helpers + search date-param validation."""
from __future__ import annotations

import pathlib
from datetime import datetime

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys_import = __import__("sys")
sys_import.path.insert(0, str(ROOT))

from tenders_client.client import ProcurementClient  # noqa: E402
from tenders_client.parsing import parse_amount, parse_date  # noqa: E402


def test_parse_amount_backtick_and_currency_variants():
    assert parse_amount("132`439.00 GEL") == 132439.0
    assert parse_amount("7`500.00 ლარი") == 7500.0
    # payment cells embed funding source right after the amount
    assert parse_amount("127`178.03 ლარი ადგილობრივი თვითმართველი ერთეულის ბიუჯეტი") == 127178.03
    assert parse_amount("130439 ლარი") == 130439.0
    assert parse_amount("") is None
    assert parse_amount(None) is None
    assert parse_amount("ჩანაწერები არ არის") is None


def test_parse_date_with_and_without_time():
    assert parse_date("05.12.2025 12:30") == datetime(2025, 12, 5, 12, 30)
    assert parse_date("31.12.2025") == datetime(2025, 12, 31)
    # embedded in author strings
    assert parse_date("ლელა ღუბიანური :: 17.12.2025") == datetime(2025, 12, 17)
    assert parse_date("no date here") is None
    assert parse_date(None) is None
    assert parse_date("99.99.2025") is None  # invalid calendar date


def test_search_rejects_malformed_dates():
    c = ProcurementClient.__new__(ProcurementClient)  # no network init
    with pytest.raises(ValueError):
        c.search_tenders(date_from="2025-12-05")      # ISO format -> loud failure
    with pytest.raises(ValueError):
        c.search_tenders(app_date_tlll="5.12.2025")   # single-digit day
    with pytest.raises(KeyError):
        c.search_tenders(no_such_param=1)
