"""Integration tests for orchestrator.run_flow.

These mock the actual Yosys subprocess call so they run in any environment
(no EDA tools required) while still exercising the real config-loading,
template-rendering, and report-parsing wiring together. The e2e test in
test_e2e.py additionally runs the real tool.
"""
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from orchestrator.run_flow import FlowError, run_variant

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "flow" / "configs"

FAKE_STAT_REPORT = """
=== picorv32 ===

   Number of wires:              100
   Number of wire bits:          200
   Number of cells:               50
"""


def _fake_completed_process(returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["yosys"], returncode=returncode, stdout="", stderr=stderr)


class TestRunVariantIntegration:
    def test_run_variant_parses_successful_yosys_output(self, tmp_path, monkeypatch):
        # Patch run_yosys to fake success and write the report file it would
        # normally produce, so we test config -> template -> parse end to end
        # without invoking a real tool.
        def fake_run_yosys(script_text: str):
            # Extract the report path the orchestrator asked Yosys to write to.
            for line in script_text.splitlines():
                if line.strip().startswith("tee -o"):
                    report_path = Path(line.split()[2])
                    report_path.write_text(FAKE_STAT_REPORT)
            return _fake_completed_process(returncode=0)

        monkeypatch.setattr("orchestrator.run_flow.run_yosys", fake_run_yosys)

        qor = run_variant(CONFIGS_DIR / "minimal.json")

        assert qor.variant_name == "minimal"
        assert qor.num_cells == 50
        assert qor.num_wires == 100

    def test_run_variant_raises_flow_error_on_nonzero_exit(self, monkeypatch):
        def fake_run_yosys(script_text: str):
            return _fake_completed_process(returncode=1, stderr="ERROR: syntax error")

        monkeypatch.setattr("orchestrator.run_flow.run_yosys", fake_run_yosys)

        with pytest.raises(FlowError, match="Yosys failed"):
            run_variant(CONFIGS_DIR / "minimal.json")

    def test_run_variant_raises_flow_error_if_report_missing(self, monkeypatch):
        def fake_run_yosys(script_text: str):
            # Succeeds but never actually writes the report file.
            return _fake_completed_process(returncode=0)

        monkeypatch.setattr("orchestrator.run_flow.run_yosys", fake_run_yosys)

        with pytest.raises(FlowError, match="was not produced"):
            run_variant(CONFIGS_DIR / "minimal.json")
