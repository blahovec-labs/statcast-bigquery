# Changelog

## [0.2.0] - 2026-05-10

### Added
- **Umpire ingestion.** New `game_umpires` table sourced from MLB statsapi
  (`/api/v1/game/{game_pk}/boxscore` officials). One row per
  (game_pk, position); positions are HP/1B/2B/3B (LF/RF in postseason).
  `statcast-bigquery sync` now fetches both pitches AND umpires by default
  in a single command. Use `--skip-umpires` to opt out, or
  `--umpires-table` to override the default `<dataset>.game_umpires`.
- New module `statcast_bigquery.umpires` (schema, client, writer).
- `UmpireClient` uses `ThreadPoolExecutor` with 8 concurrent fetches +
  exponential backoff retry. ~25K games (12 years) backfills in minutes,
  not hours.

### Why
- Statcast's pitch-level `umpire` field has been NULL across every season
  since 2015. To do umpire-bias / strike-zone analysis you need a real
  identifier, which only statsapi provides. Bundling the source means a
  single `sync` call leaves no MLB_AI feature unbacked except odds.

## [0.1.3] - 2026-05-10

### Fixed
- 7 bat-tracking columns retyped INT64 → FLOAT64. The 0.1.0 schema
  declared these as integers based on the spec table, but Statcast
  returns them as floats with real fractional values (e.g.
  `bat_speed=71.3 mph`, `attack_angle=10.03 degrees`). The error
  surfaces only on 2023+ data when bat tracking is populated:
  `pyarrow.lib.ArrowInvalid: Float value 66.5 was truncated converting to int64`.
  Affected columns: `bat_speed`, `swing_length`, `attack_angle`,
  `attack_direction`, `swing_path_tilt`,
  `intercept_ball_minus_batter_pos_x_inches`,
  `intercept_ball_minus_batter_pos_y_inches`.

## [0.1.2] - 2026-05-10

### Fixed
- Writer now force-casts STRING columns to pandas string dtype before
  pyarrow conversion. pybaseball returns some columns (notably `sv_id`)
  as Int64 when all values are NULL — pyarrow doesn't auto-coerce
  Int64 → STRING and the load fails with "Expected a string or bytes
  dtype, got int64". The 0.1.1 schema fix was correct but insufficient
  on its own; this complements it with the writer-side coercion.

## [0.1.1] - 2026-05-10

### Fixed
- `sv_id` schema type changed from `INT64` to `STRING`. Real Statcast values
  are encoded as `YYMMDD_HHMMSS` (e.g. `'151004_174434'`) — historical years
  (notably 2015) contain non-numeric values that fail Arrow conversion to
  int64 during BigQuery load. The 2024-only smoke tests passed in 0.1.0
  because pybaseball returns the column all-null for recent years.

## [0.1.0] - 2026-05-?? (planned)

### Added
- Initial release.
- `statcast-bigquery sync` — idempotent Statcast pitch-level ingestion to BigQuery.
- `statcast-bigquery docs` — 5 documentation renderers (BQ-native, LLM, dictionary, markdown, dbt).
- `statcast-bigquery verify` — Baseball Savant leaderboard verification (8 metrics).
- 25 vetted example queries; 10+ pitfall catalog; statsapi cross-reference.
- Schema spans pybaseball Statcast columns (~118 fields); auto-applied BQ-native column descriptions.
