"""Tests for StandingsClient — statsapi /standings fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from statcast_bigquery.standings.client import StandingsClient

# Minimal fixture mirroring the statsapi /standings response shape:
# https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2024
_FAKE_RESPONSE = {
    "records": [
        {
            "division": {"id": 201},
            "teamRecords": [
                {
                    "team": {"id": 147, "name": "New York Yankees"},
                    "wins": 94,
                    "losses": 68,
                    "runsScored": 815,
                    "runsAllowed": 668,
                },
                {
                    "team": {"id": 111, "name": "Boston Red Sox"},
                    "wins": 81,
                    "losses": 81,
                    "runsScored": 751,
                    "runsAllowed": 727,
                },
            ],
        },
        {
            "division": {"id": 203},
            "teamRecords": [
                {
                    "team": {"id": 117, "name": "Houston Astros"},
                    "wins": 88,
                    "losses": 73,
                    "runsScored": 740,
                    "runsAllowed": 705,
                },
            ],
        },
    ],
}


def test_fetch_season_returns_dict_keyed_by_abbr():
    with patch("statcast_bigquery.standings.client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: _FAKE_RESPONSE
        )
        mock_get.return_value.raise_for_status = MagicMock()

        client = StandingsClient()
        result = client.fetch_season(2024)

    assert "NYY" in result
    assert "BOS" in result
    assert "HOU" in result
    assert result["NYY"]["wins"] == 94
    assert result["NYY"]["losses"] == 68
    assert result["NYY"]["runs_scored"] == 815
    assert result["NYY"]["runs_allowed"] == 668


def test_fetch_season_url_includes_leagues_and_season():
    with patch("statcast_bigquery.standings.client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: _FAKE_RESPONSE
        )
        mock_get.return_value.raise_for_status = MagicMock()

        StandingsClient().fetch_season(2024)
    called_url = mock_get.call_args[0][0]
    assert "leagueId=103,104" in called_url
    assert "season=2024" in called_url
    assert "standingsTypes=regularSeason" in called_url


def test_fetch_season_retries_on_failure():
    """Transient HTTP failure should retry up to max_retries before raising."""
    with patch("statcast_bigquery.standings.client.requests.get") as mock_get:
        # Fail twice, succeed third
        bad = MagicMock()
        bad.raise_for_status.side_effect = requests.HTTPError("503")
        good = MagicMock(status_code=200, json=lambda: _FAKE_RESPONSE)
        good.raise_for_status = MagicMock()
        mock_get.side_effect = [bad, bad, good]

        client = StandingsClient(max_retries=5, sleep_seconds=0.0)
        result = client.fetch_season(2024)
    assert mock_get.call_count == 3
    assert "NYY" in result


def test_fetch_season_raises_after_max_retries():
    with patch("statcast_bigquery.standings.client.requests.get") as mock_get:
        bad = MagicMock()
        bad.raise_for_status.side_effect = requests.HTTPError("503")
        mock_get.side_effect = [bad, bad, bad]

        client = StandingsClient(max_retries=3, sleep_seconds=0.0)
        with pytest.raises(requests.HTTPError):
            client.fetch_season(2024)
    assert mock_get.call_count == 3


def test_fetch_season_unknown_team_id_skipped():
    """If statsapi returns a team_id not in MLB_TEAMS, log and skip (don't crash)."""
    bad_response = {
        "records": [{
            "division": {"id": 999},
            "teamRecords": [{
                "team": {"id": 999999, "name": "Phantom Team"},
                "wins": 50, "losses": 50,
                "runsScored": 500, "runsAllowed": 500,
            }],
        }],
    }
    with patch("statcast_bigquery.standings.client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: bad_response)
        mock_get.return_value.raise_for_status = MagicMock()
        result = StandingsClient().fetch_season(2024)
    assert result == {}


def test_oak_aliased_to_ath():
    """statsapi returns team_id 133 ('OAK'); we expose it as 'ATH' (Statcast modern)."""
    response = {
        "records": [{
            "division": {"id": 200},
            "teamRecords": [{
                "team": {"id": 133, "name": "Athletics"},
                "wins": 75, "losses": 87,
                "runsScored": 650, "runsAllowed": 700,
            }],
        }],
    }
    with patch("statcast_bigquery.standings.client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: response)
        mock_get.return_value.raise_for_status = MagicMock()
        result = StandingsClient().fetch_season(2024)
    assert "ATH" in result
    assert "OAK" not in result
    assert result["ATH"]["wins"] == 75


def test_ari_aliased_to_az():
    """statsapi returns team_id 109 ('ARI'); we expose it as 'AZ' (Statcast modern)."""
    response = {
        "records": [{
            "division": {"id": 203},
            "teamRecords": [{
                "team": {"id": 109, "name": "Arizona Diamondbacks"},
                "wins": 89, "losses": 73,
                "runsScored": 814, "runsAllowed": 720,
            }],
        }],
    }
    with patch("statcast_bigquery.standings.client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: response)
        mock_get.return_value.raise_for_status = MagicMock()
        result = StandingsClient().fetch_season(2024)
    assert "AZ" in result
    assert "ARI" not in result
    assert result["AZ"]["wins"] == 89
