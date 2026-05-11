"""Tests for CLI argument parsing — does not invoke real BQ/Savant."""

from __future__ import annotations

import argparse
import logging
from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from statcast_bigquery.cli import _iter_chunks, build_parser, cmd_docs, cmd_sync, main


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


def test_sync_parser_accepts_runs_table_flag():
    """--runs-table override flows through to ns.runs_table."""
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--start", "2024-04-01", "--end", "2024-10-31",
        "--table", "p.d.statcast_pitches",
        "--runs-table", "p.d.custom_runs",
    ])
    assert ns.runs_table == "p.d.custom_runs"


def test_sync_parser_runs_table_defaults_to_none():
    """Without --runs-table, ns.runs_table is None (cmd_sync substitutes the default)."""
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--start", "2024-04-01", "--end", "2024-10-31",
        "--table", "p.d.statcast_pitches",
    ])
    assert ns.runs_table is None


def test_iter_chunks_year_clips_to_year_end():
    chunks = _iter_chunks("2024-06-15", "2026-03-10", "year")
    assert chunks == [
        ("2024-06-15", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
        ("2026-01-01", "2026-03-10"),
    ]


def test_iter_chunks_year_single_year():
    assert _iter_chunks("2024-04-01", "2024-10-31", "year") == [
        ("2024-04-01", "2024-10-31"),
    ]


def test_iter_chunks_month_clips_to_month_end():
    chunks = _iter_chunks("2024-02-15", "2024-04-10", "month")
    assert chunks == [
        ("2024-02-15", "2024-02-29"),  # leap year
        ("2024-03-01", "2024-03-31"),
        ("2024-04-01", "2024-04-10"),
    ]


def test_iter_chunks_month_non_leap_february():
    chunks = _iter_chunks("2025-01-15", "2025-03-05", "month")
    assert chunks == [
        ("2025-01-15", "2025-01-31"),
        ("2025-02-01", "2025-02-28"),
        ("2025-03-01", "2025-03-05"),
    ]


def test_iter_chunks_range_returns_single_chunk():
    assert _iter_chunks("2024-01-01", "2024-12-31", "range") == [
        ("2024-01-01", "2024-12-31"),
    ]


def test_iter_chunks_single_day():
    assert _iter_chunks("2024-07-04", "2024-07-04", "month") == [
        ("2024-07-04", "2024-07-04"),
    ]


def test_cmd_sync_resume_skips_completed_chunks(monkeypatch, caplog):
    """--resume should call completed_chunks() and filter the chunk list."""
    fake_bq = MagicMock()
    fake_writer = MagicMock()
    fake_writer.write.return_value = 0
    fake_runs = MagicMock()
    fake_runs.completed_chunks.return_value = {
        (date(2024, 1, 1), date(2024, 12, 31)),
    }
    fake_sc = MagicMock()
    fake_sc.fetch.return_value = pd.DataFrame()

    monkeypatch.setattr("statcast_bigquery.cli.bigquery.Client", lambda: fake_bq)
    monkeypatch.setattr("statcast_bigquery.cli.BigQueryWriter", lambda client: fake_writer)
    monkeypatch.setattr("statcast_bigquery.cli.StatcastClient", lambda: fake_sc)
    monkeypatch.setattr("statcast_bigquery.runs.RunsTable", lambda client: fake_runs)

    ns = argparse.Namespace(
        command="sync", start="2024-01-01", end="2025-12-31",
        table="p.d.statcast_pitches", umpires_table=None, skip_umpires=True,
        games_table=None, skip_games=True, runs_table=None,
        chunk_by="year", resume=True, dry_run=False,
    )
    caplog.set_level(logging.INFO)
    cmd_sync(ns)
    assert "skipping 1 completed chunks" in caplog.text
    # Statcast fetch should be called once (for 2025), not twice
    assert fake_sc.fetch.call_count == 1
