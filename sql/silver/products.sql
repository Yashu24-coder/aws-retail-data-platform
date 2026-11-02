-- Clean products: category casing, price currency symbols, duplicate ids.

SELECT
    trim(product_id)                        AS product_id,
    trim(product_name)                      AS product_name,
    CASE
        WHEN upper(trim(category)) LIKE 'ELECTRONIC%' THEN 'Electronics'
        WHEN upper(trim(category)) LIKE 'HOME%'       THEN 'Home & Kitchen'
        WHEN upper(trim(category)) LIKE 'FASHION%'    THEN 'Fashion'
        WHEN upper(trim(category)) LIKE 'BEAUTY%'     THEN 'Beauty'
        WHEN upper(trim(category)) LIKE 'SPORT%'      THEN 'Sports'
        ELSE 'Uncategorised'
    END                                     AS category,
    try_cast(replace(trim(list_price), '$', '') AS DECIMAL(12, 2)) AS list_price,
    _ingest_ts
FROM bronze.products
WHERE product_id IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY product_id ORDER BY _ingest_ts DESC) = 1
