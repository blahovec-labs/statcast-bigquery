"""Run pybaseball.statcast for one day; print column names + dtypes.

Use this once at the start of Task 3 to ensure PITCHES_SCHEMA covers every column.
Output is informational only; not committed as a test.
"""

from __future__ import annotations

import pybaseball as pb


def main() -> None:
    df = pb.statcast(start_dt="2024-04-01", end_dt="2024-04-01")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    for col in df.columns:
        dtype = df[col].dtype
        print(f"  {col!r:<35}  {dtype}")


if __name__ == "__main__":
    main()
