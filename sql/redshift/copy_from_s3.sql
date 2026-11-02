-- Load gold parquet from S3 into Redshift Serverless.
-- COPY is the only supported bulk path; the IAM role is created by Terraform.

COPY gold.fct_order_items
FROM 's3://retail-platform-curated/gold/fct_order_items/'
IAM_ROLE 'arn:aws:iam::ACCOUNT_ID:role/retail-platform-redshift-loader'
FORMAT AS PARQUET
STATUPDATE ON;

SELECT COUNT(*) AS loaded_rows, MAX(date_key) AS latest_date_key
FROM gold.fct_order_items;
