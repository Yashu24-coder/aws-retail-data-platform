-- Clean the raw order extract.
-- Fixes: two date formats in one column, 11 spellings of 5 statuses,
-- duplicate rows from a re-run export, blank customer keys.

WITH parsed AS (
    SELECT
        trim(order_id)                                     AS order_id,
        trim(customer_id)                                  AS customer_id,
        coalesce(
            try_strptime(trim(order_ts), '%Y-%m-%d %H:%M:%S'),
            try_strptime(trim(order_ts), '%d/%m/%Y %H:%M'),
            try_strptime(trim(order_ts), '%Y/%m/%d')
        )::TIMESTAMP                                       AS order_ts,
        upper(trim(status))                                AS status_raw,
        try_cast(replace(trim(shipping_cost), ',', '') AS DECIMAL(12, 2)) AS shipping_cost,
        _ingest_ts
    FROM bronze.orders
),

standardised AS (
    SELECT
        order_id,
        customer_id,
        order_ts,
        CAST(order_ts AS DATE)                             AS order_date,
        CASE
            WHEN status_raw IN ('COMPLETE', 'COMPLETED', 'SHIPPED', 'DELIVERED') THEN 'completed'
            WHEN status_raw IN ('CANCEL', 'CANCELLED')                           THEN 'cancelled'
            WHEN status_raw IN ('RETURN', 'RETURNED')                            THEN 'returned'
            WHEN status_raw IN ('PENDING', 'PROCESSING')                         THEN 'open'
            ELSE 'unknown'
        END                                                AS status,
        coalesce(shipping_cost, 0)                         AS shipping_cost,
        _ingest_ts
    FROM parsed
    WHERE order_id IS NOT NULL
      AND order_ts IS NOT NULL
      AND customer_id IS NOT NULL
      AND customer_id <> ''
)

SELECT *
FROM standardised
QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY _ingest_ts DESC) = 1
