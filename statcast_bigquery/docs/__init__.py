"""Documentation renderers + curated content (taxonomy, statsapi map, pitfalls, examples)."""

from statcast_bigquery.docs.example_queries import EXAMPLE_QUERIES, ExampleQuery
from statcast_bigquery.docs.pitfalls import PITFALLS, Pitfall
from statcast_bigquery.docs.statsapi_map import STATCAST_TO_STATSAPI_MAP
from statcast_bigquery.docs.taxonomy import SEMANTIC_GROUPS, columns_in_group

__all__ = [
    "EXAMPLE_QUERIES",
    "ExampleQuery",
    "PITFALLS",
    "Pitfall",
    "SEMANTIC_GROUPS",
    "STATCAST_TO_STATSAPI_MAP",
    "columns_in_group",
]
