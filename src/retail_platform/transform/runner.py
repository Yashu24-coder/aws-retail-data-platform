"""Execute the SQL models and materialise each layer as parquet.

Each model is a plain SELECT in sql/. The runner:
  1. builds the SELECT as a view,
  2. copies the result to parquet in the layer directory (this is the S3 object),
  3. replaces the view so it reads from that parquet instead of recomputing.

That third step matters: after a run, every table you query is the parquet that
Athena would read, not an in-memory convenience table.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from ..config import Settings
from ..logging_setup import get_logger

log = get_logger("transform")

SILVER_MODELS = ("customers", "products", "orders", "order_items")
GOLD_MODELS = (
    "dim_customer", "dim_product", "dim_date",
    "fct_order_items", "mart_monthly_revenue", "mart_category_performance",
)


def _materialise(con: duckdb.DuckDBPyConnection, cfg: Settings, layer: str,
                 name: str, sql_path: Path) -> int:
    schema = layer
    qualified = f"{schema}.{name}"
    sql = sql_path.read_text(encoding="utf-8").strip().rstrip(";")

    out_file = cfg.local_root / "lake" / layer / name / "part-000.parquet"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW _stage AS {sql}")
    con.execute(
        f"COPY (SELECT * FROM _stage) TO '{out_file.as_posix()}' "
        f"(FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW {qualified} AS "
        f"SELECT * FROM read_parquet('{out_file.as_posix()}')"
    )
    con.execute("DROP VIEW _stage")

    n = con.execute(f"SELECT count(*) FROM {qualified}").fetchone()[0]
    log.info("built %-28s %7s rows", qualified, f"{n:,}")
    return int(n)


def build_layer(con: duckdb.DuckDBPyConnection, cfg: Settings, layer: str,
                models: tuple[str, ...]) -> dict[str, int]:
    sql_dir = cfg.local_root.parent / "sql" / layer
    counts: dict[str, int] = {}
    for name in models:
        path = sql_dir / f"{name}.sql"
        if not path.exists():
            raise FileNotFoundError(f"missing model: {path}")
        counts[name] = _materialise(con, cfg, layer, name, path)
    return counts
