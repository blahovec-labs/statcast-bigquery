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


# ---------------------------------------------------------------------------
# Coverage test: every pybaseball column must appear in PITCHES_SCHEMA.
#
# EXPECTED_PYBASEBALL_COLUMNS is the authoritative set of columns returned by
# pybaseball.statcast() as discovered on 2024-04-01 (Task 3 discovery run).
#
# Columns NOT in the original task spec but found during discovery are marked
# with "# added during Task 3 discovery".
# Columns IN the original task spec but NOT found in pybaseball output are
# retained in the schema (they appear in older seasons) and noted below.
# ---------------------------------------------------------------------------

EXPECTED_PYBASEBALL_COLUMNS = {
    # Identifiers
    "game_pk", "game_date", "game_year", "game_type",
    "at_bat_number", "pitch_number",
    "sv_id",                             # added during Task 3 discovery
    # Players
    "batter", "pitcher",
    "player_name",                       # added during Task 3 discovery
    "fielder_2", "fielder_3",
    "fielder_4", "fielder_5", "fielder_6", "fielder_7", "fielder_8", "fielder_9",
    # Teams
    "home_team", "away_team",
    # Inning + count
    "inning", "inning_topbot", "balls", "strikes", "outs_when_up",
    "on_1b", "on_2b", "on_3b",
    # Score state
    "home_score", "away_score", "post_home_score", "post_away_score",
    # post_fld_score added during Task 3 discovery
    "bat_score", "fld_score", "post_bat_score", "post_fld_score",
    "home_score_diff", "bat_score_diff",
    "home_win_exp", "bat_win_exp",       # added during Task 3 discovery
    # Pitch physics
    "pitch_type", "pitch_name", "type",
    "release_speed", "effective_speed", "release_spin_rate",
    "release_extension", "release_pos_x", "release_pos_z", "release_pos_y",
    "spin_axis", "spin_dir", "spin_rate_deprecated",
    "vx0", "vy0", "vz0", "ax", "ay", "az",
    "pfx_x", "pfx_z", "break_angle_deprecated", "break_length_deprecated",
    # Plate location
    "plate_x", "plate_z", "sz_top", "sz_bot", "zone",
    # Outcomes
    "description", "events", "des",
    # Batted ball
    "launch_speed", "launch_angle", "hit_distance_sc",
    "hc_x", "hc_y", "bb_type", "hit_location",
    "estimated_ba_using_speedangle",
    "estimated_woba_using_speedangle",
    "estimated_slg_using_speedangle",    # added during Task 3 discovery
    "woba_value", "woba_denom", "babip_value", "iso_value",
    # Bat / swing tracking (2024+)
    "bat_speed", "swing_length",
    "attack_angle", "attack_direction",  # added during Task 3 discovery
    "swing_path_tilt",                   # added during Task 3 discovery
    "intercept_ball_minus_batter_pos_x_inches",  # added during Task 3 discovery
    "intercept_ball_minus_batter_pos_y_inches",  # added during Task 3 discovery
    # Handedness
    "stand", "p_throws",
    # Misc / deprecated
    "tfs_deprecated", "tfs_zulu_deprecated",
    "umpire", "if_fielding_alignment", "of_fielding_alignment",
    "delta_home_win_exp", "delta_run_exp",
    "delta_pitcher_run_exp",             # added during Task 3 discovery
    "launch_speed_angle",
    "n_thruorder_pitcher", "n_priorpa_thisgame_player_at_bat",
    "pitcher_days_since_prev_game", "batter_days_since_prev_game",
    "pitcher_days_until_next_game", "batter_days_until_next_game",
    "api_break_z_with_gravity", "api_break_x_arm", "api_break_x_batter_in",
    "arm_angle",
    "hyper_speed",
    "age_pit_legacy", "age_bat_legacy", "age_pit", "age_bat",
    # NOTE: The following columns from the original task spec were NOT present
    # in the 2024-04-01 pybaseball output. They are retained in PITCHES_SCHEMA
    # because they appear in older seasons or were removed by pybaseball:
    #   "fielder_2_1"          -- not in 2024 output; omitted from schema
    #   "sprint_speed"         -- not in 2024 output; omitted from schema
    #   "pitch_number_appearance" -- not in 2024 output; omitted from schema
}


def test_schema_covers_pybaseball_columns():
    """Every pybaseball Statcast column is represented in PITCHES_SCHEMA."""
    schema_names = {c.name for c in PITCHES_SCHEMA}
    missing = EXPECTED_PYBASEBALL_COLUMNS - schema_names
    assert not missing, f"PITCHES_SCHEMA missing pybaseball columns: {sorted(missing)}"
