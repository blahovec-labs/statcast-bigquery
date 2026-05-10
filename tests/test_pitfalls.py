"""Tests for the pitfall catalog."""

from __future__ import annotations

from statcast_bigquery.docs.pitfalls import PITFALLS, Pitfall


def test_pitfalls_minimum_count():
    assert len(PITFALLS) >= 10


def test_each_pitfall_has_summary_and_explanation():
    for p in PITFALLS:
        assert isinstance(p, Pitfall)
        assert p.summary.strip()
        assert p.explanation.strip()
        assert len(p.explanation) > len(p.summary)


def test_pitfall_columns_referenced_exist_in_schema():
    """Any column name a pitfall references must exist in PITCHES_SCHEMA."""
    from statcast_bigquery.schema import PITCHES_SCHEMA

    schema_names = {c.name for c in PITCHES_SCHEMA}
    for p in PITFALLS:
        for col in p.columns:
            assert col in schema_names, f"pitfall {p.summary!r} references missing column {col}"
