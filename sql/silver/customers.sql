-- Clean customers: trim names, lower-case emails, standardise country labels.

SELECT
    trim(customer_id)                     AS customer_id,
    trim(customer_name)                   AS customer_name,
    lower(trim(email))                    AS email,
    CASE upper(trim(country))
        WHEN 'UNITED STATES' THEN 'United States'
        WHEN 'UNITED KINGDOM' THEN 'United Kingdom'
        WHEN 'UAE' THEN 'United Arab Emirates'
        ELSE trim(country)
    END                                   AS country,
    try_cast(trim(signup_date) AS DATE)   AS signup_date,
    _ingest_ts
FROM bronze.customers
WHERE customer_id IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY customer_id ORDER BY _ingest_ts DESC) = 1
