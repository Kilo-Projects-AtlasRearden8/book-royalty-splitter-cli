"""Tests for the split math.

The split math is the heart of this tool, so these tests cover it thoroughly:
exact totals, fractional-share remainders, income vs expense sign handling,
payer-100% expenses, and validation errors.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from book_royalty_splitter.models import Author, Ledger, SplitRule, Transaction
from book_royalty_splitter.split import author_statement, split_ledger


def _ledger() -> Ledger:
    ledger = Ledger()
    ledger.authors = [Author("Dylan"), Author("Jordan"), Author("Casey")]
    return ledger


def test_split_sums_exactly_to_total() -> None:
    """Shares must always sum to the transaction total (to the cent)."""
    ledger = _ledger()
    ledger.rules.append(
        SplitRule(
            "r",
            [
                ("Dylan", Decimal("33.33")),
                ("Jordan", Decimal("33.33")),
                ("Casey", Decimal("33.34")),
            ],
        )
    )
    ledger.transactions.append(
        Transaction("t1", "2026-01-01", "royalty", "desc", "cat", Decimal("100.00"), "r")
    )
    results = split_ledger(ledger)
    for _tx, shares in results:
        total = sum((s.amount for s in shares), Decimal("0"))
        assert total == Decimal("100.00")


def test_split_equal_thirds() -> None:
    ledger = _ledger()
    ledger.rules.append(
        SplitRule(
            "r",
            [
                ("Dylan", Decimal("33.33")),
                ("Jordan", Decimal("33.33")),
                ("Casey", Decimal("33.34")),
            ],
        )
    )
    ledger.transactions.append(
        Transaction("t1", "2026-01-01", "royalty", "desc", "cat", Decimal("1.00"), "r")
    )
    results = split_ledger(ledger)
    for _tx, shares in results:
        # 1.00 split into thirds; cents sum exactly.
        total = sum((s.amount for s in shares), Decimal("0"))
        assert total == Decimal("1.00")


def test_royalty_positive_expense_negative() -> None:
    ledger = _ledger()
    ledger.rules.append(SplitRule("r", [("Dylan", Decimal("50")), ("Jordan", Decimal("50"))]))
    ledger.transactions.append(
        Transaction("t1", "2026-01-01", "royalty", "desc", "cat", Decimal("100.00"), "r")
    )
    ledger.transactions.append(
        Transaction("t2", "2026-01-02", "expense", "desc", "cat", Decimal("100.00"), "r")
    )
    results = split_ledger(ledger)
    shares_by_kind: dict[str, list[Decimal]] = {}
    for _tx, shares in results:
        # kind isn't stored on Share; instead recompute sign via author_statement.
        for s in shares:
            shares_by_kind.setdefault(s.author, []).append(s.amount)
    # Split_ledger signs by kind externally via author_statement; just check raw math:
    royalty_shares = [s.amount for _tx, shares in results if _tx.kind == "royalty" for s in shares]
    expense_shares = [s.amount for _tx, shares in results if _tx.kind == "expense" for s in shares]
    assert all(a > 0 for a in royalty_shares)
    assert all(a < 0 for a in expense_shares)


def test_expense_shares_sum_to_negative_total() -> None:
    ledger = _ledger()
    ledger.rules.append(SplitRule("r", [("Dylan", Decimal("50")), ("Jordan", Decimal("50"))]))
    ledger.transactions.append(
        Transaction("t1", "2026-01-01", "expense", "desc", "cat", Decimal("100.00"), "r")
    )
    results = split_ledger(ledger)
    for _tx, shares in results:
        total = sum((s.amount for s in shares), Decimal("0"))
        assert total == Decimal("-100.00")


def test_payer_bears_100_percent_expense() -> None:
    ledger = _ledger()
    ledger.rules.append(SplitRule("r", [("Dylan", Decimal("50")), ("Jordan", Decimal("50"))]))
    ledger.transactions.append(
        Transaction(
            "t1",
            "2026-01-01",
            "expense",
            "cover",
            "design",
            Decimal("200.00"),
            "r",
            payer="Dylan",
        )
    )
    results = split_ledger(ledger)
    for _tx, shares in results:
        assert len(shares) == 1
        dylan = shares[0]
        assert dylan.author == "Dylan"
        assert dylan.amount == Decimal("-200.00")
        total = sum((s.amount for s in shares), Decimal("0"))
        assert total == Decimal("-200.00")


def test_rule_percentages_must_sum_to_100() -> None:
    with pytest.raises(ValueError, match="sum to"):
        SplitRule("bad", [("Dylan", Decimal("60")), ("Jordan", Decimal("30"))])


def test_unknown_rule_raises() -> None:
    ledger = _ledger()
    ledger.transactions.append(
        Transaction("t1", "2026-01-01", "royalty", "desc", "cat", Decimal("10.00"), "nope")
    )
    with pytest.raises(ValueError):
        split_ledger(ledger)


def test_author_statement_net() -> None:
    ledger = _ledger()
    ledger.rules.append(SplitRule("r", [("Dylan", Decimal("60")), ("Jordan", Decimal("40"))]))
    ledger.transactions.append(
        Transaction("t1", "2026-01-01", "royalty", "desc", "cat", Decimal("1000.00"), "r")
    )
    ledger.transactions.append(
        Transaction("t2", "2026-01-02", "expense", "desc", "cat", Decimal("200.00"), "r")
    )
    stmt = author_statement(ledger, "Dylan")
    assert stmt.income == Decimal("600.00")
    assert stmt.expenses == Decimal("-120.00")
    assert stmt.net == Decimal("480.00")

    stmt_j = author_statement(ledger, "Jordan")
    assert stmt_j.income == Decimal("400.00")
    assert stmt_j.expenses == Decimal("-80.00")
    assert stmt_j.net == Decimal("320.00")

    # Net sums across authors equal total net (royalties - expenses).
    total_net = stmt.net + stmt_j.net
    assert total_net == Decimal("800.00")


def test_author_statement_unknown_author_raises() -> None:
    ledger = _ledger()
    with pytest.raises(KeyError):
        author_statement(ledger, "Nobody")


def test_statement_as_dict_keys() -> None:
    ledger = _ledger()
    ledger.rules.append(SplitRule("r", [("Dylan", Decimal("60")), ("Jordan", Decimal("40"))]))
    ledger.transactions.append(
        Transaction("t1", "2026-01-01", "royalty", "desc", "cat", Decimal("100.00"), "r")
    )
    stmt = author_statement(ledger, "Dylan")
    d = stmt.as_dict()
    assert set(d) == {"author", "income", "expenses", "net", "rows"}
    assert d["author"] == "Dylan"
    assert len(d["rows"]) == 1


__all__ = []
