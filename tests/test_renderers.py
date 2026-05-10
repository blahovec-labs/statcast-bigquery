"""Snapshot-style tests for the 5 renderers."""

from __future__ import annotations

import json

from google.cloud import bigquery

from statcast_bigquery.docs.renderers import (
    render_bq_descriptions,
    render_data_dictionary,
    render_dbt_yaml,
    render_llm_context,
    render_markdown,
)
from statcast_bigquery.schema import PITCHES_SCHEMA


def test_render_bq_descriptions_returns_schema_field_list():
    fields = render_bq_descriptions()
    assert len(fields) == len(PITCHES_SCHEMA)
    for f in fields:
        assert isinstance(f, bigquery.SchemaField)
        assert f.description, f"{f.name} missing description"


def test_render_data_dictionary_outputs_expected_shape():
    rows = render_data_dictionary(dataset="mlb_v2_analytics", table="statcast_pitches")
    assert isinstance(rows, list)
    assert len(rows) == len(PITCHES_SCHEMA)
    for r in rows:
        assert {"dataset", "table", "column", "dtype",
                "description", "business_definition", "tags",
                "source_system", "upstream_lineage_json"} <= r.keys()
        assert r["dataset"] == "mlb_v2_analytics"
        assert r["table"] == "statcast_pitches"
        assert r["source_system"] == "baseball_savant"


def test_render_data_dictionary_is_valid_json():
    rows = render_data_dictionary(dataset="d", table="t")
    json.dumps(rows)  # should not raise


def test_render_llm_context_contains_required_sections():
    md = render_llm_context()
    assert "# Statcast for LLMs" in md
    assert "## Column reference" in md
    assert "## Pitfalls" in md
    assert "## Example queries" in md
    assert "## Statcast → statsapi cross-reference" in md
    # Must mention at least 5 column names
    for col in ["game_pk", "launch_speed", "description", "events", "pitcher"]:
        assert col in md


def test_render_markdown_renders_columns_grouped():
    md = render_markdown()
    assert "# statcast_pitches schema" in md
    for group_label in ["identifier", "batted_ball", "pitch_physics"]:
        assert group_label in md
    assert "| Column |" in md  # markdown tables


def test_render_dbt_yaml_has_columns_and_tests():
    yml = render_dbt_yaml(model_name="statcast_pitches")
    assert "version: 2" in yml
    assert "name: statcast_pitches" in yml
    # required-mode columns get a not_null test
    assert "not_null" in yml
