"""Tests for verify base classes — Comparison, VerificationResult, compare logic."""

from __future__ import annotations

import pytest

from statcast_bigquery.verify import Comparison, VerificationResult
from statcast_bigquery.verify.compare import compare_series


def test_comparison_within_tolerance_true_when_diff_small():
    c = Comparison(
        entity_id=1, entity_name="Player A",
        ours=0.241, expected=0.243, diff=-0.002, sample_size=200,
        within_tolerance=True,
    )
    assert c.within_tolerance


def test_compare_series_classifies_per_row():
    ours: dict[int | str, float] = {1: 0.240, 2: 0.300, 3: 0.180}
    expected: dict[int | str, float] = {1: 0.241, 2: 0.310, 3: 0.181}  # row 2 outside tolerance
    sample_sizes: dict[int | str, int] = {1: 200, 2: 200, 3: 200}
    names: dict[int | str, str] = {1: "A", 2: "B", 3: "C"}
    rows = compare_series(
        ours=ours, expected=expected, sample_sizes=sample_sizes,
        entity_names=names, tolerance=0.005,
    )
    by_id = {r.entity_id: r for r in rows}
    assert by_id[1].within_tolerance is True
    assert by_id[2].within_tolerance is False
    assert by_id[3].within_tolerance is True
    assert pytest.approx(by_id[1].diff, rel=1e-6) == -0.001


def test_verification_result_pct_within_tolerance():
    deltas = [
        Comparison(i, "x", 0.0, 0.0, 0.0, 100, True) for i in range(99)
    ] + [Comparison(99, "x", 0.0, 0.1, -0.1, 100, False)]
    r = VerificationResult(
        metric="barrel_rate", season=2024, aggregation="player-season",
        source="baseball-savant", tolerance=0.005,
        total_compared=100, within_tolerance_count=99,
        deltas=deltas,
    )
    assert r.pct_within_tolerance == 0.99
    assert r.passed(threshold=0.99) is True
    assert r.passed(threshold=0.999) is False


def test_verification_result_summary_includes_key_facts():
    r = VerificationResult(
        metric="barrel_rate", season=2024, aggregation="player-season",
        source="baseball-savant", tolerance=0.005,
        total_compared=10, within_tolerance_count=9,
        deltas=[],
    )
    s = r.summary()
    assert "barrel_rate" in s
    assert "2024" in s
    assert "9" in s and "10" in s


def test_verification_result_to_json_roundtrip():
    deltas = [Comparison(1, "A", 0.1, 0.1, 0.0, 100, True)]
    r = VerificationResult(
        metric="m", season=2024, aggregation="player-season",
        source="baseball-savant", tolerance=0.005,
        total_compared=1, within_tolerance_count=1, deltas=deltas,
    )
    j = r.to_json()
    assert j["metric"] == "m"
    assert j["deltas"][0]["entity_id"] == 1
