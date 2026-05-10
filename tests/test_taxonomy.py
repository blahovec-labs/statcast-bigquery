"""Tests for taxonomy + statsapi map."""

from __future__ import annotations

from statcast_bigquery.docs.statsapi_map import STATCAST_TO_STATSAPI_MAP
from statcast_bigquery.docs.taxonomy import (
    SEMANTIC_GROUPS,
    columns_in_group,
)
from statcast_bigquery.schema import PITCHES_SCHEMA


def test_semantic_groups_non_empty():
    assert len(SEMANTIC_GROUPS) >= 10
    assert "identifier" in SEMANTIC_GROUPS
    assert "batted_ball" in SEMANTIC_GROUPS


def test_columns_in_group_returns_matching_specs():
    ids = columns_in_group("identifier")
    names = {c.name for c in ids}
    assert "game_pk" in names


def test_every_column_has_at_least_one_semantic_tag():
    missing = [c.name for c in PITCHES_SCHEMA if not c.semantic_tags]
    assert missing == [], f"columns missing semantic_tags: {missing}"


def test_statsapi_map_covers_all_identifiers():
    """Every column tagged 'identifier' must be in STATCAST_TO_STATSAPI_MAP (None or string)."""
    ids = {c.name for c in columns_in_group("identifier")}
    missing = ids - STATCAST_TO_STATSAPI_MAP.keys()
    assert not missing, f"identifier columns missing from statsapi_map: {missing}"


def test_statsapi_map_values_are_str_or_none():
    for k, v in STATCAST_TO_STATSAPI_MAP.items():
        assert isinstance(k, str)
        assert v is None or isinstance(v, str), f"{k!r}: {v!r}"
