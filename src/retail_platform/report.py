"""Build the charts and the run summary that the README displays.

Every number in the README comes from reports/run_summary.json, which is written
by an actual pipeline run - nothing is typed by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .config import Settings  # noqa: E402
from .logging_setup import get_logger  # noqa: E402
from .query.engine import DuckDBEngine  # noqa: E402

log = get_logger("report")

INK = "#1F3552"
ACCENT = "#0F6B63"
GREY = "#8894A0"
GRID = "#DDE3E9"


def _style(ax) -> None:
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=GREY, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def monthly_revenue(engine: DuckDBEngine, out: Path) -> None:
    df = engine.sql("""
        SELECT month_start, net_revenue, orders
        FROM gold.mart_monthly_revenue
        ORDER BY month_start
    """)
    fig, ax = plt.subplots(figsize=(8.4, 3.6), dpi=200)
    _style(ax)
    lakh = df["net_revenue"] / 100_000
    ax.plot(df["month_start"], lakh, color=ACCENT, linewidth=2.2, marker="o", markersize=3.4)
    ax.fill_between(df["month_start"], lakh, color=ACCENT, alpha=0.10)
    ax.set_title("Net revenue by month (Rs. lakh)", color=INK, fontsize=11,
                 loc="left", pad=10, fontweight="bold")
    ax.set_ylabel("Rs. lakh", color=GREY, fontsize=9)
    fig.autofmt_xdate(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(out / "monthly_revenue.png", facecolor="white")
    plt.close(fig)


def category_performance(engine: DuckDBEngine, out: Path) -> None:
    df = engine.sql("""
        SELECT category, net_revenue, return_rate_pct
        FROM gold.mart_category_performance
        ORDER BY net_revenue DESC
    """)
    fig, ax = plt.subplots(figsize=(8.4, 3.4), dpi=200)
    _style(ax)
    lakh = df["net_revenue"] / 100_000
    ax.barh(df["category"][::-1], lakh[::-1], color=INK, height=0.6)
    for y, (value, rate) in enumerate(
            zip(lakh[::-1], df["return_rate_pct"][::-1], strict=True)
    ):
        ax.text(value + lakh.max() * 0.01, y, f"Rs. {value:,.1f}L   returns {rate:.1f}%",
                va="center", fontsize=8.4, color=GREY)
    ax.set_xlim(0, lakh.max() * 1.34)
    ax.set_title("Net revenue and return rate by category", color=INK, fontsize=11,
                 loc="left", pad=10, fontweight="bold")
    ax.xaxis.grid(True, color=GRID, linewidth=0.7)
    ax.yaxis.grid(False)
    fig.tight_layout()
    fig.savefig(out / "category_performance.png", facecolor="white")
    plt.close(fig)


def quality_chart(results: list[dict], out: Path) -> None:
    names = [r["name"].replace("_", " ") for r in results]
    values = [1 if r["passed"] else 0 for r in results]
    colors = [ACCENT if v else "#B4483C" for v in values]
    fig, ax = plt.subplots(figsize=(8.4, 0.42 * len(results) + 1.1), dpi=200)
    _style(ax)
    ax.barh(names[::-1], [1] * len(names), color=colors[::-1], height=0.55)
    for y, r in enumerate(results[::-1]):
        ax.text(0.015, y, r["description"][:72], va="center", fontsize=8.2,
                color="white" if r["passed"] else "white")
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.set_title("Data quality checks (green = pass, red = fail)", color=INK,
                 fontsize=11, loc="left", pad=10, fontweight="bold")
    ax.yaxis.grid(False)
    fig.tight_layout()
    fig.savefig(out / "data_quality.png", facecolor="white")
    plt.close(fig)


def layer_sizes(engine: DuckDBEngine, out: Path) -> dict[str, int]:
    sizes = {}
    for layer, tables in {
        "bronze": ["orders", "order_items", "customers", "products"],
        "silver": ["orders", "order_items", "customers", "products"],
        "gold": ["fct_order_items", "dim_customer", "dim_product", "dim_date",
                 "mart_monthly_revenue", "mart_category_performance"],
    }.items():
        sizes[layer] = sum(
            int(engine.scalar(f"SELECT count(*) FROM {layer}.{t}")) for t in tables
        )
    return sizes


def build(engine: DuckDBEngine, cfg: Settings, out_dir: Path,
          quality_results: list[dict], timings: dict[str, float]) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    monthly_revenue(engine, out_dir)
    category_performance(engine, out_dir)
    quality_chart(quality_results, out_dir)

    summary = {
        "raw_rows": {
            t: int(engine.scalar(f"SELECT count(*) FROM bronze.{t}"))
            for t in ("orders", "order_items", "customers", "products")
        },
        "silver_rows": {
            t: int(engine.scalar(f"SELECT count(*) FROM silver.{t}"))
            for t in ("orders", "order_items", "customers", "products")
        },
        "gold_rows": layer_sizes(engine, out_dir),
        "duplicate_order_rows": int(
            engine.scalar("SELECT count(*) FROM bronze.orders")
            - engine.scalar("SELECT count(DISTINCT order_id) FROM bronze.orders")
        ),
        "duplicate_line_rows": int(
            engine.scalar("SELECT count(*) FROM bronze.order_items")
            - engine.scalar("SELECT count(DISTINCT order_item_id) FROM bronze.order_items")
        ),
        "orders_dropped_for_missing_customer": int(
            engine.scalar(
                "SELECT count(DISTINCT order_id) FROM bronze.orders "
                "WHERE customer_id IS NULL OR trim(customer_id) = ''"
            )
        ),
        "net_revenue": float(
            engine.scalar("SELECT sum(net_revenue) FROM gold.mart_monthly_revenue")
        ),
        "completed_orders": int(engine.scalar(
            "SELECT count(DISTINCT order_id) FROM gold.fct_order_items"
        )),
        "months_covered": int(engine.scalar("SELECT count(*) FROM gold.mart_monthly_revenue")),
        "date_range": list(engine.sql(
            "SELECT min(order_date) AS lo, max(order_date) AS hi FROM silver.orders"
        ).iloc[0].astype(str)),
        "quality": {
            "total": len(quality_results),
            "passed": sum(1 for r in quality_results if r["passed"]),
        },
        "timings_seconds": {k: round(v, 2) for k, v in timings.items()},
    }
    summary["runtime_seconds"] = round(sum(timings.values()), 2)
    reports_dir = cfg.local_root.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    log.info("wrote run summary: net revenue %.0f across %s months",
             summary["net_revenue"], summary["months_covered"])
    return summary
