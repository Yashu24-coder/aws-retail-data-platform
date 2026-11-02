# Data dictionary

All tables live in the `retail_platform` Glue database. Local mode exposes the
same names through DuckDB schemas `bronze`, `silver` and `gold`.

## bronze.orders

Raw as received. Every column is `string` on purpose.

| Column | Type | Description |
|---|---|---|
| `order_id` | string | Source order identifier |
| `customer_id` | string | Source customer identifier; blank in ~3% of rows |
| `order_ts` | string | Order timestamp, either `YYYY-MM-DD HH:MM:SS` or `DD/MM/YYYY HH:MM` |
| `status` | string | Free-text status, 11 observed spellings |
| `shipping_cost` | string | Shipping amount, sometimes with a thousands separator |
| `_ingest_ts` | timestamp | When the pipeline landed this row |

## silver.orders

| Column | Type | Description |
|---|---|---|
| `order_id` | string | Unique after de-duplication |
| `customer_id` | string | Non-null, non-blank |
| `order_ts` | timestamp | Parsed from either source format |
| `order_date` | date | `order_ts` truncated to the day |
| `status` | string | One of `completed`, `cancelled`, `returned`, `open`, `unknown` |
| `shipping_cost` | decimal(12,2) | Nulls coalesced to 0 |

## silver.order_items

| Column | Type | Description |
|---|---|---|
| `order_item_id` | string | Unique line identifier |
| `order_id` | string | Joins to `silver.orders` |
| `product_id` | string | Joins to `silver.products` |
| `quantity` | integer | Negative for returns |
| `unit_price` | decimal(12,2) | Currency symbol stripped |
| `discount_rate` | decimal(6,2) | `0.10` for a 10% discount |

## silver.customers

| Column | Type | Description |
|---|---|---|
| `customer_id` | string | Unique |
| `customer_name` | string | Whitespace trimmed |
| `email` | string | Lower-cased. **PII - not yet masked** |
| `country` | string | Normalised label |
| `signup_date` | date | Parsed |

## silver.products

| Column | Type | Description |
|---|---|---|
| `product_id` | string | Unique |
| `product_name` | string | Variant suffix kept (`Face Serum 2`) |
| `category` | string | One of 5 canonical categories |
| `list_price` | decimal(12,2) | Currency symbol stripped |

## gold.dim_customer

| Column | Type | Description |
|---|---|---|
| `customer_key` | integer | Surrogate key, primary key |
| `customer_id` | string | Natural key, never used as a join key in BI |
| `customer_name`, `email`, `country`, `signup_date` | | Descriptive attributes |

## gold.dim_product

| Column | Type | Description |
|---|---|---|
| `product_key` | integer | Surrogate key |
| `product_id` | string | Natural key |
| `product_name`, `category`, `list_price` | | Descriptive attributes |

## gold.dim_date

| Column | Type | Description |
|---|---|---|
| `date_key` | integer | `YYYYMMDD` |
| `date` | date | Calendar date |
| `year`, `month`, `quarter`, `day_of_week` | integer | Derived parts |
| `month_start` | date | First day of the month, for grouping |
| `year_month`, `month_name`, `day_name` | string | Display labels |
| `is_weekend` | boolean | Saturday or Sunday |

## gold.fct_order_items

Grain: one row per order line. Cancelled orders excluded.

| Column | Type | Description |
|---|---|---|
| `order_item_id` | string | Primary key |
| `date_key` | integer | FK to `dim_date` |
| `customer_key` | integer | FK to `dim_customer` |
| `product_key` | integer | FK to `dim_product` |
| `order_id` | string | Degenerate dimension, useful for drill-through |
| `status` | string | Order status at load time |
| `quantity` | integer | Negative for returns |
| `unit_price` | decimal(12,2) | Price before discount |
| `discount_rate` | decimal(6,4) | 0 to 1 |
| `gross_amount` | decimal(14,2) | `quantity * unit_price` |
| `discount_amount` | decimal(14,2) | `gross_amount * discount_rate` |
| `net_amount` | decimal(14,2) | `gross_amount - discount_amount` |
| `is_return` | boolean | True when `quantity < 0` |

## gold.mart_monthly_revenue

| Column | Type | Description |
|---|---|---|
| `month_start` | date | Month bucket |
| `orders` | bigint | Distinct orders in the month |
| `line_items` | bigint | Fact rows in the month |
| `net_revenue` | decimal | Sum of `net_amount` |
| `discount_given` | decimal | Sum of `discount_amount` |
| `avg_order_value` | decimal | `net_revenue / orders` |

## gold.mart_category_performance

| Column | Type | Description |
|---|---|---|
| `category` | string | Product category |
| `line_items` | bigint | Fact rows |
| `net_revenue` | decimal | Sum of `net_amount` |
| `avg_discount_pct` | decimal | Mean discount, as a percentage |
| `return_rate_pct` | decimal | Share of lines that are returns |
| `revenue_per_product` | decimal | `net_revenue / distinct products` |
