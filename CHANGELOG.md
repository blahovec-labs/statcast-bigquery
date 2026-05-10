# Changelog

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
