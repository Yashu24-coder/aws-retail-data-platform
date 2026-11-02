-- Monthly revenue mart: what a category manager opens on a Monday.

SELECT
    dd.month_start,
    count(DISTINCT f.order_id)                                   AS orders,
    count(*)                                                     AS line_items,
    round(sum(f.net_amount), 2)                                  AS net_revenue,
    round(sum(f.discount_amount), 2)                             AS discount_given,
    round(sum(f.net_amount) / nullif(count(DISTINCT f.order_id), 0), 2) AS avg_order_value
FROM gold.fct_order_items f
JOIN gold.dim_date dd
  ON dd.date_key = f.date_key
GROUP BY dd.month_start
ORDER BY dd.month_start
