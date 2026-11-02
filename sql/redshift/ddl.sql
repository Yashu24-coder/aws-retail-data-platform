-- Redshift Serverless schema for the BI layer.
-- DISTKEY on date_key keeps time-series queries on one slice; SORTKEY on
-- date_key gives zone-map pruning for the 30-day and 90-day dashboards.

CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_customer (
    customer_key   INTEGER      NOT NULL ENCODE AZ64,
    customer_id    VARCHAR(32)  NOT NULL ENCODE ZSTD,
    customer_name  VARCHAR(160)          ENCODE ZSTD,
    email          VARCHAR(200)          ENCODE ZSTD,
    country        VARCHAR(80)           ENCODE BYTEDICT,
    signup_date    DATE                  ENCODE AZ64,
    PRIMARY KEY (customer_key)
);

CREATE TABLE IF NOT EXISTS gold.dim_product (
    product_key    INTEGER      NOT NULL ENCODE AZ64,
    product_id     VARCHAR(32)  NOT NULL ENCODE ZSTD,
    product_name   VARCHAR(200)          ENCODE ZSTD,
    category       VARCHAR(80)           ENCODE BYTEDICT,
    list_price     DECIMAL(12, 2)        ENCODE AZ64,
    PRIMARY KEY (product_key)
);

CREATE TABLE IF NOT EXISTS gold.fct_order_items (
    order_item_id   VARCHAR(40)    NOT NULL ENCODE ZSTD,
    date_key        INTEGER        NOT NULL ENCODE AZ64,
    customer_key    INTEGER                 ENCODE AZ64,
    product_key     INTEGER                 ENCODE AZ64,
    order_id        VARCHAR(40)             ENCODE ZSTD,
    status          VARCHAR(20)             ENCODE BYTEDICT,
    quantity        INTEGER                 ENCODE AZ64,
    unit_price      DECIMAL(12, 2)          ENCODE AZ64,
    discount_rate   DECIMAL(6, 4)           ENCODE AZ64,
    gross_amount    DECIMAL(14, 2)          ENCODE AZ64,
    discount_amount DECIMAL(14, 2)          ENCODE AZ64,
    net_amount      DECIMAL(14, 2)          ENCODE AZ64,
    is_return       BOOLEAN                 ENCODE RAW,
    PRIMARY KEY (order_item_id)
)
DISTSTYLE KEY
DISTKEY (date_key)
COMPOUND SORTKEY (date_key, customer_key);
