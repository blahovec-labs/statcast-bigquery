"""External validation against trusted sources (Baseball Savant leaderboards)."""

from statcast_bigquery.verify.base import Comparison, VerificationResult, Verifier
from statcast_bigquery.verify.savant import (
    BATTING_METRIC_TO_SAVANT_FIELD,
    BATTING_TOLERANCES,
    PITCHING_METRIC_TO_SAVANT_FIELD,
    PITCHING_TOLERANCES,
    BaseballSavantBattingVerifier,
    BaseballSavantPitchingVerifier,
)

__all__ = [
    "BATTING_METRIC_TO_SAVANT_FIELD",
    "BATTING_TOLERANCES",
    "BaseballSavantBattingVerifier",
    "BaseballSavantPitchingVerifier",
    "Comparison",
    "PITCHING_METRIC_TO_SAVANT_FIELD",
    "PITCHING_TOLERANCES",
    "VerificationResult",
    "Verifier",
]
