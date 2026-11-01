"""Tests for JSON load/save of ledgers."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from book_royalty_splitter.io import empty_ledger, load_ledger, save_ledger
from book_royalty_splitter.models import Author, Ledger, SplitRule, Transaction


def test_roundtrip(tmp_path) -> None:
    ledger = Ledger()
    ledger.authors = [Author("Dylan"), Author("Jordan")]
    ledger.rules.append(SplitRule("r", [("Dylan", Decimal("60")), ("Jordan", Decimal("40"))]))
    ledger.transactions.append(
        Transaction("t1", "2026-01-01", "royalty", "KDP", "books", Decimal("1000.00"), "r")
    )
    path = tmp_path / "ledger.json"
    save_ledger(ledger, path)
    loaded = load_ledger(path)
    assert len(loaded.authors) == 2
    assert len(loaded.rules) == 1
    assert len(loaded.transactions) == 1
    assert loaded.transactions[0].amount == Decimal("1000.00")
    assert loaded.transactions[0].split_rule == "r"


def test_missing_file_raises(tmp_path) -> None:
    path = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        load_ledger(path)


def test_empty_ledger_roundtrip(tmp_path) -> None:
    ledger = empty_ledger()
    path = tmp_path / "empty.json"
    save_ledger(ledger, path)
    loaded = load_ledger(path)
    assert loaded.authors == []
    assert loaded.rules == []
    assert loaded.transactions == []


def test_json_is_human_editable(tmp_path) -> None:
    path = tmp_path / "ledger.json"
    save_ledger(empty_ledger(), path)
    raw = path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert set(parsed) == {"authors", "rules", "transactions"}


__all__ = []
