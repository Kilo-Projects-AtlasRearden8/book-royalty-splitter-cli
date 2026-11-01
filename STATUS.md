# STATUS

## What was built

A local-first Python CLI for co-authors to split book royalties and expenses by
agreed percentages, with per-author statements and CSV export.

Package: `book_royalty_splitter` (src layout), console script `royalty-split`.

Files:
- `LICENSE` — MIT, copyright line exactly `Copyright (c) 2026 Asdale Dynamics, LLC`
- `README.md` — usage, commands, math, credits Asdale Dynamics, LLC
- `pyproject.toml` — packaging, pytest/ruff config, `royalty-split` entry point
- `src/book_royalty_splitter/` — models, split math, statements, CSV export, JSON IO, CLI
- `tests/` — 26 tests covering split math, statements, IO, and CLI

Core modules:
- `models.py` — `Author`, `SplitRule`, `Transaction`, `Ledger` dataclasses; Decimal money; validation that rule percentages sum to 100
- `split.py` — exact split math; royalties positive (income), expenses negative; payer-100% expense support; largest-remainder cent distribution so totals tie out exactly
- `io.py` — JSON load/save of ledgers (human-editable)
- `csv_export.py` — per-author summary + per-author transactions CSVs
- `cli.py` — argparse: init, add-author, add-rule, add-tx, split, statement, export, validate

## How to run it

Install:
```
pip install -e .
```

Run:
```
royalty-split init
royalty-split add-author "Dylan Asdale"
royalty-split add-author Jordan
royalty-split add-rule royalties "Dylan Asdale:60,Jordan:40"
royalty-split add-tx --kind royalty --amount 1200.00 --description "KDP royalties" --rule royalties
royalty-split add-tx --kind expense --amount 200.00 --description "Cover art" --rule royalties --payer "Dylan Asdale"
royalty-split split
royalty-split statement "Dylan Asdale"
royalty-split export --dir statements
```

Default ledger file: `royalty_splitter.json` in the current folder (override with
`--file`). Local-first, offline, no API keys, no network.

## Verification results

- `python3 -m pytest` — **26 passed** (split math exact totals, fractional-share remainders, income/expense sign handling, payer-100% expense, payer-with-royalty rejection, rule validation, JSON round-trip, CLI init/add/split/statement/export/validate)
- `ruff check src tests` — **All checks passed** (0 lint errors)
- `pip install -e .` builds and installs cleanly; `royalty-split --help` and `python3 -m book_royalty_splitter` both work
- End-to-end CLI smoke test confirmed: payer-100% expense assigns full cost to payer; CSV export produces summary + per-author files
- LICENSE copyright line verified exactly: `Copyright (c) 2026 Asdale Dynamics, LLC`
- README credits Asdale Dynamics, LLC
- No `.github/workflows` files added; no secrets, API keys, or personal data in files

mypy is not installed in this environment, so typecheck was not run separately; the code is fully typed and uses `from __future__ import annotations`.

## Known gaps

- mypy typecheck could not be executed (tool not installed in this environment).
- Percentages are stored as plain Decimals out of 100; no UI to edit an existing author's share (add a new rule instead).
- CSV export produces one file per author plus a summary; no single combined ledger CSV.
- Rounding policy hands leftover cents to the first member of a rule (documented in README).
- No transaction editing or deletion commands (append-only ledger).
- The `--payer` flag only applies to expenses; royalties always use the rule's percentages (passing `--payer` with a royalty is now rejected with a clear error).

## Commit

Two commits on the initial branch, plain messages, no Co-authored-by trailers, not pushed, no remote created.