"""Runtime configuration.

Everything is driven by environment variables so the same code runs against
local disk (mode=local) or real AWS (mode=aws). Defaults are safe for a fresh
clone: local mode, no credentials needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "y"}


@dataclass(frozen=True)
class Settings:
    """Resolved settings for one pipeline invocation."""

    mode: str
    aws_region: str
    account_id: str
    bucket_raw: str
    bucket_curated: str
    glue_database: str
    athena_workgroup: str
    redshift_workgroup: str
    redshift_database: str
    local_root: Path
    warehouse_path: Path
    seed: int
    days_of_history: int

    @property
    def is_aws(self) -> bool:
        return self.mode == "aws"

    def lake_uri(self, layer: str, table: str) -> str:
        """Return the location of a table in the lake, for the current mode."""
        prefix = f"{layer}/{table}"
        if self.is_aws:
            return f"s3://{self.bucket_curated}/{prefix}"
        return str(self.local_root / "lake" / layer / table)


def settings() -> Settings:
    """Build settings from the environment. Called per invocation, not imported."""
    local_root = Path(os.getenv("PLATFORM_LOCAL_ROOT", REPO_ROOT / "data"))
    return Settings(
        mode=os.getenv("PLATFORM_MODE", "local").strip().lower(),
        aws_region=os.getenv("AWS_REGION", "ap-south-1"),
        account_id=os.getenv("AWS_ACCOUNT_ID", "000000000000"),
        bucket_raw=os.getenv("BUCKET_RAW", "retail-platform-raw"),
        bucket_curated=os.getenv("BUCKET_CURATED", "retail-platform-curated"),
        glue_database=os.getenv("GLUE_DATABASE", "retail_platform"),
        athena_workgroup=os.getenv("ATHENA_WORKGROUP", "retail-analysts"),
        redshift_workgroup=os.getenv("REDSHIFT_WORKGROUP", "retail-bi"),
        redshift_database=os.getenv("REDSHIFT_DATABASE", "analytics"),
        local_root=local_root,
        warehouse_path=local_root / "warehouse" / "retail.duckdb",
        seed=int(os.getenv("PLATFORM_SEED", "42")),
        days_of_history=int(os.getenv("PLATFORM_DAYS", "420")),
    )
