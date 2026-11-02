"""Silver models must remove exactly the defects we injected."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _build(con, model: str, schema: str = "silver") -> None:
    sql = (REPO / "sql" / schema / f"{model}.sql").read_text(encoding="utf-8")
    con.execute(f"CREATE OR REPLACE VIEW {schema}.{model} AS {sql.strip().rstrip(';')}")


def test_orders_deduplicated_and_typed(seeded):
    _build(seeded, "orders")
    rows = seeded.execute(
        "SELECT order_id, status, order_date FROM silver.orders ORDER BY order_id"
    ).fetchall()
    assert [r[0] for r in rows] == ["O1", "O2"], "duplicate O1 kept or bad rows survived"
    assert rows[0][1] == "completed"
    assert rows[1][1] == "cancelled", "status casing not normalised"
    assert str(rows[1][2]) == "2026-02-07", "dd/mm/yyyy format not parsed"


def test_blank_customer_and_bad_date_dropped(seeded):
    _build(seeded, "orders")
    count = seeded.execute("SELECT count(*) FROM silver.orders").fetchone()[0]
    assert count == 2, "rows with blank customer or unparseable date should be dropped"


def test_items_numeric_cast(seeded):
    _build(seeded, "order_items")
    rows = seeded.execute(
        "SELECT order_item_id, quantity, unit_price, discount_rate "
        "FROM silver.order_items ORDER BY order_item_id"
    ).fetchall()
    assert len(rows) == 3, "duplicate item I1 not collapsed"
    assert rows[0][2] == 100.00
    assert float(rows[0][3]) == 0.10, "percent string not converted to a rate"
    assert rows[1][1] == -1, "returns must keep their negative quantity"


def test_customers_normalised(seeded):
    _build(seeded, "customers")
    row = seeded.execute(
        "SELECT customer_name, email, country FROM silver.customers WHERE customer_id = 'C1'"
    ).fetchone()
    assert row[0] == "Ananya Sharma", "surrounding whitespace not trimmed"
    assert row[1] == "ananya@example.com", "email not lower-cased"
