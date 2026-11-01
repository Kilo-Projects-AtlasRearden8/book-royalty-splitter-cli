"""Load and save ledgers as JSON.

Local-first: everything is a plain JSON file on disk. No network, no keys, no
personal data beyond what the user types. The format is intentionally simple so
it can be edited by hand or generated from other tools.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from .models import Author, Ledger, SplitRule, Transaction


def _dec(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def ledger_from_dict(data: dict[str, Any]) -> Ledger:
    """Build a :class:`Ledger` from a plain dict (as loaded from JSON)."""
    authors = [Author(name=a["name"]) for a in data.get("authors", [])]
    rules: list[SplitRule] = []
    for r in data.get("rules", []):
        members = [
            (m["author"], _dec(m["percent"])) for m in r.get("members", [])
        ]
        rules.append(SplitRule(name=r["name"], members=members))
    transactions: list[Transaction] = []
    for t in data.get("transactions", []):
        transactions.append(
            Transaction(
                id=t["id"],
                date=t["date"],
                kind=t["kind"],
                description=t.get("description", ""),
                category=t.get("category", "uncategorized"),
                amount=_dec(t["amount"]),
                split_rule=t["split_rule"],
                payer=t.get("payer"),
            )
        )
    return Ledger(authors=authors, rules=rules, transactions=transactions)


def ledger_to_dict(ledger: Ledger) -> dict[str, Any]:
    """Serialize a :class:`Ledger` to a plain dict."""
    return {
        "authors": [asdict(a) for a in ledger.authors],
        "rules": [
            {
                "name": r.name,
                "members": [
                    {"author": name, "percent": str(p)} for name, p in r.members
                ],
            }
            for r in ledger.rules
        ],
        "transactions": [
            {
                "id": t.id,
                "date": t.date,
                "kind": t.kind,
                "description": t.description,
                "category": t.category,
                "amount": str(t.amount),
                "split_rule": t.split_rule,
                "payer": t.payer,
            }
            for t in ledger.transactions
        ],
    }


def load_ledger(path: str | Path) -> Ledger:
    """Load a ledger from a JSON file, raising on missing/invalid input."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Ledger file not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Ledger JSON must be an object")
    return ledger_from_dict(data)


def save_ledger(ledger: Ledger, path: str | Path) -> None:
    """Write a ledger to a JSON file (pretty-printed, UTF-8)."""
    p = Path(path)
    data = ledger_to_dict(ledger)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def empty_ledger() -> Ledger:
    return Ledger()


__all__ = [
    "ledger_from_dict",
    "ledger_to_dict",
    "load_ledger",
    "save_ledger",
    "empty_ledger",
]
