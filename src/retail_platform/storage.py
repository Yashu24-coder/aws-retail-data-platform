"""Storage abstraction: local disk for development, S3 for AWS mode.

The pipeline never calls boto3 directly. It asks for a storage backend and
writes through that, which is why the same ingest code runs in both modes.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

from .config import Settings


class Storage(Protocol):
    def put_file(self, local_path: Path, key: str) -> str: ...
    def list_keys(self, prefix: str) -> list[str]: ...
    def location(self, key: str) -> str: ...


class LocalStorage:
    """Writes into a local directory tree that stands in for S3."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def put_file(self, local_path: Path, key: str) -> str:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() != local_path.resolve():
            shutil.copy2(local_path, target)
        return str(target)

    def list_keys(self, prefix: str) -> list[str]:
        base = self.root / prefix
        if not base.exists():
            return []
        return sorted(str(p.relative_to(self.root)) for p in base.rglob("*") if p.is_file())

    def location(self, key: str) -> str:
        return str(self.root / key)


class S3Storage:
    """Writes to a real S3 bucket. boto3 is imported lazily on purpose."""

    def __init__(self, bucket: str, region: str) -> None:
        self.bucket = bucket
        self.region = region
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import boto3  # noqa: PLC0415 - lazy import keeps local mode dependency-free

            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def put_file(self, local_path: Path, key: str) -> str:
        self.client.upload_file(str(local_path), self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def list_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return sorted(keys)

    def location(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"


def get_storage(cfg: Settings) -> Storage:
    if cfg.is_aws:
        return S3Storage(cfg.bucket_raw, cfg.aws_region)
    return LocalStorage(cfg.local_root / "lake" / "raw")
