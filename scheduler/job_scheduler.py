"""Parallel job scheduler for running multiple EDA flow variants at once.

Stands in for a distributed-computing job queue (e.g. Slurm/LSF, which is
what production CAD/EDA automation targets): each config file in
flow/configs/ is submitted as an independent "job", run concurrently in a
process pool, and the results are collected into a single comparison table
once every job finishes (or reported individually as they fail).

Usage:
    python -m scheduler.job_scheduler                # run all configs
    python -m scheduler.job_scheduler --workers 2     # cap parallelism
    python -m scheduler.job_scheduler --csv out.csv   # also write a CSV
"""
from __future__ import annotations

import argparse
import csv
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from orchestrator.qor_parser import SynthQoR
from orchestrator.run_flow import FlowError, run_variant

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = REPO_ROOT / "flow" / "configs"


def _run_job(config_path: Path) -> tuple[str, SynthQoR | None, str | None]:
    """Worker function — must be top-level/picklable for ProcessPoolExecutor."""
    try:
        qor = run_variant(config_path)
        return (config_path.name, qor, None)
    except FlowError as e:
        return (config_path.name, None, str(e))


def discover_configs(configs_dir: Path) -> list[Path]:
    configs = sorted(configs_dir.glob("*.json"))
    if not configs:
        raise FileNotFoundError(f"No config files found in {configs_dir}")
    return configs


def run_all(configs_dir: Path, max_workers: int | None = None) -> list[tuple[str, SynthQoR | None, str | None]]:
    configs = discover_configs(configs_dir)
    results: list[tuple[str, SynthQoR | None, str | None]] = []

    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_job, cfg): cfg for cfg in configs}
        for future in as_completed(futures):
            results.append(future.result())

    return results


def print_summary(results: list[tuple[str, SynthQoR | None, str | None]]) -> None:
    print(f"\n{'variant':<16}{'cells':>10}{'wires':>10}{'wire_bits':>12}   status")
    print("-" * 60)
    for name, qor, error in sorted(results, key=lambda r: r[0]):
        if qor is not None:
            print(f"{qor.variant_name:<16}{qor.num_cells:>10}{qor.num_wires:>10}{qor.num_wire_bits:>12}   ok")
        else:
            print(f"{name:<16}{'--':>10}{'--':>10}{'--':>12}   FAILED: {error}")


def write_csv(results: list[tuple[str, SynthQoR | None, str | None]], csv_path: Path) -> None:
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "cells", "wires", "wire_bits", "status"])
        for name, qor, error in sorted(results, key=lambda r: r[0]):
            if qor is not None:
                writer.writerow([qor.variant_name, qor.num_cells, qor.num_wires, qor.num_wire_bits, "ok"])
            else:
                writer.writerow([name, "", "", "", f"FAILED: {error}"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs-dir", type=Path, default=CONFIGS_DIR)
    parser.add_argument("--workers", type=int, default=None, help="Max parallel jobs (default: CPU count)")
    parser.add_argument("--csv", type=Path, default=None, help="Optional path to write results as CSV")
    args = parser.parse_args()

    results = run_all(args.configs_dir, max_workers=args.workers)
    print_summary(results)

    if args.csv:
        write_csv(results, args.csv)
        print(f"\nWrote {args.csv}")

    return 1 if any(error for _, _, error in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
