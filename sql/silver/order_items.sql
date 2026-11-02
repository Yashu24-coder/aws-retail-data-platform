-- Clean the order line extract: numeric casts, percent strings to decimals,
-- duplicate line ids collapsed.

SELECT
    trim(order_item_id)                                        AS order_item_id,
    trim(order_id)                                             AS order_id,
    trim(product_id)                                           AS product_id,
    try_cast(trim(quantity) AS INTEGER)                        AS quantity,
    try_cast(replace(trim(unit_price), '$', '') AS DECIMAL(12, 2)) AS unit_price,
    try_cast(replace(trim(discount_pct), '%', '') AS DECIMAL(6, 2)) / 100.0 AS discount_rate,
    _ingest_ts
FROM bronze.order_items
WHERE order_item_id IS NOT NULL
  AND order_id IS NOT NULL
  AND try_cast(trim(quantity) AS INTEGER) IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY order_item_id ORDER BY _ingest_ts DESC) = 1
