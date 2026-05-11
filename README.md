# statcast-bigquery

Idempotent Statcast → BigQuery ingestion, with first-class documentation for SQL/LLM agents and round-trip validation against Baseball Savant.

## Install

    pip install statcast-bigquery

## Quickstart

    gcloud auth application-default login
    statcast-bigquery sync \
        --start 2024-04-01 --end 2024-10-31 \
        --table myproject.mydataset.statcast_pitches

## Backfill

Backfill historical seasons in resumable chunks:

    statcast-bigquery sync \
        --start 2015-04-01 --end 2026-05-11 \
        --chunk-by year --resume \
        --table myproject.mydataset.statcast_pitches

`--resume` skips chunks already recorded as success in
`<dataset>._statcast_ingest_runs`. Override with `--runs-table` if you
want the run log in a sidecar dataset. Re-running with the same
`--chunk-by` is safe; switching `--chunk-by year` → `month` between
runs will re-process (chunks must match exactly to skip).

## Documentation

    statcast-bigquery docs --format llm > STATCAST_FOR_LLMS.md

## Seed your data dictionary

If you maintain a `data_dictionary` table (one row per column with
business definitions, tags, lineage), you can seed it directly:

    statcast-bigquery docs --format dictionary --apply \
        --dataset mydataset --table myproject.mydataset.statcast_pitches \
        --dictionary-table myproject.shared_ops.data_dictionary

Atomically replaces rows for `(dataset, table)` only; other entries in
the dictionary table are untouched. Required target schema:

    dataset, table, column, dtype, description, business_definition,
    owner, tags ARRAY<STRING>, source_system, upstream_lineage_json,
    created_at TIMESTAMP, updated_at TIMESTAMP

## Verification

    statcast-bigquery verify \
        --source baseball-savant \
        --aggregation player-season \
        --metric all --season 2024 \
        --table myproject.mydataset.statcast_pitches

## Standings verify

End-to-end integrity check: reconstruct each team's season standings
from the pitch data and compare against MLB statsapi:

    statcast-bigquery verify \
        --source baseball-savant \
        --aggregation team-season \
        --metric all --season 2024 \
        --table myproject.mydataset.statcast_pitches

Three metrics are checked per team: `wins`, `losses`, `run_diff`.
Default tolerances are ±1 game and ±5 runs. A passing run gives high
confidence that no games are missing from the pitch ingest.

MIT licensed. This software does not include or distribute MLB data.
