"""Per-row comparison logic — independent of source."""

from __future__ import annotations

from statcast_bigquery.verify.base import Comparison


def compare_series(
    *,
    ours: dict[int, float],
    expected: dict[int, float],
    sample_sizes: dict[int, int],
    entity_names: dict[int, str],
    tolerance: float,
) -> list[Comparison]:
    """Inner-join `ours` and `expected` on entity_id; produce one Comparison per shared id."""
    ids = sorted(set(ours) & set(expected))
    rows: list[Comparison] = []
    for i in ids:
        diff = ours[i] - expected[i]
        rows.append(
            Comparison(
                entity_id=i,
                entity_name=entity_names.get(i, str(i)),
                ours=ours[i],
                expected=expected[i],
                diff=diff,
                sample_size=sample_sizes.get(i, 0),
                within_tolerance=abs(diff) <= tolerance,
            )
        )
    return rows
