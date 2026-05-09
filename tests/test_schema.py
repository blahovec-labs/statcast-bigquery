"""Tests for the ColumnSpec dataclass and PITCHES_SCHEMA registry."""

from __future__ import annotations

import pytest

from statcast_bigquery.schema import (
    PITCHES_SCHEMA,
    SCHEMA_VERSION,
    ColumnSpec,
    PartitioningSpec,
    get_partitioning,
)


def test_column_spec_requires_business_definition():
    with pytest.raises(ValueError, match="business_definition"):
        ColumnSpec(
            name="foo",
            type="STRING",
            mode="NULLABLE",
            short_description="short",
            business_definition="",  # empty -> error
            semantic_tags=[],
            valid_range=None,
            valid_values=None,
            example_value=None,
            gotchas=[],
            statsapi_equivalent=None,
            pybaseball_source_field="foo",
            deprecated_in_year=None,
        )


def test_column_spec_rejects_invalid_type():
    with pytest.raises(ValueError, match="type"):
        ColumnSpec(
            name="foo",
            type="VARCHAR",  # type: ignore[arg-type]  # not a valid BQ type
            mode="NULLABLE",
            short_description="short",
            business_definition="long form",
            semantic_tags=[],
            valid_range=None,
            valid_values=None,
            example_value=None,
            gotchas=[],
            statsapi_equivalent=None,
            pybaseball_source_field="foo",
            deprecated_in_year=None,
        )


def test_column_spec_rejects_invalid_mode():
    with pytest.raises(ValueError, match="mode"):
        ColumnSpec(
            name="foo",
            type="STRING",
            mode="OPTIONAL",  # type: ignore[arg-type]  # not valid
            short_description="short",
            business_definition="long form",
            semantic_tags=[],
            valid_range=None,
            valid_values=None,
            example_value=None,
            gotchas=[],
            statsapi_equivalent=None,
            pybaseball_source_field="foo",
            deprecated_in_year=None,
        )


def test_pitches_schema_is_non_empty():
    assert len(PITCHES_SCHEMA) > 0


def test_pitches_schema_has_no_duplicates():
    names = [c.name for c in PITCHES_SCHEMA]
    assert len(names) == len(set(names))


def test_every_column_has_business_definition():
    missing = [c.name for c in PITCHES_SCHEMA if not c.business_definition.strip()]
    assert missing == [], f"columns missing business_definition: {missing}"


def test_every_column_has_pybaseball_source_field():
    missing = [c.name for c in PITCHES_SCHEMA if not c.pybaseball_source_field]
    assert missing == [], f"columns missing pybaseball_source_field: {missing}"


def test_partitioning_spec():
    p = get_partitioning()
    assert isinstance(p, PartitioningSpec)
    assert p.field == "game_date"
    assert p.type == "DAY"
    assert p.clustering == ["home_team", "away_team", "game_pk"]


def test_schema_version_set():
    assert isinstance(SCHEMA_VERSION, str)
    assert SCHEMA_VERSION  # non-empty
