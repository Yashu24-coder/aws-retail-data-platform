"""Glue PySpark job: silver -> gold.

Builds the star schema and the two marts, then registers the new partitions in
the Glue catalog so Athena sees them immediately.
"""

import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import Window
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME", "glue_database", "curated_bucket"])

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

DATABASE = args["glue_database"]
CURATED = args["curated_bucket"]


def read_silver(table: str):
    return glue_context.create_dynamic_frame.from_catalog(
        database=DATABASE, table_name=f"silver_{table}", transformation_ctx=f"src_{table}"
    ).toDF()


def write_gold(df, table: str):
    df.write.mode("overwrite").option("compression", "zstd").format("parquet").save(
        f"s3://{CURATED}/gold/{table}/"
    )
    print(f"wrote gold.{table}: {df.count()} rows")


customers = read_silver("customers")
products = read_silver("products")
orders = read_silver("orders")
items = read_silver("order_items")

# ------------------------------------------------------------- dimensions
w = Window.orderBy("customer_id")
dim_customer = customers.select(
    F.row_number().over(w).alias("customer_key"),
    "customer_id", "customer_name", "email", "country", "signup_date",
)

w = Window.orderBy("product_id")
dim_product = products.select(
    F.row_number().over(w).alias("product_key"),
    "product_id", "product_name", "category", "list_price",
)

bounds = orders.select(F.min("order_date").alias("lo"), F.max("order_date").alias("hi")).first()
dim_date = (
    spark.sql(
        "SELECT explode(sequence("
        f"to_date('{bounds.lo}'), to_date('{bounds.hi}'), interval 1 day)) AS d"
    )
    .select(
        F.date_format("d", "yyyyMMdd").cast("int").alias("date_key"),
        F.col("d").alias("date"),
        F.year("d").alias("year"),
        F.month("d").alias("month"),
        F.trunc("d", "month").cast("date").alias("month_start"),
        F.date_format("d", "yyyy-MM").alias("year_month"),
        F.date_format("d", "MMMM").alias("month_name"),
        F.quarter("d").alias("quarter"),
        F.dayofweek("d").alias("day_of_week"),
        F.date_format("d", "EEEE").alias("day_name"),
        F.dayofweek("d").isin(0, 6).alias("is_weekend"),
    )
)

write_gold(dim_customer, "dim_customer")
write_gold(dim_product, "dim_product")
write_gold(dim_date, "dim_date")

# ------------------------------------------------------------------- fact
fact = (
    items.join(orders, "order_id")
    .join(dim_customer.select("customer_key", "customer_id"), "customer_id", "left")
    .join(dim_product.select("product_key", "product_id"), "product_id", "left")
    .filter(F.col("status") != "cancelled")
    .select(
        "order_item_id",
        F.date_format("order_date", "yyyyMMdd").cast("int").alias("date_key"),
        "customer_key", "product_key", "order_id", "status",
        "quantity", "unit_price", "discount_rate",
        F.round(F.col("quantity") * F.col("unit_price"), 2).alias("gross_amount"),
        F.round(F.col("quantity") * F.col("unit_price") * F.col("discount_rate"), 2).alias(
            "discount_amount"),
        F.round(F.col("quantity") * F.col("unit_price") * (1 - F.col("discount_rate")), 2).alias(
            "net_amount"),
        (F.col("quantity") < 0).alias("is_return"),
    )
)

write_gold(fact, "fct_order_items")

# ------------------------------------------------------------------ marts
monthly = (
    fact.join(dim_date.select("date_key", "month_start"), "date_key")
    .groupBy("month_start")
    .agg(
        F.countDistinct("order_id").alias("orders"),
        F.count("*").alias("line_items"),
        F.round(F.sum("net_amount"), 2).alias("net_revenue"),
        F.round(F.sum("discount_amount"), 2).alias("discount_given"),
        F.round(F.sum("net_amount") / F.countDistinct("order_id"), 2).alias("avg_order_value"),
    )
    .orderBy("month_start")
)

category = (
    fact.join(dim_product.select("product_key", "category"), "product_key")
    .groupBy("category")
    .agg(
        F.count("*").alias("line_items"),
        F.round(F.sum("net_amount"), 2).alias("net_revenue"),
        F.round(F.avg("discount_rate") * 100, 2).alias("avg_discount_pct"),
        F.round(100 * F.sum(F.col("is_return").cast("int")) / F.count("*"), 2).alias(
            "return_rate_pct"),
        F.round(F.sum("net_amount") / F.countDistinct("product_key"), 2).alias(
            "revenue_per_product"),
    )
)

write_gold(monthly, "mart_monthly_revenue")
write_gold(category, "mart_category_performance")

job.commit()
