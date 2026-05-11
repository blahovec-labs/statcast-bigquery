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
    # Our SQL returns barrel_rate as a fraction (0.085), not a percent (8.5),
    # so divide Savant's brl_percent by 100 to simulate what BQ produces.
    our_rows = pd.DataFrame({
        "id": savant_batter["player_id"].head(50).values,
        "value": savant_batter[brl_col].head(50).values / 100.0,
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


def test_batting_barrel_rate_scales_savant_percent_to_fraction(monkeypatch):
    """Savant returns brl_percent=8.5 (percent); our SQL returns 0.085 (fraction).
    Verifier must scale Savant down by /100 so they match within tolerance."""
    import pandas as pd
    from statcast_bigquery.verify.savant import BaseballSavantBattingVerifier
    import statcast_bigquery.verify.savant as savant_mod

    fake_savant = pd.DataFrame([
        {"player_id": 100, "brl_percent": 8.5, "last_name, first_name": "Doe, John"},
    ])
    monkeypatch.setattr(savant_mod.pb, "statcast_batter_exitvelo_barrels",
                        lambda season, minBBE: fake_savant)
    monkeypatch.setattr(savant_mod.pb, "statcast_batter_expected_stats",
                        lambda season, minPA: fake_savant)
    monkeypatch.setattr(savant_mod, "_run_aggregation",
                        lambda *a, **kw: {100: (0.085, 100)})  # our SQL returns fraction
    monkeypatch.setattr(savant_mod, "_lookup_batter_names",
                        lambda season: {100: "Doe, John"})

    v = BaseballSavantBattingVerifier(
        client=None, table="p.d.t", season=2024, metric="barrel_rate"
    )
    result = v.run()
    assert result.total_compared == 1
    assert result.within_tolerance_count == 1, \
        f"expected within tolerance, got delta={result.deltas[0].diff}"


def test_pitching_hard_hit_allowed_scales_savant_percent(monkeypatch):
    import pandas as pd
    from statcast_bigquery.verify.savant import BaseballSavantPitchingVerifier
    import statcast_bigquery.verify.savant as savant_mod

    fake_savant = pd.DataFrame([
        {"player_id": 200, "ev95percent": 35.0, "last_name, first_name": "Doe, Jane"},
    ])
    monkeypatch.setattr(savant_mod.pb, "statcast_pitcher_exitvelo_barrels",
                        lambda season, minBBE: fake_savant)
    monkeypatch.setattr(savant_mod, "_run_aggregation",
                        lambda *a, **kw: {200: (0.35, 200)})
    monkeypatch.setattr(savant_mod, "_lookup_pitcher_names",
                        lambda season: {200: "Doe, Jane"})

    v = BaseballSavantPitchingVerifier(
        client=None, table="p.d.t", season=2024, metric="hard_hit_allowed"
    )
    result = v.run()
    assert result.within_tolerance_count == 1


def test_batting_avg_exit_velo_does_not_scale(monkeypatch):
    """Non-percentage metrics (avg_hit_speed) must NOT be scaled."""
    import pandas as pd
    from statcast_bigquery.verify.savant import BaseballSavantBattingVerifier
    import statcast_bigquery.verify.savant as savant_mod

    fake_savant = pd.DataFrame([
        {"player_id": 300, "avg_hit_speed": 89.5, "last_name, first_name": "Doe, J"},
    ])
    monkeypatch.setattr(savant_mod.pb, "statcast_batter_exitvelo_barrels",
                        lambda season, minBBE: fake_savant)
    monkeypatch.setattr(savant_mod, "_run_aggregation",
                        lambda *a, **kw: {300: (89.5, 100)})
    monkeypatch.setattr(savant_mod, "_lookup_batter_names",
                        lambda season: {300: "Doe, J"})

    v = BaseballSavantBattingVerifier(
        client=None, table="p.d.t", season=2024, metric="avg_exit_velo"
    )
    result = v.run()
    assert result.deltas[0].expected == 89.5  # unchanged
    assert result.within_tolerance_count == 1
