"""Tests for StatcastClient."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from statcast_bigquery.client import StatcastClient

FIXTURE = Path(__file__).parent / "fixtures" / "statcast_sample_2024-04-01.parquet"


@pytest.fixture
def fixture_df() -> pd.DataFrame:
    return pd.read_parquet(FIXTURE)


def test_fetch_returns_dataframe_when_pybaseball_returns_data(fixture_df: pd.DataFrame):
    with patch("statcast_bigquery.client.pb.statcast", return_value=fixture_df):
        client = StatcastClient(sleep_seconds=0)
        result = client.fetch("2024-04-01", "2024-04-01")
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


def test_fetch_filters_to_regular_season(fixture_df: pd.DataFrame):
    fixture_df.loc[0, "game_type"] = "S"  # spring training
    with patch("statcast_bigquery.client.pb.statcast", return_value=fixture_df):
        client = StatcastClient(sleep_seconds=0)
        result = client.fetch("2024-04-01", "2024-04-01")
    assert (result["game_type"] == "R").all()


def test_fetch_returns_empty_dataframe_on_none_response():
    with patch("statcast_bigquery.client.pb.statcast", return_value=None):
        client = StatcastClient(sleep_seconds=0)
        result = client.fetch("2024-04-01", "2024-04-01")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_fetch_returns_empty_dataframe_on_empty_response():
    with patch("statcast_bigquery.client.pb.statcast", return_value=pd.DataFrame()):
        client = StatcastClient(sleep_seconds=0)
        result = client.fetch("2024-04-01", "2024-04-01")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_fetch_sleeps_between_requests():
    """Polite sleep is configurable; default 2.0 (V1 pattern)."""
    client = StatcastClient()
    assert client.sleep_seconds == 2.0
