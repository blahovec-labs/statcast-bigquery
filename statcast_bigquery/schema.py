"""ColumnSpec dataclass + PITCHES_SCHEMA: single source of truth for the Statcast pitch table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SCHEMA_VERSION = "0.1.0"

BqType = Literal[
    "INT64",
    "FLOAT64",
    "STRING",
    "BOOL",
    "DATE",
    "TIMESTAMP",
    "TIME",
    "NUMERIC",
]
BqMode = Literal["REQUIRED", "NULLABLE"]

_VALID_TYPES = set(BqType.__args__)  # type: ignore[attr-defined]
_VALID_MODES = set(BqMode.__args__)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ColumnSpec:
    """Single source of truth for one column in `statcast_pitches`."""

    name: str
    type: BqType
    mode: BqMode
    short_description: str
    business_definition: str
    semantic_tags: list[str]
    valid_range: tuple[float, float] | None
    valid_values: list[str] | None
    example_value: object | None
    gotchas: list[str]
    statsapi_equivalent: str | None
    pybaseball_source_field: str
    deprecated_in_year: int | None

    def __post_init__(self) -> None:
        if self.type not in _VALID_TYPES:
            raise ValueError(f"{self.name}: invalid type {self.type!r}")
        if self.mode not in _VALID_MODES:
            raise ValueError(f"{self.name}: invalid mode {self.mode!r}")
        if not self.business_definition.strip():
            raise ValueError(f"{self.name}: business_definition required")


@dataclass(frozen=True)
class PartitioningSpec:
    field: str
    type: Literal["DAY", "MONTH", "YEAR"]
    clustering: list[str]


def get_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="game_date",
        type="DAY",
        clustering=["home_team", "away_team", "game_pk"],
    )


# Authored in Task 3. Keep this empty list here so framework tests pass.
PITCHES_SCHEMA: list[ColumnSpec] = [
    ColumnSpec(
        name="game_pk",
        type="INT64",
        mode="REQUIRED",
        short_description="MLB unique game identifier.",
        business_definition=(
            "Stable integer identifying a single MLB game across all data sources "
            "(statsapi, Statcast, Retrosheet). Use as the canonical join key."
        ),
        semantic_tags=["identifier", "join_key", "mlb_canonical"],
        valid_range=None,
        valid_values=None,
        example_value=746789,
        gotchas=[],
        statsapi_equivalent="gamePk",
        pybaseball_source_field="game_pk",
        deprecated_in_year=None,
    ),
]
