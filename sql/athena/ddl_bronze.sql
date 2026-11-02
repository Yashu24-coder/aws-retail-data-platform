-- Athena external table over the raw bronze parquet in S3.
-- The Glue crawler creates this automatically; the DDL is committed so the
-- schema is reviewable in a pull request.

CREATE EXTERNAL TABLE IF NOT EXISTS retail_platform.bronze_orders (
    order_id       string,
    customer_id    string,
    order_ts       string,
    status         string,
    shipping_cost  string,
    _ingest_ts     timestamp
)
PARTITIONED BY (dt string)
STORED AS PARQUET
LOCATION 's3://retail-platform-curated/bronze/orders/'
TBLPROPERTIES ('parquet.compression' = 'ZSTD');

MSCK REPAIR TABLE retail_platform.bronze_orders;
