# Runbook

What to do when the pipeline is not green. Written for whoever is on call,
including future me.

## Daily checks

1. Open the `pipeline-smoke` job in GitHub Actions - it should be green.
2. `reports/data_quality.md` should read 12 / 12.
3. In CloudWatch, `retail-platform-*` alarms should be in `OK`.

## Re-run a day

```bash
# local
PLATFORM_MODE=local python -m retail_platform.cli run-all

# AWS: re-run the Glue job for one date
aws glue start-job-run --job-name retail-platform-bronze-to-silver \
  --arguments '{"--dt":"2026-10-31"}'
```

Both paths are idempotent. Locally the day's parquet is overwritten; in Redshift
the `MERGE` on `order_item_id` prevents double counting. Re-running is always
safe - that is the whole point of the design.

## Backfill 30 days

```bash
for d in $(seq 0 29); do
  dt=$(date -d "-${d} day" +%F)
  aws glue start-job-run --job-name retail-platform-bronze-to-silver \
    --arguments "{\"--dt\":\"${dt}\"}"
done
```

Glue job bookmarks mean a backfill only reprocesses the partitions you name.

## Common failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `silver_orders_not_empty` fails | extract did not land today | check `aws s3 ls s3://<raw>/bronze/orders/`, re-run ingest |
| `fct_no_orphan_customer` fails | customer extract arrived after the order extract | run silver for customers first, then orders, then gold |
| `mart_months_covered` fails | only a partial month loaded | backfill the missing partitions |
| Glue `OutOfMemoryError` | worker count too low for the partition size | raise `glue_number_of_workers` to 10, re-run |
| Athena `HIVE_PARTITION_SCHEMA_MISMATCH` | a source column changed type | re-run the crawler, then re-run silver |
| Redshift `COPY` fails with `Spectrum scan error` | gold prefix has a zero-byte file | delete the `_SUCCESS` marker or empty part file, re-run COPY |
| `ModuleNotFoundError: duckdb` | dependencies not installed | `pip install -r requirements-dev.txt` |

## Rollback

Gold and silver are derived data - delete and rebuild rather than restore:

```bash
aws s3 rm s3://<curated>/gold/ --recursive
aws glue start-job-run --job-name retail-platform-silver-to-gold
```

Bronze is the only layer worth backing up; versioning is enabled on the bucket.

## Cost guardrails

- Athena workgroup is capped at **1 GB scanned per query** - a runaway `SELECT *`
  fails instead of billing.
- Redshift Serverless is behind `create_redshift = false` by default.
- Raw bucket expires objects after 400 days; curated transitions to Standard-IA
  at 90 days.
