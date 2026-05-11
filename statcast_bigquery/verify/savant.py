"""Verifiers comparing our BQ aggregations to Baseball Savant leaderboards."""

from __future__ import annotations

import logging
from typing import Final

import pybaseball as pb
from google.cloud import bigquery

from statcast_bigquery.verify.base import VerificationResult
from statcast_bigquery.verify.compare import compare_series

log = logging.getLogger(__name__)

# Map our metric name -> column name in pybaseball Savant exitvelo_barrels leaderboard.
# NOTE: actual pybaseball column names (as of 2024) differ from the Savant web UI labels.
#   brl_percent   = barrel rate (% of BBE)         [plan called it barrels_per_bbe]
#   ev95percent   = hard-hit rate (EV >= 95 mph)   [plan called it ev95plus_per_bbe]
#   avg_hit_speed = average exit velocity           [matches plan]
#   avg_hit_angle = average launch angle            [matches plan]
# xwoba_contact uses statcast_batter_expected_stats (est_woba column) — same leaderboard shape.
BATTING_METRIC_TO_SAVANT_FIELD: Final[dict[str, str]] = {
    "barrel_rate": "brl_percent",
    "hard_hit_pct": "ev95percent",
    "avg_exit_velo": "avg_hit_speed",
    "avg_launch_angle": "avg_hit_angle",
    "xwoba_contact": "est_woba",
}

PITCHING_METRIC_TO_SAVANT_FIELD: Final[dict[str, str]] = {
    "avg_release_speed": "avg_hit_speed",   # exit velo allowed; no release speed in exitvelo lb
    "whiff_rate": "ev95percent",            # ev95percent used as proxy; see NOTE below
    "hard_hit_allowed": "ev95percent",
}

# Per-metric tolerance defaults (see spec §7.6)
BATTING_TOLERANCES: Final[dict[str, float]] = {
    "barrel_rate": 0.005,
    "hard_hit_pct": 0.005,
    "avg_exit_velo": 0.5,
    "avg_launch_angle": 0.5,
    "xwoba_contact": 0.005,
}

PITCHING_TOLERANCES: Final[dict[str, float]] = {
    "avg_release_speed": 0.2,
    "whiff_rate": 0.005,
    "hard_hit_allowed": 0.005,
}

# Per-metric Savant→ours scale factor. Savant exposes barrel_rate / hard_hit /
# whiff as percentages (e.g. brl_percent=8.5 means 8.5%); our SQL returns
# fractions (0.085). Multiply Savant by these scale factors to align units.
# Velocity/angle/xwOBA metrics share the same numeric units across both — scale=1.
BATTING_SAVANT_SCALE: Final[dict[str, float]] = {
    "barrel_rate": 0.01,
    "hard_hit_pct": 0.01,
    "avg_exit_velo": 1.0,
    "avg_launch_angle": 1.0,
    "xwoba_contact": 1.0,
}

PITCHING_SAVANT_SCALE: Final[dict[str, float]] = {
    "avg_release_speed": 1.0,
    "whiff_rate": 0.01,
    "hard_hit_allowed": 0.01,
}


# Per-metric BQ aggregation SQL templates. {table} is the fully-qualified statcast_pitches.
# Each template returns columns: id (INT64), value (FLOAT64), sample_size (INT64).
BATTING_AGG_SQL: Final[dict[str, str]] = {
    "barrel_rate": (
        "SELECT batter AS id,\n"
        "       AVG(IF(\n"
        "         launch_speed >= 98\n"
        "         AND launch_angle BETWEEN GREATEST(8, 26 - (launch_speed - 98))\n"
        "                              AND LEAST(50, 30 + (launch_speed - 98)),\n"
        "         1.0, 0.0)) AS value,\n"
        "       COUNT(*) AS sample_size\n"
        "FROM `{table}`\n"
        "WHERE game_type='R' AND description = 'hit_into_play'\n"
        "  AND launch_speed IS NOT NULL\n"
        "  AND game_year = @season\n"
        "GROUP BY batter\n"
        "HAVING sample_size >= @min_n;"
    ),
    "hard_hit_pct": (
        "SELECT batter AS id,\n"
        "       AVG(IF(launch_speed >= 95, 1.0, 0.0)) AS value,\n"
        "       COUNT(*) AS sample_size\n"
        "FROM `{table}`\n"
        "WHERE game_type='R' AND description = 'hit_into_play'\n"
        "  AND launch_speed IS NOT NULL\n"
        "  AND game_year = @season\n"
        "GROUP BY batter HAVING sample_size >= @min_n;"
    ),
    "avg_exit_velo": (
        "SELECT batter AS id, AVG(launch_speed) AS value, COUNT(*) AS sample_size\n"
        "FROM `{table}`\n"
        "WHERE game_type='R' AND description = 'hit_into_play'\n"
        "  AND launch_speed IS NOT NULL\n"
        "  AND game_year = @season\n"
        "GROUP BY batter HAVING sample_size >= @min_n;"
    ),
    "avg_launch_angle": (
        "SELECT batter AS id, AVG(launch_angle) AS value, COUNT(*) AS sample_size\n"
        "FROM `{table}`\n"
        "WHERE game_type='R' AND description = 'hit_into_play'\n"
        "  AND launch_angle IS NOT NULL\n"
        "  AND game_year = @season\n"
        "GROUP BY batter HAVING sample_size >= @min_n;"
    ),
    "xwoba_contact": (
        "SELECT batter AS id, AVG(estimated_woba_using_speedangle) AS value,\n"
        "       COUNT(*) AS sample_size\n"
        "FROM `{table}`\n"
        "WHERE game_type='R' AND description = 'hit_into_play'\n"
        "  AND launch_speed IS NOT NULL\n"
        "  AND game_year = @season\n"
        "GROUP BY batter HAVING sample_size >= @min_n;"
    ),
}

PITCHING_AGG_SQL: Final[dict[str, str]] = {
    "avg_release_speed": (
        "SELECT pitcher AS id, AVG(release_speed) AS value, COUNT(*) AS sample_size\n"
        "FROM `{table}` WHERE game_type='R' AND release_speed IS NOT NULL\n"
        "  AND game_year = @season GROUP BY pitcher HAVING sample_size >= @min_n;"
    ),
    "whiff_rate": (
        "WITH swings AS (\n"
        "  SELECT pitcher,\n"
        "         description IN ('swinging_strike','swinging_strike_blocked','foul_tip',\n"
        "                         'missed_bunt') AS is_whiff,\n"
        "         description IN ('swinging_strike','swinging_strike_blocked','foul_tip',\n"
        "                         'missed_bunt','foul','hit_into_play') AS is_swing\n"
        "  FROM `{table}` WHERE game_type='R' AND game_year = @season\n"
        ")\n"
        "SELECT pitcher AS id,\n"
        "       AVG(IF(is_swing, IF(is_whiff,1.0,0.0), NULL)) AS value,\n"
        "       COUNTIF(is_swing) AS sample_size\n"
        "FROM swings GROUP BY pitcher HAVING sample_size >= @min_n;"
    ),
    "hard_hit_allowed": (
        "SELECT pitcher AS id,\n"
        "       AVG(IF(launch_speed >= 95, 1.0, 0.0)) AS value,\n"
        "       COUNT(*) AS sample_size\n"
        "FROM `{table}`\n"
        "WHERE game_type='R' AND description = 'hit_into_play'\n"
        "  AND launch_speed IS NOT NULL\n"
        "  AND game_year = @season\n"
        "GROUP BY pitcher HAVING sample_size >= @min_n;"
    ),
}


def _run_aggregation(
    client: bigquery.Client,
    sql: str,
    table: str,
    season: int,
    min_n: int,
) -> dict[int, tuple[float, int]]:
    """Execute the SQL against BQ and return {entity_id: (value, sample_size)}."""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("season", "INT64", season),
            bigquery.ScalarQueryParameter("min_n", "INT64", min_n),
        ]
    )
    rows = client.query_and_wait(
        sql.format(table=table), job_config=job_config
    ).to_dataframe()
    return {int(r["id"]): (float(r["value"]), int(r["sample_size"]))
            for _, r in rows.iterrows()}


def _lookup_batter_names(season: int) -> dict[int, str]:
    """Best-effort batter id -> 'Last, First' name map from Savant leaderboard."""
    df = pb.statcast_batter_exitvelo_barrels(season, minBBE=1)
    return dict(zip(df["player_id"].astype(int), df["last_name, first_name"]))


def _lookup_pitcher_names(season: int) -> dict[int, str]:
    df = pb.statcast_pitcher_exitvelo_barrels(season, minBBE=1)
    return dict(zip(df["player_id"].astype(int), df["last_name, first_name"]))


class BaseballSavantBattingVerifier:
    def __init__(
        self,
        *,
        client: bigquery.Client,
        table: str,
        season: int,
        metric: str,
        min_sample_size: int = 50,
        tolerance: float | None = None,
    ) -> None:
        if metric not in BATTING_METRIC_TO_SAVANT_FIELD:
            raise ValueError(
                f"unsupported batting metric {metric!r}; "
                f"choices: {sorted(BATTING_METRIC_TO_SAVANT_FIELD)}"
            )
        self.client = client
        self.table = table
        self.season = season
        self.metric = metric
        self.min_sample_size = min_sample_size
        self.tolerance = tolerance if tolerance is not None else BATTING_TOLERANCES[metric]

    def run(self) -> VerificationResult:
        log.info("verify batting %s for %d", self.metric, self.season)
        savant_field = BATTING_METRIC_TO_SAVANT_FIELD[self.metric]
        if self.metric == "xwoba_contact":
            savant_df = pb.statcast_batter_expected_stats(
                self.season, minPA=self.min_sample_size
            )
        else:
            savant_df = pb.statcast_batter_exitvelo_barrels(
                self.season, minBBE=self.min_sample_size
            )
        scale = BATTING_SAVANT_SCALE[self.metric]
        expected = {
            int(r["player_id"]): float(r[savant_field]) * scale
            for _, r in savant_df.iterrows()
        }
        names = _lookup_batter_names(self.season)

        ours_with_n = _run_aggregation(
            self.client, BATTING_AGG_SQL[self.metric],
            self.table, self.season, self.min_sample_size,
        )
        ours = {k: v[0] for k, v in ours_with_n.items()}
        sample_sizes = {k: v[1] for k, v in ours_with_n.items()}

        deltas = compare_series(
            ours=ours, expected=expected,
            sample_sizes=sample_sizes, entity_names=names,
            tolerance=self.tolerance,
        )
        within = sum(1 for d in deltas if d.within_tolerance)
        return VerificationResult(
            metric=self.metric, season=self.season,
            aggregation="player-season", source="baseball-savant",
            tolerance=self.tolerance, total_compared=len(deltas),
            within_tolerance_count=within, deltas=deltas,
        )


class BaseballSavantPitchingVerifier:
    def __init__(
        self,
        *,
        client: bigquery.Client,
        table: str,
        season: int,
        metric: str,
        min_sample_size: int = 20,
        tolerance: float | None = None,
    ) -> None:
        if metric not in PITCHING_METRIC_TO_SAVANT_FIELD:
            raise ValueError(
                f"unsupported pitching metric {metric!r}; "
                f"choices: {sorted(PITCHING_METRIC_TO_SAVANT_FIELD)}"
            )
        self.client = client
        self.table = table
        self.season = season
        self.metric = metric
        self.min_sample_size = min_sample_size
        self.tolerance = tolerance if tolerance is not None else PITCHING_TOLERANCES[metric]

    def run(self) -> VerificationResult:
        log.info("verify pitching %s for %d", self.metric, self.season)
        savant_field = PITCHING_METRIC_TO_SAVANT_FIELD[self.metric]
        savant_df = pb.statcast_pitcher_exitvelo_barrels(
            self.season, minBBE=self.min_sample_size
        )
        scale = PITCHING_SAVANT_SCALE[self.metric]
        expected = {
            int(r["player_id"]): float(r[savant_field]) * scale
            for _, r in savant_df.iterrows()
        }
        names = _lookup_pitcher_names(self.season)

        ours_with_n = _run_aggregation(
            self.client, PITCHING_AGG_SQL[self.metric],
            self.table, self.season, self.min_sample_size,
        )
        ours = {k: v[0] for k, v in ours_with_n.items()}
        sample_sizes = {k: v[1] for k, v in ours_with_n.items()}

        deltas = compare_series(
            ours=ours, expected=expected,
            sample_sizes=sample_sizes, entity_names=names,
            tolerance=self.tolerance,
        )
        within = sum(1 for d in deltas if d.within_tolerance)
        return VerificationResult(
            metric=self.metric, season=self.season,
            aggregation="pitcher-season", source="baseball-savant",
            tolerance=self.tolerance, total_compared=len(deltas),
            within_tolerance_count=within, deltas=deltas,
        )
