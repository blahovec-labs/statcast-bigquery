"""Tests for CLI argument parsing — does not invoke real BQ/Savant."""

from __future__ import annotations

import pytest

from statcast_bigquery.cli import build_parser, cmd_docs, main


def test_parser_accepts_sync_args():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--start", "2024-04-01", "--end", "2024-04-15",
        "--table", "p.d.t",
    ])
    assert ns.command == "sync"
    assert ns.start == "2024-04-01"
    assert ns.end == "2024-04-15"
    assert ns.table == "p.d.t"
    assert ns.chunk_by == "year"  # default


def test_parser_accepts_docs_args():
    parser = build_parser()
    ns = parser.parse_args(["docs", "--format", "llm"])
    assert ns.command == "docs"
    assert ns.format == "llm"


def test_parser_accepts_verify_args():
    parser = build_parser()
    ns = parser.parse_args([
        "verify", "--source", "baseball-savant",
        "--aggregation", "player-season",
        "--metric", "barrel_rate",
        "--season", "2024",
        "--table", "p.d.statcast_pitches",
    ])
    assert ns.command == "verify"
    assert ns.metric == "barrel_rate"
    assert ns.season == 2024
    assert ns.threshold == 0.99  # default


def test_parser_rejects_invalid_format():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["docs", "--format", "xml"])


def test_main_version_flag(capsys):
    from statcast_bigquery import __version__
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    captured = capsys.readouterr()
    assert __version__ in captured.out
    assert exc.value.code == 0


def test_docs_dictionary_apply_requires_dictionary_table(monkeypatch):
    """--apply without --dictionary-table should error out with rc=2."""
    parser = build_parser()
    ns = parser.parse_args([
        "docs", "--format", "dictionary",
        "--dataset", "my_dataset",
        "--table", "p.d.statcast_pitches",
        "--apply",
    ])
    assert ns.apply is True
    assert ns.dictionary_table is None
    # Ensure cmd_docs short-circuits before touching BigQuery
    monkeypatch.setattr("statcast_bigquery.cli.bigquery.Client",
                        lambda: pytest.fail("bigquery.Client must not be called"))
    rc = cmd_docs(ns)
    assert rc == 2
