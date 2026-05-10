"""ColumnSpec dataclass + PITCHES_SCHEMA: single source of truth for the Statcast pitch table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SCHEMA_VERSION = "0.1.0"

BqType = Literal[
    "INT64",
    "FLOAT64",
    "STRING",
    "BOOL",
    "DATE",
    "TIMESTAMP",
    "TIME",
    "NUMERIC",
]
BqMode = Literal["REQUIRED", "NULLABLE"]

_VALID_TYPES = set(BqType.__args__)  # type: ignore[attr-defined]
_VALID_MODES = set(BqMode.__args__)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ColumnSpec:
    """Single source of truth for one column in `statcast_pitches`."""

    name: str
    type: BqType
    mode: BqMode
    short_description: str
    business_definition: str
    semantic_tags: list[str]
    valid_range: tuple[float, float] | None
    valid_values: list[str] | None
    example_value: object | None
    gotchas: list[str]
    statsapi_equivalent: str | None
    pybaseball_source_field: str
    deprecated_in_year: int | None

    def __post_init__(self) -> None:
        if self.type not in _VALID_TYPES:
            raise ValueError(f"{self.name}: invalid type {self.type!r}")
        if self.mode not in _VALID_MODES:
            raise ValueError(f"{self.name}: invalid mode {self.mode!r}")
        if not self.business_definition.strip():
            raise ValueError(f"{self.name}: business_definition required")


@dataclass(frozen=True)
class PartitioningSpec:
    field: str
    type: Literal["DAY", "MONTH", "YEAR"]
    clustering: list[str]


def get_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="game_date",
        type="DAY",
        clustering=["home_team", "away_team", "game_pk"],
    )


# Authored in Task 3. Full 118-column coverage of pybaseball.statcast() output.
PITCHES_SCHEMA: list[ColumnSpec] = [
    # -------------------------------------------------------------------------
    # Identifiers
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="game_pk",
        type="INT64",
        mode="REQUIRED",
        short_description="MLB unique game identifier.",
        business_definition=(
            "Stable integer identifying a single MLB game across all data sources "
            "(statsapi, Statcast, Retrosheet). Use as the canonical join key."
        ),
        semantic_tags=["identifier", "join_key", "mlb_canonical"],
        valid_range=None,
        valid_values=None,
        example_value=746789,
        gotchas=[],
        statsapi_equivalent="gamePk",
        pybaseball_source_field="game_pk",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_date",
        type="DATE",
        mode="REQUIRED",
        short_description="Date the game was played (ET).",
        business_definition=(
            "Calendar date (ET) on which the game occurred. Serves as the partition "
            "key for this table. Games that start after midnight ET still carry the "
            "logical game date, not the wall-clock date."
        ),
        semantic_tags=["temporal", "identifier", "mlb_canonical"],
        valid_range=None,
        valid_values=None,
        example_value="2024-04-01",
        gotchas=[
            "Late-night games (e.g., West-Coast doubleheader Game 2) may have a "
            "wall-clock date one day ahead of game_date."
        ],
        statsapi_equivalent="officialDate",
        pybaseball_source_field="game_date",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_year",
        type="INT64",
        mode="REQUIRED",
        short_description="Calendar year of the game.",
        business_definition=(
            "Four-digit calendar year in which the game was played. Redundant with "
            "EXTRACT(YEAR FROM game_date) but retained for convenient filtering "
            "and partitioning without date arithmetic."
        ),
        semantic_tags=["temporal", "identifier"],
        valid_range=(2008.0, 2030.0),
        valid_values=None,
        example_value=2024,
        gotchas=["Statcast coverage begins mid-2015; pre-2015 rows are sparse or absent."],
        statsapi_equivalent="season",
        pybaseball_source_field="game_year",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_type",
        type="STRING",
        mode="NULLABLE",
        short_description="Type of game (Regular, Postseason, Spring, etc.).",
        business_definition=(
            "Single-character code describing the game type. R=Regular Season, "
            "S=Spring Training, E=Exhibition, F=Wild Card, D=Division Series, "
            "L=League Championship, W=World Series, A=All-Star."
        ),
        semantic_tags=["pitch_context", "identifier"],
        valid_range=None,
        valid_values=["R", "S", "E", "F", "D", "L", "W", "A"],
        example_value="R",
        gotchas=[
            "Most analytical queries should filter game_type='R' to exclude "
            "Spring Training and postseason from rate-stat denominators."
        ],
        statsapi_equivalent="gameType",
        pybaseball_source_field="game_type",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="at_bat_number",
        type="INT64",
        mode="NULLABLE",
        short_description="Plate appearance number within the game.",
        business_definition=(
            "Sequential count of plate appearances within a game, starting at 1. "
            "Increments on each new batter regardless of inning. Use with game_pk "
            "and pitch_number to reconstruct game flow."
        ),
        semantic_tags=["pitch_context", "identifier"],
        valid_range=(1.0, 100.0),
        valid_values=None,
        example_value=23,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="at_bat_number",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="pitch_number",
        type="INT64",
        mode="NULLABLE",
        short_description="Pitch sequence number within the plate appearance.",
        business_definition=(
            "Count of pitches thrown in this plate appearance, starting at 1 for "
            "the first pitch. Resets to 1 for each new at_bat_number."
        ),
        semantic_tags=["pitch_context"],
        valid_range=(1.0, 25.0),
        valid_values=None,
        example_value=3,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="pitch_number",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="sv_id",
        type="STRING",
        mode="NULLABLE",
        short_description="Non-unique Baseball Savant play-event ID per game.",
        business_definition=(
            "Internal Baseball Savant identifier for a play event within a game. "
            "Encoded as 'YYMMDD_HHMMSS' (string), not a numeric ID. "
            "Not guaranteed to be unique; use (game_pk, at_bat_number, pitch_number) "
            "as the natural key instead."
        ),
        semantic_tags=["identifier"],
        valid_range=None,
        valid_values=None,
        example_value="151004_174434",
        gotchas=[
            "Not unique — do not use as a primary key.",
            "String, not int — values like '151004_174434' encode YYMMDD_HHMMSS.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="sv_id",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Players
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="batter",
        type="INT64",
        mode="NULLABLE",
        short_description="MLB Player ID of the batter.",
        business_definition=(
            "Unique MLB Player ID (MLBAM ID) for the batter in this plate appearance. "
            "Stable across seasons; use to join to player dimension tables."
        ),
        semantic_tags=["identifier", "join_key", "mlb_canonical"],
        valid_range=None,
        valid_values=None,
        example_value=660670,
        gotchas=[],
        statsapi_equivalent="batterId",
        pybaseball_source_field="batter",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="pitcher",
        type="INT64",
        mode="NULLABLE",
        short_description="MLB Player ID of the pitcher.",
        business_definition=(
            "Unique MLB Player ID (MLBAM ID) for the pitcher throwing this pitch. "
            "Stable across seasons; use to join to player dimension tables."
        ),
        semantic_tags=["identifier", "join_key", "mlb_canonical"],
        valid_range=None,
        valid_values=None,
        example_value=592789,
        gotchas=[],
        statsapi_equivalent="pitcherId",
        pybaseball_source_field="pitcher",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="player_name",
        type="STRING",
        mode="NULLABLE",
        short_description="Display name of the pitcher (Last, First format).",
        business_definition=(
            "Human-readable display name for the pitcher in 'Last, First' format "
            "as provided by Baseball Savant. Primarily for debugging and display; "
            "use the numeric `pitcher` ID for programmatic joins."
        ),
        semantic_tags=["identifier"],
        valid_range=None,
        valid_values=None,
        example_value="Cole, Gerrit",
        gotchas=[
            "Name format is 'Last, First', not 'First Last'.",
            "Do not join on name — use the `pitcher` MLBAM ID instead.",
        ],
        statsapi_equivalent="fullName",
        pybaseball_source_field="player_name",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fielder_2",
        type="INT64",
        mode="NULLABLE",
        short_description="Catcher MLB Player ID at time of pitch.",
        business_definition=(
            "MLBAM Player ID of the catcher (fielding position 2) at the time of the "
            "pitch. NULL when fielder alignment data is unavailable."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None,
        valid_values=None,
        example_value=663728,
        gotchas=["May be NULL for some historical records before 2018."],
        statsapi_equivalent=None,
        pybaseball_source_field="fielder_2",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fielder_3",
        type="INT64",
        mode="NULLABLE",
        short_description="First baseman MLB Player ID at time of pitch.",
        business_definition=(
            "MLBAM Player ID of the first baseman (position 3) at the time of pitch. "
            "NULL when fielder data is unavailable."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None,
        valid_values=None,
        example_value=572816,
        gotchas=["May be NULL for historical records pre-2018."],
        statsapi_equivalent=None,
        pybaseball_source_field="fielder_3",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fielder_4",
        type="INT64",
        mode="NULLABLE",
        short_description="Second baseman MLB Player ID at time of pitch.",
        business_definition=(
            "MLBAM Player ID of the second baseman (position 4) at the time of pitch. "
            "NULL when fielder data is unavailable."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None,
        valid_values=None,
        example_value=621439,
        gotchas=["May be NULL for historical records pre-2018."],
        statsapi_equivalent=None,
        pybaseball_source_field="fielder_4",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fielder_5",
        type="INT64",
        mode="NULLABLE",
        short_description="Third baseman MLB Player ID at time of pitch.",
        business_definition=(
            "MLBAM Player ID of the third baseman (position 5) at the time of pitch. "
            "NULL when fielder data is unavailable."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None,
        valid_values=None,
        example_value=624413,
        gotchas=["May be NULL for historical records pre-2018."],
        statsapi_equivalent=None,
        pybaseball_source_field="fielder_5",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fielder_6",
        type="INT64",
        mode="NULLABLE",
        short_description="Shortstop MLB Player ID at time of pitch.",
        business_definition=(
            "MLBAM Player ID of the shortstop (position 6) at the time of pitch. "
            "NULL when fielder data is unavailable."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None,
        valid_values=None,
        example_value=665742,
        gotchas=["May be NULL for historical records pre-2018."],
        statsapi_equivalent=None,
        pybaseball_source_field="fielder_6",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fielder_7",
        type="INT64",
        mode="NULLABLE",
        short_description="Left fielder MLB Player ID at time of pitch.",
        business_definition=(
            "MLBAM Player ID of the left fielder (position 7) at the time of pitch. "
            "NULL when fielder data is unavailable."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None,
        valid_values=None,
        example_value=641355,
        gotchas=["May be NULL for historical records pre-2018."],
        statsapi_equivalent=None,
        pybaseball_source_field="fielder_7",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fielder_8",
        type="INT64",
        mode="NULLABLE",
        short_description="Center fielder MLB Player ID at time of pitch.",
        business_definition=(
            "MLBAM Player ID of the center fielder (position 8) at the time of pitch. "
            "NULL when fielder data is unavailable."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None,
        valid_values=None,
        example_value=608369,
        gotchas=["May be NULL for historical records pre-2018."],
        statsapi_equivalent=None,
        pybaseball_source_field="fielder_8",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fielder_9",
        type="INT64",
        mode="NULLABLE",
        short_description="Right fielder MLB Player ID at time of pitch.",
        business_definition=(
            "MLBAM Player ID of the right fielder (position 9) at the time of pitch. "
            "NULL when fielder data is unavailable."
        ),
        semantic_tags=["identifier", "join_key"],
        valid_range=None,
        valid_values=None,
        example_value=665487,
        gotchas=["May be NULL for historical records pre-2018."],
        statsapi_equivalent=None,
        pybaseball_source_field="fielder_9",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Teams
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="home_team",
        type="STRING",
        mode="NULLABLE",
        short_description="Home team abbreviation.",
        business_definition=(
            "Three-letter abbreviation for the home team, as used by Baseball Savant "
            "(e.g., NYY, LAD). May differ from statsapi team abbreviations for some "
            "franchises (e.g., 'AZ' vs 'ARI', 'ATH' vs 'OAK')."
        ),
        semantic_tags=["team", "identifier"],
        valid_range=None,
        valid_values=None,
        example_value="NYY",
        gotchas=[
            "Abbreviations changed when franchises relocated (OAK → ATH in 2025).",
            "Use game_pk + statsapi for authoritative team IDs; abbreviations are display-only.",
        ],
        statsapi_equivalent="homeTeam.abbreviation",
        pybaseball_source_field="home_team",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_team",
        type="STRING",
        mode="NULLABLE",
        short_description="Away team abbreviation.",
        business_definition=(
            "Three-letter abbreviation for the away (visiting) team as used by "
            "Baseball Savant. Same caveats as home_team regarding franchise moves."
        ),
        semantic_tags=["team", "identifier"],
        valid_range=None,
        valid_values=None,
        example_value="BOS",
        gotchas=[
            "Abbreviations changed when franchises relocated (OAK → ATH in 2025).",
        ],
        statsapi_equivalent="awayTeam.abbreviation",
        pybaseball_source_field="away_team",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Inning + count + baserunners
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="inning",
        type="INT64",
        mode="NULLABLE",
        short_description="Inning number at time of pitch.",
        business_definition=(
            "Pre-pitch inning number, starting at 1. Extra-inning games will have "
            "values > 9."
        ),
        semantic_tags=["pitch_context"],
        valid_range=(1.0, 25.0),
        valid_values=None,
        example_value=7,
        gotchas=[],
        statsapi_equivalent="about.inning",
        pybaseball_source_field="inning",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="inning_topbot",
        type="STRING",
        mode="NULLABLE",
        short_description="Top or bottom half of the inning.",
        business_definition=(
            "Indicates which half of the inning is being played. 'Top' means the "
            "away team is batting; 'Bot' means the home team is batting."
        ),
        semantic_tags=["pitch_context"],
        valid_range=None,
        valid_values=["Top", "Bot"],
        example_value="Top",
        gotchas=[
            "The value is 'Bot' (not 'Bottom') — string matches must use 'Bot'."
        ],
        statsapi_equivalent="about.halfInning",
        pybaseball_source_field="inning_topbot",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="balls",
        type="INT64",
        mode="NULLABLE",
        short_description="Ball count before this pitch.",
        business_definition=(
            "Number of balls in the count at the time this pitch was thrown (pre-pitch). "
            "Ranges 0-3; a fourth ball results in a walk and starts the next at-bat."
        ),
        semantic_tags=["pitch_context"],
        valid_range=(0.0, 3.0),
        valid_values=None,
        example_value=2,
        gotchas=[],
        statsapi_equivalent="count.balls",
        pybaseball_source_field="balls",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="strikes",
        type="INT64",
        mode="NULLABLE",
        short_description="Strike count before this pitch.",
        business_definition=(
            "Number of strikes in the count at the time this pitch was thrown (pre-pitch). "
            "Ranges 0-2; a third strike on a non-foul ends the at-bat."
        ),
        semantic_tags=["pitch_context"],
        valid_range=(0.0, 2.0),
        valid_values=None,
        example_value=1,
        gotchas=[
            "A foul ball with 2 strikes does not increment strikes; the count stays at 2."
        ],
        statsapi_equivalent="count.strikes",
        pybaseball_source_field="strikes",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="outs_when_up",
        type="INT64",
        mode="NULLABLE",
        short_description="Outs recorded before this plate appearance.",
        business_definition=(
            "Number of outs in the inning at the start of this plate appearance (pre-pitch). "
            "Ranges 0-2."
        ),
        semantic_tags=["pitch_context"],
        valid_range=(0.0, 2.0),
        valid_values=None,
        example_value=1,
        gotchas=[],
        statsapi_equivalent="count.outs",
        pybaseball_source_field="outs_when_up",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="on_1b",
        type="INT64",
        mode="NULLABLE",
        short_description="MLBAM ID of runner on first base (NULL if empty).",
        business_definition=(
            "MLBAM Player ID of the baserunner occupying first base at the time of "
            "the pitch. NULL when first base is unoccupied."
        ),
        semantic_tags=["runner", "pitch_context"],
        valid_range=None,
        valid_values=None,
        example_value=660670,
        gotchas=["NULL means base is empty, not missing data."],
        statsapi_equivalent=None,
        pybaseball_source_field="on_1b",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="on_2b",
        type="INT64",
        mode="NULLABLE",
        short_description="MLBAM ID of runner on second base (NULL if empty).",
        business_definition=(
            "MLBAM Player ID of the baserunner occupying second base at the time of "
            "the pitch. NULL when second base is unoccupied."
        ),
        semantic_tags=["runner", "pitch_context"],
        valid_range=None,
        valid_values=None,
        example_value=592789,
        gotchas=["NULL means base is empty, not missing data."],
        statsapi_equivalent=None,
        pybaseball_source_field="on_2b",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="on_3b",
        type="INT64",
        mode="NULLABLE",
        short_description="MLBAM ID of runner on third base (NULL if empty).",
        business_definition=(
            "MLBAM Player ID of the baserunner occupying third base at the time of "
            "the pitch. NULL when third base is unoccupied."
        ),
        semantic_tags=["runner", "pitch_context"],
        valid_range=None,
        valid_values=None,
        example_value=641355,
        gotchas=["NULL means base is empty, not missing data."],
        statsapi_equivalent=None,
        pybaseball_source_field="on_3b",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Score state
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="home_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Home team score before this pitch.",
        business_definition=(
            "Runs scored by the home team as of the start of this plate appearance, "
            "before this pitch is thrown."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 30.0),
        valid_values=None,
        example_value=3,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="home_score",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Away team score before this pitch.",
        business_definition=(
            "Runs scored by the away team as of the start of this plate appearance, "
            "before this pitch is thrown."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 30.0),
        valid_values=None,
        example_value=1,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="away_score",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="post_home_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Home team score after this pitch.",
        business_definition=(
            "Runs scored by the home team immediately after this pitch resolves. "
            "Differs from home_score when a run scores on this play."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 30.0),
        valid_values=None,
        example_value=3,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="post_home_score",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="post_away_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Away team score after this pitch.",
        business_definition=(
            "Runs scored by the away team immediately after this pitch resolves. "
            "Differs from away_score when a run scores on this play."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 30.0),
        valid_values=None,
        example_value=2,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="post_away_score",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="bat_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Batting team score before this pitch.",
        business_definition=(
            "Score of the team currently at bat before this pitch. Derived from "
            "home_score/away_score based on inning_topbot. Convenience column."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 30.0),
        valid_values=None,
        example_value=2,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="bat_score",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="fld_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Fielding team score before this pitch.",
        business_definition=(
            "Score of the team currently in the field before this pitch. Derived from "
            "home_score/away_score based on inning_topbot. Convenience column."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 30.0),
        valid_values=None,
        example_value=3,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="fld_score",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="post_bat_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Batting team score after this pitch.",
        business_definition=(
            "Score of the team at bat immediately after this pitch resolves. Differs "
            "from bat_score when a run scores on this play."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 30.0),
        valid_values=None,
        example_value=3,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="post_bat_score",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="post_fld_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Fielding team score after this pitch.",
        business_definition=(
            "Score of the team in the field immediately after this pitch resolves. "
            "Added during Task 3 discovery — present in pybaseball output."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 30.0),
        valid_values=None,
        example_value=3,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="post_fld_score",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_score_diff",
        type="INT64",
        mode="NULLABLE",
        short_description="Home score minus away score at time of pitch.",
        business_definition=(
            "Run differential from the home team's perspective (home_score - away_score) "
            "at the time of the pitch. Positive means home team is leading."
        ),
        semantic_tags=["score_state"],
        valid_range=(-30.0, 30.0),
        valid_values=None,
        example_value=2,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="home_score_diff",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="bat_score_diff",
        type="INT64",
        mode="NULLABLE",
        short_description="Batting team score minus fielding team score.",
        business_definition=(
            "Run differential from the batting team's perspective "
            "(bat_score - fld_score). Positive means batting team is leading."
        ),
        semantic_tags=["score_state"],
        valid_range=(-30.0, 30.0),
        valid_values=None,
        example_value=-1,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="bat_score_diff",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Pitch type / classification
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="pitch_type",
        type="STRING",
        mode="NULLABLE",
        short_description="Two-letter pitch type code from Statcast.",
        business_definition=(
            "Statcast pitch classification code. Common values: FF=4-Seam Fastball, "
            "SI=Sinker, SL=Slider, CH=Changeup, CU=Curveball, FC=Cutter, "
            "KC=Knuckle-Curve, ST=Sweeper, SV=Slurve, CS=Slow Curve, KN=Knuckleball, "
            "EP=Eephus, PO=Pitchout, FA=Fastball (generic), IN=Intentional Ball. "
            "NULL for pitches that could not be classified."
        ),
        semantic_tags=["pitch_physics", "pitch_context"],
        valid_range=None,
        valid_values=[
            "FF", "SI", "SL", "CH", "CU", "FC", "KC", "ST", "SV",
            "CS", "KN", "EP", "PO", "FA", "IN", "FO", "SC",
        ],
        example_value="FF",
        gotchas=[
            "Classification methodology changed significantly between 2016 and 2020 "
            "as Statcast switched algorithms; pitch_type values are not directly "
            "comparable across that boundary.",
            "NULL rows are not throws to the plate — check `description` for context.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="pitch_type",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="pitch_name",
        type="STRING",
        mode="NULLABLE",
        short_description="Human-readable pitch name from Statcast.",
        business_definition=(
            "Full English name for the pitch type (e.g., '4-Seam Fastball', 'Slider'). "
            "Corresponds to pitch_type code but is more human-readable. NULL when "
            "pitch_type is NULL."
        ),
        semantic_tags=["pitch_physics", "pitch_context"],
        valid_range=None,
        valid_values=None,
        example_value="4-Seam Fastball",
        gotchas=["Use pitch_type for grouping/filtering; pitch_name is display-only."],
        statsapi_equivalent=None,
        pybaseball_source_field="pitch_name",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="type",
        type="STRING",
        mode="NULLABLE",
        short_description="Broad pitch outcome: B=Ball, S=Strike, X=In play.",
        business_definition=(
            "Single-character pitch result category. B=ball (including pitchouts), "
            "S=strike (swinging, called, foul, or foul tip), X=ball put in play. "
            "Use `description` for more granular outcome."
        ),
        semantic_tags=["outcome_pitch"],
        valid_range=None,
        valid_values=["B", "S", "X"],
        example_value="S",
        gotchas=[
            "Foul balls count as S (strike), not X (in play).",
            "Intentional balls and pitchouts are B.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="type",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Pitch physics — velocity and spin
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="release_speed",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitch velocity in mph out of hand.",
        business_definition=(
            "Velocity of the pitch in miles per hour measured at the point of release, "
            "normalized to a consistent out-of-hand scale. This is the 'raw' velocity "
            "before accounting for distance to the plate (see effective_speed)."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(50.0, 110.0),
        valid_values=None,
        example_value=96.4,
        gotchas=[
            "NULL on non-pitch events (pickoff attempts, mound visits).",
            "Pre-2017 values from PITCHf/x differ slightly in calibration from "
            "post-2017 Trackman values.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="release_speed",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="effective_speed",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Perceived velocity adjusted for release extension.",
        business_definition=(
            "Derived pitch velocity (mph) that accounts for how far in front of the "
            "pitching rubber the pitcher releases the ball (release_extension). A longer "
            "extension at the same release_speed results in a higher effective_speed "
            "because the ball has less distance to travel."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(50.0, 115.0),
        valid_values=None,
        example_value=97.8,
        gotchas=[
            "NULL when release_extension is unavailable.",
            "Not directly comparable to PITCHf/x era data before ~2017.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="effective_speed",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="release_spin_rate",
        type="INT64",
        mode="NULLABLE",
        short_description="Spin rate in RPM at pitch release.",
        business_definition=(
            "Spin rate of the pitch in revolutions per minute (RPM) as measured by "
            "Statcast at the point of release. High spin rate generally produces more "
            "movement but the direction depends on spin axis."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(0.0, 3500.0),
        valid_values=None,
        example_value=2312,
        gotchas=[
            "Spin rate availability improved significantly in 2017; pre-2017 values "
            "are less reliable.",
            "Some pitchers doctor spin with substances; pre-2021 enforcement values "
            "may be artificially elevated.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="release_spin_rate",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="release_extension",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitcher extension in feet from pitching rubber.",
        business_definition=(
            "Distance in feet from the pitching rubber to the point of ball release. "
            "A value of 6.5 means the pitcher released the ball 6.5 feet in front "
            "of the rubber. Higher extension reduces the reaction time for batters."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(3.0, 9.0),
        valid_values=None,
        example_value=6.4,
        gotchas=["NULL for some pre-2017 pitches."],
        statsapi_equivalent=None,
        pybaseball_source_field="release_extension",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="release_pos_x",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Horizontal release position in feet (catcher's view).",
        business_definition=(
            "Horizontal position of the ball at the point of release, measured in feet "
            "from the center of the rubber from the catcher's perspective. Negative "
            "values are to the right (first-base side), positive to the left."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-4.0, 4.0),
        valid_values=None,
        example_value=-1.7,
        gotchas=["Catcher's perspective: negative = arm-side for a right-handed pitcher."],
        statsapi_equivalent=None,
        pybaseball_source_field="release_pos_x",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="release_pos_z",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Vertical release position in feet.",
        business_definition=(
            "Vertical position of the ball at the point of release in feet above the "
            "ground. Typical values range from about 5.0 (sidearm) to 7.5 (overhand)."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(3.0, 9.0),
        valid_values=None,
        example_value=6.1,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="release_pos_z",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="release_pos_y",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Distance from catcher to release point in feet.",
        business_definition=(
            "Distance in feet from the catcher (home plate) to the release point, "
            "measured along the y-axis (mound-to-plate direction). Typical values "
            "are around 54-55 feet (mound is 60.5 feet from plate, minus extension)."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(50.0, 60.0),
        valid_values=None,
        example_value=54.1,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="release_pos_y",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="spin_axis",
        type="INT64",
        mode="NULLABLE",
        short_description="Spin axis in degrees (0-360, 2D X-Z plane).",
        business_definition=(
            "Orientation of the pitch's spin axis in the 2D X-Z plane, measured in "
            "degrees (0-360). 180° corresponds to pure backspin (4-seam fastball), "
            "0°/360° corresponds to pure topspin. Determines the direction of "
            "Magnus-force movement."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(0.0, 360.0),
        valid_values=None,
        example_value=215,
        gotchas=[
            "Spin axis does not encode transverse spin (gyro component); "
            "use api_break_* fields for net movement.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="spin_axis",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Pitch physics — trajectory (Statcast ball-tracking model)
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="vx0",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitch velocity (ft/s) in x-dimension at y=50 ft.",
        business_definition=(
            "Velocity of the pitch in feet per second along the x-axis (horizontal, "
            "catcher's perspective) at the reference point y=50 feet from home plate. "
            "Used with vy0/vz0 and ax/ay/az to reconstruct the full pitch trajectory."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-20.0, 20.0),
        valid_values=None,
        example_value=-8.3,
        gotchas=["Values are at y=50 ft reference, not at release."],
        statsapi_equivalent=None,
        pybaseball_source_field="vx0",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="vy0",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitch velocity (ft/s) in y-dimension at y=50 ft.",
        business_definition=(
            "Velocity of the pitch in feet per second along the y-axis (toward the "
            "plate) at the reference point y=50 feet. Always negative (ball is moving "
            "toward the catcher)."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-160.0, -100.0),
        valid_values=None,
        example_value=-138.5,
        gotchas=["Always negative; magnitude converts approximately to mph via /1.467."],
        statsapi_equivalent=None,
        pybaseball_source_field="vy0",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="vz0",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitch velocity (ft/s) in z-dimension at y=50 ft.",
        business_definition=(
            "Velocity of the pitch in feet per second along the z-axis (vertical) "
            "at the reference point y=50 feet from home plate."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-25.0, 25.0),
        valid_values=None,
        example_value=-6.2,
        gotchas=["Values are at y=50 ft reference, not at release."],
        statsapi_equivalent=None,
        pybaseball_source_field="vz0",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="ax",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitch acceleration (ft/s²) in x-dimension at y=50 ft.",
        business_definition=(
            "Horizontal acceleration of the pitch in feet per second squared at the "
            "reference point y=50 feet. Captures lateral movement from spin and drag."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-30.0, 30.0),
        valid_values=None,
        example_value=14.2,
        gotchas=["Values are at y=50 ft reference, not at release."],
        statsapi_equivalent=None,
        pybaseball_source_field="ax",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="ay",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitch acceleration (ft/s²) in y-dimension at y=50 ft.",
        business_definition=(
            "Deceleration of the pitch along the y-axis (toward the plate) in feet "
            "per second squared, primarily caused by aerodynamic drag. Negative "
            "values indicate the ball is slowing down."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(15.0, 35.0),
        valid_values=None,
        example_value=28.7,
        gotchas=["Always positive (drag decelerates the ball in the -y direction)."],
        statsapi_equivalent=None,
        pybaseball_source_field="ay",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="az",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitch acceleration (ft/s²) in z-dimension at y=50 ft.",
        business_definition=(
            "Vertical acceleration of the pitch in feet per second squared, combining "
            "gravity (-32.2 ft/s²) and the Magnus lift from spin. A 4-seam fastball "
            "with backspin has less negative az than a curveball."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-50.0, 15.0),
        valid_values=None,
        example_value=-20.4,
        gotchas=["Gravity contributes -32.2 ft/s²; positive Magnus lift reduces magnitude."],
        statsapi_equivalent=None,
        pybaseball_source_field="az",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="pfx_x",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Horizontal pitch movement in feet (catcher's view).",
        business_definition=(
            "Horizontal movement of the pitch in feet relative to a theoretical "
            "spin-free trajectory (gravity-only path), measured from the catcher's "
            "perspective. Positive values break toward the left (first-base side for "
            "a right-hander)."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-3.0, 3.0),
        valid_values=None,
        example_value=0.73,
        gotchas=[
            "Reference is a gravity-only no-spin trajectory, not a straight line.",
            "Catcher's perspective: a right-handed pitcher's pfx_x is typically positive.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="pfx_x",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="pfx_z",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Vertical pitch movement in feet (induced vertical break).",
        business_definition=(
            "Vertical movement of the pitch in feet relative to a spin-free "
            "(gravity-only) trajectory. Positive values indicate the ball dropped "
            "less than gravity would predict (e.g., fastball 'rise'). Negative "
            "values indicate extra drop (e.g., curveball)."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-3.0, 3.0),
        valid_values=None,
        example_value=1.12,
        gotchas=[
            "Positive pfx_z is 'rise' relative to gravity, not literal upward movement.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="pfx_z",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Pitch physics — modern API break metrics
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="api_break_z_with_gravity",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Vertical break in inches including gravity effect.",
        business_definition=(
            "Vertical break of the pitch in inches, measured as total drop from a "
            "straight-line path including the effect of gravity. Unlike pfx_z (which "
            "removes gravity), this reflects the total vertical displacement the batter "
            "must account for. Available from the Statcast API."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-80.0, 10.0),
        valid_values=None,
        example_value=-25.3,
        gotchas=[
            "Includes gravity; pfx_z excludes gravity. Prefer this for batter-relevant "
            "movement calculations.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="api_break_z_with_gravity",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="api_break_x_arm",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Horizontal break in inches toward pitcher's arm side.",
        business_definition=(
            "Horizontal movement of the pitch in inches toward the pitcher's throwing-arm "
            "side, from the Statcast API. For a right-handed pitcher, positive values "
            "mean the ball moved toward the right (first-base side from the catcher's view)."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-30.0, 30.0),
        valid_values=None,
        example_value=12.4,
        gotchas=[
            "Arm-side perspective differs between LHP and RHP; normalize before "
            "cross-handedness comparisons.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="api_break_x_arm",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="api_break_x_batter_in",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Horizontal break in inches toward batter's inside.",
        business_definition=(
            "Horizontal movement of the pitch in inches toward the batter's body "
            "(inside edge of the strike zone), from the Statcast API. Accounts for "
            "batter handedness, making this useful for matchup analysis."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-30.0, 30.0),
        valid_values=None,
        example_value=-8.7,
        gotchas=[
            "Sign convention is batter-relative; unlike api_break_x_arm which is "
            "pitcher-relative.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="api_break_x_batter_in",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="arm_angle",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Pitcher's arm angle in degrees at release.",
        business_definition=(
            "Angle in degrees between the ground and the line from the pitcher's "
            "shoulder to the ball at the point of release. 0° = sidearm, 90° = "
            "directly overhead. Captures the pitcher's arm slot."
        ),
        semantic_tags=["pitch_physics", "physics"],
        valid_range=(-10.0, 90.0),
        valid_values=None,
        example_value=38.5,
        gotchas=["Negative values are possible for submarine pitchers."],
        statsapi_equivalent=None,
        pybaseball_source_field="arm_angle",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Plate location
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="plate_x",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Horizontal position at home plate in feet (catcher's view).",
        business_definition=(
            "Horizontal position of the ball as it crosses the front of home plate, "
            "in feet from the center of the plate, from the catcher's perspective. "
            "Positive = glove side (for RHB, left side); negative = arm side. "
            "In 2026+ aligns with the ABS challenge system."
        ),
        semantic_tags=["pitch_location"],
        valid_range=(-3.0, 3.0),
        valid_values=None,
        example_value=-0.42,
        gotchas=[
            "Center of plate is 0.0; the plate is 17 inches (0.708 ft) wide each side.",
            "2026+ ABS alignment may shift historical calibration.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="plate_x",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="plate_z",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Vertical position at home plate in feet.",
        business_definition=(
            "Vertical height of the ball as it crosses the front of home plate, "
            "in feet above the ground. Values between sz_bot and sz_top are in the "
            "strike zone. In 2026+ aligns with the ABS challenge system."
        ),
        semantic_tags=["pitch_location"],
        valid_range=(-1.0, 6.0),
        valid_values=None,
        example_value=2.73,
        gotchas=[
            "The strike zone bounds are batter-specific (sz_top, sz_bot); there is no "
            "universal cutoff.",
            "2026+ ABS alignment may shift historical calibration.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="plate_z",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="sz_top",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Top of batter's strike zone in feet.",
        business_definition=(
            "Top of the batter-specific strike zone in feet above the ground, "
            "as determined by Statcast for this plate appearance. Varies by batter "
            "height and stance. In 2026+ aligns with the ABS-defined zone."
        ),
        semantic_tags=["pitch_location"],
        valid_range=(2.5, 4.5),
        valid_values=None,
        example_value=3.47,
        gotchas=[
            "Zone is batter-specific and can vary pitch to pitch within a PA for "
            "some legacy data.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="sz_top",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="sz_bot",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Bottom of batter's strike zone in feet.",
        business_definition=(
            "Bottom of the batter-specific strike zone in feet above the ground. "
            "Determined by Statcast based on batter height and stance. In 2026+ "
            "aligns with the ABS-defined zone."
        ),
        semantic_tags=["pitch_location"],
        valid_range=(1.0, 2.5),
        valid_values=None,
        example_value=1.52,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="sz_bot",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="zone",
        type="INT64",
        mode="NULLABLE",
        short_description="Strike zone location code (1-14).",
        business_definition=(
            "Integer code for where the pitch crossed the plate relative to the "
            "strike zone. Zones 1-9 are within the strike zone (3x3 grid, "
            "1=upper-left to 9=lower-right from catcher's view). Zones 11-14 are "
            "chase zones outside the strike zone."
        ),
        semantic_tags=["pitch_location"],
        valid_range=(1.0, 14.0),
        valid_values=None,
        example_value=5,
        gotchas=[
            "Zone 10 does not exist; values jump from 9 to 11.",
            "Chase zones 11-14 are often used for umpire bias analysis.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="zone",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Outcomes — pitch-level
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="description",
        type="STRING",
        mode="NULLABLE",
        short_description="Detailed description of this pitch outcome.",
        business_definition=(
            "Granular description of what happened on the pitch. Common values include: "
            "'called_strike', 'ball', 'swinging_strike', 'foul', 'hit_into_play', "
            "'blocked_ball', 'foul_tip', 'swinging_strike_blocked', 'pitchout', "
            "'intent_ball', 'missed_bunt', 'foul_bunt'. Drives the `type` column."
        ),
        semantic_tags=["outcome_pitch"],
        valid_range=None,
        valid_values=[
            "called_strike", "ball", "swinging_strike", "foul", "hit_into_play",
            "blocked_ball", "foul_tip", "swinging_strike_blocked", "pitchout",
            "intent_ball", "missed_bunt", "foul_bunt", "hit_into_play_score",
            "foul_pitchout",
        ],
        example_value="called_strike",
        gotchas=[
            "'hit_into_play' and 'hit_into_play_score' are separate values; check both "
            "when filtering balls in play.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="description",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="events",
        type="STRING",
        mode="NULLABLE",
        short_description="Event type for the resulting plate appearance.",
        business_definition=(
            "Plate appearance outcome when one occurs on this pitch. Non-NULL only on "
            "the final pitch of a plate appearance. Common values: 'single', 'double', "
            "'triple', 'home_run', 'strikeout', 'walk', 'field_out', 'grounded_into_double_play', "
            "'hit_by_pitch', 'sac_fly', 'sac_bunt', 'force_out', 'field_error', etc."
        ),
        semantic_tags=["outcome_at_bat"],
        valid_range=None,
        valid_values=None,
        example_value="single",
        gotchas=[
            "NULL on all non-terminal pitches — most rows have NULL events.",
            "Filter events IS NOT NULL to get plate appearance outcomes only.",
        ],
        statsapi_equivalent="result.eventType",
        pybaseball_source_field="events",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="des",
        type="STRING",
        mode="NULLABLE",
        short_description="Game-day narrative description of the plate appearance.",
        business_definition=(
            "Free-text game-day description of the full plate appearance (e.g., "
            "'Jose Ramirez singles on a ground ball to shortstop ...'). Non-NULL "
            "only on the terminal pitch of the plate appearance."
        ),
        semantic_tags=["outcome_at_bat"],
        valid_range=None,
        valid_values=None,
        example_value="Aaron Judge homers (3) on a fly ball to center field.",
        gotchas=["NULL on non-terminal pitches.", "Free text — not suitable for grouping."],
        statsapi_equivalent="result.description",
        pybaseball_source_field="des",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Batted ball
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="launch_speed",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Exit velocity in mph.",
        business_definition=(
            "Speed of the ball off the bat in miles per hour (Statcast measurement). "
            "Includes estimated values for some balls that were not directly tracked. "
            "NULL when the pitch was not put in play — check `description` or `events` first."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(20.0, 130.0),
        valid_values=None,
        example_value=98.7,
        gotchas=[
            "NULL on non-batted balls (strikeouts, walks, etc.).",
            "Includes estimates for some pre-2015 and poorly tracked balls.",
            "Use `estimated_woba_using_speedangle` for expected value; "
            "raw launch_speed alone is insufficient.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="launch_speed",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="launch_angle",
        type="INT64",
        mode="NULLABLE",
        short_description="Launch angle in degrees off the bat.",
        business_definition=(
            "Vertical angle of the batted ball relative to the horizontal at the "
            "point of contact, in degrees. Negative = groundball, 0-10 = liner/"
            "groundball, 10-25 = liner, 25-50 = flyball, >50 = popup. "
            "NULL on non-batted balls."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(-90.0, 90.0),
        valid_values=None,
        example_value=28,
        gotchas=["NULL on non-batted balls.", "Stored as integer (rounded)."],
        statsapi_equivalent=None,
        pybaseball_source_field="launch_angle",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="hit_distance_sc",
        type="INT64",
        mode="NULLABLE",
        short_description="Projected hit distance in feet (Statcast).",
        business_definition=(
            "Projected distance in feet of the batted ball, as estimated by Statcast. "
            "For fly balls and line drives this is the landing distance. NULL when "
            "the ball was not put in play or trajectory data is unavailable."
        ),
        semantic_tags=["batted_ball", "post_hit"],
        valid_range=(0.0, 600.0),
        valid_values=None,
        example_value=412,
        gotchas=["NULL on non-batted balls and groundballs that did not carry."],
        statsapi_equivalent=None,
        pybaseball_source_field="hit_distance_sc",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="hc_x",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Hit coordinate X (spray chart pixel, origin at home plate).",
        business_definition=(
            "X-coordinate of the batted ball's first landing (or fielding) location "
            "in the Baseball Savant spray-chart pixel coordinate system. Origin is "
            "home plate; positive X is toward first base. NULL on non-batted balls."
        ),
        semantic_tags=["batted_ball", "post_hit"],
        valid_range=None,
        valid_values=None,
        example_value=122.7,
        gotchas=[
            "Coordinate system is spray-chart pixels, not feet; not directly "
            "comparable to hc_y or real-world distances without a scaling factor.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="hc_x",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="hc_y",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Hit coordinate Y (spray chart pixel, origin at home plate).",
        business_definition=(
            "Y-coordinate of the batted ball's first landing (or fielding) location "
            "in the Baseball Savant spray-chart pixel coordinate system. Positive Y "
            "points toward center field. NULL on non-batted balls."
        ),
        semantic_tags=["batted_ball", "post_hit"],
        valid_range=None,
        valid_values=None,
        example_value=134.5,
        gotchas=[
            "Y-axis increases away from home plate toward the outfield wall.",
            "Same pixel-coordinate caveat as hc_x.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="hc_y",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="bb_type",
        type="STRING",
        mode="NULLABLE",
        short_description="Batted ball type classification.",
        business_definition=(
            "Categorical classification of the batted ball trajectory. Values: "
            "'ground_ball', 'line_drive', 'fly_ball', 'popup'. NULL on non-batted "
            "balls and some unclassified events."
        ),
        semantic_tags=["batted_ball", "post_hit"],
        valid_range=None,
        valid_values=["ground_ball", "line_drive", "fly_ball", "popup"],
        example_value="fly_ball",
        gotchas=["NULL on non-batted balls; also NULL for some pre-2016 events."],
        statsapi_equivalent=None,
        pybaseball_source_field="bb_type",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="hit_location",
        type="INT64",
        mode="NULLABLE",
        short_description="Fielding position number of first fielder to touch the ball.",
        business_definition=(
            "Position number (1-9) of the first fielder to touch the batted ball, "
            "per scorekeeper convention (1=pitcher, 2=catcher, 3=1B, 4=2B, 5=3B, "
            "6=SS, 7=LF, 8=CF, 9=RF). NULL when unavailable or not applicable."
        ),
        semantic_tags=["batted_ball", "post_hit"],
        valid_range=(1.0, 9.0),
        valid_values=None,
        example_value=8,
        gotchas=["NULL on many events; reliability improved after 2019."],
        statsapi_equivalent=None,
        pybaseball_source_field="hit_location",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Expected stats
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="estimated_ba_using_speedangle",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Expected batting average based on exit velocity and launch angle.",
        business_definition=(
            "Model-derived probability that this batted ball results in a hit, based "
            "solely on exit velocity and launch angle. Ranges 0.0 to 1.0. Also known "
            "as xBA. NULL on non-batted balls."
        ),
        semantic_tags=["expected_stats", "batted_ball"],
        valid_range=(0.0, 1.0),
        valid_values=None,
        example_value=0.412,
        gotchas=[
            "NULL on non-batted balls.",
            "Model is recalibrated annually; values before 2019 may use older coefficients.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="estimated_ba_using_speedangle",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="estimated_woba_using_speedangle",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Expected wOBA based on exit velocity and launch angle.",
        business_definition=(
            "Model-derived expected weighted On-Base Average (xwOBA) for this batted "
            "ball, based on exit velocity and launch angle. Removes defense and park "
            "effects to estimate the true offensive value of contact quality. NULL on "
            "non-batted balls."
        ),
        semantic_tags=["expected_stats", "batted_ball"],
        valid_range=(0.0, 2.0),
        valid_values=None,
        example_value=0.581,
        gotchas=[
            "NULL on non-batted balls.",
            "xwOBA > 1.0 is possible for elite barrels.",
            "Model recalibrated annually.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="estimated_woba_using_speedangle",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="estimated_slg_using_speedangle",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Expected SLG based on exit velocity and launch angle.",
        business_definition=(
            "Model-derived expected slugging percentage (xSLG) for this batted ball "
            "based on exit velocity and launch angle. Added during Task 3 discovery "
            "— present in pybaseball output. NULL on non-batted balls."
        ),
        semantic_tags=["expected_stats", "batted_ball"],
        valid_range=(0.0, 4.0),
        valid_values=None,
        example_value=0.893,
        gotchas=[
            "NULL on non-batted balls.",
            "Model recalibrated annually.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="estimated_slg_using_speedangle",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="woba_value",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Actual wOBA credit for this play.",
        business_definition=(
            "The linear-weights wOBA value actually awarded for this plate appearance "
            "outcome (e.g., single = ~0.888, home run = ~2.101). Non-NULL only on "
            "terminal pitches of plate appearances that earn wOBA credit."
        ),
        semantic_tags=["expected_stats", "outcome_at_bat"],
        valid_range=(0.0, 3.0),
        valid_values=None,
        example_value=0.888,
        gotchas=[
            "NULL on non-terminal pitches and events like strikeouts/walks when "
            "the woba_denom is 0.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="woba_value",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="woba_denom",
        type="INT64",
        mode="NULLABLE",
        short_description="wOBA denominator flag (1 if PA counts, 0 otherwise).",
        business_definition=(
            "Indicator (0 or 1) for whether this plate appearance counts in the "
            "wOBA denominator. Sac bunts are excluded (woba_denom=0) while most "
            "other PAs are included (woba_denom=1). Non-NULL only on terminal pitches."
        ),
        semantic_tags=["expected_stats", "outcome_at_bat"],
        valid_range=(0.0, 1.0),
        valid_values=None,
        example_value=1,
        gotchas=["NULL on non-terminal pitches."],
        statsapi_equivalent=None,
        pybaseball_source_field="woba_denom",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="babip_value",
        type="INT64",
        mode="NULLABLE",
        short_description="BABIP indicator (1 if event counts in BABIP, 0 otherwise).",
        business_definition=(
            "Binary flag (0 or 1) indicating whether this plate appearance result "
            "is included in BABIP (Batting Average on Balls in Play). Home runs and "
            "strikeouts are excluded (0); singles, doubles, triples on BIP are 1."
        ),
        semantic_tags=["expected_stats", "outcome_at_bat"],
        valid_range=(0.0, 1.0),
        valid_values=None,
        example_value=1,
        gotchas=["NULL on non-terminal pitches."],
        statsapi_equivalent=None,
        pybaseball_source_field="babip_value",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="iso_value",
        type="INT64",
        mode="NULLABLE",
        short_description="ISO extra-base value for this event.",
        business_definition=(
            "Isolated Power value for this plate appearance: 0 for singles, outs, "
            "walks; 1 for doubles; 2 for triples; 3 for home runs. Used to compute "
            "aggregate ISO (SLG - AVG). Non-NULL only on terminal pitches."
        ),
        semantic_tags=["expected_stats", "outcome_at_bat"],
        valid_range=(0.0, 3.0),
        valid_values=None,
        example_value=3,
        gotchas=["NULL on non-terminal pitches."],
        statsapi_equivalent=None,
        pybaseball_source_field="iso_value",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="launch_speed_angle",
        type="INT64",
        mode="NULLABLE",
        short_description="Launch speed/angle zone (1-6, barrel classification).",
        business_definition=(
            "Categorical encoding of the launch speed and angle combination: "
            "1=Weak, 2=Topped, 3=Under, 4=Flare/Burner, 5=Solid Contact, 6=Barrel. "
            "Barrels (6) have EV >= 98 mph and launch angle 8-50 degrees. NULL on "
            "non-batted balls."
        ),
        semantic_tags=["batted_ball", "expected_stats"],
        valid_range=(1.0, 6.0),
        valid_values=None,
        example_value=6,
        gotchas=[
            "NULL on non-batted balls.",
            "Barrel definition (zone 6) is the stricter MLB/Statcast standard.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="launch_speed_angle",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Bat tracking / swing metrics (2024+)
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="bat_speed",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Bat speed in mph at the sweet spot (2024+).",
        business_definition=(
            "Speed of the bat's sweet spot in miles per hour at the point of contact "
            "or the swing arc, as tracked by Statcast bat-tracking technology. "
            "Available from 2024 season onwards. NULL for pre-2024 data and non-swing events."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(30.0, 90.0),
        valid_values=None,
        example_value=72,
        gotchas=[
            "NULL for all pre-2024 data — do not interpret NULL as zero.",
            "Stored as FLOAT64 (sub-mph fractional values are real).",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="bat_speed",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="swing_length",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Swing length in feet (2024+).",
        business_definition=(
            "Total arc length of the bat's sweet spot during the swing in feet, as "
            "tracked by Statcast bat-tracking technology. Longer swings take more time; "
            "shorter swings allow later contact decisions. Available from 2024 onwards."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(3.0, 12.0),
        valid_values=None,
        example_value=7,
        gotchas=[
            "NULL for all pre-2024 data.",
            "Stored as FLOAT64 (sub-mph fractional values are real).",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="swing_length",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="attack_angle",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Vertical bat attack angle in degrees at contact.",
        business_definition=(
            "Vertical angle of the bat's sweet spot traveling path at the estimated "
            "impact point, in degrees. Positive values indicate an uppercut; 0 is "
            "level; negative is a downswing. Captures swing plane."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(-30.0, 40.0),
        valid_values=None,
        example_value=15,
        gotchas=["NULL for non-swing events and pre-bat-tracking seasons."],
        statsapi_equivalent=None,
        pybaseball_source_field="attack_angle",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="attack_direction",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Horizontal bat attack direction in degrees.",
        business_definition=(
            "Horizontal angle of the bat's sweet spot traveling path at the estimated "
            "impact point, in degrees. Captures whether the swing is pulling, going "
            "up the middle, or going the other way. Internal Statcast tracking field."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(-180.0, 180.0),
        valid_values=None,
        example_value=25,
        gotchas=["NULL for non-swing events and pre-bat-tracking seasons."],
        statsapi_equivalent=None,
        pybaseball_source_field="attack_direction",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="swing_path_tilt",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Vertical angular orientation of swing plane (40ms before contact).",
        business_definition=(
            "Vertical angular orientation of the swing plane in the 40 milliseconds "
            "before contact, in degrees. Reflects the tilt of the bat path at the "
            "critical pre-contact moment. Internal Statcast tracking field."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(-90.0, 90.0),
        valid_values=None,
        example_value=-12,
        gotchas=["NULL for non-swing events and pre-bat-tracking seasons."],
        statsapi_equivalent=None,
        pybaseball_source_field="swing_path_tilt",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="intercept_ball_minus_batter_pos_x_inches",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Horizontal gap between bat-ball intercept and batter center (inches).",
        business_definition=(
            "Horizontal distance in inches between the bat/ball intercept point and "
            "the batter's center position at the moment of contact. Positive values "
            "indicate the contact point is away from the batter's body (outside); "
            "negative indicates contact inside. Internal Statcast tracking field."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(-30.0, 30.0),
        valid_values=None,
        example_value=4,
        gotchas=["NULL for non-swing events and pre-bat-tracking seasons."],
        statsapi_equivalent=None,
        pybaseball_source_field="intercept_ball_minus_batter_pos_x_inches",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="intercept_ball_minus_batter_pos_y_inches",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Mound-to-plate gap between intercept and batter center (inches).",
        business_definition=(
            "Distance in inches along the mound-to-plate axis between the bat/ball "
            "intercept point and the batter's center position. Captures whether contact "
            "occurred out front or deep in the zone. Internal Statcast tracking field."
        ),
        semantic_tags=["batted_ball", "physics", "post_hit"],
        valid_range=(-30.0, 30.0),
        valid_values=None,
        example_value=-2,
        gotchas=["NULL for non-swing events and pre-bat-tracking seasons."],
        statsapi_equivalent=None,
        pybaseball_source_field="intercept_ball_minus_batter_pos_y_inches",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="hyper_speed",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Adjusted exit velocity (sub-88 mph floored at 88 mph).",
        business_definition=(
            "Exit velocity adjusted for use in certain expected-stats models: batted "
            "balls with raw launch_speed below 88 mph are set to 88 mph before model "
            "evaluation. This floors weak contact to reduce model noise. NULL on "
            "non-batted balls."
        ),
        semantic_tags=["batted_ball", "expected_stats", "post_hit"],
        valid_range=(88.0, 130.0),
        valid_values=None,
        example_value=98.7,
        gotchas=[
            "Not the same as raw launch_speed — floor of 88 mph applied.",
            "NULL on non-batted balls.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="hyper_speed",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Handedness
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="stand",
        type="STRING",
        mode="NULLABLE",
        short_description="Batter's batting stance side (L or R).",
        business_definition=(
            "Side of the plate where the batter stood: L=Left-handed batter, "
            "R=Right-handed batter. Switch hitters will appear as L or R depending "
            "on which side they batted from against this pitcher."
        ),
        semantic_tags=["handedness"],
        valid_range=None,
        valid_values=["L", "R"],
        example_value="R",
        gotchas=["Switch hitters appear as the side they batted from, not their natural side."],
        statsapi_equivalent="batSide.code",
        pybaseball_source_field="stand",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="p_throws",
        type="STRING",
        mode="NULLABLE",
        short_description="Pitcher's throwing hand (L or R).",
        business_definition=(
            "Hand the pitcher used to throw this pitch: L=Left-handed, R=Right-handed. "
            "Ambidextrous pitchers are rare but will appear as whichever hand they "
            "used for each specific pitch."
        ),
        semantic_tags=["handedness"],
        valid_range=None,
        valid_values=["L", "R"],
        example_value="R",
        gotchas=[],
        statsapi_equivalent="pitchHand.code",
        pybaseball_source_field="p_throws",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Fielding alignment
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="if_fielding_alignment",
        type="STRING",
        mode="NULLABLE",
        short_description="Infield defensive alignment at time of pitch.",
        business_definition=(
            "Describes the infield defensive alignment used by the fielding team. "
            "Common values: 'Standard', 'Shift', 'Strategic'. Shifts were banned "
            "starting in the 2023 MLB season."
        ),
        semantic_tags=["pitch_context"],
        valid_range=None,
        valid_values=None,
        example_value="Standard",
        gotchas=[
            "Infield shift was banned in 2023; post-2023 data shows primarily 'Standard'.",
            "NULL for some historical records.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="if_fielding_alignment",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="of_fielding_alignment",
        type="STRING",
        mode="NULLABLE",
        short_description="Outfield defensive alignment at time of pitch.",
        business_definition=(
            "Describes the outfield defensive alignment used by the fielding team. "
            "Common values: 'Standard', '4th outfielder', 'Strategic'. "
            "NULL for some historical records."
        ),
        semantic_tags=["pitch_context"],
        valid_range=None,
        valid_values=None,
        example_value="Standard",
        gotchas=["NULL for some historical records."],
        statsapi_equivalent=None,
        pybaseball_source_field="of_fielding_alignment",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Win/run expectancy
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="delta_home_win_exp",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Change in home team win expectancy this plate appearance.",
        business_definition=(
            "Change in the home team's win expectancy percentage from the start to "
            "the end of this plate appearance. Positive = better for home team; "
            "negative = worse. Computed from pre- and post-PA game state."
        ),
        semantic_tags=["score_state"],
        valid_range=(-1.0, 1.0),
        valid_values=None,
        example_value=0.042,
        gotchas=["NULL on non-terminal pitches within a PA."],
        statsapi_equivalent=None,
        pybaseball_source_field="delta_home_win_exp",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="delta_run_exp",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Change in run expectancy for this pitch.",
        business_definition=(
            "Change in the expected number of runs to score in this half-inning "
            "from before to after this pitch. Positive = more runs expected; "
            "negative = fewer runs expected. Pitch-level metric."
        ),
        semantic_tags=["score_state"],
        valid_range=(-3.0, 3.0),
        valid_values=None,
        example_value=-0.118,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="delta_run_exp",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="delta_pitcher_run_exp",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Change in run expectancy attributable to the pitcher.",
        business_definition=(
            "Change in expected runs attributable to the pitcher for this pitch, "
            "from the Statcast run-expectancy model. Added during Task 3 discovery "
            "— present in pybaseball output. Positive = run expectancy increased "
            "against the pitcher."
        ),
        semantic_tags=["score_state"],
        valid_range=(-3.0, 3.0),
        valid_values=None,
        example_value=-0.062,
        gotchas=["NULL for some pitches; model details per Baseball Savant CSV docs."],
        statsapi_equivalent=None,
        pybaseball_source_field="delta_pitcher_run_exp",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_win_exp",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Home team win expectancy before this pitch (0-1).",
        business_definition=(
            "Pre-pitch probability (0.0 to 1.0) that the home team wins the game, "
            "from the Statcast win-expectancy model. Added during Task 3 discovery "
            "— present in pybaseball output."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 1.0),
        valid_values=None,
        example_value=0.612,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="home_win_exp",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="bat_win_exp",
        type="FLOAT64",
        mode="NULLABLE",
        short_description="Batting team win expectancy before this pitch (0-1).",
        business_definition=(
            "Pre-pitch probability (0.0 to 1.0) that the batting team wins the game, "
            "from the Statcast win-expectancy model. Added during Task 3 discovery "
            "— present in pybaseball output."
        ),
        semantic_tags=["score_state"],
        valid_range=(0.0, 1.0),
        valid_values=None,
        example_value=0.388,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="bat_win_exp",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Age metrics
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="age_pit_legacy",
        type="INT64",
        mode="NULLABLE",
        short_description="Pitcher age on June 30 of the game year (legacy).",
        business_definition=(
            "Age of the pitcher in years as of June 30 of the game year, using the "
            "legacy Baseball Savant convention. This is the older aging convention; "
            "prefer age_pit (December 31) for modern analyses."
        ),
        semantic_tags=["temporal"],
        valid_range=(18.0, 50.0),
        valid_values=None,
        example_value=28,
        gotchas=["June 30 convention differs from December 31 (age_pit); do not mix."],
        statsapi_equivalent=None,
        pybaseball_source_field="age_pit_legacy",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="age_bat_legacy",
        type="INT64",
        mode="NULLABLE",
        short_description="Batter age on June 30 of the game year (legacy).",
        business_definition=(
            "Age of the batter in years as of June 30 of the game year, using the "
            "legacy Baseball Savant convention. Prefer age_bat (December 31) for "
            "modern analyses."
        ),
        semantic_tags=["temporal"],
        valid_range=(18.0, 50.0),
        valid_values=None,
        example_value=26,
        gotchas=["June 30 convention differs from December 31 (age_bat); do not mix."],
        statsapi_equivalent=None,
        pybaseball_source_field="age_bat_legacy",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="age_pit",
        type="INT64",
        mode="NULLABLE",
        short_description="Pitcher age on December 31 of the game year.",
        business_definition=(
            "Age of the pitcher in years as of December 31 of the game year. This "
            "is the current Baseball Savant convention for player aging; use this "
            "in preference to age_pit_legacy."
        ),
        semantic_tags=["temporal"],
        valid_range=(18.0, 50.0),
        valid_values=None,
        example_value=28,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="age_pit",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="age_bat",
        type="INT64",
        mode="NULLABLE",
        short_description="Batter age on December 31 of the game year.",
        business_definition=(
            "Age of the batter in years as of December 31 of the game year. This "
            "is the current Baseball Savant convention for player aging."
        ),
        semantic_tags=["temporal"],
        valid_range=(18.0, 50.0),
        valid_values=None,
        example_value=25,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="age_bat",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Appearance / game-context counters
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="n_thruorder_pitcher",
        type="INT64",
        mode="NULLABLE",
        short_description="Times through the order for the pitcher in this game.",
        business_definition=(
            "How many times the pitcher has faced the batting order in this game "
            "through this plate appearance. 1 = first time through the order, "
            "2 = second time, etc. Useful for TTO penalty analysis."
        ),
        semantic_tags=["pitch_context"],
        valid_range=(1.0, 5.0),
        valid_values=None,
        example_value=2,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="n_thruorder_pitcher",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="n_priorpa_thisgame_player_at_bat",
        type="INT64",
        mode="NULLABLE",
        short_description="Number of prior plate appearances for this batter in this game.",
        business_definition=(
            "Count of plate appearances the batter has already completed in this game "
            "before the current PA. 0 on the first PA, 1 on the second, etc. "
            "Enables times-through-the-order analysis from the batter's perspective."
        ),
        semantic_tags=["pitch_context"],
        valid_range=(0.0, 8.0),
        valid_values=None,
        example_value=1,
        gotchas=[],
        statsapi_equivalent=None,
        pybaseball_source_field="n_priorpa_thisgame_player_at_bat",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="pitcher_days_since_prev_game",
        type="INT64",
        mode="NULLABLE",
        short_description="Days elapsed since pitcher's previous game appearance.",
        business_definition=(
            "Number of calendar days between the pitcher's previous game appearance "
            "and this game. NULL if this is the pitcher's first appearance of the "
            "season (or if data is unavailable)."
        ),
        semantic_tags=["temporal", "pitch_context"],
        valid_range=(0.0, 200.0),
        valid_values=None,
        example_value=4,
        gotchas=["NULL at the start of the season or for pitcher's first career game."],
        statsapi_equivalent=None,
        pybaseball_source_field="pitcher_days_since_prev_game",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="batter_days_since_prev_game",
        type="INT64",
        mode="NULLABLE",
        short_description="Days elapsed since batter's previous game appearance.",
        business_definition=(
            "Number of calendar days between the batter's previous game appearance "
            "and this game. NULL if this is the batter's first appearance of the season."
        ),
        semantic_tags=["temporal", "pitch_context"],
        valid_range=(0.0, 200.0),
        valid_values=None,
        example_value=1,
        gotchas=["NULL at the start of the season or for batter's first career game."],
        statsapi_equivalent=None,
        pybaseball_source_field="batter_days_since_prev_game",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="pitcher_days_until_next_game",
        type="INT64",
        mode="NULLABLE",
        short_description="Days until pitcher's next game appearance.",
        business_definition=(
            "Number of calendar days between this game and the pitcher's next game "
            "appearance. NULL if this is the pitcher's last appearance of the season "
            "or if next appearance data is unavailable."
        ),
        semantic_tags=["temporal", "pitch_context"],
        valid_range=(0.0, 200.0),
        valid_values=None,
        example_value=4,
        gotchas=["NULL at the end of the season."],
        statsapi_equivalent=None,
        pybaseball_source_field="pitcher_days_until_next_game",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="batter_days_until_next_game",
        type="INT64",
        mode="NULLABLE",
        short_description="Days until batter's next game appearance.",
        business_definition=(
            "Number of calendar days between this game and the batter's next game "
            "appearance. NULL if this is the batter's last appearance of the season."
        ),
        semantic_tags=["temporal", "pitch_context"],
        valid_range=(0.0, 200.0),
        valid_values=None,
        example_value=1,
        gotchas=["NULL at the end of the season."],
        statsapi_equivalent=None,
        pybaseball_source_field="batter_days_until_next_game",
        deprecated_in_year=None,
    ),
    # -------------------------------------------------------------------------
    # Deprecated columns (legacy PITCHf/x era)
    # -------------------------------------------------------------------------
    ColumnSpec(
        name="spin_dir",
        type="INT64",
        mode="NULLABLE",
        short_description="Deprecated spin direction from PITCHf/x era.",
        business_definition=(
            "Legacy spin direction field from the PITCHf/x tracking system, deprecated "
            "when Statcast (Trackman) replaced PITCHf/x circa 2017. No longer populated "
            "for modern data. Use spin_axis for current spin direction."
        ),
        semantic_tags=["pitch_physics"],
        valid_range=None,
        valid_values=None,
        example_value=None,
        gotchas=[
            "NULL for all post-2017 data.",
            "Not comparable to spin_axis; different measurement system.",
        ],
        statsapi_equivalent=None,
        pybaseball_source_field="spin_dir",
        deprecated_in_year=2017,
    ),
    ColumnSpec(
        name="spin_rate_deprecated",
        type="INT64",
        mode="NULLABLE",
        short_description="Deprecated spin rate from PITCHf/x era.",
        business_definition=(
            "Legacy spin rate field from the PITCHf/x tracking system, deprecated "
            "when Statcast replaced PITCHf/x circa 2017. Use release_spin_rate for "
            "current data."
        ),
        semantic_tags=["pitch_physics"],
        valid_range=None,
        valid_values=None,
        example_value=None,
        gotchas=["NULL for all post-2017 data. Use release_spin_rate instead."],
        statsapi_equivalent=None,
        pybaseball_source_field="spin_rate_deprecated",
        deprecated_in_year=2017,
    ),
    ColumnSpec(
        name="break_angle_deprecated",
        type="INT64",
        mode="NULLABLE",
        short_description="Deprecated break angle from PITCHf/x era.",
        business_definition=(
            "Legacy break angle field from the PITCHf/x tracking system, deprecated "
            "circa 2017. Use pfx_x/pfx_z or api_break_* for current pitch movement data."
        ),
        semantic_tags=["pitch_physics"],
        valid_range=None,
        valid_values=None,
        example_value=None,
        gotchas=["NULL for all post-2017 data."],
        statsapi_equivalent=None,
        pybaseball_source_field="break_angle_deprecated",
        deprecated_in_year=2017,
    ),
    ColumnSpec(
        name="break_length_deprecated",
        type="INT64",
        mode="NULLABLE",
        short_description="Deprecated break length from PITCHf/x era.",
        business_definition=(
            "Legacy break length field from the PITCHf/x tracking system, deprecated "
            "circa 2017. Use pfx_x/pfx_z or hit_distance_sc for current data."
        ),
        semantic_tags=["pitch_physics"],
        valid_range=None,
        valid_values=None,
        example_value=None,
        gotchas=["NULL for all post-2017 data."],
        statsapi_equivalent=None,
        pybaseball_source_field="break_length_deprecated",
        deprecated_in_year=2017,
    ),
    ColumnSpec(
        name="tfs_deprecated",
        type="INT64",
        mode="NULLABLE",
        short_description="Deprecated TFS timestamp field from PITCHf/x era.",
        business_definition=(
            "Legacy timestamp field from the PITCHf/x (TFS) tracking system, deprecated "
            "when Statcast replaced PITCHf/x circa 2017. No longer populated for modern "
            "data. Meaning: internal frame-count or timestamp from the old system."
        ),
        semantic_tags=["temporal"],
        valid_range=None,
        valid_values=None,
        example_value=None,
        gotchas=["NULL for all post-2017 data."],
        statsapi_equivalent=None,
        pybaseball_source_field="tfs_deprecated",
        deprecated_in_year=2017,
    ),
    ColumnSpec(
        name="tfs_zulu_deprecated",
        type="INT64",
        mode="NULLABLE",
        short_description="Deprecated TFS Zulu timestamp from PITCHf/x era.",
        business_definition=(
            "Legacy UTC (Zulu) timestamp field from the PITCHf/x (TFS) tracking system, "
            "deprecated circa 2017. No longer populated for modern data."
        ),
        semantic_tags=["temporal"],
        valid_range=None,
        valid_values=None,
        example_value=None,
        gotchas=["NULL for all post-2017 data."],
        statsapi_equivalent=None,
        pybaseball_source_field="tfs_zulu_deprecated",
        deprecated_in_year=2017,
    ),
    ColumnSpec(
        name="umpire",
        type="INT64",
        mode="NULLABLE",
        short_description="Deprecated umpire field.",
        business_definition=(
            "Legacy field that was intended to carry the home plate umpire's ID. "
            "Deprecated and consistently NULL in modern Statcast data. Do not rely "
            "on this for umpire analysis; use statsapi game data instead."
        ),
        semantic_tags=["identifier"],
        valid_range=None,
        valid_values=None,
        example_value=None,
        gotchas=["Always NULL in current data — not a reliable umpire identifier."],
        statsapi_equivalent="officials[].official.id",
        pybaseball_source_field="umpire",
        deprecated_in_year=2017,
    ),
]
