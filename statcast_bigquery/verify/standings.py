"""Verifier comparing reconstructed standings (from pitch data) to MLB statsapi."""

from __future__ import annotations

import logging
from typing import Final

from google.cloud import bigquery

from statcast_bigquery.games.teams import MLB_TEAMS
from statcast_bigquery.standings.client import _STATCAST_ABBR_ALIASES, StandingsClient
from statcast_bigquery.verify.base import VerificationResult
from statcast_bigquery.verify.compare import compare_series

log = logging.getLogger(__name__)


# Shared CTE wrapped around per-metric expression. {table} = pitches table FQN.
_BASE_CTE = (
    "WITH last_pitch AS (\n"
    "  SELECT game_pk, home_team, away_team, inning_topbot,\n"
    "         post_bat_score, post_fld_score,\n"
    "         ROW_NUMBER() OVER (\n"
    "           PARTITION BY game_pk\n"
    "           ORDER BY at_bat_number DESC, pitch_number DESC\n"
    "         ) AS rn\n"
    "  FROM `{table}`\n"
    "  WHERE game_type='R' AND game_year = @season\n"
    "),\n"
    "game_finals AS (\n"
    "  SELECT game_pk, home_team, away_team,\n"
    "         IF(inning_topbot='Top', post_fld_score, post_bat_score) AS home_score,\n"
    "         IF(inning_topbot='Top', post_bat_score, post_fld_score) AS away_score\n"
    "  FROM last_pitch WHERE rn=1\n"
    "),\n"
    "team_games AS (\n"
    "  SELECT home_team AS team, home_score AS rs, away_score AS ra FROM game_finals\n"
    "  UNION ALL\n"
    "  SELECT away_team, away_score, home_score FROM game_finals\n"
    ")\n"
)


STANDINGS_AGG_SQL: Final[dict[str, str]] = {
    "wins": (
        _BASE_CTE
        + "SELECT team AS id,\n"
        + "       SUM(IF(rs > ra, 1, 0)) AS value,\n"
        + "       COUNT(*) AS sample_size\n"
        + "FROM team_games GROUP BY team HAVING sample_size >= @min_n;"
    ),
    "losses": (
        _BASE_CTE
        + "SELECT team AS id,\n"
        + "       SUM(IF(rs < ra, 1, 0)) AS value,\n"
        + "       COUNT(*) AS sample_size\n"
        + "FROM team_games GROUP BY team HAVING sample_size >= @min_n;"
    ),
    "run_diff": (
        _BASE_CTE
        + "SELECT team AS id,\n"
        + "       SUM(rs) - SUM(ra) AS value,\n"
        + "       COUNT(*) AS sample_size\n"
        + "FROM team_games GROUP BY team HAVING sample_size >= @min_n;"
    ),
}


STANDINGS_TOLERANCES: Final[dict[str, float]] = {
    "wins": 1.0,
    "losses": 1.0,
    "run_diff": 5.0,
}


# Map metric → statsapi field name
_STATSAPI_FIELD: Final[dict[str, str]] = {
    "wins": "wins",
    "losses": "losses",
    "run_diff": "_run_diff",  # synthesized from runs_scored - runs_allowed
}


def _run_aggregation(
    client: bigquery.Client,
    sql: str,
    table: str,
    season: int,
    min_n: int,
) -> dict[str, tuple[float, int]]:
    """Run the BQ query and return {team_abbr: (value, sample_size)}."""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("season", "INT64", season),
            bigquery.ScalarQueryParameter("min_n", "INT64", min_n),
        ]
    )
    rows = client.query_and_wait(
        sql.format(table=table), job_config=job_config
    ).to_dataframe()
    return {
        str(r["id"]): (float(r["value"]), int(r["sample_size"]))
        for _, r in rows.iterrows()
    }


def _team_full_names() -> dict[int | str, str]:
    """abbr → 'Team Full Name' (display) lookup from MLB_TEAMS, with Statcast aliases."""
    return {
        _STATCAST_ABBR_ALIASES.get(meta["abbr"], meta["abbr"]): meta.get("full_name", meta["abbr"])
        for meta in MLB_TEAMS.values()
    }


class BaseballStandingsVerifier:
    SUPPORTED_METRICS = frozenset(STANDINGS_AGG_SQL.keys())

    def __init__(
        self,
        *,
        client: bigquery.Client | None,
        table: str,
        season: int,
        metric: str,
        min_sample_size: int = 1,
        tolerance: float | None = None,
    ) -> None:
        if metric not in self.SUPPORTED_METRICS:
            raise ValueError(
                f"unsupported standings metric {metric!r}; "
                f"choices: {sorted(self.SUPPORTED_METRICS)}"
            )
        self.client = client
        self.table = table
        self.season = season
        self.metric = metric
        self.min_sample_size = min_sample_size
        self.tolerance = (
            tolerance if tolerance is not None else STANDINGS_TOLERANCES[metric]
        )

    def run(self) -> VerificationResult:
        log.info("verify standings %s for %d", self.metric, self.season)
        standings = StandingsClient().fetch_season(self.season)
        if self.metric == "run_diff":
            expected: dict[int | str, float] = {
                abbr: float(rec["runs_scored"] - rec["runs_allowed"])
                for abbr, rec in standings.items()
            }
        else:
            field = _STATSAPI_FIELD[self.metric]
            expected = {
                abbr: float(rec[field]) for abbr, rec in standings.items()
            }
        names: dict[int | str, str] = _team_full_names()

        ours_with_n = _run_aggregation(
            self.client,  # type: ignore[arg-type]  # None only in tests; monkeypatched away
            STANDINGS_AGG_SQL[self.metric],
            self.table, self.season, self.min_sample_size,
        )
        ours: dict[int | str, float] = {k: v[0] for k, v in ours_with_n.items()}
        sample_sizes: dict[int | str, int] = {k: v[1] for k, v in ours_with_n.items()}

        deltas = compare_series(
            ours=ours, expected=expected,
            sample_sizes=sample_sizes, entity_names=names,
            tolerance=self.tolerance,
        )
        within = sum(1 for d in deltas if d.within_tolerance)
        return VerificationResult(
            metric=self.metric, season=self.season,
            aggregation="team-season", source="statsapi",
            tolerance=self.tolerance, total_compared=len(deltas),
            within_tolerance_count=within, deltas=deltas,
        )
