# Book Royalty Splitter CLI

A friendly, local-first command-line tool for co-authors to split book royalties
and expenses by agreed percentages. It prints per-author statements and exports
CSV files you can open in any spreadsheet app.

Built by **Asdale Dynamics, LLC** — an Indiana LLC focused on beginner-friendly
AI education, books and guides, and practical tools for authors and small
businesses. Part of the same plain-English, step-by-step spirit as *The Massive
AI Manual* and dylanasdale.github.io: no jargon, no condescension, no keys, no
network.

## Who this is for

Co-authors, indie publishers, and KDP authors who want to answer one question
together: *"After expenses, how much does each of us get?"*

You define your co-authors and their agreed split percentages, log royalty
payments and expenses, and the CLI does the math — exactly, to the cent — and
shows you each person's income, expenses, and net balance.

## Features

- **Split royalties and expenses** by agreed percentages (they can differ).
- **Exact money math** — uses decimal arithmetic so pennies never disappear.
- **Per-author statements** — income, expenses, and net for each co-author.
- **CSV export** — summary plus one transactions file per author.
- **Local-first, offline** — everything is a plain JSON file on your computer.
  No API keys, no accounts, no network, no personal data sent anywhere.
- **MIT licensed** — free to use, modify, and share.

## Install

```bash
pip install -e .
```

This gives you the `royalty-split` command. You can also run it without
installing:

```bash
PYTHONPATH=src python3 -m book_royalty_splitter --help
```

## Quick start

Create a ledger file and add your co-authors:

```bash
royalty-split init
royalty-split add-author "Dylan Asdale"
royalty-split add-author "Jordan"
```

Define how royalties are split:

```bash
royalty-split add-rule royalties "Dylan Asdale:60,Jordan:40"
```

Log income and expenses:

```bash
royalty-split add-tx --kind royalty --date 2026-04-01 --amount 1200.00 \
    --description "KDP royalties" --rule royalties

royalty-split add-tx --kind expense --date 2026-04-05 --amount 200.00 \
    --description "Cover art" --rule royalties --payer "Dylan Asdale"
```

See the split:

```bash
royalty-split split
```

Example output:

```
Author                Income    Expenses         Net
------------------------------------------------------------
Dylan Asdale          720.00   -120.00     600.00
Jordan                480.00    -80.00     400.00
```

One author's statement:

```bash
royalty-split statement "Dylan Asdale"
```

Export to CSV (a folder called `statements/` by default):

```bash
royalty-split export --dir statements
```

That writes `statements_summary.csv` plus one transactions CSV per author —
ready to open in Excel, Google Sheets, or Numbers.

## Commands

| Command | What it does |
|---------|--------------|
| `init` | Create an empty ledger JSON file |
| `add-author NAME` | Add a co-author |
| `add-rule NAME "A:60,B:40"` | Add a split rule (percentages must total 100) |
| `add-tx` | Log a royalty or expense transaction |
| `split` | Show every author's income, expenses, net |
| `statement NAME` | Show one author's full statement |
| `export --dir DIR` | Export CSV statements |
| `validate` | Check the ledger file is valid |

Use `--file ledger.json` with any command to point at a different ledger file
(the default is `royalty_splitter.json` in the current folder).

## How the math works

- Royalties are income: each author gets their share of the total.
- Expenses are costs: each author's share reduces their net.
- If an expense is paid by one person (`--payer`), that author bears 100% of it.
- Percentages are fractions out of 100 and must sum to 100 for each rule.
- Every cent is accounted for: if rounding leaves a fraction of a cent, the
  leftover penny goes to the first author in the rule so totals always tie out.

## Data format

Your ledger is a plain JSON file (`royalty_splitter.json` by default). You can
edit it by hand if you want:

```json
{
  "authors": [{"name": "Dylan Asdale"}, {"name": "Jordan"}],
  "rules": [{"name": "royalties", "members": [{"author": "Dylan Asdale", "percent": "60"}, {"author": "Jordan", "percent": "40"}]}],
  "transactions": [
    {"id": "tx001", "date": "2026-04-01", "kind": "royalty", "description": "KDP royalties", "category": "books", "amount": "1200.00", "split_rule": "royalties", "payer": null}
  ]
}
```

## Testing

```bash
python3 -m pytest
```

24 tests cover the split math, statements, JSON round-trips, and the CLI.

## License

MIT License. Copyright (c) 2026 Asdale Dynamics, LLC.

Credit: This tool is published by **Asdale Dynamics, LLC**, an Indiana LLC
(founded October 2026) focused on beginner-friendly AI education, books, guides,
and practical author and small-business tools. Learn more at
dylanasdale.github.io.

## About

Dylan Asdale is a registered nurse turned AI author and founder of Asdale
Dynamics, LLC. His book *The Massive AI Manual* explains AI "like a friend
would" — plain English, step by step, never condescending. This splitter is one
of the practical small-business tools the LLC publishes for authors and
self-publishers.

*Education-only disclaimer: this tool helps with bookkeeping math. It is not
accounting, tax, or legal advice. Talk to a qualified professional for your
specific situation.*