-- Customer dimension with an integer surrogate key.

SELECT
    row_number() OVER (ORDER BY customer_id) AS customer_key,
    customer_id,
    customer_name,
    email,
    country,
    signup_date
FROM silver.customers
