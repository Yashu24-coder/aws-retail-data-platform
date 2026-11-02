-- Order line fact at the grain of one row per order item.
-- Cancelled orders are excluded; returns are kept with a negative quantity so
-- revenue nets out without a separate refund table.

SELECT
    i.order_item_id,
    CAST(strftime(o.order_date, '%Y%m%d') AS INTEGER) AS date_key,
    dc.customer_key,
    dp.product_key,
    o.order_id,
    o.status,
    i.quantity,
    i.unit_price,
    i.discount_rate,
    round(i.quantity * i.unit_price, 2)                       AS gross_amount,
    round(i.quantity * i.unit_price * i.discount_rate, 2)     AS discount_amount,
    round(i.quantity * i.unit_price * (1 - i.discount_rate), 2) AS net_amount,
    CASE WHEN i.quantity < 0 THEN TRUE ELSE FALSE END         AS is_return
FROM silver.order_items i
JOIN silver.orders o
  ON o.order_id = i.order_id
LEFT JOIN gold.dim_customer dc
  ON dc.customer_id = o.customer_id
LEFT JOIN gold.dim_product dp
  ON dp.product_id = i.product_id
WHERE o.status <> 'cancelled'
