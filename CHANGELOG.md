# Changelog

## [0.3.1] - 2026-05-11

### Fixed
- Savant verify: scale Savant percentage metrics (`brl_percent`,
  `ev95percent`) to fractions before comparing to our SQL aggregations.
  Closes the 100x mismatch that caused the post-0.2.0 verify FAIL.
- Declare `db-dtypes` as a runtime dependency. `verify` calls
  `bigquery.Client.query_and_wait(...).to_dataframe()` which requires
  `db-dtypes` for INT64 columns. Missing it caused `verify` to
  `ModuleNotFoundError` in any environment that didn't have
  `db-dtypes` coincidentally pulled in by another package.
- Verify SQL templates aligned with Baseball Savant leaderboard
  definitions:
  - `barrel_rate` uses Statcast's canonical `launch_speed_angle = 6`
    classification (the pre-computed barrel flag) instead of
    approximating the curved zone in SQL.
  - Batting + `hard_hit_allowed` pitching metrics now filter to BBE
    (`description = 'hit_into_play'`) and exclude bunts via
    `bb_type IN ('popup','ground_ball','line_drive','fly_ball')`.
  - `xwoba_contact` now matches Savant's `est_woba`: averages xwOBA
    contributions across all plate appearances (BBE use
    `estimated_woba_using_speedangle`, non-BBE use `woba_value`),
    excluding sac bunts (`woba_denom = 0`).

### Added
- Real `--resume` checkpointing. Sync now records every chunk to a
  `_statcast_ingest_runs` table colocated with the pitches table
  (underscore-prefixed so BigQuery console hides it). `--resume` skips
  chunks already recorded as `success` or `empty`. Override location
  with `--runs-table project.dataset.table`.
- Real `--chunk-by month` iterator. Previously `month` was an argparse
  choice but fell through to single-range behavior. Now emits one chunk
  per calendar month, clipped to `[start, end]`.
- `docs --format dictionary --apply --dictionary-table proj.ds.tbl`
  writes data-dictionary rows directly into a BQ table (DELETE rows
  for `(dataset, table)`, INSERT new ones, atomic via
  `BEGIN TRANSACTION` ... `COMMIT TRANSACTION`). Mirrors `bq-apply`.
- Example queries rewritten in idiomatic BigQuery (`COUNTIF`,
  `SAFE_DIVIDE`, `DATE_SUB`, `APPROX_QUANTILES`). Test gate swapped
  from DuckDB EXPLAIN to sqlglot BigQuery-dialect parse — drops the
  ~30MB native duckdb wheel from dev deps in favor of pure-Python
  sqlglot. Adds a per-query check that every name in `columns_used`
  exists in `PITCHES_SCHEMA`.

### Changed
- Test fixture in `tests/test_renderers.py` no longer references the
  author's specific dataset name; uses generic `"my_dataset"`.

## [0.3.0] - 2026-05-10

### Added
- **Game schedule ingestion.** New `games` table sourced from MLB statsapi
  `/api/v1/schedule` with `hydrate=probablePitcher,venue`. Covers regular
  season + every postseason round (R, P, F, D, L, W). One row per game_pk
  — includes both completed games (with final scores) and future scheduled
  games (with probable pitchers), so this single table powers
  "yesterday's results" and "today's slate" views.
- `statcast-bigquery sync` now fetches games alongside pitches + umpires
  by default. Use `--skip-games` to opt out or `--games-table` to override
  the default `<dataset>.games`. Games are season-grained: one statsapi
  HTTP call returns the entire season (~2,500 games), so the sync auto-
  detects the seasons overlapping `[start, end]` and replaces them
  wholesale.
- New module `statcast_bigquery.games` (schema, teams, client, writer)
  plus `MLB_TEAMS` constant — 30-team id → abbrev/league/division map.

### Why
- MLB_AI v1 right-nav game cards (yesterday results, today's slate with
  probable pitchers) need a games table. Modeling future games needs
  scheduled-game records before they're played. Bundling source means a
  single sync run keeps statcast_pitches, game_umpires, AND games all
  fresh in one Cloud Run Job execution.

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
