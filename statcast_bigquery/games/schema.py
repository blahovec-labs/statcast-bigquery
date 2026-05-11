"""GAMES_SCHEMA: single source of truth for the games table.

Sourced from MLB statsapi /api/v1/schedule (+ hydrate=probablePitcher,venue).
One row per game_pk; includes both completed and scheduled games so this
table powers both 'yesterday's results' and 'today/upcoming' views.
"""

from __future__ import annotations

from statcast_bigquery.schema import ColumnSpec, PartitioningSpec

GAMES_SCHEMA: list[ColumnSpec] = [
    # -----------------------------------------------------------------
    # Identifiers + temporal
    # -----------------------------------------------------------------
    ColumnSpec(
        name="game_pk",
        type="INT64",
        mode="REQUIRED",
        short_description="MLB statsapi game primary key.",
        business_definition=(
            "Stable game identifier across statsapi endpoints. Joins to "
            "statcast_pitches.game_pk and game_umpires.game_pk."
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
        name="season",
        type="INT64",
        mode="REQUIRED",
        short_description="MLB season year (e.g. 2024).",
        business_definition=(
            "Four-digit season year. Joins to season-level features and "
            "filters multi-year backfills."
        ),
        semantic_tags=["temporal"],
        valid_range=(2015.0, 2099.0),
        valid_values=None,
        example_value=2024,
        gotchas=[],
        statsapi_equivalent="season",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_date",
        type="DATE",
        mode="REQUIRED",
        short_description="Official local game date.",
        business_definition=(
            "Calendar date the game is officially scheduled for in the home "
            "stadium's local time (statsapi `officialDate`). Use this for "
            "date-based filters and joins. Partition key."
        ),
        semantic_tags=["temporal", "partition_key"],
        valid_range=None,
        valid_values=None,
        example_value="2024-09-15",
        gotchas=[
            "Game can be 'officialDate' = day N but `game_datetime` is in UTC "
            "on day N+1 for late evening starts.",
        ],
        statsapi_equivalent="officialDate",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_datetime",
        type="TIMESTAMP",
        mode="REQUIRED",
        short_description="Scheduled game start time in UTC.",
        business_definition=(
            "First-pitch scheduled time in UTC (statsapi `gameDate` field, "
            "which is misnamed — it's a timestamp). For local time, convert "
            "with the venue's timezone."
        ),
        semantic_tags=["temporal"],
        valid_range=None,
        valid_values=None,
        example_value="2024-09-15T22:10:00Z",
        gotchas=[],
        statsapi_equivalent="gameDate",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_type",
        type="STRING",
        mode="REQUIRED",
        short_description="Game type code.",
        business_definition=(
            "Statsapi `gameType` code. R=Regular, P=Postseason (legacy), "
            "F=Wild Card, D=Division Series, L=League Championship, W=World Series."
        ),
        semantic_tags=["category"],
        valid_range=None,
        valid_values=["R", "P", "F", "D", "L", "W"],
        example_value="R",
        gotchas=[
            "Spring training (S), exhibition (E), and All-Star (A) game types "
            "are intentionally NOT ingested.",
        ],
        statsapi_equivalent="gameType",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    # -----------------------------------------------------------------
    # Status (changes as game progresses)
    # -----------------------------------------------------------------
    ColumnSpec(
        name="status_code",
        type="STRING",
        mode="REQUIRED",
        short_description="Single-letter game status code.",
        business_definition=(
            "Statsapi `status.codedGameState`. S=Scheduled, P=Pre-game, "
            "I=In Progress, F=Final, D=Postponed, C=Cancelled, U=Suspended, "
            "DR=Delayed, etc."
        ),
        semantic_tags=["category"],
        valid_range=None,
        valid_values=None,
        example_value="F",
        gotchas=[
            "For predictions on future games, filter status_code = 'S'.",
            "For completed results, use status_code = 'F'.",
        ],
        statsapi_equivalent="status.codedGameState",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="status_detail",
        type="STRING",
        mode="REQUIRED",
        short_description="Human-readable status text.",
        business_definition=(
            "Display string like 'Scheduled', 'Final', 'In Progress', "
            "'Postponed'. Use for UI; use status_code for logic."
        ),
        semantic_tags=["display_name"],
        valid_range=None,
        valid_values=None,
        example_value="Final",
        gotchas=[],
        statsapi_equivalent="status.detailedState",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    # -----------------------------------------------------------------
    # Teams (denormalized abbrev + league + division)
    # -----------------------------------------------------------------
    ColumnSpec(
        name="home_team_id",
        type="INT64",
        mode="REQUIRED",
        short_description="MLB statsapi home team id.",
        business_definition="Stable team identifier.",
        semantic_tags=["identifier", "team"],
        valid_range=None,
        valid_values=None,
        example_value=147,
        gotchas=[],
        statsapi_equivalent="teams.home.team.id",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_team_abbrev",
        type="STRING",
        mode="REQUIRED",
        short_description="Home team 2-3 letter abbreviation.",
        business_definition=(
            "Canonical short code (e.g. 'NYY', 'BOS'). Mapped from "
            "home_team_id via statcast_bigquery.games.teams.MLB_TEAMS."
        ),
        semantic_tags=["display_name", "team"],
        valid_range=None,
        valid_values=None,
        example_value="NYY",
        gotchas=[],
        statsapi_equivalent="(derived)",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_league",
        type="STRING",
        mode="NULLABLE",
        short_description="Home team league (AL/NL).",
        business_definition="American League or National League.",
        semantic_tags=["category", "team"],
        valid_range=None,
        valid_values=["AL", "NL"],
        example_value="AL",
        gotchas=[],
        statsapi_equivalent="(derived)",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="home_division",
        type="STRING",
        mode="NULLABLE",
        short_description="Home team division.",
        business_definition="East / Central / West.",
        semantic_tags=["category", "team"],
        valid_range=None,
        valid_values=["East", "Central", "West"],
        example_value="East",
        gotchas=[],
        statsapi_equivalent="(derived)",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_team_id",
        type="INT64",
        mode="REQUIRED",
        short_description="MLB statsapi away team id.",
        business_definition="Stable team identifier.",
        semantic_tags=["identifier", "team"],
        valid_range=None,
        valid_values=None,
        example_value=111,
        gotchas=[],
        statsapi_equivalent="teams.away.team.id",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_team_abbrev",
        type="STRING",
        mode="REQUIRED",
        short_description="Away team 2-3 letter abbreviation.",
        business_definition="Canonical short code (e.g. 'BOS', 'LAD').",
        semantic_tags=["display_name", "team"],
        valid_range=None,
        valid_values=None,
        example_value="BOS",
        gotchas=[],
        statsapi_equivalent="(derived)",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_league",
        type="STRING",
        mode="NULLABLE",
        short_description="Away team league (AL/NL).",
        business_definition="American League or National League.",
        semantic_tags=["category", "team"],
        valid_range=None,
        valid_values=["AL", "NL"],
        example_value="AL",
        gotchas=[],
        statsapi_equivalent="(derived)",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="away_division",
        type="STRING",
        mode="NULLABLE",
        short_description="Away team division.",
        business_definition="East / Central / West.",
        semantic_tags=["category", "team"],
        valid_range=None,
        valid_values=["East", "Central", "West"],
        example_value="East",
        gotchas=[],
        statsapi_equivalent="(derived)",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    # -----------------------------------------------------------------
    # Venue
    # -----------------------------------------------------------------
    ColumnSpec(
        name="venue_id",
        type="INT64",
        mode="NULLABLE",
        short_description="MLB statsapi venue id.",
        business_definition="Stable stadium identifier.",
        semantic_tags=["identifier"],
        valid_range=None,
        valid_values=None,
        example_value=1,
        gotchas=[],
        statsapi_equivalent="venue.id",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="venue_name",
        type="STRING",
        mode="NULLABLE",
        short_description="Stadium name.",
        business_definition="Display name (e.g. 'Yankee Stadium').",
        semantic_tags=["display_name"],
        valid_range=None,
        valid_values=None,
        example_value="Yankee Stadium",
        gotchas=[],
        statsapi_equivalent="venue.name",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    # -----------------------------------------------------------------
    # Probable pitchers (NULL for past games or not-yet-announced)
    # -----------------------------------------------------------------
    ColumnSpec(
        name="probable_home_pitcher_id",
        type="INT64",
        mode="NULLABLE",
        short_description="MLB statsapi player id of the probable home starter.",
        business_definition=(
            "Announced before game time. NULL for past games (not "
            "retrospectively re-hydrated) and for future games where the "
            "team hasn't announced yet."
        ),
        semantic_tags=["identifier", "pitcher"],
        valid_range=None,
        valid_values=None,
        example_value=676282,
        gotchas=[
            "Replaced by actual starter once the game begins. For confirmed "
            "starters of completed games, query statcast_pitches min(at_bat_number).",
        ],
        statsapi_equivalent="teams.home.probablePitcher.id",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="probable_home_pitcher_name",
        type="STRING",
        mode="NULLABLE",
        short_description="Display name of probable home starter.",
        business_definition="Full name (e.g. 'Gerrit Cole').",
        semantic_tags=["display_name", "pitcher"],
        valid_range=None,
        valid_values=None,
        example_value="Gerrit Cole",
        gotchas=[],
        statsapi_equivalent="teams.home.probablePitcher.fullName",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="probable_away_pitcher_id",
        type="INT64",
        mode="NULLABLE",
        short_description="MLB statsapi player id of the probable away starter.",
        business_definition="Same semantics as probable_home_pitcher_id.",
        semantic_tags=["identifier", "pitcher"],
        valid_range=None,
        valid_values=None,
        example_value=605135,
        gotchas=[],
        statsapi_equivalent="teams.away.probablePitcher.id",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="probable_away_pitcher_name",
        type="STRING",
        mode="NULLABLE",
        short_description="Display name of probable away starter.",
        business_definition="Full name.",
        semantic_tags=["display_name", "pitcher"],
        valid_range=None,
        valid_values=None,
        example_value="Logan Webb",
        gotchas=[],
        statsapi_equivalent="teams.away.probablePitcher.fullName",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    # -----------------------------------------------------------------
    # Final scores (NULL until game is Final)
    # -----------------------------------------------------------------
    ColumnSpec(
        name="final_home_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Home team's final run total.",
        business_definition=(
            "NULL until status_code = 'F'. May be partially populated for "
            "in-progress games (statsapi returns running total)."
        ),
        semantic_tags=["outcome_game"],
        valid_range=(0.0, 60.0),
        valid_values=None,
        example_value=5,
        gotchas=[
            "Not strictly NULL until Final — in-progress games surface "
            "current score. Filter on status_code = 'F' for final results.",
        ],
        statsapi_equivalent="teams.home.score",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="final_away_score",
        type="INT64",
        mode="NULLABLE",
        short_description="Away team's final run total.",
        business_definition="See final_home_score. NULL until Final.",
        semantic_tags=["outcome_game"],
        valid_range=(0.0, 60.0),
        valid_values=None,
        example_value=3,
        gotchas=[],
        statsapi_equivalent="teams.away.score",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    # -----------------------------------------------------------------
    # Doubleheader / series metadata
    # -----------------------------------------------------------------
    ColumnSpec(
        name="double_header_flag",
        type="STRING",
        mode="NULLABLE",
        short_description="Doubleheader flag.",
        business_definition=(
            "N = single game (most), Y = traditional doubleheader, "
            "S = split doubleheader."
        ),
        semantic_tags=["category"],
        valid_range=None,
        valid_values=["N", "Y", "S"],
        example_value="N",
        gotchas=[],
        statsapi_equivalent="doubleHeader",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="game_number",
        type="INT64",
        mode="NULLABLE",
        short_description="Game number within doubleheader (1 or 2; 1 for single games).",
        business_definition="Combined with game_pk, deduplicates DH games for the same date.",
        semantic_tags=["identifier"],
        valid_range=(1.0, 2.0),
        valid_values=None,
        example_value=1,
        gotchas=[],
        statsapi_equivalent="gameNumber",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
    ColumnSpec(
        name="series_description",
        type="STRING",
        mode="NULLABLE",
        short_description="Postseason series description (NULL for regular season).",
        business_definition="e.g. 'Division Series', 'World Series'. NULL for game_type = 'R'.",
        semantic_tags=["display_name"],
        valid_range=None,
        valid_values=None,
        example_value="World Series",
        gotchas=[],
        statsapi_equivalent="seriesDescription",
        pybaseball_source_field="",
        deprecated_in_year=None,
    ),
]


def get_games_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="game_date",
        type="DAY",
        clustering=["game_type", "home_team_id"],
    )
