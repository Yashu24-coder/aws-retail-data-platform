"""Glue PySpark job: bronze -> silver.

Mirrors sql/silver/*.sql. The SQL models are the reference implementation used
by tests and local mode; this job is the production executor. Keep them in step -
the CI smoke test compares row counts.

Job parameters:
  --JOB_NAME, --dt (optional, defaults to yesterday), --glue_database,
  --curated_bucket
"""

import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql import types as T

args = getResolvedOptions(sys.argv, ["JOB_NAME", "glue_database", "curated_bucket"])

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

DATABASE = args["glue_database"]
CURATED = args["curated_bucket"]


def read_bronze(table: str):
    return glue_context.create_dynamic_frame.from_catalog(
        database=DATABASE, table_name=f"bronze_{table}", transformation_ctx=f"src_{table}"
    ).toDF()


def write_silver(df, table: str, partition_cols=None):
    writer = (
        df.write.mode("overwrite")
        .option("compression", "zstd")
        .format("parquet")
    )
    if partition_cols:
        writer = writer.partitionBy(*partition_cols)
    writer.save(f"s3://{CURATED}/silver/{table}/")
    print(f"wrote silver.{table}: {df.count()} rows")


# ------------------------------------------------------------------ orders
orders = read_bronze("orders")

parsed_ts = F.coalesce(
    F.to_timestamp("order_ts", "yyyy-MM-dd HH:mm:ss"),
    F.to_timestamp("order_ts", "dd/MM/yyyy HH:mm"),
)

orders_silver = (
    orders.withColumn("order_id", F.trim("order_id"))
    .withColumn("customer_id", F.trim("customer_id"))
    .withColumn("order_ts", parsed_ts)
    .withColumn("status_raw", F.upper(F.trim("status")))
    .withColumn(
        "status",
        F.when(
            F.col("status_raw").isin("COMPLETE", "COMPLETED", "SHIPPED", "DELIVERED"),
            "completed",
        )
        .when(F.col("status_raw").isin("CANCEL", "CANCELLED"), "cancelled")
        .when(F.col("status_raw").isin("RETURN", "RETURNED"), "returned")
        .when(F.col("status_raw").isin("PENDING", "PROCESSING"), "open")
        .otherwise("unknown"),
    )
    .withColumn(
        "shipping_cost",
        F.coalesce(F.regexp_replace("shipping_cost", ",", "").cast(T.DecimalType(12, 2)), F.lit(0)),
    )
    .withColumn("order_date", F.to_date("order_ts"))
    .filter(
        F.col("order_id").isNotNull()
        & F.col("order_ts").isNotNull()
        & F.col("customer_id").isNotNull()
        & (F.col("customer_id") != "")
    )
)

w = F.Window.partitionBy("order_id").orderBy(F.col("_ingest_ts").desc())
orders_silver = (
    orders_silver.withColumn("_rn", F.row_number().over(w))
    .filter(F.col("_rn") == 1)
    .drop("_rn", "status_raw")
)

write_silver(orders_silver, "orders")

# -------------------------------------------------------------- order_items
items = read_bronze("order_items")
items_silver = (
    items.withColumn("order_item_id", F.trim("order_item_id"))
    .withColumn("order_id", F.trim("order_id"))
    .withColumn("product_id", F.trim("product_id"))
    .withColumn("quantity", F.trim("quantity").cast(T.IntegerType()))
    .withColumn(
        "unit_price",
        F.regexp_replace(F.trim("unit_price"), r"\$", "").cast(T.DecimalType(12, 2)),
    )
    .withColumn(
        "discount_rate",
        (F.regexp_replace(F.trim("discount_pct"), "%", "").cast(T.DecimalType(6, 2)) / 100),
    )
    .filter(F.col("quantity").isNotNull() & F.col("order_id").isNotNull())
)

w = F.Window.partitionBy("order_item_id").orderBy(F.col("_ingest_ts").desc())
items_silver = (
    items_silver.withColumn("_rn", F.row_number().over(w)).filter(F.col("_rn") == 1).drop("_rn")
)

write_silver(items_silver, "order_items")

# ---------------------------------------------------------------- customers
customers = read_bronze("customers")
customers_silver = (
    customers.withColumn("customer_id", F.trim("customer_id"))
    .withColumn("customer_name", F.trim("customer_name"))
    .withColumn("email", F.lower(F.trim("email")))
    .withColumn(
        "country",
        F.when(F.upper(F.trim("country")) == "UNITED STATES", "United States")
        .when(F.upper(F.trim("country")) == "UNITED KINGDOM", "United Kingdom")
        .when(F.upper(F.trim("country")) == "UAE", "United Arab Emirates")
        .otherwise(F.trim("country")),
    )
    .withColumn("signup_date", F.to_date("signup_date"))
    .filter(F.col("customer_id").isNotNull())
)
w = F.Window.partitionBy("customer_id").orderBy(F.col("_ingest_ts").desc())
customers_silver = (
    customers_silver.withColumn("_rn", F.row_number().over(w)).filter(F.col("_rn") == 1).drop("_rn")
)

write_silver(customers_silver, "customers")

# ----------------------------------------------------------------- products
products = read_bronze("products")
products_silver = (
    products.withColumn("product_id", F.trim("product_id"))
    .withColumn("product_name", F.trim("product_name"))
    .withColumn(
        "category",
        F.when(F.upper(F.trim("category")).startswith("ELECTRONIC"), "Electronics")
        .when(F.upper(F.trim("category")).startswith("HOME"), "Home & Kitchen")
        .when(F.upper(F.trim("category")).startswith("FASHION"), "Fashion")
        .when(F.upper(F.trim("category")).startswith("BEAUTY"), "Beauty")
        .when(F.upper(F.trim("category")).startswith("SPORT"), "Sports")
        .otherwise("Uncategorised"),
    )
    .withColumn(
        "list_price", F.regexp_replace(F.trim("list_price"), r"\$", "").cast(T.DecimalType(12, 2))
    )
    .filter(F.col("product_id").isNotNull())
)
w = F.Window.partitionBy("product_id").orderBy(F.col("_ingest_ts").desc())
products_silver = (
    products_silver.withColumn("_rn", F.row_number().over(w)).filter(F.col("_rn") == 1).drop("_rn")
)

write_silver(products_silver, "products")

job.commit()
