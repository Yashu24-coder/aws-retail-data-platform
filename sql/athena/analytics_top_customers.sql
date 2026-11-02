-- Top 20 customers by net revenue, last 90 days.
-- Runs unchanged in Athena against the gold layer.

SELECT
    dc.customer_id,
    dc.customer_name,
    dc.country,
    count(DISTINCT f.order_id)  AS orders,
    round(sum(f.net_amount), 2) AS net_revenue
FROM retail_platform.gold_fct_order_items f
JOIN retail_platform.gold_dim_customer dc
  ON dc.customer_key = f.customer_key
WHERE f.date_key >= CAST(date_format(current_date - INTERVAL '90' DAY, '%Y%m%d') AS integer)
GROUP BY 1, 2, 3
ORDER BY net_revenue DESC
LIMIT 20;
