---
skillx:
  name: box-least-squares
  purpose: Use Box Least Squares as a transit-specific backup or cross-check when validating the final candidate period.
  scope_in:
    - box-shaped transit searches
    - validation or backup search around promising candidate periods
  scope_out:
    - not for replacing the primary TLS workflow by default
    - not for unconstrained method-shopping across many unrelated peaks
  requires:
    - cleaned light curve
    - reasonable duration assumptions or search ranges
  preferred_tools:
    - astropy.timeseries.BoxLeastSquares
    - focused candidate comparison near the most plausible transit period
  risks:
    - coarse period grids missing the true peak
    - selecting a high-power alias without cross-checking
    - spending too much time on backup search while never producing the final file
  examples:
    - input: Cross-check a transit candidate period from the main workflow.
      expected_behavior: use BLS to confirm or challenge the candidate rather than to derail the whole task into exhaustive exploratory searching.
---

# Guidance

Use BLS as a support method:
- confirm a TLS candidate
- inspect a close alternative
- recover a candidate if TLS is unstable

Do not let backup validation become the entire workflow.

# Notes for Agent

This skill is secondary.
Its best use is focused confirmation, not endless exploration.


# Derived Execution Layer

## Candidate Preconditions
- cleaned light curve exists
- there is a candidate period or focused search window to check

## Candidate Postconditions
- BLS is used as confirmation or backup, not as endless exploratory drift

## Candidate Failure Modes
- coarse grid misses the real peak
- backup search replaces the main workflow without justification

## Candidate Evaluator Hooks
- candidate cross-check near the final selected period
- confirmation that final output still gets written

## Bundle Interaction Note
- this is a support skill for candidate validation, not the bundle owner
