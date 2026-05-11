"""Validate every entry in EXAMPLE_QUERIES parses as BigQuery SQL and uses
columns that actually exist in PITCHES_SCHEMA."""

from __future__ import annotations

import pytest
import sqlglot
from sqlglot.errors import ParseError

from statcast_bigquery.docs.example_queries import EXAMPLE_QUERIES, ExampleQuery
from statcast_bigquery.schema import PITCHES_SCHEMA

PITCHES_COLUMN_NAMES = {c.name for c in PITCHES_SCHEMA}


@pytest.mark.parametrize("q", EXAMPLE_QUERIES, ids=lambda q: q.title)
def test_query_parses_as_bigquery(q: ExampleQuery):
    """Every example query must parse under BigQuery dialect."""
    sql = q.sql.format(table="`proj.ds.statcast_pitches`")
    try:
        sqlglot.parse_one(sql, dialect="bigquery")
    except ParseError as e:
        pytest.fail(f"BigQuery parse error in {q.title!r}: {e}\nSQL:\n{sql}")


@pytest.mark.parametrize("q", EXAMPLE_QUERIES, ids=lambda q: q.title)
def test_columns_used_exist_in_schema(q: ExampleQuery):
    """Every name in q.columns_used must exist in PITCHES_SCHEMA — catches stale
    metadata after a schema rename."""
    missing = [c for c in q.columns_used if c not in PITCHES_COLUMN_NAMES]
    assert not missing, (
        f"{q.title!r}: columns_used references {missing} not in PITCHES_SCHEMA"
    )


def test_at_least_25_queries():
    """Floor: catalog must remain comprehensive."""
    assert len(EXAMPLE_QUERIES) >= 25
