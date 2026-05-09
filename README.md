# statcast-bigquery

Idempotent Statcast → BigQuery ingestion, with first-class documentation for SQL/LLM agents and round-trip validation against Baseball Savant.

## Install

    pip install statcast-bigquery

## Quickstart

    gcloud auth application-default login
    statcast-bigquery sync \
        --start 2024-04-01 --end 2024-10-31 \
        --table myproject.mydataset.statcast_pitches

## Documentation

    statcast-bigquery docs --format llm > STATCAST_FOR_LLMS.md

## Verification

    statcast-bigquery verify \
        --source baseball-savant \
        --aggregation player-season \
        --metric all --season 2024 \
        --table myproject.mydataset.statcast_pitches

MIT licensed. This software does not include or distribute MLB data.
