"""Tests for the CLI entry points."""

from __future__ import annotations

import pytest

from book_royalty_splitter.cli import main


def _run(args: list[str], capsys, ledger_file) -> int:
    full = ["--file", str(ledger_file)] + args
    code = main(full)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_init_creates_file(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    code, out, _err = _run(["init"], capsys, ledger_file)
    assert code == 0
    assert ledger_file.exists()
    assert "Created empty ledger" in out


def test_init_force_overwrites(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    ledger_file.write_text("{}")
    code, out, _err = _run(["init", "--force"], capsys, ledger_file)
    assert code == 0


def test_add_author(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    _run(["init"], capsys, ledger_file)
    code, out, _err = _run(["add-author", "Dylan Asdale"], capsys, ledger_file)
    assert code == 0


def test_add_author_duplicate_rejected(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    _run(["init"], capsys, ledger_file)
    _run(["add-author", "Dylan Asdale"], capsys, ledger_file)
    code, out, err = _run(["add-author", "Dylan Asdale"], capsys, ledger_file)
    assert code == 1


def test_add_rule_invalid_percent_rejected(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    _run(["init"], capsys, ledger_file)
    code, out, err = _run(
        ["add-rule", "r", "Dylan:60,Jordan:30"], capsys, ledger_file
    )
    assert code == 1


def test_split_and_statement(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    _run(["init"], capsys, ledger_file)
    _run(["add-author", "Dylan"], capsys, ledger_file)
    _run(["add-author", "Jordan"], capsys, ledger_file)
    _run(["add-rule", "r", "Dylan:60,Jordan:40"], capsys, ledger_file)
    _run(
        ["add-tx", "--kind", "royalty", "--date", "2026-01-01", "--amount", "1000.00",
         "--description", "KDP", "--rule", "r"],
        capsys, ledger_file,
    )
    code, out, _err = _run(["split"], capsys, ledger_file)
    assert code == 0
    assert "Dylan" in out
    assert "Jordan" in out

    code, out, _err = _run(["statement", "Dylan"], capsys, ledger_file)
    assert code == 0
    assert "Dylan" in out
    assert "Net" in out


def test_statement_unknown_author(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    _run(["init"], capsys, ledger_file)
    code, out, err = _run(["statement", "Nobody"], capsys, ledger_file)
    assert code == 1


def test_export_creates_csv(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    out_dir = tmp_path / "stmts"
    _run(["init"], capsys, ledger_file)
    _run(["add-author", "Dylan"], capsys, ledger_file)
    _run(["add-author", "Jordan"], capsys, ledger_file)
    _run(["add-rule", "r", "Dylan:60,Jordan:40"], capsys, ledger_file)
    _run(
        ["add-tx", "--kind", "royalty", "--amount", "1000.00", "--description", "KDP",
         "--rule", "r"],
        capsys, ledger_file,
    )
    code, out, _err = _run(["export", "--dir", str(out_dir)], capsys, ledger_file)
    assert code == 0
    summary = out_dir / "statements_summary.csv"
    assert summary.exists()
    text = summary.read_text()
    assert "Dylan" in text
    assert "Jordan" in text
    # header present
    assert text.splitlines()[0] == "author,income,expenses,net"


def test_validate_ok(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    _run(["init"], capsys, ledger_file)
    _run(["add-author", "Dylan"], capsys, ledger_file)
    code, out, _err = _run(["validate"], capsys, ledger_file)
    assert code == 0
    assert "OK" in out


def test_add_tx_payer_with_royalty_rejected(tmp_path, capsys) -> None:
    ledger_file = tmp_path / "ledger.json"
    _run(["init"], capsys, ledger_file)
    _run(["add-author", "Dylan"], capsys, ledger_file)
    _run(["add-author", "Jordan"], capsys, ledger_file)
    _run(["add-rule", "r", "Dylan:60,Jordan:40"], capsys, ledger_file)
    code, out, err = _run(
        [
            "add-tx",
            "--kind",
            "royalty",
            "--amount",
            "1000.00",
            "--description",
            "KDP",
            "--rule",
            "r",
            "--payer",
            "Dylan",
        ],
        capsys, ledger_file,
    )
    assert code == 1


def test_main_no_command_errors() -> None:
    with pytest.raises(SystemExit):
        main([])


__all__ = []
