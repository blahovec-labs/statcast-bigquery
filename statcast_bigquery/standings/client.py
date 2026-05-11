"""StandingsClient: fetches season standings from MLB statsapi /standings.

Single HTTP call per season returns all 30 teams' W-L-RS-RA. Maps statsapi
team_id to the abbreviation used in statcast_pitches.home_team/away_team via
the existing MLB_TEAMS constant.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Final

import requests

from statcast_bigquery.games.teams import MLB_TEAMS

log = logging.getLogger(__name__)

DEFAULT_SLEEP_SECONDS: Final[float] = 2.0
DEFAULT_MAX_RETRIES: Final[int] = 5
STATSAPI_BASE: Final[str] = "https://statsapi.mlb.com/api/v1/standings"


class StandingsClient:
    """Pull team-season W-L-RS-RA from statsapi /standings."""

    def __init__(
        self,
        sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.sleep_seconds = sleep_seconds
        self.max_retries = max_retries

    def fetch_season(self, season: int) -> dict[str, dict[str, Any]]:
        """Return {team_abbr: {wins, losses, runs_scored, runs_allowed}}.

        Both leagues (AL=103, NL=104), regular season only. Unknown team_ids
        (not present in MLB_TEAMS) are logged and skipped.
        """
        url = (
            f"{STATSAPI_BASE}?leagueId=103,104&season={season}"
            "&standingsTypes=regularSeason"
        )
        attempt = 0
        last_err: Exception | None = None
        while attempt < self.max_retries:
            attempt += 1
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                payload = resp.json()
                break
            except Exception as e:
                last_err = e
                backoff = self.sleep_seconds * (2 ** (attempt - 1))
                log.warning(
                    "standings fetch attempt %d failed: %s; backoff %.1fs",
                    attempt, e, backoff,
                )
                time.sleep(backoff)
        else:
            assert last_err is not None
            raise last_err

        result: dict[str, dict[str, Any]] = {}
        for division in payload.get("records", []):
            for team_record in division.get("teamRecords", []):
                team_id = team_record["team"]["id"]
                team_meta = MLB_TEAMS.get(team_id)
                if team_meta is None:
                    log.warning(
                        "statsapi team_id %d not in MLB_TEAMS; skipping", team_id,
                    )
                    continue
                abbr = team_meta["abbr"]
                result[abbr] = {
                    "wins": int(team_record["wins"]),
                    "losses": int(team_record["losses"]),
                    "runs_scored": int(team_record["runsScored"]),
                    "runs_allowed": int(team_record["runsAllowed"]),
                }
        return result
