# Cost

## Local mode

Rs. 0. DuckDB, local parquet and matplotlib. Nothing leaves the machine.

## AWS mode, monthly estimate

Assumes one daily run, ~5,800 rows growing 20% a month, and one analyst
querying a few times a day. Prices are `ap-south-1` on-demand, and rounded.

| Service | Configuration | Estimated monthly |
|---|---|---|
| S3 (raw + curated) | ~2 GB, versioning, ZSTD parquet | Rs. 5 |
| Glue jobs | 2 jobs x 2 DPU-hours x 30 days | Rs. 900 |
| Glue crawler | 1 run/day, 1 DPU-hour | Rs. 450 |
| Athena | ~50 queries x 20 MB scanned | Rs. 20 |
| CloudWatch | 3 alarms, minimal logs | Rs. 60 |
| Redshift Serverless | **8 RPU x 730 hours if left running** | Rs. 22,000 |
| **Total without Redshift** | | **~Rs. 1,450** |
| **Total with Redshift left on** | | **~Rs. 23,500** |

## The one rule

Redshift Serverless bills from creation, not from first query. Keep
`create_redshift = false` and turn it on only for a demo window:

```bash
terraform apply -var="create_redshift=true"
# demo
terraform apply -var="create_redshift=false"
```

Free-tier notes: Glue has no free tier beyond the first million catalog objects;
S3 gives 5 GB for 12 months on a new account; Athena charges $5 per TB scanned,
which is where the 1 GB per-query cap pays for itself.

## What would change the numbers at scale

- 100x data volume: Glue dominates (~Rs. 90,000/month) and the argument for
  provisioned Redshift or Athena-only starts.
- Daily queries from 1 analyst to 30: Athena stays cheap; move to Redshift once
  dashboards need sub-second response.
