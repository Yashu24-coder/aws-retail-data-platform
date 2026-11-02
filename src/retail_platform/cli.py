"""Command line entry point.

    python -m retail_platform.cli run-all

Commands: generate, ingest, transform, quality, report, run-all, aws-status.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time

from .config import REPO_ROOT, settings
from .extract.generate_sources import generate
from .ingest import land, register_bronze_views
from .logging_setup import configure, get_logger
from .quality.checks import run_checks, summarise, write_report
from .query.engine import DuckDBEngine
from .transform.runner import GOLD_MODELS, SILVER_MODELS, build_layer

log = get_logger("cli")


def _engine(cfg, read_only: bool = False) -> DuckDBEngine:
    return DuckDBEngine(cfg, read_only=read_only)


def cmd_generate(cfg, args) -> int:
    counts = generate(cfg.local_root / "raw", seed=cfg.seed, days=cfg.days_of_history)
    for table, n in counts.items():
        log.info("generated %-12s %6s rows", table, n)
    return 0


def cmd_ingest(cfg, args) -> int:
    counts = land(cfg, cfg.local_root / "raw")
    log.info("bronze landed: %s rows total", sum(counts.values()))
    return 0


def cmd_transform(cfg, args) -> int:
    engine = _engine(cfg)
    register_bronze_views(engine.con, cfg)
    silver = build_layer(engine.con, cfg, "silver", SILVER_MODELS)
    gold = build_layer(engine.con, cfg, "gold", GOLD_MODELS)
    engine.close()
    log.info("silver: %s rows | gold: %s rows", sum(silver.values()), sum(gold.values()))
    return 0


def cmd_quality(cfg, args) -> int:
    engine = _engine(cfg)
    results = run_checks(engine.con, cfg)
    summary = summarise(results)
    write_report(results, cfg.local_root.parent / "reports")
    engine.close()
    log.info("quality: %s/%s passed", summary["passed"], summary["total"])
    return 0 if summary["ok"] else 1


def cmd_report(cfg, args) -> int:
    import json

    from .report import build

    engine = _engine(cfg)
    results = json.loads(
        (cfg.local_root.parent / "reports" / "data_quality.json").read_text(encoding="utf-8")
    )
    build(engine, cfg, REPO_ROOT / "docs" / "images", results, {"report": 0.0})
    engine.close()
    return 0


def cmd_run_all(cfg, args) -> int:
    timings: dict[str, float] = {}
    started = time.perf_counter()

    t = time.perf_counter()
    generate(cfg.local_root / "raw", seed=cfg.seed, days=cfg.days_of_history)
    timings["generate"] = time.perf_counter() - t

    t = time.perf_counter()
    land(cfg, cfg.local_root / "raw")
    timings["ingest"] = time.perf_counter() - t

    engine = _engine(cfg)
    register_bronze_views(engine.con, cfg)

    t = time.perf_counter()
    build_layer(engine.con, cfg, "silver", SILVER_MODELS)
    timings["silver"] = time.perf_counter() - t

    t = time.perf_counter()
    build_layer(engine.con, cfg, "gold", GOLD_MODELS)
    timings["gold"] = time.perf_counter() - t

    t = time.perf_counter()
    results = run_checks(engine.con, cfg)
    summary = summarise(results)
    write_report(results, cfg.local_root.parent / "reports")
    timings["quality"] = time.perf_counter() - t

    from dataclasses import asdict

    t = time.perf_counter()
    from .report import build

    build(engine, cfg, REPO_ROOT / "docs" / "images", [asdict(r) for r in results], timings)
    timings["report"] = time.perf_counter() - t
    engine.close()

    total = time.perf_counter() - started
    log.info("pipeline finished in %.1fs | quality %s/%s", total,
             summary["passed"], summary["total"])
    for stage, seconds in timings.items():
        log.info("  %-10s %6.2fs", stage, seconds)
    return 0 if summary["ok"] else 1


def cmd_aws_status(cfg, args) -> int:
    """Report what exists in the AWS account, without changing anything."""
    if not cfg.is_aws:
        log.error("PLATFORM_MODE is '%s'; set PLATFORM_MODE=aws to use this command", cfg.mode)
        return 2
    from .storage import get_storage

    storage = get_storage(cfg)
    keys = storage.list_keys("bronze/")
    log.info("raw bucket has %s bronze objects", len(keys))
    for key in keys[:10]:
        log.info("  %s", key)
    return 0


COMMANDS = {
    "generate": cmd_generate,
    "ingest": cmd_ingest,
    "transform": cmd_transform,
    "quality": cmd_quality,
    "report": cmd_report,
    "run-all": cmd_run_all,
    "aws-status": cmd_aws_status,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="retail_platform", description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--reset", action="store_true", help="delete the local lake first")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    configure(args.log_level)
    cfg = settings()

    if args.reset:
        for sub in ("lake", "warehouse"):
            target = cfg.local_root / sub
            if target.exists():
                shutil.rmtree(target)
        log.info("reset local lake and warehouse")

    return COMMANDS[args.command](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
