"""Tests for the games module: schema, teams constant, and GameClient parsing."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from statcast_bigquery.games.client import (
    DEFAULT_GAME_TYPES,
    GameClient,
)
from statcast_bigquery.games.schema import (
    GAMES_SCHEMA,
    get_games_partitioning,
)
from statcast_bigquery.games.teams import MLB_TEAMS, team_info

SAMPLE_GAME = {
    "gamePk": 746070,
    "season": 2024,
    "gameDate": "2024-09-15T22:10:00Z",
    "officialDate": "2024-09-15",
    "gameType": "R",
    "doubleHeader": "N",
    "gameNumber": 1,
    "seriesDescription": "Regular Season",
    "status": {
        "codedGameState": "F",
        "detailedState": "Final",
    },
    "teams": {
        "home": {
            "team": {"id": 116, "name": "Detroit Tigers"},
            "score": 4,
            "probablePitcher": None,
        },
        "away": {
            "team": {"id": 147, "name": "New York Yankees"},
            "score": 3,
            "probablePitcher": None,
        },
    },
    "venue": {"id": 2394, "name": "Comerica Park"},
}

SCHEDULED_GAME = {
    "gamePk": 776100,
    "season": 2026,
    "gameDate": "2026-05-11T22:10:00Z",
    "officialDate": "2026-05-11",
    "gameType": "R",
    "doubleHeader": "N",
    "gameNumber": 1,
    "seriesDescription": "Regular Season",
    "status": {
        "codedGameState": "S",
        "detailedState": "Scheduled",
    },
    "teams": {
        "home": {
            "team": {"id": 114, "name": "Cleveland Guardians"},
            "score": None,
            "probablePitcher": {"id": 676282, "fullName": "Joey Cantillo"},
        },
        "away": {
            "team": {"id": 108, "name": "Los Angeles Angels"},
            "score": None,
            "probablePitcher": None,
        },
    },
    "venue": {"id": 5, "name": "Progressive Field"},
}


def test_teams_has_all_30_teams():
    assert len(MLB_TEAMS) == 30
    leagues = {t["league"] for t in MLB_TEAMS.values()}
    assert leagues == {"AL", "NL"}
    divisions = {(t["league"], t["division"]) for t in MLB_TEAMS.values()}
    assert len(divisions) == 6


def test_team_info_lookup():
    nyy = team_info(147)
    assert nyy is not None and nyy["abbr"] == "NYY"
    lad = team_info(119)
    assert lad is not None and lad["abbr"] == "LAD"
    assert team_info(999999) is None


def test_schema_has_all_expected_fields():
    names = [s.name for s in GAMES_SCHEMA]
    for required in (
        "game_pk", "season", "game_date", "game_datetime", "game_type",
        "status_code", "status_detail",
        "home_team_id", "home_team_abbrev", "home_league", "home_division",
        "away_team_id", "away_team_abbrev", "away_league", "away_division",
        "venue_id", "venue_name",
        "probable_home_pitcher_id", "probable_home_pitcher_name",
        "probable_away_pitcher_id", "probable_away_pitcher_name",
        "final_home_score", "final_away_score",
        "double_header_flag", "game_number", "series_description",
    ):
        assert required in names, f"missing schema field {required}"


def test_partitioning_is_game_date_clustered_by_type_and_home():
    p = get_games_partitioning()
    assert p.field == "game_date"
    assert p.type == "DAY"
    assert p.clustering == ["game_type", "home_team_id"]


def test_default_game_types_are_regular_and_postseason():
    assert DEFAULT_GAME_TYPES == ("R", "P", "F", "D", "L", "W")


def test_parse_completed_game_with_score():
    client = GameClient()
    row = client._parse_game(SAMPLE_GAME)
    assert row is not None
    assert row.game_pk == 746070
    assert row.game_type == "R"
    assert row.status_code == "F"
    assert row.home_team_id == 116
    assert row.home_team_abbrev == "DET"
    assert row.home_league == "AL"
    assert row.home_division == "Central"
    assert row.away_team_abbrev == "NYY"
    assert row.final_home_score == 4
    assert row.final_away_score == 3
    assert row.probable_home_pitcher_id is None


def test_parse_scheduled_game_with_probable_pitcher():
    client = GameClient()
    row = client._parse_game(SCHEDULED_GAME)
    assert row is not None
    assert row.status_code == "S"
    assert row.status_detail == "Scheduled"
    assert row.final_home_score is None
    assert row.probable_home_pitcher_id == 676282
    assert row.probable_home_pitcher_name == "Joey Cantillo"
    assert row.probable_away_pitcher_id is None
    assert row.probable_away_pitcher_name is None


def test_parse_skips_game_with_missing_pk():
    bad = dict(SAMPLE_GAME)
    bad["gamePk"] = None
    client = GameClient()
    assert client._parse_game(bad) is None


def test_unknown_team_id_falls_back_to_unk():
    bad = {
        "gamePk": 1,
        "season": 2024,
        "gameDate": "2024-07-16T00:00:00Z",
        "officialDate": "2024-07-16",
        "gameType": "A",  # All-Star
        "status": {"codedGameState": "F", "detailedState": "Final"},
        "teams": {
            "home": {"team": {"id": 159, "name": "American League"}, "score": 5,
                     "probablePitcher": None},
            "away": {"team": {"id": 160, "name": "National League"}, "score": 3,
                     "probablePitcher": None},
        },
        "venue": {"id": None, "name": None},
    }
    client = GameClient()
    row = client._parse_game(bad)
    assert row is not None
    assert row.home_team_abbrev == "UNK"
    assert row.home_league is None


def test_fetch_season_returns_empty_on_persistent_failure():
    client = GameClient(max_retries=1)
    with patch.object(client, "_fetch_season", return_value=None):
        df = client.fetch_season(2024)
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_fetch_season_parses_full_response():
    client = GameClient(max_retries=1)
    fake_doc = {
        "dates": [
            {"games": [SAMPLE_GAME]},
            {"games": [SCHEDULED_GAME]},
        ]
    }
    with patch.object(client, "_fetch_season", return_value=fake_doc):
        df = client.fetch_season(2024)
    assert len(df) == 2
    assert set(df["game_type"]) == {"R"}
    assert set(df["status_code"]) == {"F", "S"}


def test_url_includes_required_params():
    client = GameClient()
    url = client._build_url(2024)
    assert "season=2024" in url
    assert "sportId=1" in url
    assert "gameType=R%2CP%2CF%2CD%2CL%2CW" in url
    assert "hydrate=probablePitcher%2Cvenue" in url
