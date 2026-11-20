"""StatcastClient: thin wrapper around pybaseball.statcast with retry + politeness."""

from __future__ import annotations

import logging
import time
from typing import Final

import pandas as pd
import pybaseball as pb

log = logging.getLogger(__name__)

DEFAULT_SLEEP_SECONDS: Final[float] = 2.0
DEFAULT_MAX_RETRIES: Final[int] = 5

REGULAR_SEASON: Final[frozenset[str]] = frozenset({"R"})
# Statcast postseason game types: F = wild card, D = division series,
# L = league championship series, W = World Series.
POSTSEASON: Final[frozenset[str]] = frozenset({"F", "D", "L", "W"})


class StatcastClient:
    """Pull pitch-level Statcast data for a date range.

    Regular season only by default; ``include_postseason=True`` also keeps the
    four playoff rounds. Spring training and exhibition games are always dropped.
    """

    def __init__(
        self,
        sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        include_postseason: bool = False,
    ) -> None:
        self.sleep_seconds = sleep_seconds
        self.max_retries = max_retries
        self.game_types = REGULAR_SEASON | POSTSEASON if include_postseason else REGULAR_SEASON

    def fetch(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Pull Statcast pitches between [start_date, end_date], filtered to ``game_types``.

        Returns an empty DataFrame on no data; raises on persistent failure.
        """
        log.info("statcast: pull %s -> %s", start_date, end_date)
        attempt = 0
        last_err: Exception | None = None
        while attempt < self.max_retries:
            attempt += 1
            try:
                df = pb.statcast(start_dt=start_date, end_dt=end_date)
                break
            except Exception as e:  # pybaseball can raise generic Exception on rate limits
                last_err = e
                backoff = self.sleep_seconds * (2 ** (attempt - 1))
                log.warning(
                    "statcast attempt %d failed: %s; backoff %.1fs", attempt, e, backoff
                )
                time.sleep(backoff)
        else:
            assert last_err is not None
            raise last_err

        if df is None or len(df) == 0:
            log.info("statcast: no data for %s -> %s", start_date, end_date)
            return pd.DataFrame()

        result = df[df["game_type"].isin(sorted(self.game_types))].copy()
        if not isinstance(result, pd.DataFrame):
            result = pd.DataFrame(result)
        log.info("statcast: %d pitches (game types %s)", len(result), sorted(self.game_types))
        time.sleep(self.sleep_seconds)
        return result
