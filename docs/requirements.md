# Requirements — EDA Flow Automation Pipeline

## Problem
Design engineers evaluating a CPU core need to compare feature configurations
(multiplier, barrel shifter, interrupts, etc.) against area/timing tradeoffs
before committing to a floorplan. Running each variant through the tool
chain by hand — editing scripts, re-invoking tools, copying numbers into a
spreadsheet — doesn't scale past two or three configurations and is easy to
get wrong (stale scripts, mismatched reports).

## User stories
- As a design engineer, I want to define a new design variant as a small
  config file (not a hand-edited script) so I can add configurations without
  touching tool-specific Tcl.
- As a design engineer, I want to run all variants in parallel and get a
  single comparison table, so I can make an area/performance tradeoff
  decision quickly instead of babysitting sequential runs.
- As a CAD/EDA tools engineer, I want the flow scripts under version control
  and covered by tests, so a broken template or a tool-version bump is
  caught in CI before it silently produces bad QoR numbers.
- As a new team member, I want a documented, containerized environment so I
  can reproduce any reported result without manually installing the tool
  chain.

## Scope
**In scope (implemented, tested, run against a real design in CI):**
- Config-driven synthesis (Yosys) for PicoRV32, parameterized per variant
- Parallel job scheduling across variants
- QoR report parsing and CSV/table output
- Unit, integration, and end-to-end test coverage
- CI pipeline that installs the tool chain and runs the suite on every push

**Verified manually against a real PDK, not run in CI (needs the Docker
image + full OpenROAD toolchain, too heavy for every CI run):**
- OpenROAD place-and-route via OpenROAD-flow-scripts (ORFS) +
  SkyWater130 `sky130hd`, config in `flow/pnr/orfs-design/` — run
  end-to-end (synthesis → floorplan → place → CTS → route → finish) for
  the `minimal` variant. Result: 0 routing DRC violations, 0 negative
  slack (WNS/TNS), 10.30 ns worst-case slack margin on a 20 ns clock,
  clean IR drop. See README for the full table.
- `flow/pnr/openroad_flow.tcl` (hand-written OpenROAD Tcl reference)
  documents the same flow via the raw API; not the path used for the
  verified numbers above (ORFS handles tech-LEF ordering and
  liberty-based synthesis mapping that the hand-written script would
  otherwise have to reimplement)
- DRC/LVS closure via KLayout — not yet run

## Success criteria
- Adding a new design variant requires only a new JSON config file
- `python -m scheduler.job_scheduler` produces a correct comparison table for
  all variants with no manual steps
- CI fails if a config is malformed, a template regression breaks synthesis,
  or the parser can't read a tool's report
- At least one variant closes timing and DRC cleanly through the full
  RTL-to-GDSII flow against a real PDK — achieved for `minimal`
