"""Unit tests for RunsTable — the _statcast_ingest_runs metadata table."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd

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
    """If recording itself fails (transient BQ error), log loudly but do not raise —
    we'd rather lose a skip-list entry than fail an already-successful sync chunk."""
    client = MagicMock()
    client.query_and_wait.side_effect = RuntimeError("BQ flapping")
    rt = RunsTable(client=client)
    ref = RunsTableRef.parse("p.d._statcast_ingest_runs")
    # Must not raise
    rt.record_success(ref=ref, chunk_start=date(2024, 1, 1),
                      chunk_end=date(2024, 12, 31), chunk_kind="year",
                      rows_written=100)
    assert "failed to record run" in caplog.text.lower()
