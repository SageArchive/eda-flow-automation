"""End-to-end test: runs the real Yosys toolchain against real RTL.

Skipped automatically if `yosys` isn't on PATH (e.g. a bare dev machine
without the CAD tools installed), so the rest of the test suite stays fast
and portable. CI installs Yosys, so this runs there.
"""
import shutil
from pathlib import Path

import pytest

from orchestrator.run_flow import run_variant
from scheduler.job_scheduler import discover_configs, run_all

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "flow" / "configs"

requires_yosys = pytest.mark.skipif(
    shutil.which("yosys") is None, reason="yosys not installed on this machine"
)


@requires_yosys
def test_minimal_variant_synthesizes_successfully():
    qor = run_variant(CONFIGS_DIR / "minimal.json")

    # PicoRV32 is a few thousand gates at minimum; a loose bound keeps this
    # test stable across Yosys/ABC version upgrades while still catching a
    # badly broken flow (e.g. synthesizing the wrong/empty design).
    assert 5_000 < qor.num_cells < 50_000


@requires_yosys
def test_full_featured_variant_has_more_cells_than_minimal():
    """Sanity check: enabling MUL/DIV/barrel-shifter/IRQ should grow the design."""
    minimal_qor = run_variant(CONFIGS_DIR / "minimal.json")
    full_qor = run_variant(CONFIGS_DIR / "full_featured.json")

    assert full_qor.num_cells > minimal_qor.num_cells


@requires_yosys
def test_scheduler_runs_all_configs_in_parallel():
    configs = discover_configs(CONFIGS_DIR)
    results = run_all(CONFIGS_DIR, max_workers=len(configs))

    assert len(results) == len(configs)
    assert all(error is None for _, _, error in results), [
        (name, error) for name, _, error in results if error
    ]
