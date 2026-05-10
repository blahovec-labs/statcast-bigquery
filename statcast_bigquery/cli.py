"""CLI entrypoint: statcast-bigquery {sync,docs,verify}."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta

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
    p_sync.add_argument("--table", required=True, help="project.dataset.table")
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
    if not ns.dry_run:
        writer.create_table_if_missing(ref)

    chunks = _iter_year_chunks(ns.start, ns.end) if ns.chunk_by == "year" \
        else [(ns.start, ns.end)]
    for cs, ce in chunks:
        log.info("chunk %s -> %s", cs, ce)
        if ns.dry_run:
            continue
        df = sc.fetch(cs, ce)
        writer.write(ref, df, cs, ce)
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
