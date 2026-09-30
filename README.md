# EDA Flow Automation Pipeline

Config-driven, tested automation around an open-source RTL-to-GDSII flow for
[PicoRV32](https://github.com/YosysHQ/picorv32) (a small RV32I RISC-V core).
Built as a portfolio project targeting EDA/CAD tools-automation roles —
specifically to demonstrate the Python/Tcl scripting, build-pipeline
automation, parallel job management, and unit/integration/e2e testing
practices those roles require, using a fully open-source tool chain
(Yosys / OpenROAD / KLayout) in place of licensed commercial EDA software.

## What it does

Define a design variant as a small JSON config (which core features are
enabled, target clock period) instead of hand-editing tool scripts. The
orchestrator renders a Yosys synthesis script from a template, runs it,
and parses the resulting report into structured QoR (quality-of-results)
metrics. The scheduler runs every variant in `flow/configs/` **in
parallel** — standing in for how a real job would be submitted to a
distributed compute queue — and produces a single comparison table.

```
flow/configs/*.json  ──►  orchestrator/run_flow.py  ──►  Yosys synthesis
                                    │                          │
                                    ▼                          ▼
                          flow/templates/*.ys      orchestrator/qor_parser.py
                                                              │
scheduler/job_scheduler.py  ◄────────────────────────────────┘
        │  (parallel across all variants)
        ▼
   comparison table / CSV
```

The **P&R stage** has been run end-to-end against a real PDK (see "Verified
P&R results" below) using OpenROAD-flow-scripts (ORFS) rather than the
hand-written `flow/pnr/openroad_flow.tcl` — ORFS owns the correct tech-LEF
read order and the liberty-based technology mapping that P&R needs, which a
hand-rolled script would have to reimplement. `flow/pnr/openroad_flow.tcl`
is kept as a from-scratch reference of the same flow using the raw
OpenROAD Tcl API; `flow/pnr/orfs-design/` holds the actual config used for
the verified run.

## Results — synthesis stage (measured, `yosys 0.33`, generic `abc -g cmos2` mapping)

| variant | ENABLE_MUL | ENABLE_FAST_MUL | ENABLE_DIV | BARREL_SHIFTER | ENABLE_IRQ | cells | wires |
|---|---|---|---|---|---|---|---|
| minimal | 0 | 0 | 0 | 0 | 0 | 13,661 | 19,946 |
| balanced | 1 | 0 | 1 | 1 | 0 | 14,591 | 21,162 |
| full_featured | 1 | 1 | 1 | 1 | 1 | 18,174 | 27,793 |

Full-featured is ~33% larger than minimal — mostly the fast multiplier and
IRQ logic. Reproduce with:

```bash
pip install -r requirements.txt
PYTHONPATH=. python -m scheduler.job_scheduler --csv qor_results.csv
```

Note: these are technology-independent gate counts (generic `abc -g cmos2`
mapping), not sky130 standard cells — useful for comparing variants
relatively, not for area in real units. For that, see below.

## Results — full RTL-to-GDSII (measured, OpenROAD-flow-scripts + SkyWater130 `sky130hd`, `minimal` variant, 20 ns clock)

Run via `make DESIGN_CONFIG=./designs/sky130hd/picorv32/config.mk` inside
the `openroad/orfs` Docker image (config in `flow/pnr/orfs-design/`),
covering synthesis → floorplan → placement → CTS → global/detailed route →
finish, against the real `sky130_fd_sc_hd` standard-cell library:

| Metric | Result |
|---|---|
| Standard cells (post-synthesis, real sky130 cells) | 6,402 |
| Logic area (post-synthesis) | 84,319.6 µm² |
| Final chip area (incl. fill/tap/decap cells) | 279,385.5 µm² |
| Routing DRC violations | **0** |
| Worst negative slack (WNS) / total negative slack (TNS) | 0.00 / 0.00 (no violations) |
| Worst slack margin (best case) | 10.30 ns of 20 ns clock |
| IR drop, VDD / VSS | 0.00% / 0.01% (both clean) |

The synthesis-stage table above uses generic technology-independent gates
(for fast, config-driven variant comparison); this table is the real
sky130 physical result for one variant, run through the full flow. The gap
between 84,319.6 µm² (synthesized logic) and 279,385.5 µm² (final chip
area) is fill/tap/decap/buffer insertion during place-and-route, not a
measurement error.

**Layout screenshots** (final placement, routing, congestion, clock tree — `docs/screenshots/`):

| | minimal | balanced | full_featured |
|---|---|---|---|
| Final placement | [placement](docs/screenshots/pnr_minimal/final_placement.webp.png) | [placement](docs/screenshots/pnr_balanced/final_placement.webp.png) | [placement](docs/screenshots/pnr_full_featured/final_placement.webp.png) |
| Final routing | [routing](docs/screenshots/pnr_minimal/final_routing.webp.png) | [routing](docs/screenshots/pnr_balanced/final_routing.webp.png) | [routing](docs/screenshots/pnr_full_featured/final_routing.webp.png) |
| Congestion | [congestion](docs/screenshots/pnr_minimal/final_congestion.webp.png) | [congestion](docs/screenshots/pnr_balanced/final_congestion.webp.png) | [congestion](docs/screenshots/pnr_full_featured/final_congestion.webp.png) |

## Running

```bash
# single variant
PYTHONPATH=. python -m orchestrator.run_flow flow/configs/minimal.json

# all variants, in parallel, as a comparison table
PYTHONPATH=. python -m scheduler.job_scheduler

# tests (unit + integration run anywhere; e2e tests auto-skip if yosys
# isn't installed)
PYTHONPATH=. pytest tests/ -v
```

## Adding a new design variant

Drop a new JSON file into `flow/configs/` (see the existing three for the
shape). No script changes needed — `test_config_validation.py` will catch a
malformed config in CI before it reaches the tool chain.

## Repo layout

```
rtl/                    PicoRV32 source (ISC licensed, vendored)
flow/configs/           Design-variant configs (JSON)
flow/templates/         Yosys synthesis script template
flow/pnr/               OpenROAD P&R: reference Tcl script + orfs-design/
                        (the ORFS config.mk/constraint.sdc used for the
                        verified real-PDK run)
orchestrator/           Config -> script -> tool run -> QoR parse
scheduler/              Parallel job runner + comparison table/CSV output
tests/                  Unit, integration (mocked), and e2e (real tool) tests
docker/                 Reproducible environment incl. OpenROAD + KLayout
docs/requirements.md    Problem statement, user stories, scope
.github/workflows/      CI: install Yosys, run tests, run full QoR sweep
```

## Why these design choices

- **Config-driven, not script-driven** — the failure mode this avoids is a
  pile of near-duplicate hand-edited Tcl scripts, one per experiment.
- **chparam before hierarchy, not wrapper modules** — PicoRV32 gates several
  submodules (e.g. the multiplier) behind `generate` blocks, so the
  parameter override has to land before Yosys elaborates the hierarchy or
  the submodule is silently dropped. Caught by `test_e2e.py` diffing cell
  counts across variants, not by inspection.
- **Loose bounds in the e2e assertions, exact values in the unit tests** — a
  tool-version bump changes exact gate counts; the e2e test should survive
  that, the parser unit test (fixed input string) shouldn't need to.
