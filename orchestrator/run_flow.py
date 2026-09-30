"""Orchestrate a single EDA synthesis run for one design-variant config.

Usage:
    python -m orchestrator.run_flow flow/configs/balanced.json

Responsibilities:
  1. Load a variant config (JSON: top module, clock period, param overrides)
  2. Render the Yosys script template for that variant
  3. Invoke Yosys as a subprocess
  4. Parse the resulting QoR report
  5. Return/print a structured result (consumed by scheduler/job_scheduler.py)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from jinja2 import Template

from orchestrator.qor_parser import SynthQoR, parse_yosys_stat

REPO_ROOT = Path(__file__).resolve().parent.parent
RTL_PATH = REPO_ROOT / "rtl" / "picorv32.v"
TEMPLATE_PATH = REPO_ROOT / "flow" / "templates" / "synth_template.ys"


class FlowError(RuntimeError):
    """Raised when the underlying EDA tool invocation fails."""


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return json.load(f)


def render_script(config: dict, report_path: Path) -> str:
    template = Template(TEMPLATE_PATH.read_text())
    return template.render(
        variant_name=config["variant_name"],
        rtl_path=str(RTL_PATH),
        top_module=config["top_module"],
        params=config["params"],
        report_path=str(report_path),
    )


def run_yosys(script_text: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ys", delete=False
    ) as script_file:
        script_file.write(script_text)
        script_path = script_file.name

    result = subprocess.run(
        ["yosys", "-q", "-s", script_path],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result


def run_variant(config_path: Path) -> SynthQoR:
    config = load_config(config_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = Path(tmp_dir) / f"{config['variant_name']}_stat.rpt"
        script_text = render_script(config, report_path)
        result = run_yosys(script_text)

        if result.returncode != 0:
            raise FlowError(
                f"Yosys failed for variant '{config['variant_name']}' "
                f"(exit {result.returncode}):\n{result.stderr}"
            )

        if not report_path.exists():
            raise FlowError(
                f"Expected report file was not produced: {report_path}"
            )

        report_text = report_path.read_text()

    return parse_yosys_stat(report_text, config["variant_name"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Path to a variant config JSON file")
    args = parser.parse_args()

    try:
        qor = run_variant(args.config)
    except FlowError as e:
        print(f"[run_flow] FAILED: {e}", file=sys.stderr)
        return 1

    print(json.dumps(qor.as_row(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
