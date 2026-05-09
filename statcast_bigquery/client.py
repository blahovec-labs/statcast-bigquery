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


class StatcastClient:
    """Pull pitch-level Statcast data for a date range, regular-season only."""

    def __init__(
        self,
        sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.sleep_seconds = sleep_seconds
        self.max_retries = max_retries

    def fetch(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Pull Statcast pitches between [start_date, end_date], filtered to regular season.

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

        result = df[df["game_type"] == "R"].copy()
        if not isinstance(result, pd.DataFrame):
            result = pd.DataFrame(result)
        log.info("statcast: %d regular-season pitches", len(result))
        time.sleep(self.sleep_seconds)
        return result
