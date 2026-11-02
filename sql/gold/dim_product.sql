-- Product dimension with an integer surrogate key.

SELECT
    row_number() OVER (ORDER BY product_id) AS product_key,
    product_id,
    product_name,
    category,
    list_price
FROM silver.products
