import pytest

from orchestrator.qor_parser import parse_yosys_stat

SAMPLE_STAT_REPORT = """
11. Printing statistics.

=== picorv32 ===

   Number of wires:              19946
   Number of wire bits:          22519
   Number of public wires:          180
   Number of public wire bits:    2305
   Number of memories:               0
   Number of memory bits:            0
   Number of processes:              0
   Number of cells:              13661
     $_DFFE_PP_                   1240
     $_NAND_                      6008
     $_NOR_                       4980

"""


def test_parse_yosys_stat_extracts_summary_counts():
    qor = parse_yosys_stat(SAMPLE_STAT_REPORT, variant_name="minimal")

    assert qor.variant_name == "minimal"
    assert qor.num_cells == 13661
    assert qor.num_wires == 19946
    assert qor.num_wire_bits == 22519


def test_parse_yosys_stat_extracts_cell_breakdown():
    qor = parse_yosys_stat(SAMPLE_STAT_REPORT, variant_name="minimal")

    assert qor.cell_breakdown["$_DFFE_PP_"] == 1240
    assert qor.cell_breakdown["$_NAND_"] == 6008
    assert qor.cell_breakdown["$_NOR_"] == 4980


def test_parse_yosys_stat_raises_on_malformed_report():
    with pytest.raises(ValueError):
        parse_yosys_stat("this is not a yosys report", variant_name="minimal")


def test_as_row_shape():
    qor = parse_yosys_stat(SAMPLE_STAT_REPORT, variant_name="minimal")
    row = qor.as_row()

    assert row == {
        "variant": "minimal",
        "cells": 13661,
        "wires": 19946,
        "wire_bits": 22519,
    }
