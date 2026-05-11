"""Unit tests for RunsTable — the _statcast_ingest_runs metadata table."""

from __future__ import annotations

import logging
from datetime import date
from unittest.mock import MagicMock

import pandas as pd
from google.cloud.exceptions import NotFound

from statcast_bigquery.runs import RunsTable, RunsTableRef


def test_runs_table_ref_parse():
    ref = RunsTableRef.parse("proj.ds._statcast_ingest_runs")
    assert ref.project == "proj"
    assert ref.dataset == "ds"
    assert ref.table == "_statcast_ingest_runs"
    assert str(ref) == "proj.ds._statcast_ingest_runs"


def test_record_success_inserts_row():
    client = MagicMock()
    rt = RunsTable(client=client)
    ref = RunsTableRef.parse("p.d._statcast_ingest_runs")
    rt.record_success(
        ref=ref, chunk_start=date(2026, 5, 1), chunk_end=date(2026, 5, 31),
        chunk_kind="month", rows_written=12345,
    )
    assert client.query_and_wait.call_count == 1
    sql = client.query_and_wait.call_args[0][0]
    assert f"INSERT INTO `{ref}`" in sql
    params = {p.name: p.value for p in
              client.query_and_wait.call_args[1]["job_config"].query_parameters}
    assert params["chunk_start"] == date(2026, 5, 1)
    assert params["chunk_end"] == date(2026, 5, 31)
    assert params["chunk_kind"] == "month"
    assert params["rows_written"] == 12345
    assert params["status"] == "success"


def test_record_empty_uses_status_empty():
    client = MagicMock()
    rt = RunsTable(client=client)
    ref = RunsTableRef.parse("p.d._statcast_ingest_runs")
    rt.record_empty(ref=ref, chunk_start=date(2024, 1, 1),
                    chunk_end=date(2024, 1, 31), chunk_kind="month")
    params = {p.name: p.value for p in
              client.query_and_wait.call_args[1]["job_config"].query_parameters}
    assert params["status"] == "empty"
    assert params["rows_written"] == 0


def test_record_failed_uses_status_failed():
    client = MagicMock()
    rt = RunsTable(client=client)
    ref = RunsTableRef.parse("p.d._statcast_ingest_runs")
    rt.record_failed(ref=ref, chunk_start=date(2024, 1, 1),
                     chunk_end=date(2024, 1, 31), chunk_kind="year",
                     error="rate limit")
    params = {p.name: p.value for p in
              client.query_and_wait.call_args[1]["job_config"].query_parameters}
    assert params["status"] == "failed"


def test_completed_chunks_returns_set_of_date_pairs():
    client = MagicMock()
    fake_df = pd.DataFrame([
        {"chunk_start": date(2024, 1, 1), "chunk_end": date(2024, 12, 31)},
        {"chunk_start": date(2025, 1, 1), "chunk_end": date(2025, 12, 31)},
    ])
    qjob = MagicMock()
    qjob.to_dataframe.return_value = fake_df
    client.query_and_wait.return_value = qjob

    rt = RunsTable(client=client)
    ref = RunsTableRef.parse("p.d._statcast_ingest_runs")
    chunks = rt.completed_chunks(ref=ref)
    assert chunks == {
        (date(2024, 1, 1), date(2024, 12, 31)),
        (date(2025, 1, 1), date(2025, 12, 31)),
    }
    sql = client.query_and_wait.call_args[0][0]
    assert "status IN ('success', 'empty')" in sql


def test_record_failure_does_not_raise(caplog):
    """If recording itself fails (transient BQ error), log loudly but do not raise."""
    client = MagicMock()
    client.query_and_wait.side_effect = RuntimeError("BQ flapping")
    rt = RunsTable(client=client)
    ref = RunsTableRef.parse("p.d._statcast_ingest_runs")
    with caplog.at_level(logging.ERROR, logger="statcast_bigquery.runs"):
        # Must not raise
        rt.record_success(ref=ref, chunk_start=date(2024, 1, 1),
                          chunk_end=date(2024, 12, 31), chunk_kind="year",
                          rows_written=100)
    assert "failed to record run" in caplog.text.lower()


def test_create_table_if_missing_calls_create_when_absent():
    """If the runs table doesn't exist, create_table_if_missing should create it
    with the documented schema (chunk_start, chunk_end, status, library_version, ...)."""
    client = MagicMock()
    client.get_table.side_effect = NotFound("not found")
    rt = RunsTable(client=client)
    ref = RunsTableRef.parse("p.d._statcast_ingest_runs")
    rt.create_table_if_missing(ref)
    assert client.create_table.call_count == 1
    table_arg = client.create_table.call_args[0][0]
    field_names = [f.name for f in table_arg.schema]
    # Spot-check the 8 documented fields
    assert "chunk_start" in field_names
    assert "chunk_end" in field_names
    assert "chunk_kind" in field_names
    assert "rows_written" in field_names
    assert "status" in field_names
    assert "started_at" in field_names
    assert "finished_at" in field_names
    assert "library_version" in field_names


def test_create_table_if_missing_skips_when_table_exists():
    """If get_table succeeds, no create_table call should happen."""
    client = MagicMock()
    # get_table returns a normal Table mock — no NotFound raised
    rt = RunsTable(client=client)
    ref = RunsTableRef.parse("p.d._statcast_ingest_runs")
    rt.create_table_if_missing(ref)
    assert client.create_table.call_count == 0
