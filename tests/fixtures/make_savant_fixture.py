"""One-off helper: pull pybaseball Savant leaderboards for 2024; freeze as parquet.

Run once during plan execution; commit the resulting parquet. Tests use the fixture
instead of hitting Savant.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pybaseball as pb


def main() -> None:
    bat = pb.statcast_batter_exitvelo_barrels(2024, minBBE=50)
    pit = pb.statcast_pitcher_exitvelo_barrels(2024, minBBE=50)
    out_dir = Path(__file__).parent
    bat.to_parquet(out_dir / "savant_batter_2024.parquet", index=False)
    pit.to_parquet(out_dir / "savant_pitcher_2024.parquet", index=False)
    # Combined fixture for tests
    combined = pd.concat(
        [bat.assign(_kind="batter"), pit.assign(_kind="pitcher")],
        ignore_index=True,
    )
    combined.to_parquet(out_dir / "savant_leaderboard_2024.parquet", index=False)
    print(f"Wrote {len(bat)} batter + {len(pit)} pitcher rows.")


if __name__ == "__main__":
    main()
