-- Category mart: revenue, discount depth and return rate side by side.

SELECT
    dp.category,
    count(*)                                                    AS line_items,
    round(sum(f.net_amount), 2)                                 AS net_revenue,
    round(avg(f.discount_rate) * 100, 2)                        AS avg_discount_pct,
    round(100.0 * sum(CASE WHEN f.is_return THEN 1 ELSE 0 END) / count(*), 2) AS return_rate_pct,
    round(sum(f.net_amount) / count(DISTINCT dp.product_key), 2) AS revenue_per_product
FROM gold.fct_order_items f
JOIN gold.dim_product dp
  ON dp.product_key = f.product_key
GROUP BY dp.category
ORDER BY net_revenue DESC
