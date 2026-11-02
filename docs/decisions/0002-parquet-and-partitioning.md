# 0002 - Parquet with `dt` partitions

**Status:** accepted

## Context

Athena bills per byte scanned, and the whole dataset is time-series. CSV would
force a full scan for every query and store dates as text.

## Decision

Write parquet with ZSTD compression, partitioned as
`s3://<curated>/<layer>/<table>/dt=YYYY-MM-DD/`, and always partition-prune in
analyst queries by filtering on `dt` or `date_key`.

## Consequences

- Columnar reads mean a query touching 3 of 14 columns scans ~20% of the data.
- ZSTD cuts the demo dataset from 1.1 MB CSV to 180 KB parquet; at scale the
  ratio is typically 5-10x against CSV.
- `dt` (load date) and `date_key` (business date) are deliberately different:
  backfilling a day writes to a new `dt` partition while keeping the original
  business date, which keeps reprocessing idempotent.
- Small files are the known risk. Above ~100 MB/day, add a compaction job.
