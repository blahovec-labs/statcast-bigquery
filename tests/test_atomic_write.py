"""Writes must never leave the target with rows deleted but not replaced.

Regression for 2026-06-09: the pitch writer ran DELETE as its own query, then a
separate load job. The load 400'd (a new Savant column), the DELETE had already
committed, and the whole 7-day window (2026-06-02..06-08) was wiped. Later daily
runs refilled 06-03..06-08; 06-02 had aged out of the lookback and stayed empty.

Contract now, for all three writers: load the new rows into a staging table FIRST,
then DELETE + INSERT ... SELECT in ONE multi-statement transaction, then drop the
staging table. A failed load issues no DELETE at all.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest
from google.cloud import bigquery

from statcast_bigquery.games.writer import GamesTableRef, GameWriter
from statcast_bigquery.umpires.writer import UmpireTableRef, UmpireWriter
from statcast_bigquery.writer import BigQueryWriter, TableRef


def make_client() -> MagicMock:
    client = MagicMock(spec=bigquery.Client)
    client.project = "p"
    return client


def pitches_df() -> pd.DataFrame:
    return pd.DataFrame({"game_date": [date(2026, 6, 2)], "game_pk": [1]})


def umpires_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "game_pk": [1],
            "game_date": [date(2026, 6, 2)],
            "position": ["HP"],
            "umpire_id": [10],
            "umpire_name": ["Ump"],
        }
    )


def games_df() -> pd.DataFrame:
    return pd.DataFrame({"game_pk": [1], "season": [2026]})


def write_pitches(client: MagicMock) -> None:
    BigQueryWriter(client=client).write(
        TableRef.parse("p.d.statcast_pitches"), pitches_df(), "2026-06-02", "2026-06-08"
    )


def write_umpires(client: MagicMock) -> None:
    UmpireWriter(client=client).write(
        UmpireTableRef.parse("p.d.game_umpires"), umpires_df(), "2026-06-02", "2026-06-08"
    )


def write_games(client: MagicMock) -> None:
    GameWriter(client=client).write(GamesTableRef.parse("p.d.games"), games_df(), [2026])


WRITERS = {
    "pitches": (write_pitches, "p.d.statcast_pitches"),
    "umpires": (write_umpires, "p.d.game_umpires"),
    "games": (write_games, "p.d.games"),
}


def sql_calls(client: MagicMock) -> list[str]:
    return [c.args[0] for c in client.query_and_wait.call_args_list]


@pytest.mark.parametrize("name", WRITERS)
def test_failed_load_deletes_nothing(name):
    write, _target = WRITERS[name]
    client = make_client()
    client.load_table_from_dataframe.return_value.result.side_effect = RuntimeError(
        "400 Cannot add fields (field: miss_distance)"
    )

    with pytest.raises(RuntimeError):
        write(client)

    assert not any("DELETE" in sql for sql in sql_calls(client))


@pytest.mark.parametrize("name", WRITERS)
def test_load_targets_staging_not_the_live_table(name):
    write, target = WRITERS[name]
    client = make_client()

    write(client)

    destination = str(client.load_table_from_dataframe.call_args.args[1])
    assert destination != target
    assert "_staging_" in destination


@pytest.mark.parametrize("name", WRITERS)
def test_delete_and_insert_commit_in_one_transaction(name):
    write, target = WRITERS[name]
    client = make_client()

    write(client)

    swaps = [sql for sql in sql_calls(client) if "DELETE" in sql]
    assert len(swaps) == 1
    sql = swaps[0]
    assert sql.lstrip().startswith("BEGIN TRANSACTION")
    assert sql.rstrip().endswith("COMMIT TRANSACTION;")
    assert sql.index("DELETE") < sql.index("INSERT INTO")
    assert f"`{target}`" in sql
    staging = str(client.load_table_from_dataframe.call_args.args[1])
    assert f"FROM `{staging}`" in sql


@pytest.mark.parametrize("name", WRITERS)
def test_staging_table_dropped_even_when_swap_fails(name):
    write, _target = WRITERS[name]
    client = make_client()
    client.query_and_wait.side_effect = RuntimeError("transaction aborted")

    with pytest.raises(RuntimeError):
        write(client)

    staging = str(client.load_table_from_dataframe.call_args.args[1])
    dropped = [str(c.args[0]) for c in client.delete_table.call_args_list]
    assert staging in dropped


def test_games_empty_fetch_still_clears_seasons_without_staging():
    """Existing contract: an empty games fetch is an intentional DELETE-only."""
    client = make_client()

    GameWriter(client=client).write(GamesTableRef.parse("p.d.games"), games_df().iloc[0:0], [2026])

    assert client.load_table_from_dataframe.call_count == 0
    assert any("DELETE" in sql for sql in sql_calls(client))
