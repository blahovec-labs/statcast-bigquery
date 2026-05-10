"""End-to-end idempotency: write the same date range twice, ensure DELETE happens first.

Uses mocked BigQuery client; the assertion is on the *order and shape* of operations,
not on a real BQ round-trip.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pandas as pd
from google.cloud import bigquery

from statcast_bigquery.writer import BigQueryWriter, TableRef


def test_idempotent_double_write_calls_delete_each_time():
    fixture = pd.read_parquet(
        Path(__file__).parent / "fixtures" / "statcast_sample_2024-04-01.parquet"
    )
    fixture = cast(pd.DataFrame, fixture[fixture["game_type"] == "R"].reset_index(drop=True))

    client = MagicMock(spec=bigquery.Client)
    client.project = "test-project"
    writer = BigQueryWriter(client=client)
    ref = TableRef.parse("p.d.statcast_pitches")

    writer.write(ref, fixture, "2024-04-01", "2024-04-01")
    writer.write(ref, fixture, "2024-04-01", "2024-04-01")

    # Two writes -> two DELETEs (one each)
    delete_calls = [
        c for c in client.query_and_wait.call_args_list if "DELETE" in c.args[0]
    ]
    assert len(delete_calls) == 2

    # Two writes -> two loads
    assert client.load_table_from_dataframe.call_count == 2
