---
skillx:
  name: casadi-ipopt-nlp
  purpose: Formulate and solve the nonlinear AC OPF with CasADi and IPOPT, then extract a reportable operating point that satisfies the task constraints.
  scope_in:
    - decision-variable construction
    - objective and constraint assembly
    - solver configuration and initialization
    - solution extraction for report.json
  scope_out:
    - not for substituting a simpler non-AC optimization
    - not for guessing a feasible report without solver-backed values
    - not for hiding failed convergence behind optimistic status text
  requires:
    - trustworthy network parsing
    - correct AC branch equations and nodal-balance expressions
    - consistent variable bounds and initialization
  preferred_tools:
    - casadi
    - IPOPT
    - multiple initialization attempts when needed
  risks:
    - infeasibility from inconsistent bounds or sign conventions
    - poor initialization leading to solver failure
    - emitting a structurally valid report from an infeasible solve
    - over-rounding output values and violating verifier tolerances
  examples:
    - input: Solve the peak-hour AC-feasible operating point and write the required report.json.
      expected_behavior: build the full NLP, solve it honestly, and export numerically consistent report fields that satisfy the task checks.
---

# Guidance

Formulate the real AC problem the task asks for.
Use multiple initializations if the solve is fragile, but do not fake feasibility.

The final report must agree with the solved state:
- generator outputs
- bus voltages and angles
- branch loadings
- feasibility metrics
- solver status

# Notes for Agent

This skill is the execution backbone, but it depends on the data and branch-physics layers being correct first.


# Derived Execution Layer

## Candidate Preconditions
- trustworthy parsed data and exact AC equations are already in place
- bounds and initializations are consistent with the task model

## Candidate Postconditions
- report.json reflects an honestly solved AC-feasible operating point
- solver status is consistent with the extracted solution

## Candidate Failure Modes
- infeasible formulation hidden behind optimistic report text
- poor initialization leading to avoidable solver failure
- numerically inconsistent report fields

## Candidate Evaluator Hooks
- report-schema validation
- feasibility metric recomputation
- generation-load-loss consistency check

## Bundle Interaction Note
- this is the final execution stage and should not paper over upstream data or physics mistakes
