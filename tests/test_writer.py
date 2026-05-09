"""Tests for BigQueryWriter — uses bigquery.Client mocks."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from statcast_bigquery.writer import BigQueryWriter, TableRef


def make_mock_client() -> MagicMock:
    client = MagicMock(spec=bigquery.Client)
    client.project = "test-project"
    return client


def test_table_ref_parses_fully_qualified():
    ref = TableRef.parse("myproject.mydataset.mytable")
    assert ref.project == "myproject"
    assert ref.dataset == "mydataset"
    assert ref.table == "mytable"


def test_table_ref_rejects_bad_format():
    with pytest.raises(ValueError):
        TableRef.parse("only.two")


def test_create_table_if_missing_creates_when_not_exists():
    client = make_mock_client()
    client.get_table.side_effect = NotFound("missing")
    writer = BigQueryWriter(client=client)

    writer.create_table_if_missing(TableRef.parse("p.d.statcast_pitches"))

    assert client.create_table.call_count == 1
    table_arg = client.create_table.call_args.args[0]
    assert table_arg.time_partitioning is not None
    assert table_arg.time_partitioning.field == "game_date"
    assert table_arg.clustering_fields == ["home_team", "away_team", "game_pk"]


def test_create_table_if_missing_no_op_when_exists():
    client = make_mock_client()
    client.get_table.return_value = MagicMock()
    writer = BigQueryWriter(client=client)

    writer.create_table_if_missing(TableRef.parse("p.d.statcast_pitches"))

    assert client.create_table.call_count == 0


def test_idempotent_write_emits_delete_then_insert():
    client = make_mock_client()
    writer = BigQueryWriter(client=client)
    df = pd.DataFrame({"game_date": [date(2024, 4, 1)], "game_pk": [1]})
    ref = TableRef.parse("p.d.statcast_pitches")

    writer.write(ref, df, start_date="2024-04-01", end_date="2024-04-01")

    # First call should be the DELETE (transactional) — verify query_and_wait was used
    assert client.query_and_wait.call_count >= 1
    delete_sql = client.query_and_wait.call_args_list[0].args[0]
    assert "DELETE" in delete_sql
    assert "BETWEEN" in delete_sql


def test_write_skips_when_dataframe_empty():
    client = make_mock_client()
    writer = BigQueryWriter(client=client)

    writer.write(TableRef.parse("p.d.t"), pd.DataFrame(), "2024-04-01", "2024-04-01")

    assert client.query_and_wait.call_count == 0
    assert client.load_table_from_dataframe.call_count == 0
