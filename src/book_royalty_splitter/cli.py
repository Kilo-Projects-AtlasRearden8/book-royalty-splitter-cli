"""Command-line interface for the book royalty splitter.

Usage::

    royalty-split init                     # create an empty ledger file
    royalty-split add-author "Dylan Asdale"
    royalty-split add-rule royalties Dylan:60,Jordan:40
    royalty-split add-tx --kind royalty --date 2026-03-31 --amount 1200.00 \
        --description "KDP royalties" --rule royalties
    royalty-split add-tx --kind expense --date 2026-04-02 --amount 300.00 \
        --description "Cover art" --rule royalties --payer Dylan
    royalty-split split                    # show per-author balances
    royalty-split statement "Dylan Asdale" # one author's statement
    royalty-split export --dir statements  # CSV export
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .csv_export import write_all_csv
from .io import empty_ledger, load_ledger, save_ledger
from .models import Author, Ledger, SplitRule, Transaction
from .split import CENT, author_statement, split_ledger

DEFAULT_LEDGER = Path("royalty_splitter.json")


def _parse_amount(text: str) -> Decimal:
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        raise argparse.ArgumentTypeError(f"invalid amount: {text!r}")


def _parse_percent(text: str) -> Decimal:
    value = _parse_amount(text)
    if value < 0 or value > 100:
        raise argparse.ArgumentTypeError(f"percent must be 0..100: {text!r}")
    return value


def _parse_rule(text: str) -> list[tuple[str, Decimal]]:
    """Parse 'Name:60,Other:40' into a list of (name, percent) pairs."""
    members: list[tuple[str, Decimal]] = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise argparse.ArgumentTypeError(f"rule entry needs Name:Pct: {chunk!r}")
        name, _, pct = chunk.partition(":")
        name = name.strip()
        if not name:
            raise argparse.ArgumentTypeError(f"empty author name in rule: {chunk!r}")
        try:
            percent = Decimal(pct)
        except InvalidOperation:
            raise argparse.ArgumentTypeError(f"invalid percent: {pct!r}")
        members.append((name, percent))
    if not members:
        raise argparse.ArgumentTypeError("rule needs at least one member")
    return members


def _load_or_create(path: Path) -> Ledger:
    if path.exists():
        return load_ledger(path)
    return empty_ledger()


def _save(ledger: Ledger, path: Path) -> None:
    save_ledger(ledger, path)
    print(f"Saved ledger to {path}")


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if path.exists() and not args.force:
        print(f"Ledger already exists at {path}; use --force to overwrite")
        return 1
    save_ledger(empty_ledger(), path)
    print(f"Created empty ledger at {path}")
    print("Next: royalty-split add-author ...  then royalty-split add-rule ...")
    return 0


def cmd_add_author(args: argparse.Namespace) -> int:
    ledger = _load_or_create(Path(args.file))
    if any(a.name == args.name for a in ledger.authors):
        print(f"Author {args.name!r} already exists")
        return 1
    ledger.authors.append(Author(name=args.name))
    ledger.validate()
    _save(ledger, Path(args.file))
    return 0


def cmd_add_rule(args: argparse.Namespace) -> int:
    ledger = _load_or_create(Path(args.file))
    members = _parse_rule(args.rule)
    total = sum((p for _, p in members), Decimal("0"))
    if total != Decimal("100"):
        print(f"Rule percentages sum to {total}, not 100")
        return 1
    ledger.rules.append(SplitRule(name=args.name, members=members))
    ledger.validate()
    _save(ledger, Path(args.file))
    print(f"Added rule {args.name!r}: {args.rule}")
    return 0


def _today() -> str:
    return date.today().isoformat()


def cmd_add_tx(args: argparse.Namespace) -> int:
    ledger = _load_or_create(Path(args.file))
    rule = ledger.rule_by_name(args.rule)
    payer: str | None = args.payer or None
    if payer and args.kind != "expense":
        print(f"--payer only applies to expenses, not {args.kind}")
        return 1
    if payer and payer not in rule.member_names():
        print(f"Payer {payer!r} is not a member of rule {args.rule!r}")
        return 1

    tx = Transaction(
        id=args.id or f"tx{len(ledger.transactions) + 1:03d}",
        date=args.date or _today(),
        kind=args.kind,
        description=args.description,
        category=args.category,
        amount=args.amount,
        split_rule=args.rule,
        payer=payer,
    )
    ledger.transactions.append(tx)
    ledger.validate()
    _save(ledger, Path(args.file))
    print(f"Added {tx.kind} {tx.id}: {tx.description} ({args.amount}) via {args.rule}")
    return 0


def _format_money(value: Decimal) -> str:
    return f"{value.quantize(CENT):>10}"


def cmd_split(args: argparse.Namespace) -> int:
    ledger = _load_or_create(Path(args.file))
    results = split_ledger(ledger)
    if not results:
        print("No transactions yet.")
        return 0

    # Aggregate per author.
    income: dict[str, Decimal] = {}
    expenses: dict[str, Decimal] = {}
    for tx, shares in results:
        for share in shares:
            if tx.kind == "royalty":
                income[share.author] = income.get(share.author, Decimal("0")) + share.amount
            else:
                expenses[share.author] = expenses.get(share.author, Decimal("0")) + share.amount

    names = ledger.author_names()
    print(f"{'Author':<24}{'Income':>12}{'Expenses':>12}{'Net':>12}")
    print("-" * 60)
    for name in names:
        inc = income.get(name, Decimal("0"))
        exp = expenses.get(name, Decimal("0"))
        net = inc + exp  # expenses are negative
        print(f"{name:<24}{_format_money(inc)}{_format_money(exp)}{_format_money(net)}")
    return 0


def cmd_statement(args: argparse.Namespace) -> int:
    ledger = _load_or_create(Path(args.file))
    try:
        stmt = author_statement(ledger, args.author)
    except KeyError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Statement for {stmt.author}")
    print(f"{'Date':<12}{'Kind':<10}{'Description':<30}{'Total':>12}{'Share':>12}")
    print("-" * 76)
    for tx, share in stmt.rows:
        print(
            f"{tx.date:<12}{tx.kind:<10}{tx.description[:30]:<30}"
            f"{_format_money(tx.amount)}{_format_money(share.amount)}"
        )
    print("-" * 76)
    print(f"{'Income':<52}{_format_money(stmt.income)}")
    print(f"{'Expenses':<52}{_format_money(stmt.expenses)}")
    print(f"{'Net':<52}{_format_money(stmt.net)}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    ledger = _load_or_create(Path(args.file))
    out_dir = Path(args.dir)
    paths = write_all_csv(ledger, out_dir)
    print(f"Exported {len(paths)} CSV file(s) to {out_dir}/")
    for p in paths:
        print(f"  - {p}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    ledger = _load_or_create(Path(args.file))
    try:
        ledger.validate()
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid: {exc}")
        return 1
    print(f"Ledger OK: {len(ledger.authors)} author(s), "
          f"{len(ledger.rules)} rule(s), {len(ledger.transactions)} transaction(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="royalty-split",
        description="Split book royalties and expenses between co-authors.",
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_LEDGER),
        help=f"Ledger JSON file (default: {DEFAULT_LEDGER})",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    def add(parent: argparse.ArgumentParser) -> None:
        parent.add_argument("--file", default=str(DEFAULT_LEDGER),
                            help=f"Ledger JSON file (default: {DEFAULT_LEDGER})")

    p = sub.add_parser("init", help="create an empty ledger JSON file")
    p.add_argument("--force", action="store_true", help="overwrite existing file")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("add-author", help="add a co-author to the ledger")
    p.add_argument("name", help="author name")
    p.set_defaults(func=cmd_add_author)

    p = sub.add_parser("add-rule", help="add a split rule (Name:Pct,...)")
    p.add_argument("name", help="rule name")
    p.add_argument("rule", help='e.g. "Dylan:60,Jordan:40"')
    p.set_defaults(func=cmd_add_rule)

    p = sub.add_parser("add-tx", help="add a royalty or expense transaction")
    p.add_argument("--kind", choices=["royalty", "expense"], required=True)
    p.add_argument("--date", default="", help="YYYY-MM-DD (default: today)")
    p.add_argument("--description", required=True)
    p.add_argument("--category", default="uncategorized")
    p.add_argument("--amount", type=_parse_amount, required=True)
    p.add_argument("--rule", required=True, help="split rule name")
    p.add_argument("--payer", default="",
                   help="for expenses, the single author who pays 100%")
    p.add_argument("--id", default="", help="transaction id (auto if omitted)")
    p.set_defaults(func=cmd_add_tx)

    p = sub.add_parser("split", help="show per-author income/expenses/net")
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("statement", help="print one author's statement")
    p.add_argument("author", help="author name")
    p.set_defaults(func=cmd_statement)

    p = sub.add_parser("export", help="export CSV statements to a directory")
    p.add_argument("--dir", default="statements", help="output directory")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("validate", help="validate the ledger file")
    p.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
