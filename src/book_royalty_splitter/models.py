"""Data models for the book royalty splitter.

Everything is plain dataclasses so the ledger can be serialized to and from
JSON. Money is always handled as :class:`decimal.Decimal` to avoid floating
point drift, and percentages are stored as ``Decimal`` values out of 100.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

TransactionKind = Literal["royalty", "expense"]

_NAME_RE = re.compile(r"^[A-Za-z0-9 _'&.-]{1,80}$")


def _validate_name(name: str, *, what: str = "name") -> str:
    """Sanity-check a human-readable identifier; keep it short and printable."""
    if not isinstance(name, str) or not _NAME_RE.match(name.strip()):
        raise ValueError(f"Invalid {what}: {name!r}")
    return name.strip()


@dataclass
class Author:
    """A co-author of the book."""

    name: str

    def __post_init__(self) -> None:
        self.name = _validate_name(self.name, what="author name")


@dataclass
class SplitRule:
    """How a transaction is divided among authors.

    ``members`` is a list of ``(author_name, percent_out_of_100)`` pairs. The
    percentages must sum to exactly 100. For expenses that one author bears
    entirely, the rule has a single member at 100.
    """

    name: str
    members: list[tuple[str, Decimal]]

    def __post_init__(self) -> None:
        self.name = _validate_name(self.name, what="rule name")
        if not self.members:
            raise ValueError(f"SplitRule {self.name!r} has no members")
        total = sum((p for _, p in self.members), Decimal("0"))
        if total != Decimal("100"):
            raise ValueError(
                f"SplitRule {self.name!r} percentages sum to {total}, not 100"
            )
        for author_name, percent in self.members:
            _validate_name(author_name, what="author name in rule")
            if percent < 0:
                raise ValueError(
                    f"Negative percentage {percent} in rule {self.name!r}"
                )

    def member_names(self) -> list[str]:
        return [name for name, _ in self.members]

    def percent_for(self, author_name: str) -> Decimal:
        for name, percent in self.members:
            if name == author_name:
                return percent
        return Decimal("0")


@dataclass
class Transaction:
    """A single royalty payment or expense.

    ``amount`` is always a positive number. ``kind`` decides whether it is
    income (royalty) or outflow (expense) in a statement.
    """

    id: str
    date: str  # ISO-8601 date, e.g. 2026-03-31
    kind: TransactionKind
    description: str
    category: str
    amount: Decimal
    split_rule: str
    payer: str | None = None  # for expenses paid entirely by one author

    def __post_init__(self) -> None:
        self.id = _validate_name(self.id, what="transaction id")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", self.date):
            raise ValueError(f"Invalid date {self.date!r}; expected YYYY-MM-DD")
        if self.kind not in ("royalty", "expense"):
            raise ValueError(f"Invalid kind {self.kind!r}")
        self.description = self.description.strip() or self.id
        self.category = (self.category or "uncategorized").strip().lower()
        amount = self.amount
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < 0:
            raise ValueError(f"Transaction {self.id!r} has a negative amount")
        self.amount = amount
        _validate_name(self.split_rule, what="split rule")


@dataclass
class Ledger:
    """The whole bookkeeping state: authors, rules, and transactions."""

    authors: list[Author] = field(default_factory=list)
    rules: list[SplitRule] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)

    # ------------------------------------------------------------------ rules
    def rule_by_name(self, name: str) -> SplitRule:
        for rule in self.rules:
            if rule.name == name:
                return rule
        raise KeyError(f"No split rule named {name!r}")

    def author_names(self) -> list[str]:
        return [a.name for a in self.authors]

    def validate(self) -> None:
        names = set(self.author_names())
        for rule in self.rules:
            for member in rule.member_names():
                if member not in names:
                    raise ValueError(
                        f"Rule {rule.name!r} references unknown author {member!r}"
                    )
        for tx in self.transactions:
            if tx.split_rule not in {r.name for r in self.rules}:
                raise ValueError(
                    f"Transaction {tx.id!r} references unknown rule {tx.split_rule!r}"
                )
            rule = self.rule_by_name(tx.split_rule)
            for member in rule.member_names():
                if member not in names:
                    raise ValueError(
                        f"Transaction {tx.id!r} rule references unknown author {member!r}"
                    )


__all__ = [
    "Author",
    "SplitRule",
    "Transaction",
    "Ledger",
    "TransactionKind",
    "Decimal",
]
