"""Gold layer: surrogate keys, referential integrity, revenue arithmetic."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _build_all(con) -> None:
    for model in ("customers", "products", "orders", "order_items"):
        sql = (REPO / "sql" / "silver" / f"{model}.sql").read_text(encoding="utf-8")
        con.execute(f"CREATE OR REPLACE VIEW silver.{model} AS {sql.strip().rstrip(';')}")
    for model in ("dim_customer", "dim_product", "dim_date", "fct_order_items",
                  "mart_monthly_revenue", "mart_category_performance"):
        sql = (REPO / "sql" / "gold" / f"{model}.sql").read_text(encoding="utf-8")
        con.execute(f"CREATE OR REPLACE VIEW gold.{model} AS {sql.strip().rstrip(';')}")


def test_fact_has_no_orphan_dimension_keys(seeded):
    _build_all(seeded)
    orphans = seeded.execute(
        "SELECT count(*) FROM gold.fct_order_items "
        "WHERE customer_key IS NULL OR product_key IS NULL"
    ).fetchone()[0]
    assert orphans == 0


def test_cancelled_orders_excluded_from_fact(seeded):
    _build_all(seeded)
    order_ids = {r[0] for r in seeded.execute(
        "SELECT DISTINCT order_id FROM gold.fct_order_items").fetchall()}
    assert "O2" not in order_ids, "cancelled order leaked into the fact table"


def test_net_amount_arithmetic(seeded):
    _build_all(seeded)
    rows = seeded.execute(
        "SELECT order_item_id, gross_amount, discount_amount, net_amount "
        "FROM gold.fct_order_items ORDER BY order_item_id"
    ).fetchall()
    assert len(rows) == 2
    gross, discount, net = float(rows[0][1]), float(rows[0][2]), float(rows[0][3])
    assert abs(net - (gross - discount)) < 0.01
    assert net == 180.00, "2 x 100 with a 10% discount should net 180"


def test_dim_date_covers_history(seeded):
    _build_all(seeded)
    days = seeded.execute("SELECT count(*) FROM gold.dim_date").fetchone()[0]
    assert days >= 2


def test_mart_monthly_revenue_totals(seeded):
    _build_all(seeded)
    total = seeded.execute(
        "SELECT sum(net_revenue) FROM gold.mart_monthly_revenue").fetchone()[0]
    fact_total = seeded.execute(
        "SELECT sum(net_amount) FROM gold.fct_order_items").fetchone()[0]
    assert abs(float(total) - float(fact_total)) < 0.01
