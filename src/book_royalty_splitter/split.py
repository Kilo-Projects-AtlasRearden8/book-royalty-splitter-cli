"""Split math: divide money between co-authors by agreed percentages.

The math is exact: amounts are :class:`decimal.Decimal`, percentages are
fractions out of 100, and remainders from truncation are distributed to the
first member of the rule (so every cent is accounted for and the totals always
tie out).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from .models import Ledger, SplitRule, Transaction

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class Share:
    """One author's portion of a transaction."""

    author: str
    amount: Decimal

    @property
    def is_income(self) -> bool:
        return self.amount > 0


def _split_amount(amount: Decimal, members: list[tuple[str, Decimal]]) -> list[Share]:
    """Divide ``amount`` by the rule's percentages.

    Each member gets ``floor(amount * percent / 100)`` truncated to cents, and
    any leftover cents are handed out one at a time to the first members so the
    pieces sum exactly to ``amount``.
    """
    shares: list[Share] = []
    remainder = amount
    for author, percent in members:
        raw = (amount * percent / HUNDRED).quantize(CENT, rounding=ROUND_DOWN)
        shares.append(Share(author=author, amount=raw))
        remainder -= raw
    # Distribute leftover cents to the earliest members (rounding policy).
    i = 0
    while remainder > 0 and shares:
        shares[i % len(shares)] = Share(
            author=shares[i % len(shares)].author,
            amount=shares[i % len(shares)].amount + CENT,
        )
        remainder -= CENT
        i += 1
    while remainder < 0 and shares:
        shares[i % len(shares)] = Share(
            author=shares[i % len(shares)].author,
            amount=shares[i % len(shares)].amount - CENT,
        )
        remainder += CENT
        i += 1
    return shares


def split_transaction(tx: Transaction, rule: SplitRule) -> list[Share]:
    """Return the shares for a single transaction, signed by kind.

    Royalties are positive (income for the author); expenses are negative
    (money the author owes). If an expense has a ``payer``, that author bears
    100% of it.
    """
    if tx.kind == "expense" and tx.payer:
        return [Share(author=tx.payer, amount=-tx.amount)]
    sign: Decimal = Decimal("1") if tx.kind == "royalty" else Decimal("-1")
    return [
        Share(author=s.author, amount=s.amount * sign)
        for s in _split_amount(tx.amount, rule.members)
    ]


def split_ledger(ledger: Ledger) -> list[tuple[Transaction, list[Share]]]:
    """Split every transaction in the ledger.

    The ledger is validated first so bad input is rejected before any math.
    """
    ledger.validate()
    out: list[tuple[Transaction, list[Share]]] = []
    for tx in ledger.transactions:
        rule = ledger.rule_by_name(tx.split_rule)
        out.append((tx, split_transaction(tx, rule)))
    return out


def author_statement(ledger: Ledger, author_name: str) -> Statement:
    """Build a per-author statement: income, expenses, and net balance."""
    if author_name not in ledger.author_names():
        raise KeyError(f"Unknown author {author_name!r}")
    income = Decimal("0")
    expenses = Decimal("0")
    rows: list[tuple[Transaction, Share]] = []
    for tx, shares in split_ledger(ledger):
        for share in shares:
            if share.author == author_name:
                rows.append((tx, share))
                if tx.kind == "royalty":
                    income += share.amount
                else:
                    expenses += share.amount
    return Statement(
        author=author_name,
        rows=tuple(rows),
        income=income,
        expenses=expenses,
        net=(income + expenses),  # expenses are already negative
    )


@dataclass
class Statement:
    """A per-author statement."""

    author: str
    rows: tuple[tuple[Transaction, Share], ...]
    income: Decimal
    expenses: Decimal
    net: Decimal

    def total_income(self) -> Decimal:
        return self.income

    def total_expenses(self) -> Decimal:
        return self.expenses

    def net_balance(self) -> Decimal:
        return self.net

    def as_dict(self) -> dict:
        return {
            "author": self.author,
            "income": str(self.income.quantize(CENT)),
            "expenses": str(self.expenses.quantize(CENT)),
            "net": str(self.net.quantize(CENT)),
            "rows": [
                {
                    "transaction": tx.id,
                    "date": tx.date,
                    "kind": tx.kind,
                    "description": tx.description,
                    "category": tx.category,
                    "total": str(tx.amount.quantize(CENT)),
                    "share": str(share.amount.quantize(CENT)),
                }
                for tx, share in self.rows
            ],
        }


__all__ = [
    "Share",
    "split_transaction",
    "split_ledger",
    "author_statement",
    "Statement",
]
