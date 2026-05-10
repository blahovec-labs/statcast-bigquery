"""GAME_UMPIRES_SCHEMA: single source of truth for the game_umpires table.

Sources umpire crew assignments from MLB statsapi (/api/v1/game/{game_pk}/boxscore).
One row per (game_pk, position). Statcast's `umpire` field is always NULL — this
table is how downstream queries get an actual umpire identifier per game.
"""

from __future__ import annotations

from statcast_bigquery.schema import ColumnSpec, PartitioningSpec

GAME_UMPIRES_SCHEMA: list[ColumnSpec] = [
    ColumnSpec(
        name="game_pk",
        type="INT64",
        mode="REQUIRED",
        short_description="MLB statsapi game primary key.",
        business_definition=(
            "Same identifier used by `statcast_pitches.game_pk`. Joins this table "
            "to per-pitch data for umpire-level analysis."
        ),
        semantic_tags=["identifier"],
        valid_range=None,
        valid_values=None,
        example_value=746070,
        gotchas=[],
        statsapi_equivalent="gamePk",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_date",
        type="DATE",
        mode="REQUIRED",
        short_description="Date the game was played (in stadium-local time).",
        business_definition=(
            "Date of the game, denormalized for partitioning. Matches "
            "`statcast_pitches.game_date` for the same `game_pk`."
        ),
        semantic_tags=["temporal", "partition_key"],
        valid_range=None,
        valid_values=None,
        example_value="2023-08-15",
        gotchas=[],
        statsapi_equivalent="gameDate",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="position",
        type="STRING",
        mode="REQUIRED",
        short_description="Umpire position on the field.",
        business_definition=(
            "Position the umpire is officiating: HP (home plate), 1B, 2B, 3B, "
            "LF, RF. Most regular-season games have only 4 (HP/1B/2B/3B); "
            "postseason games may include LF/RF crew expansions. HP is the "
            "ball/strike caller and the only position relevant to umpire "
            "bias features."
        ),
        semantic_tags=["category"],
        valid_range=None,
        valid_values=["HP", "1B", "2B", "3B", "LF", "RF"],
        example_value="HP",
        gotchas=[
            "Filter to position='HP' for ball/strike umpire-bias analysis.",
            "Older games may use slightly different officialType strings — "
            "client normalizes to these 6 codes.",
        ],
        statsapi_equivalent="officials[].officialType",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="umpire_id",
        type="INT64",
        mode="REQUIRED",
        short_description="MLB statsapi person ID for the umpire.",
        business_definition=(
            "Umpire's identifier in the MLB statsapi people endpoint. Stable "
            "across games and seasons; same umpire always gets the same ID. "
            "Use this as the join key for umpire-level rolling-window features."
        ),
        semantic_tags=["identifier"],
        valid_range=None,
        valid_values=None,
        example_value=427164,
        gotchas=[],
        statsapi_equivalent="officials[].official.id",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="umpire_name",
        type="STRING",
        mode="NULLABLE",
        short_description="Full name of the umpire as listed in statsapi.",
        business_definition=(
            "Human-readable umpire name (e.g. 'Andy Fletcher'). Useful for "
            "dashboards and reports; do NOT join on this — names can change "
            "(marriages, etc.). Use umpire_id for joins."
        ),
        semantic_tags=["display_name"],
        valid_range=None,
        valid_values=None,
        example_value="Andy Fletcher",
        gotchas=["Do not join on this — name strings are not stable identifiers."],
        statsapi_equivalent="officials[].official.fullName",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
]


def get_umpires_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="game_date",
        type="DAY",
        clustering=["game_pk"],
    )
