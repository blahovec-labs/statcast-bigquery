"""Tests for umpires.client.UmpireClient and umpires.schema."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from statcast_bigquery.umpires.client import _POSITION_MAP, UmpireClient, UmpireRow
from statcast_bigquery.umpires.schema import (
    GAME_UMPIRES_SCHEMA,
    get_umpires_partitioning,
)

SAMPLE_BOXSCORE = {
    "officials": [
        {"official": {"id": 427164, "fullName": "Andy Fletcher"},
         "officialType": "Home Plate"},
        {"official": {"id": 483912, "fullName": "Mike Muchlinski"},
         "officialType": "First Base"},
        {"official": {"id": 596740, "fullName": "Jansen Visconti"},
         "officialType": "Second Base"},
        {"official": {"id": 554242, "fullName": "Edwin Moscoso"},
         "officialType": "Third Base"},
    ]
}


def test_schema_has_all_required_fields():
    names = [s.name for s in GAME_UMPIRES_SCHEMA]
    assert names == ["game_pk", "game_date", "position", "umpire_id", "umpire_name"]


def test_partitioning_is_game_date():
    p = get_umpires_partitioning()
    assert p.field == "game_date"
    assert p.type == "DAY"
    assert p.clustering == ["game_pk"]


def test_position_map_covers_canonical_codes():
    assert _POSITION_MAP["Home Plate"] == "HP"
    assert set(_POSITION_MAP.values()) == {"HP", "1B", "2B", "3B", "LF", "RF"}


def test_parse_officials_extracts_canonical_rows():
    client = UmpireClient()
    rows = client._parse_officials(746070, "2023-08-15", SAMPLE_BOXSCORE)
    assert len(rows) == 4
    hp = next(r for r in rows if r.position == "HP")
    assert hp == UmpireRow(
        game_pk=746070, game_date="2023-08-15",
        position="HP", umpire_id=427164, umpire_name="Andy Fletcher",
    )


def test_parse_officials_skips_unknown_position():
    doc = {"officials": [{
        "official": {"id": 1, "fullName": "X"},
        "officialType": "Some Future Position",
    }]}
    client = UmpireClient()
    rows = client._parse_officials(1, "2024-01-01", doc)
    assert rows == []


def test_parse_officials_skips_missing_id():
    doc = {"officials": [{
        "official": {"fullName": "X"},  # no id
        "officialType": "Home Plate",
    }]}
    client = UmpireClient()
    rows = client._parse_officials(1, "2024-01-01", doc)
    assert rows == []


def test_fetch_returns_empty_for_no_games():
    client = UmpireClient()
    df = client.fetch([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert list(df.columns) == ["game_pk", "game_date", "position",
                                  "umpire_id", "umpire_name"]


def test_fetch_concurrent_assembles_rows():
    client = UmpireClient(max_workers=2, max_retries=1)
    with patch.object(client, "_fetch_one", return_value=SAMPLE_BOXSCORE):
        df = client.fetch([(746070, "2023-08-15"), (746071, "2023-08-15")])
    assert len(df) == 8  # 4 officials × 2 games
    assert set(df["position"]) == {"HP", "1B", "2B", "3B"}
