# Changelog

## [0.1.0] - 2026-05-?? (planned)

### Added
- Initial release.
- `statcast-bigquery sync` — idempotent Statcast pitch-level ingestion to BigQuery.
- `statcast-bigquery docs` — 5 documentation renderers (BQ-native, LLM, dictionary, markdown, dbt).
- `statcast-bigquery verify` — Baseball Savant leaderboard verification (8 metrics).
- 25 vetted example queries; 10+ pitfall catalog; statsapi cross-reference.
- Schema spans pybaseball Statcast columns (~118 fields); auto-applied BQ-native column descriptions.
