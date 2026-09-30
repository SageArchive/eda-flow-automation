"""Parse EDA tool reports into structured Quality-of-Results (QoR) metrics.

Currently supports Yosys `stat -width` output. The OpenROAD report parsers
(area.rpt / timing.rpt / power.rpt) are stubbed with the same interface so the
orchestrator and scheduler don't need to change when the P&R stage is wired
up against a real PDK.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SynthQoR:
    variant_name: str
    num_cells: int
    num_wires: int
    num_wire_bits: int
    cell_breakdown: dict[str, int] = field(default_factory=dict)

    def as_row(self) -> dict:
        return {
            "variant": self.variant_name,
            "cells": self.num_cells,
            "wires": self.num_wires,
            "wire_bits": self.num_wire_bits,
        }


_CELL_LINE_RE = re.compile(r"^\s*\$?[\w$]+\s+\d+\s*$")
_NUM_CELLS_RE = re.compile(r"Number of cells:\s+(\d+)")
_NUM_WIRES_RE = re.compile(r"Number of wires:\s+(\d+)")
_NUM_WIRE_BITS_RE = re.compile(r"Number of wire bits:\s+(\d+)")
_BREAKDOWN_LINE_RE = re.compile(r"^\s+(\$?\w+)\s+(\d+)\s*$")


def parse_yosys_stat(report_text: str, variant_name: str) -> SynthQoR:
    """Parse the text produced by Yosys' `stat -width` command.

    Raises ValueError if the expected summary lines aren't found, so a
    malformed/empty report fails loudly instead of silently returning zeros.
    """
    cells_match = _NUM_CELLS_RE.search(report_text)
    wires_match = _NUM_WIRES_RE.search(report_text)
    wire_bits_match = _NUM_WIRE_BITS_RE.search(report_text)

    if not (cells_match and wires_match and wire_bits_match):
        raise ValueError(
            f"Could not find expected 'stat' summary lines in report for "
            f"variant '{variant_name}'. Was the Yosys run successful?"
        )

    breakdown: dict[str, int] = {}
    in_cell_section = False
    for line in report_text.splitlines():
        if "Number of cells:" in line:
            in_cell_section = True
            continue
        if in_cell_section:
            m = _BREAKDOWN_LINE_RE.match(line)
            if m:
                breakdown[m.group(1)] = int(m.group(2))
            elif line.strip() == "":
                break

    return SynthQoR(
        variant_name=variant_name,
        num_cells=int(cells_match.group(1)),
        num_wires=int(wires_match.group(1)),
        num_wire_bits=int(wire_bits_match.group(1)),
        cell_breakdown=breakdown,
    )
