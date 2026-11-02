"""Land raw extracts into the bronze layer.

Local mode: CSV -> parquet, partitioned by ingest date, written under
data/lake/bronze/<table>/dt=YYYY-MM-DD/.
AWS mode: the same parquet is written locally then uploaded to S3, where a Glue
crawler registers it in the catalog and Athena can query it in place.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from .config import Settings
from .logging_setup import get_logger
from .storage import get_storage

log = get_logger("ingest")

TABLES = ("customers", "products", "orders", "order_items")


def bronze_dir(cfg: Settings, table: str, dt: str) -> Path:
    return cfg.local_root / "lake" / "bronze" / table / f"dt={dt}"


def land(cfg: Settings, source_dir: Path, dt: str | None = None) -> dict[str, int]:
    """Convert each source CSV to partitioned parquet and register it."""
    dt = dt or date.today().isoformat()
    con = duckdb.connect()
    counts: dict[str, int] = {}
    storage = get_storage(cfg)

    for table in TABLES:
        csv_path = source_dir / f"{table}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"missing source extract: {csv_path}")

        out_dir = bronze_dir(cfg, table, dt)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "part-000.parquet"

        # Everything is read as VARCHAR on purpose: bronze keeps the source
        # exactly as it arrived, defects included. Typing happens in silver.
        con.execute(
            f"""
            COPY (
                SELECT *, TIMESTAMP '{dt} 00:00:00' AS _ingest_ts
                FROM read_csv_auto('{csv_path.as_posix()}', all_varchar = true)
            ) TO '{out_file.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
        n = con.execute(
            f"SELECT count(*) FROM read_parquet('{out_file.as_posix()}')"
        ).fetchone()[0]
        counts[table] = int(n)

        if cfg.is_aws:
            key = f"bronze/{table}/dt={dt}/part-000.parquet"
            uri = storage.put_file(out_file, key)
            log.info("uploaded %s rows to %s", n, uri)
        else:
            log.info("landed %-12s %6s rows -> %s", table, n,
                     out_file.relative_to(cfg.local_root))

    return counts


def register_bronze_views(con: duckdb.DuckDBPyConnection, cfg: Settings) -> None:
    """Point bronze views at the parquet partitions (Athena does this via the catalog)."""
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    for table in TABLES:
        glob = (cfg.local_root / "lake" / "bronze" / table / "**" / "*.parquet").as_posix()
        con.execute(
            f"""
            CREATE OR REPLACE VIEW bronze.{table} AS
            SELECT * FROM read_parquet('{glob}', hive_partitioning = true,
                                       union_by_name = true)
            """
        )
