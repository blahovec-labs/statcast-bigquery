"""Tests for BaseballSavantBattingVerifier + BaseballSavantPitchingVerifier."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from statcast_bigquery.verify.savant import (
    BATTING_METRIC_TO_SAVANT_FIELD,
    BATTING_TOLERANCES,
    PITCHING_TOLERANCES,
    BaseballSavantBattingVerifier,
    BaseballSavantPitchingVerifier,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def savant_batter() -> pd.DataFrame:
    return pd.read_parquet(FIXTURES / "savant_batter_2024.parquet")


@pytest.fixture
def savant_pitcher() -> pd.DataFrame:
    return pd.read_parquet(FIXTURES / "savant_pitcher_2024.parquet")


def test_batting_metric_to_savant_field_covers_all_default_metrics():
    expected = {
        "barrel_rate", "hard_hit_pct", "avg_exit_velo",
        "avg_launch_angle", "xwoba_contact",
    }
    assert expected <= BATTING_METRIC_TO_SAVANT_FIELD.keys()


def test_batting_tolerances_set():
    for m in ["barrel_rate", "hard_hit_pct", "avg_exit_velo",
              "avg_launch_angle", "xwoba_contact"]:
        assert m in BATTING_TOLERANCES
        assert BATTING_TOLERANCES[m] > 0


def test_pitching_tolerances_set():
    for m in ["avg_release_speed", "whiff_rate", "hard_hit_allowed"]:
        assert m in PITCHING_TOLERANCES
        assert PITCHING_TOLERANCES[m] > 0


def test_batting_verifier_run_with_mocked_savant(savant_batter: pd.DataFrame):
    bq = MagicMock()
    # Actual column name for barrel rate in pybaseball exitvelo_barrels: brl_percent
    brl_col = BATTING_METRIC_TO_SAVANT_FIELD["barrel_rate"]  # "brl_percent"
    # _run_aggregation expects columns: id, value, sample_size
    our_rows = pd.DataFrame({
        "id": savant_batter["player_id"].head(50).values,
        "value": savant_batter[brl_col].head(50).values,
        "sample_size": savant_batter["attempts"].head(50).values,
    })
    bq.query_and_wait.return_value.to_dataframe.return_value = our_rows
    name_lookup = dict(
        zip(savant_batter["player_id"].head(50), savant_batter["last_name, first_name"].head(50))
    )

    verifier = BaseballSavantBattingVerifier(
        client=bq,
        table="p.d.statcast_pitches",
        season=2024,
        metric="barrel_rate",
        min_sample_size=50,
    )

    with patch("statcast_bigquery.verify.savant.pb.statcast_batter_exitvelo_barrels",
               return_value=savant_batter):
        with patch("statcast_bigquery.verify.savant._lookup_batter_names",
                   return_value=name_lookup):
            result = verifier.run()

    assert result.metric == "barrel_rate"
    assert result.season == 2024
    assert result.total_compared > 0
    # All deltas should be exactly zero (we mocked the BQ response with savant data)
    assert all(c.within_tolerance for c in result.deltas)
    assert result.passed(threshold=0.99)


def test_batting_verifier_invalid_metric_raises():
    bq = MagicMock()
    with pytest.raises(ValueError, match="metric"):
        BaseballSavantBattingVerifier(
            client=bq, table="p.d.t", season=2024,
            metric="not_a_metric",
        ).run()


def test_pitching_verifier_run(savant_pitcher: pd.DataFrame):
    bq = MagicMock()
    # _run_aggregation expects columns: id, value, sample_size
    our_rows = pd.DataFrame({
        "id": savant_pitcher["player_id"].head(30).values,
        "value": [94.0] * 30,
        "sample_size": [50] * 30,
    })
    bq.query_and_wait.return_value.to_dataframe.return_value = our_rows
    name_lookup = dict(
        zip(savant_pitcher["player_id"].head(30),
            savant_pitcher["last_name, first_name"].head(30))
    )

    verifier = BaseballSavantPitchingVerifier(
        client=bq, table="p.d.statcast_pitches", season=2024,
        metric="avg_release_speed", min_sample_size=20,
    )

    # Mocked savant gives different velo than ours -> should report deltas
    with patch("statcast_bigquery.verify.savant.pb.statcast_pitcher_exitvelo_barrels",
               return_value=savant_pitcher):
        with patch("statcast_bigquery.verify.savant._lookup_pitcher_names",
                   return_value=name_lookup):
            result = verifier.run()

    assert result.metric == "avg_release_speed"
    assert result.total_compared > 0
