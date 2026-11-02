"""Generate a realistic, deliberately messy e-commerce source extract.

Real source systems are never clean. This generator reproduces the defects you
actually meet: duplicate rows from a re-run export, two date formats in the same
column, currency symbols inside numeric fields, trailing spaces, inconsistent
casing, negative quantities for returns, and nulls where a join key is missing.

The defects are intentional and fixed by the silver models - see
docs/data_quality.md for the expected counts.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

CATEGORIES = {
    "Electronics": ["Wireless Earbuds", "USB-C Hub", "Bluetooth Speaker", "Smart Watch"],
    "Home & Kitchen": ["Steel Cookware Set", "Ceramic Mug Set", "Air Fryer", "Water Purifier"],
    "Fashion": ["Cotton Kurta", "Running Shoes", "Leather Wallet", "Denim Jacket"],
    "Beauty": ["Face Serum", "Sunscreen SPF50", "Hair Oil", "Lip Balm"],
    "Sports": ["Yoga Mat", "Cricket Bat", "Dumbbell Set", "Cycling Helmet"],
}
COUNTRIES = ["India", "India", "India", "United States", "United Kingdom", "UAE", "Singapore"]
FIRST = ["Ananya", "Rohit", "Priya", "Karthik", "Meera", "Arjun", "Divya", "Vikram", "Sneha",
         "Rahul", "Fatima", "Joseph", "Nisha", "Aditya", "Lakshmi", "Sameer"]
LAST = ["Sharma", "Reddy", "Iyer", "Patel", "Nair", "Menon", "Gupta", "Rao", "Khan", "Thomas",
        "Verma", "Joshi", "Pillai", "Das"]
STATUSES = ["COMPLETE", "complete", "Completed", "SHIPPED", "delivered", "PENDING", "processing",
            "CANCELLED", "cancel", "RETURNED", "return"]


def _date_pair(ts: datetime, rng: random.Random) -> str:
    """Return one of two date formats - the source team changed format mid-year."""
    if rng.random() < 0.22:
        return ts.strftime("%d/%m/%Y %H:%M")
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def generate(out_dir: Path, seed: int = 42, days: int = 420) -> dict[str, int]:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    end = datetime(2026, 10, 31, 18, 0, 0)
    start = end - timedelta(days=days)

    # --- customers ---------------------------------------------------------
    customers = []
    for i in range(1, 421):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        name = f"{first} {last}"
        if rng.random() < 0.06:
            name = f"  {name} "
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        if rng.random() < 0.05:
            email = email.upper()
        customers.append({
            "customer_id": f"C{i:05d}",
            "customer_name": name,
            "email": email,
            "country": rng.choice(COUNTRIES),
            "signup_date": (start + timedelta(days=rng.randint(0, days - 30))).strftime("%Y-%m-%d"),
        })

    # --- products ----------------------------------------------------------
    products = []
    pid = 1
    for category, names in CATEGORIES.items():
        for name in names:
            for variant in range(1, 3):
                base = rng.choice([299, 499, 899, 1299, 1999, 3499, 4999, 7999])
                label = f"{name} {variant}" if variant > 1 else name
                products.append({
                    "product_id": f"P{pid:04d}",
                    "product_name": label,
                    "category": category.upper() if rng.random() < 0.15 else category,
                    "list_price": f"${base}.00" if rng.random() < 0.18 else f"{base}.00",
                })
                pid += 1

    # --- orders and items --------------------------------------------------
    orders, items = [], []
    item_id = 1
    for n in range(1, 1501):
        order_id = f"O{n:06d}"
        ts = start + timedelta(
            minutes=rng.randint(0, days * 24 * 60),
            seconds=rng.randint(0, 59),
        )
        customer = rng.choice(customers)
        customer_id = customer["customer_id"]
        if rng.random() < 0.03:                     # missing join key
            customer_id = ""
        status = rng.choice(STATUSES)
        shipping = f"{rng.choice([0, 49, 79, 99, 149])}.00"
        if rng.random() < 0.04:
            shipping = f"{shipping[:-3]},00"         # thousands separator defect

        orders.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "order_ts": _date_pair(ts, rng),
            "status": status,
            "shipping_cost": shipping,
        })

        for _ in range(rng.randint(1, 4)):
            product = rng.choice(products)
            qty = rng.randint(1, 3)
            if status.upper().startswith("RETURN") and rng.random() < 0.5:
                qty = -qty
            price = float(product["list_price"].replace("$", ""))
            discount = rng.choice([0, 0, 0, 5, 10, 15, 20, 25, 30, 40])
            items.append({
                "order_item_id": f"I{item_id:07d}",
                "order_id": order_id,
                "product_id": product["product_id"],
                "quantity": str(qty),
                "unit_price": f"{price:.2f}",
                "discount_pct": f"{discount}%",
            })
            item_id += 1

    # --- inject duplicate rows (a re-run export) ---------------------------
    for _ in range(35):
        orders.append(dict(rng.choice(orders)))
    for _ in range(60):
        items.append(dict(rng.choice(items)))

    rng.shuffle(orders)

    def write(name: str, rows: list[dict], fields: list[str]) -> None:
        with (out_dir / name).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    write("customers.csv", customers, list(customers[0].keys()))
    write("products.csv", products, list(products[0].keys()))
    write("orders.csv", orders, list(orders[0].keys()))
    write("order_items.csv", items, list(items[0].keys()))

    return {
        "customers": len(customers),
        "products": len(products),
        "orders": len(orders),
        "order_items": len(items),
    }
