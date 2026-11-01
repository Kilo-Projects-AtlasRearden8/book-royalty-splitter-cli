"""CSV export for per-author statements.

Two tables are produced per statement:
  * ``<author>_summary.csv``  - one row per author with income, expenses, net.
  * ``<author>_transactions.csv`` - one row per transaction share.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from .models import Ledger
from .split import author_statement

CENT = Decimal("0.01")


def _fmt(value: Decimal) -> str:
    return str(value.quantize(CENT))


def _author_slug(name: str) -> str:
    """File-safe slug for an author name."""
    slug = "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in name.strip())
    slug = slug.strip("._") or "author"
    return slug.lower()


def write_summary_csv(ledger: Ledger, out_dir: str | Path) -> list[Path]:
    """Write one summary CSV containing every author's totals."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "statements_summary.csv"
    statements = [author_statement(ledger, name) for name in ledger.author_names()]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["author", "income", "expenses", "net"])
        for s in statements:
            writer.writerow([s.author, _fmt(s.income), _fmt(s.expenses), _fmt(s.net)])
    return [path]


def write_author_csv(ledger: Ledger, author_name: str, out_dir: str | Path) -> Path:
    """Write a per-author transactions CSV."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    statement = author_statement(ledger, author_name)
    path = out / f"{_author_slug(author_name)}_transactions.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["date", "transaction", "kind", "category", "description", "total", "share"]
        )
        for tx, share in statement.rows:
            writer.writerow(
                [
                    tx.date,
                    tx.id,
                    tx.kind,
                    tx.category,
                    tx.description,
                    _fmt(tx.amount),
                    _fmt(share.amount),
                ]
            )
    return path


def write_all_csv(ledger: Ledger, out_dir: str | Path) -> list[Path]:
    """Write every per-author CSV plus the summary CSV."""
    paths = write_summary_csv(ledger, out_dir)
    for name in ledger.author_names():
        paths.append(write_author_csv(ledger, name, out_dir))
    return paths


__all__ = [
    "write_summary_csv",
    "write_author_csv",
    "write_all_csv",
]
