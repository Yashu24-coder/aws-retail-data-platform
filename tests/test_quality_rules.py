"""The quality contract must load, and its SQL must actually run."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
RULES = yaml.safe_load((REPO / "quality" / "checks.yml").read_text(encoding="utf-8"))["checks"]


def test_rules_have_required_fields():
    for rule in RULES:
        for field in ("name", "sql", "expect", "threshold", "severity"):
            assert field in rule, f"{rule.get('name')} missing {field}"
        assert rule["expect"] in {"eq", "gte", "lte", "gt", "lt"}
        assert rule["severity"] in {"error", "warn"}


def test_rule_names_unique():
    names = [r["name"] for r in RULES]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("rule", RULES, ids=[r["name"] for r in RULES])
def test_rule_sql_is_valid(rule):
    """Catches typos in table or column names without needing a full run."""
    connection = duckdb.connect()
    for schema in ("bronze", "silver", "gold"):
        connection.execute(f"CREATE SCHEMA {schema}")
    for schema, table in [
        ("silver", "orders"), ("silver", "order_items"),
        ("gold", "fct_order_items"), ("gold", "dim_product"),
        ("gold", "mart_monthly_revenue"),
    ]:
        connection.execute(f"CREATE TABLE {schema}.{table} AS SELECT * FROM (SELECT 1) t(x)")
    connection.execute("ALTER TABLE silver.orders ADD COLUMN order_id INTEGER")
    connection.execute("ALTER TABLE silver.orders ADD COLUMN order_date DATE")
    connection.execute("ALTER TABLE silver.orders ADD COLUMN customer_id VARCHAR")
    connection.execute("ALTER TABLE silver.order_items ADD COLUMN unit_price DECIMAL(10,2)")
    connection.execute("ALTER TABLE silver.order_items ADD COLUMN discount_rate DECIMAL(6,2)")
    connection.execute("ALTER TABLE gold.fct_order_items ADD COLUMN customer_key INTEGER")
    connection.execute("ALTER TABLE gold.fct_order_items ADD COLUMN product_key INTEGER")
    connection.execute("ALTER TABLE gold.fct_order_items ADD COLUMN net_amount DECIMAL(10,2)")
    connection.execute("ALTER TABLE gold.fct_order_items ADD COLUMN gross_amount DECIMAL(10,2)")
    connection.execute("ALTER TABLE gold.fct_order_items ADD COLUMN discount_amount DECIMAL(10,2)")
    connection.execute("ALTER TABLE gold.dim_product ADD COLUMN category VARCHAR")
    try:
        connection.execute(rule["sql"]).fetchone()
    finally:
        connection.close()
