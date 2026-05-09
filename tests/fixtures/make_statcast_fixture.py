"""One-off helper: pull pybaseball.statcast for one day and freeze as parquet.

Run once during plan execution; commit the resulting parquet. Future tests use
the fixture instead of hitting Baseball Savant.
"""

from __future__ import annotations

from pathlib import Path

import pybaseball as pb


def main() -> None:
    df = pb.statcast(start_dt="2024-04-01", end_dt="2024-04-01")
    out = Path(__file__).parent / "statcast_sample_2024-04-01.parquet"
    df.to_parquet(out, index=False)
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
