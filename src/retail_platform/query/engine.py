"""Two engines, one interface.

DuckDBEngine runs the exact SQL in sql/ locally. AthenaEngine sends the same
statements to Athena against the Glue catalog. Keeping them behind one interface
is what lets the tests and the local demo exercise real query code.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import duckdb

from ..config import Settings
from ..logging_setup import get_logger

log = get_logger("query")


class DuckDBEngine:
    def __init__(self, cfg: Settings, read_only: bool = False) -> None:
        cfg.warehouse_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(cfg.warehouse_path), read_only=read_only)

    def sql(self, statement: str):
        return self.con.execute(statement).df()

    def scalar(self, statement: str) -> Any:
        return self.con.execute(statement).fetchone()[0]

    def run_file(self, path: Path) -> None:
        self.con.execute(path.read_text(encoding="utf-8"))

    def close(self) -> None:
        self.con.close()


class AthenaEngine:
    """Polls Athena until a query finishes, then reads results from S3."""

    def __init__(self, cfg: Settings) -> None:
        import boto3  # noqa: PLC0415

        self.cfg = cfg
        self.client = boto3.client("athena", region_name=cfg.aws_region)

    def scalar(self, statement: str, database: str | None = None) -> Any:
        qid = self.client.start_query_execution(
            QueryString=statement,
            QueryExecutionContext={"Database": database or self.cfg.glue_database},
            WorkGroup=self.cfg.athena_workgroup,
        )["QueryExecutionId"]

        while True:
            info = self.client.get_query_execution(QueryExecutionId=qid)
            state = info["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                break
            if state in {"FAILED", "CANCELLED"}:
                reason = info["QueryExecution"]["Status"].get("StateChangeReason")
                raise RuntimeError(f"athena query {qid} {state}: {reason}")
            time.sleep(2)

        rows = self.client.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]
        if not rows:
            return None
        return rows[1]["Data"][0].get("VarCharValue") if len(rows) > 1 else None
