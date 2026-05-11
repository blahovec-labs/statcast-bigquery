"""CLI entrypoint: statcast-bigquery {sync,docs,verify}."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta

import pandas as pd
from google.cloud import bigquery

from statcast_bigquery._version import __version__
from statcast_bigquery.client import StatcastClient
from statcast_bigquery.docs.renderers import (
    render_bq_descriptions,
    render_data_dictionary,
    render_dbt_yaml,
    render_llm_context,
    render_markdown,
)
from statcast_bigquery.games.client import GameClient
from statcast_bigquery.games.writer import GamesTableRef, GameWriter
from statcast_bigquery.umpires.client import UmpireClient
from statcast_bigquery.umpires.writer import UmpireTableRef, UmpireWriter
from statcast_bigquery.verify.savant import (
    BATTING_METRIC_TO_SAVANT_FIELD,
    PITCHING_METRIC_TO_SAVANT_FIELD,
    BaseballSavantBattingVerifier,
    BaseballSavantPitchingVerifier,
)
from statcast_bigquery.writer import BigQueryWriter, TableRef

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("statcast-bigquery")

ALL_BATTING_METRICS = list(BATTING_METRIC_TO_SAVANT_FIELD)
ALL_PITCHING_METRICS = list(PITCHING_METRIC_TO_SAVANT_FIELD)
DOC_FORMATS = ["bq-apply", "llm", "dictionary", "markdown", "dbt"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="statcast-bigquery")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    # sync
    p_sync = sub.add_parser("sync", help="Pull Statcast and write to BigQuery")
    p_sync.add_argument("--start", required=True, help="YYYY-MM-DD start (inclusive)")
    p_sync.add_argument("--end", required=True, help="YYYY-MM-DD end (inclusive)")
    p_sync.add_argument("--table", required=True, help="project.dataset.table for pitches")
    p_sync.add_argument(
        "--umpires-table",
        help=(
            "project.dataset.table for game_umpires. "
            "Defaults to <pitches-dataset>.game_umpires."
        ),
    )
    p_sync.add_argument(
        "--skip-umpires", action="store_true",
        help="Skip umpire ingestion (pitches only).",
    )
    p_sync.add_argument(
        "--games-table",
        help=(
            "project.dataset.table for games. "
            "Defaults to <pitches-dataset>.games."
        ),
    )
    p_sync.add_argument(
        "--skip-games", action="store_true",
        help="Skip games schedule ingestion.",
    )
    p_sync.add_argument("--chunk-by", default="year", choices=["year", "month", "range"])
    p_sync.add_argument("--resume", action="store_true",
                        help="Skip year-chunks already recorded in _statcast_ingest_runs")
    p_sync.add_argument("--dry-run", action="store_true")

    # docs
    p_docs = sub.add_parser("docs", help="Render documentation in various formats")
    p_docs.add_argument("--format", required=True, choices=DOC_FORMATS)
    p_docs.add_argument("--table", help="project.dataset.table (required for bq-apply, dictionary)")
    p_docs.add_argument("--dataset", help="for dictionary format")
    p_docs.add_argument("--output", default="-", help="path or '-' for stdout (default)")
    p_docs.add_argument("--apply", action="store_true",
        help="For dictionary format: write directly to --dictionary-table instead of stdout JSON.")
    p_docs.add_argument("--dictionary-table",
        help="project.dataset.table for the data_dictionary table (required with --apply).")

    # verify
    p_v = sub.add_parser("verify", help="Compare aggregations to external sources")
    p_v.add_argument("--source", default="baseball-savant", choices=["baseball-savant"])
    p_v.add_argument("--aggregation", required=True,
                     choices=["player-season", "pitcher-season"])
    p_v.add_argument("--metric", required=True,
                     choices=[*ALL_BATTING_METRICS, *ALL_PITCHING_METRICS, "all"])
    p_v.add_argument("--season", required=True, type=int)
    p_v.add_argument("--table", required=True)
    p_v.add_argument("--tolerance", type=float, default=None)
    p_v.add_argument("--min-sample-size", type=int, default=50)
    p_v.add_argument("--threshold", type=float, default=0.99)
    p_v.add_argument("--output", default="-")

    return parser


def _iter_year_chunks(start: str, end: str) -> list[tuple[str, str]]:
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    chunks: list[tuple[str, str]] = []
    cur = s
    while cur <= e:
        year_end = date(cur.year, 12, 31)
        last = min(year_end, e)
        chunks.append((cur.isoformat(), last.isoformat()))
        cur = last + timedelta(days=1)
    return chunks


def cmd_sync(ns: argparse.Namespace) -> int:
    client = bigquery.Client()
    sc = StatcastClient()
    writer = BigQueryWriter(client=client)
    ref = TableRef.parse(ns.table)

    sync_umpires = not getattr(ns, "skip_umpires", False)
    umpire_ref: UmpireTableRef | None = None
    umpire_client: UmpireClient | None = None
    umpire_writer: UmpireWriter | None = None
    if sync_umpires:
        umpire_table = getattr(ns, "umpires_table", None) or \
            f"{ref.project}.{ref.dataset}.game_umpires"
        umpire_ref = UmpireTableRef.parse(umpire_table)
        umpire_client = UmpireClient()
        umpire_writer = UmpireWriter(client=client)

    sync_games = not getattr(ns, "skip_games", False)
    games_ref: GamesTableRef | None = None
    games_client: GameClient | None = None
    games_writer: GameWriter | None = None
    if sync_games:
        games_table = getattr(ns, "games_table", None) or \
            f"{ref.project}.{ref.dataset}.games"
        games_ref = GamesTableRef.parse(games_table)
        games_client = GameClient()
        games_writer = GameWriter(client=client)

    if not ns.dry_run:
        writer.create_table_if_missing(ref)
        if umpire_writer is not None and umpire_ref is not None:
            umpire_writer.create_table_if_missing(umpire_ref)
        if games_writer is not None and games_ref is not None:
            games_writer.create_table_if_missing(games_ref)

    chunks = _iter_year_chunks(ns.start, ns.end) if ns.chunk_by == "year" \
        else [(ns.start, ns.end)]
    for cs, ce in chunks:
        log.info("chunk %s -> %s", cs, ce)
        if ns.dry_run:
            continue
        df = sc.fetch(cs, ce)
        writer.write(ref, df, cs, ce)

        if (sync_umpires and umpire_client is not None
                and umpire_writer is not None and umpire_ref is not None):
            if df.empty:
                log.info("no pitches for chunk %s -> %s; skip umpire fetch", cs, ce)
                continue
            games = (
                df[["game_pk", "game_date"]]
                .drop_duplicates()
                .assign(game_date=lambda x: pd.to_datetime(x["game_date"]).dt.strftime("%Y-%m-%d"))
                .itertuples(index=False, name=None)
            )
            umpire_df = umpire_client.fetch(games)
            umpire_writer.write(umpire_ref, umpire_df, cs, ce)

    # Games are season-grained (one statsapi call per season returns full
    # past + future schedule), so fetch once after the chunk loop covering
    # every season that overlaps [start, end].
    if (sync_games and games_client is not None
            and games_writer is not None and games_ref is not None):
        start_year = datetime.strptime(ns.start, "%Y-%m-%d").date().year
        end_year = datetime.strptime(ns.end, "%Y-%m-%d").date().year
        seasons = list(range(start_year, end_year + 1))
        log.info("games: syncing seasons %s", seasons)
        games_df = games_client.fetch_seasons(seasons)
        games_writer.write(games_ref, games_df, seasons)
    return 0


def cmd_docs(ns: argparse.Namespace) -> int:
    if ns.format == "bq-apply":
        if not ns.table:
            log.error("--table required for bq-apply")
            return 2
        client = bigquery.Client()
        ref = TableRef.parse(ns.table)
        table = client.get_table(str(ref))
        table.schema = render_bq_descriptions()
        client.update_table(table, ["schema"])
        log.info("updated schema descriptions on %s", ref)
        return 0

    if ns.format == "llm":
        out = render_llm_context()
    elif ns.format == "dictionary":
        if not (ns.dataset and ns.table):
            log.error("--dataset and --table required for dictionary")
            return 2
        ref = TableRef.parse(ns.table)
        if ns.apply:
            if not ns.dictionary_table:
                log.error("--dictionary-table required with --apply")
                return 2
            from statcast_bigquery.docs.renderers import apply_data_dictionary
            client = bigquery.Client()
            n = apply_data_dictionary(
                client=client,
                dictionary_table=ns.dictionary_table,
                dataset=ns.dataset,
                table=ref.table,
            )
            log.info("applied %d rows to %s", n, ns.dictionary_table)
            return 0
        out = json.dumps(
            render_data_dictionary(dataset=ns.dataset, table=ref.table), indent=2
        )
    elif ns.format == "markdown":
        out = render_markdown()
    elif ns.format == "dbt":
        out = render_dbt_yaml()
    else:
        raise AssertionError(f"unhandled format {ns.format}")

    if ns.output == "-":
        with open(sys.stdout.fileno(), mode="w", encoding="utf-8", newline="") as f:
            f.write(out)
    else:
        with open(ns.output, "w", encoding="utf-8") as f:
            f.write(out)
    return 0


def cmd_verify(ns: argparse.Namespace) -> int:
    client = bigquery.Client()
    metrics = ([*ALL_BATTING_METRICS] if ns.aggregation == "player-season"
               else [*ALL_PITCHING_METRICS]) if ns.metric == "all" else [ns.metric]

    overall_pass = True
    all_results: list[dict] = []
    for m in metrics:
        if ns.aggregation == "player-season":
            v = BaseballSavantBattingVerifier(
                client=client, table=ns.table, season=ns.season, metric=m,
                min_sample_size=ns.min_sample_size, tolerance=ns.tolerance,
            )
        else:
            v = BaseballSavantPitchingVerifier(
                client=client, table=ns.table, season=ns.season, metric=m,
                min_sample_size=ns.min_sample_size, tolerance=ns.tolerance,
            )
        result = v.run()
        print(result.summary())
        verdict = "PASS" if result.passed(ns.threshold) else "FAIL"
        print(f"{verdict} (threshold {ns.threshold:.2%})\n")
        if not result.passed(ns.threshold):
            overall_pass = False
        all_results.append(result.to_json())

    if ns.output != "-":
        with open(ns.output, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)

    return 0 if overall_pass else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    if ns.command == "sync":
        return cmd_sync(ns)
    if ns.command == "docs":
        return cmd_docs(ns)
    if ns.command == "verify":
        return cmd_verify(ns)
    raise AssertionError(f"unhandled command {ns.command}")


if __name__ == "__main__":
    sys.exit(main())
