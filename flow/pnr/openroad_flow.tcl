# OpenROAD RTL-to-GDSII P&R script.
#
# NOTE: This stage requires the OpenROAD toolchain (see docker/Dockerfile) and
# a real standard-cell PDK (e.g. the open SkyWater130 PDK). It is not executed
# by this repo's CI — CI covers the synthesis stage (flow/templates) plus unit/
# integration tests with mocked subprocess calls. This script documents the
# intended production flow and is exercised manually / in the Docker image.

set design_name   $::env(DESIGN_NAME)
set netlist       $::env(SYNTH_NETLIST)
set sdc_file      $::env(SDC_FILE)
set report_dir    $::env(REPORT_DIR)
set platform_lef  $::env(PLATFORM_LEF)
set platform_lib  $::env(PLATFORM_LIB)

read_lef $platform_lef
read_liberty $platform_lib
read_verilog $netlist
link_design $design_name
read_sdc $sdc_file

# Floorplan
initialize_floorplan -utilization 45 -aspect_ratio 1.0 -core_space 2.0
place_pins -random

# Placement
global_placement -density 0.55
detailed_placement

# Clock tree synthesis
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4

# Routing
global_route
detailed_route

# QoR reports consumed by orchestrator/qor_parser.py
report_design_area  > "$report_dir/area.rpt"
report_worst_slack  > "$report_dir/timing.rpt"
report_power         > "$report_dir/power.rpt"

write_def "$report_dir/$design_name.def"
