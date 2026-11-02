-- Idempotent daily load: stage, then MERGE so a re-run of the same partition
-- cannot double-count revenue. This is the pattern the local pipeline emulates
-- with an overwrite of the day's partition.

CREATE TEMP TABLE stage_fct_order_items (LIKE gold.fct_order_items);

COPY stage_fct_order_items
FROM 's3://retail-platform-curated/gold/fct_order_items/dt=2026-10-31/'
IAM_ROLE 'arn:aws:iam::ACCOUNT_ID:role/retail-platform-redshift-loader'
FORMAT AS PARQUET;

BEGIN;

DELETE FROM gold.fct_order_items
USING stage_fct_order_items s
WHERE gold.fct_order_items.order_item_id = s.order_item_id;

INSERT INTO gold.fct_order_items SELECT * FROM stage_fct_order_items;

COMMIT;

ANALYZE gold.fct_order_items;
