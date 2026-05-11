"""GameClient: fetch full-season schedule from MLB statsapi.

Endpoint:
  /api/v1/schedule?sportId=1&season=YYYY&gameType=R,P,F,D,L,W&hydrate=probablePitcher

One HTTP call returns the entire season (~2,500 games). For a daily sync,
we just fetch the current season every run — it's a small payload and
keeps the table perfectly synchronized including future schedule changes,
probable pitcher updates, and postponed-game adjustments.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Final

import pandas as pd

from statcast_bigquery.games.teams import team_info

log = logging.getLogger(__name__)

STATSAPI_SCHEDULE_URL: Final = "https://statsapi.mlb.com/api/v1/schedule"
DEFAULT_GAME_TYPES: Final[tuple[str, ...]] = ("R", "P", "F", "D", "L", "W")
DEFAULT_HYDRATE: Final[str] = "probablePitcher,venue"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
DEFAULT_MAX_RETRIES: Final[int] = 3


@dataclass(frozen=True)
class GameRow:
    game_pk: int
    season: int
    game_date: str  # YYYY-MM-DD (officialDate)
    game_datetime: str  # ISO 8601 UTC (gameDate)
    game_type: str
    status_code: str
    status_detail: str
    home_team_id: int
    home_team_abbrev: str
    home_league: str | None
    home_division: str | None
    away_team_id: int
    away_team_abbrev: str
    away_league: str | None
    away_division: str | None
    venue_id: int | None
    venue_name: str | None
    probable_home_pitcher_id: int | None
    probable_home_pitcher_name: str | None
    probable_away_pitcher_id: int | None
    probable_away_pitcher_name: str | None
    final_home_score: int | None
    final_away_score: int | None
    double_header_flag: str | None
    game_number: int | None
    series_description: str | None


class GameClient:
    """Pull a full-season MLB schedule with one HTTP call per season."""

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        game_types: Iterable[str] = DEFAULT_GAME_TYPES,
        hydrate: str = DEFAULT_HYDRATE,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.game_types = tuple(game_types)
        self.hydrate = hydrate

    def _build_url(self, season: int) -> str:
        params = {
            "sportId": "1",
            "season": str(season),
            "gameType": ",".join(self.game_types),
            "hydrate": self.hydrate,
        }
        return f"{STATSAPI_SCHEDULE_URL}?{urllib.parse.urlencode(params)}"

    def _fetch_season(self, season: int) -> dict[str, Any] | None:
        url = self._build_url(season)
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(url, timeout=self.timeout_seconds) as r:
                    return json.load(r)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = e
            backoff = 2 ** (attempt - 1)
            log.warning(
                "schedule season=%d attempt %d failed: %s; backoff %ds",
                season, attempt, last_err, backoff,
            )
            time.sleep(backoff)
        log.error("schedule season=%d gave up after %d attempts: %s",
                  season, self.max_retries, last_err)
        return None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _parse_game(self, doc: dict) -> GameRow | None:
        teams = doc.get("teams", {}) or {}
        home = teams.get("home", {}) or {}
        away = teams.get("away", {}) or {}
        home_team = home.get("team") or {}
        away_team = away.get("team") or {}
        home_pp = home.get("probablePitcher") or {}
        away_pp = away.get("probablePitcher") or {}
        venue = doc.get("venue") or {}
        status = doc.get("status") or {}

        home_id = self._safe_int(home_team.get("id"))
        away_id = self._safe_int(away_team.get("id"))
        game_pk = self._safe_int(doc.get("gamePk"))
        if game_pk is None or home_id is None or away_id is None:
            log.debug("skip game with missing PK or team_id: %s", doc.get("gamePk"))
            return None

        home_info = team_info(home_id) or {}
        away_info = team_info(away_id) or {}
        home_abbr = home_info.get("abbr") if home_info else None
        away_abbr = away_info.get("abbr") if away_info else None

        # MLB occasionally fields All-Star / exhibition teams (e.g. team_id 159
        # = National League All-Stars) without entries in our map. Fall back to
        # statsapi-provided abbreviation if present, else 'UNK' to keep schema
        # NOT NULL invariant satisfied.
        if not home_abbr:
            home_abbr = home_team.get("abbreviation") or "UNK"
        if not away_abbr:
            away_abbr = away_team.get("abbreviation") or "UNK"

        return GameRow(
            game_pk=game_pk,
            season=self._safe_int(doc.get("season")) or 0,
            game_date=doc.get("officialDate", ""),
            game_datetime=doc.get("gameDate", ""),
            game_type=doc.get("gameType", ""),
            status_code=status.get("codedGameState", "") or "",
            status_detail=status.get("detailedState", "") or "",
            home_team_id=home_id,
            home_team_abbrev=home_abbr,
            home_league=home_info.get("league") if home_info else None,
            home_division=home_info.get("division") if home_info else None,
            away_team_id=away_id,
            away_team_abbrev=away_abbr,
            away_league=away_info.get("league") if away_info else None,
            away_division=away_info.get("division") if away_info else None,
            venue_id=self._safe_int(venue.get("id")),
            venue_name=venue.get("name"),
            probable_home_pitcher_id=self._safe_int(home_pp.get("id")),
            probable_home_pitcher_name=home_pp.get("fullName"),
            probable_away_pitcher_id=self._safe_int(away_pp.get("id")),
            probable_away_pitcher_name=away_pp.get("fullName"),
            final_home_score=self._safe_int(home.get("score")),
            final_away_score=self._safe_int(away.get("score")),
            double_header_flag=doc.get("doubleHeader"),
            game_number=self._safe_int(doc.get("gameNumber")),
            series_description=doc.get("seriesDescription"),
        )

    def fetch_season(self, season: int) -> pd.DataFrame:
        """Fetch all games for one season. Returns empty DF on persistent failure."""
        log.info("games: fetching season %d schedule (gameType=%s)",
                 season, ",".join(self.game_types))
        doc = self._fetch_season(season)
        if doc is None:
            return self._empty_df()

        rows: list[GameRow] = []
        for date_block in doc.get("dates", []) or []:
            for game in date_block.get("games", []) or []:
                row = self._parse_game(game)
                if row is not None:
                    rows.append(row)
        log.info("games: season %d -> %d rows", season, len(rows))
        if not rows:
            return self._empty_df()

        df = pd.DataFrame([r.__dict__ for r in rows])
        df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
        df["game_datetime"] = pd.to_datetime(df["game_datetime"], utc=True)
        return df

    def fetch_seasons(self, seasons: Iterable[int]) -> pd.DataFrame:
        """Concatenate multiple seasons (used by backfill mode)."""
        frames: list[pd.DataFrame] = []
        for s in seasons:
            df = self.fetch_season(s)
            if not df.empty:
                frames.append(df)
        if not frames:
            return self._empty_df()
        return pd.concat(frames, ignore_index=True)

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        cols: list[str] = [
            "game_pk", "season", "game_date", "game_datetime", "game_type",
            "status_code", "status_detail",
            "home_team_id", "home_team_abbrev", "home_league", "home_division",
            "away_team_id", "away_team_abbrev", "away_league", "away_division",
            "venue_id", "venue_name",
            "probable_home_pitcher_id", "probable_home_pitcher_name",
            "probable_away_pitcher_id", "probable_away_pitcher_name",
            "final_home_score", "final_away_score",
            "double_header_flag", "game_number", "series_description",
        ]
        return pd.DataFrame({c: [] for c in cols})
