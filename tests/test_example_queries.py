"""Tests for the example query registry."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from statcast_bigquery.docs.example_queries import EXAMPLE_QUERIES, ExampleQuery
from statcast_bigquery.schema import PITCHES_SCHEMA

FIXTURE = Path(__file__).parent / "fixtures" / "statcast_sample_2024-04-01.parquet"


def test_minimum_query_count():
    assert len(EXAMPLE_QUERIES) >= 25


def test_every_query_has_required_fields():
    for q in EXAMPLE_QUERIES:
        assert isinstance(q, ExampleQuery)
        assert q.title.strip()
        assert q.question.strip()
        assert q.sql.strip()
        assert "{table}" in q.sql, f"{q.title!r}: SQL must contain '{{table}}' placeholder"
        assert q.columns_used


def test_query_columns_exist_in_schema():
    schema_names = {c.name for c in PITCHES_SCHEMA}
    for q in EXAMPLE_QUERIES:
        for col in q.columns_used:
            assert col in schema_names, f"{q.title!r} references missing column {col!r}"


@pytest.fixture
def fixture_table() -> duckdb.DuckDBPyConnection:
    df = pd.read_parquet(FIXTURE)
    df = df[df["game_type"] == "R"]
    con = duckdb.connect(":memory:")
    con.register("statcast_pitches_view", df)
    con.execute("CREATE TABLE statcast_pitches AS SELECT * FROM statcast_pitches_view")
    return con


def test_every_query_parses_against_fixture(fixture_table: duckdb.DuckDBPyConnection):
    """Every example query parses (DuckDB is permissive enough to validate SQL syntax)."""
    for q in EXAMPLE_QUERIES:
        sql = q.sql.replace("{table}", "statcast_pitches")
        try:
            fixture_table.execute(f"EXPLAIN {sql}")
        except Exception as e:
            pytest.fail(f"{q.title!r} did not parse: {e}\nSQL:\n{sql}")
