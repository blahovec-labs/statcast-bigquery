"""UmpireClient: fetch umpire crew per game from MLB statsapi.

Uses /api/v1/game/{game_pk}/boxscore which returns a small (~few KB) JSON with
the `officials` array. Concurrent fetches with bounded parallelism + retry.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Final

import pandas as pd

log = logging.getLogger(__name__)

STATSAPI_BOXSCORE_URL: Final = (
    "https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
)

DEFAULT_MAX_WORKERS: Final[int] = 8
DEFAULT_TIMEOUT_SECONDS: Final[float] = 15.0
DEFAULT_MAX_RETRIES: Final[int] = 3

# Map statsapi officialType strings to canonical short codes.
_POSITION_MAP: Final[dict[str, str]] = {
    "Home Plate": "HP",
    "First Base": "1B",
    "Second Base": "2B",
    "Third Base": "3B",
    "Left Field": "LF",
    "Right Field": "RF",
}


@dataclass(frozen=True)
class UmpireRow:
    game_pk: int
    game_date: str  # YYYY-MM-DD
    position: str
    umpire_id: int
    umpire_name: str | None


class UmpireClient:
    """Fetch boxscore officials per game, concurrent + retry-resilient."""

    def __init__(
        self,
        max_workers: int = DEFAULT_MAX_WORKERS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def _fetch_one(self, game_pk: int) -> dict | None:
        """Single boxscore fetch with retry. Returns parsed JSON or None on persistent failure."""
        url = STATSAPI_BOXSCORE_URL.format(game_pk=game_pk)
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(url, timeout=self.timeout_seconds) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                # 404 = game not found in statsapi (rare but possible for old/cancelled games)
                if e.code == 404:
                    log.debug("statsapi 404 for game_pk=%d; skip", game_pk)
                    return None
                last_err = e
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = e
            backoff = 2 ** (attempt - 1)
            log.warning(
                "boxscore game_pk=%d attempt %d failed: %s; backoff %ds",
                game_pk, attempt, last_err, backoff,
            )
            time.sleep(backoff)
        log.error("boxscore game_pk=%d gave up after %d attempts: %s",
                  game_pk, self.max_retries, last_err)
        return None

    def _parse_officials(self, game_pk: int, game_date: str, doc: dict) -> list[UmpireRow]:
        rows: list[UmpireRow] = []
        for o in doc.get("officials", []):
            position_raw = o.get("officialType", "")
            position = _POSITION_MAP.get(position_raw)
            if position is None:
                log.debug("game_pk=%d unknown officialType=%r; skip",
                          game_pk, position_raw)
                continue
            official = o.get("official") or {}
            umpire_id = official.get("id")
            if umpire_id is None:
                continue
            rows.append(UmpireRow(
                game_pk=game_pk,
                game_date=game_date,
                position=position,
                umpire_id=int(umpire_id),
                umpire_name=official.get("fullName"),
            ))
        return rows

    def fetch(self, games: Iterable[tuple[int, str]]) -> pd.DataFrame:
        """Fetch officials for a sequence of (game_pk, game_date) tuples.

        Returns a DataFrame with columns: game_pk, game_date, position,
        umpire_id, umpire_name. Empty DataFrame on no data.
        """
        games_list = list(games)
        empty_cols: list[str] = [
            "game_pk", "game_date", "position", "umpire_id", "umpire_name",
        ]
        if not games_list:
            return pd.DataFrame({c: [] for c in empty_cols})

        log.info("umpires: fetching %d games via statsapi", len(games_list))
        all_rows: list[UmpireRow] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._fetch_one, gp): (gp, gd)
                for gp, gd in games_list
            }
            for i, fut in enumerate(as_completed(futures), start=1):
                gp, gd = futures[fut]
                doc = fut.result()
                if doc is None:
                    continue
                all_rows.extend(self._parse_officials(gp, gd, doc))
                if i % 250 == 0:
                    log.info("umpires: %d/%d games fetched", i, len(games_list))

        log.info("umpires: %d rows from %d games", len(all_rows), len(games_list))
        df = pd.DataFrame([r.__dict__ for r in all_rows])
        if not df.empty:
            df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
        return df
