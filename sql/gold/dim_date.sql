-- Calendar dimension covering the full order history, so BI tools can
-- slice by month, quarter and weekday without date arithmetic.

WITH bounds AS (
    SELECT min(order_date) AS lo, max(order_date) AS hi FROM silver.orders
),
days AS (
    SELECT unnest(generate_series(lo, hi, INTERVAL 1 DAY))::DATE AS d FROM bounds
)
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key,
    d                                      AS date,
    year(d)                                AS year,
    month(d)                               AS month,
    CAST(date_trunc('month', d) AS DATE)   AS month_start,
    strftime(d, '%Y-%m')                   AS year_month,
    strftime(d, '%B')                      AS month_name,
    quarter(d)                             AS quarter,
    dayofweek(d)                           AS day_of_week,
    strftime(d, '%A')                      AS day_name,
    CASE WHEN dayofweek(d) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend
FROM days
