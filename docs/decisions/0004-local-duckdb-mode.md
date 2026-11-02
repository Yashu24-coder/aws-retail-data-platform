# 0004 - Local mode on DuckDB

**Status:** accepted

## Context

A portfolio repository that only runs in someone else's AWS account cannot be
reviewed. A mock that fakes the pipeline proves nothing about the SQL.

## Decision

Run the real SQL against real parquet locally, using DuckDB as the query engine
and the local filesystem in place of S3. The `Storage` interface swaps
`LocalStorage` for `S3Storage` on a single environment variable.

## Consequences

- `make run` works on a clean machine in seconds, with no credentials, so a
  reviewer can see the pipeline end to end.
- The same `sql/` files run in both modes: if a query works locally it works in
  Athena, apart from the dialect differences listed in 0003.
- DuckDB is not Spark. Window functions and ANSI joins behave the same, but
  shuffle behaviour, broadcast joins and skew are only exercised in the Glue
  jobs - so the local run is a correctness check, not a performance check.
