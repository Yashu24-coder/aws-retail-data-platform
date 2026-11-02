# 0003 - Both Athena and Redshift Serverless

**Status:** accepted

## Context

Two consumers with different needs: analysts running exploratory SQL a few times
a day, and BI dashboards that need sub-second response with concurrent users.

## Decision

Serve both from the same gold parquet. Athena reads it in place; Redshift
Serverless takes a `COPY` and serves BI.

## Consequences

- Athena needs no loading step, so a new mart is queryable the moment the job
  writes it.
- Redshift adds a load step and real cost, but gives concurrency, result caching
  and the `DISTKEY`/`SORTKEY` performance BI tools assume.
- Running both means two dialects to keep honest. `sql/gold/` is written in
  portable SQL and the two dialect-specific files are isolated in
  `sql/athena/` and `sql/redshift/`.
- If the team were Athena-only, the whole Redshift module would be deleted -
  which is why it sits behind a single `create_redshift` flag.
