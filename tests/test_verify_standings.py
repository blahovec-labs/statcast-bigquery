"""Tests for BaseballStandingsVerifier."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import statcast_bigquery.verify.standings as standings_mod
from statcast_bigquery.verify.standings import (
    STANDINGS_AGG_SQL,
    STANDINGS_TOLERANCES,
    BaseballStandingsVerifier,
)


def test_supported_metrics():
    assert set(BaseballStandingsVerifier.SUPPORTED_METRICS) == {
        "wins", "losses", "run_diff",
    }


def test_default_tolerances():
    assert STANDINGS_TOLERANCES["wins"] == 1.0
    assert STANDINGS_TOLERANCES["losses"] == 1.0
    assert STANDINGS_TOLERANCES["run_diff"] == 5.0


def test_sql_template_wins_has_metric_expression():
    sql = STANDINGS_AGG_SQL["wins"]
    assert "SUM(IF(rs > ra, 1, 0))" in sql
    assert "WITH last_pitch" in sql
    assert "game_finals" in sql
    assert "team_games" in sql
    assert "{table}" in sql


def test_sql_template_losses():
    assert "SUM(IF(rs < ra, 1, 0))" in STANDINGS_AGG_SQL["losses"]


def test_sql_template_run_diff():
    assert "SUM(rs) - SUM(ra)" in STANDINGS_AGG_SQL["run_diff"]


def test_unsupported_metric_raises():
    with pytest.raises(ValueError, match="unsupported standings metric"):
        BaseballStandingsVerifier(
            client=None, table="p.d.t", season=2024, metric="batting_avg",
        )


def test_run_wins_within_tolerance(monkeypatch):
    """Ours = statsapi for all teams → 100% within tolerance."""
    fake_standings = {
        "NYY": {"wins": 94, "losses": 68, "runs_scored": 815, "runs_allowed": 668},
        "BOS": {"wins": 81, "losses": 81, "runs_scored": 751, "runs_allowed": 727},
    }
    fake_ours = {"NYY": (94, 162), "BOS": (81, 162)}

    fake_client = MagicMock()
    monkeypatch.setattr(standings_mod, "_run_aggregation",
                        lambda *a, **kw: fake_ours)
    monkeypatch.setattr(standings_mod.StandingsClient, "fetch_season",
                        lambda self, season: fake_standings)

    v = BaseballStandingsVerifier(
        client=fake_client, table="p.d.t", season=2024, metric="wins",
    )
    result = v.run()
    assert result.total_compared == 2
    assert result.within_tolerance_count == 2


def test_run_wins_one_outside_tolerance(monkeypatch):
    """Ours differs by 3 wins from statsapi for NYY → outside tolerance (1)."""
    fake_standings = {
        "NYY": {"wins": 94, "losses": 68, "runs_scored": 815, "runs_allowed": 668},
        "BOS": {"wins": 81, "losses": 81, "runs_scored": 751, "runs_allowed": 727},
    }
    fake_ours = {"NYY": (91, 162), "BOS": (81, 162)}  # NYY -3, BOS exact

    fake_client = MagicMock()
    monkeypatch.setattr(standings_mod, "_run_aggregation",
                        lambda *a, **kw: fake_ours)
    monkeypatch.setattr(standings_mod.StandingsClient, "fetch_season",
                        lambda self, season: fake_standings)

    v = BaseballStandingsVerifier(
        client=fake_client, table="p.d.t", season=2024, metric="wins",
    )
    result = v.run()
    assert result.within_tolerance_count == 1
    assert result.total_compared == 2


def test_run_run_diff_tolerance_5(monkeypatch):
    """run_diff tolerance is 5; diff of 4 should pass, diff of 6 should fail."""
    fake_standings = {
        "NYY": {"wins": 94, "losses": 68, "runs_scored": 815, "runs_allowed": 668},  # rd = +147
        "BOS": {"wins": 81, "losses": 81, "runs_scored": 751, "runs_allowed": 727},  # rd = +24
    }
    # NYY ours rd = 151 (diff +4, within tolerance)
    # BOS ours rd = 18 (diff -6, outside tolerance)
    fake_ours = {"NYY": (151, 162), "BOS": (18, 162)}

    fake_client = MagicMock()
    monkeypatch.setattr(standings_mod, "_run_aggregation",
                        lambda *a, **kw: fake_ours)
    monkeypatch.setattr(standings_mod.StandingsClient, "fetch_season",
                        lambda self, season: fake_standings)

    v = BaseballStandingsVerifier(
        client=fake_client, table="p.d.t", season=2024, metric="run_diff",
    )
    result = v.run()
    assert result.within_tolerance_count == 1


def test_entity_id_is_team_abbrev_string(monkeypatch):
    """Comparison.entity_id should be the team abbreviation (str), not numeric."""
    fake_standings = {
        "NYY": {"wins": 94, "losses": 68, "runs_scored": 815, "runs_allowed": 668},
    }
    fake_ours = {"NYY": (94, 162)}
    fake_client = MagicMock()
    monkeypatch.setattr(standings_mod, "_run_aggregation",
                        lambda *a, **kw: fake_ours)
    monkeypatch.setattr(standings_mod.StandingsClient, "fetch_season",
                        lambda self, season: fake_standings)
    v = BaseballStandingsVerifier(
        client=fake_client, table="p.d.t", season=2024, metric="wins",
    )
    result = v.run()
    assert result.deltas[0].entity_id == "NYY"
    assert isinstance(result.deltas[0].entity_id, str)
