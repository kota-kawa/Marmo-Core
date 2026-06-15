---
skillx:
  name: ac-branch-pi-model
  purpose: Implement the exact AC branch pi-model equations, including tap ratio and phase shift handling, so branch flows, loadings, and nodal balances match the task formulation.
  scope_in:
    - branch P/Q flow computation in both directions
    - apparent-power loading checks
    - transformer tap and phase-shift handling
    - contributions to nodal balance equations
  scope_out:
    - not for replacing the AC formulation with a DC approximation
    - not for hand-waving sign conventions or unit conversions
    - not for generic solver setup beyond the branch-physics layer
  requires:
    - parsed branch data
    - per-unit voltage magnitudes and angles
    - correct bus index mapping
  preferred_tools:
    - exact equations from math-model.md and the provided helper script
    - explicit forward and reverse branch-flow calculations
  risks:
    - wrong transformer handling for TAP or SHIFT
    - sign mistakes in P/Q flow formulas
    - inconsistent MVA-limit calculations
    - mixing MW/MVAr outputs with per-unit internals incorrectly
  examples:
    - input: Compute branch flows and loading percentages inside an AC OPF solution pipeline.
      expected_behavior: use the exact pi-model equations and produce branch values consistent with the task’s feasibility checks.
---

# Guidance

Treat this as a physics-accuracy skill, not a heuristic one.
Use the exact bidirectional branch-flow equations and convert to MVA only at the reporting edge.

If signs, taps, or units are wrong here, the optimizer can still converge numerically while the verifier rejects the report.

# Notes for Agent

This is the most likely place for silent numerical corruption.
Be exact.

