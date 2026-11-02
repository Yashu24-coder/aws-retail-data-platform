"""Shared fixtures: a tiny in-memory warehouse built from known bad rows."""

from __future__ import annotations

import duckdb
import pytest


@pytest.fixture()
def con():
    con = duckdb.connect()
    con.execute("CREATE SCHEMA bronze")
    con.execute("CREATE SCHEMA silver")
    con.execute("CREATE SCHEMA gold")
    con.execute("""
        CREATE TABLE bronze.orders (
            order_id VARCHAR, customer_id VARCHAR, order_ts VARCHAR,
            status VARCHAR, shipping_cost VARCHAR, _ingest_ts TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE bronze.order_items (
            order_item_id VARCHAR, order_id VARCHAR, product_id VARCHAR,
            quantity VARCHAR, unit_price VARCHAR, discount_pct VARCHAR,
            _ingest_ts TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE bronze.customers (
            customer_id VARCHAR, customer_name VARCHAR, email VARCHAR,
            country VARCHAR, signup_date VARCHAR, _ingest_ts TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE bronze.products (
            product_id VARCHAR, product_name VARCHAR, category VARCHAR,
            list_price VARCHAR, _ingest_ts TIMESTAMP
        )
    """)
    yield con
    con.close()


@pytest.fixture()
def seeded(con):
    """Two clean orders, one duplicate, one blank customer, two date formats."""
    con.execute("""
        INSERT INTO bronze.orders VALUES
          ('O1', 'C1', '2026-01-05 10:00:00', 'COMPLETE',   '49.00',  TIMESTAMP '2026-02-01'),
          ('O2', 'C2', '07/02/2026 11:30',    'cancel',     '0.00',   TIMESTAMP '2026-02-01'),
          ('O1', 'C1', '2026-01-05 10:00:00', 'complete',   '49.00',  TIMESTAMP '2026-02-02'),
          ('O3', '',   '2026-03-01 09:00:00', 'SHIPPED',    '99.00',  TIMESTAMP '2026-02-01'),
          ('O4', 'C1', 'not a date',          'PENDING',    '0.00',   TIMESTAMP '2026-02-01')
    """)
    con.execute("""
        INSERT INTO bronze.order_items VALUES
          ('I1', 'O1', 'P1', '2',  '100.00', '10%', TIMESTAMP '2026-02-01'),
          ('I2', 'O1', 'P2', '-1', '$50.00', '0%',  TIMESTAMP '2026-02-01'),
          ('I1', 'O1', 'P1', '2',  '100.00', '10%', TIMESTAMP '2026-02-02'),
          ('I3', 'O2', 'P1', '1',  '100.00', '0%',  TIMESTAMP '2026-02-01')
    """)
    con.execute("""
        INSERT INTO bronze.customers VALUES
          ('C1', '  Ananya Sharma ', 'ANANYA@Example.com', 'India', '2025-12-01',
           TIMESTAMP '2026-02-01'),
          ('C2', 'Rohit Reddy', 'rohit@example.com', 'UNITED STATES', '2025-11-01',
           TIMESTAMP '2026-02-01')
    """)
    con.execute("""
        INSERT INTO bronze.products VALUES
          ('P1', 'Earbuds', 'ELECTRONICS', '$1200.00', TIMESTAMP '2026-02-01'),
          ('P2', 'Mug Set', 'home & kitchen', '499.00', TIMESTAMP '2026-02-01')
    """)
    return con
