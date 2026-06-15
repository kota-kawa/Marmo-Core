---
skillx:
  name: exoplanet-workflows
  purpose: Coordinate the end-to-end light-curve workflow so the task stays focused on recovering the exoplanet orbital period and writing it in the required format.
  scope_in:
    - tasks that require a full transit-search pipeline from raw light curve to final period value
    - situations where multiple astronomy methods are available and need correct ordering
  scope_out:
    - not for broad astrophysical interpretation beyond period recovery
    - not for characterizing the planet or star beyond what is needed to recover the period
    - not for replacing transit-focused methods with unrelated exploratory analysis
  requires:
    - access to the light-curve data and its quality/error columns
    - ability to run preprocessing and period-search steps before writing the result
  preferred_tools:
    - structured preprocessing pipeline
    - transit-focused period search
    - validation by phase-folding or candidate comparison before final output
  risks:
    - doing generic exploration without producing the required file
    - selecting a nontransit periodicity
    - switching methods repeatedly without converging on a final candidate
  examples:
    - input: Recover the exoplanet period hidden beneath strong stellar variability in a TESS light curve.
      expected_behavior: clean and detrend the light curve, run a transit-focused search, validate the candidate, and write one rounded period to /root/period.txt.
---

# Guidance

Keep the pipeline narrow:
- quality filtering
- outlier handling
- detrending that preserves transits
- transit search
- final period validation
- write `/root/period.txt`

This task does not ask for a report, plot bundle, or multiple candidate list.
The deliverable is one final period value.

# Notes for Agent

Method choice matters less than finishing the right pipeline and writing the final scalar correctly.


# Derived Execution Layer

## Candidate Preconditions
- the TESS light curve file is readable
- a full pipeline can be executed from preprocessing to final file write

## Candidate Postconditions
- /root/period.txt exists with one positive period in days
- the final answer comes from a transit-focused workflow

## Candidate Failure Modes
- generic astronomy exploration without final file output
- selecting a nonplanet periodicity
- never converging to one final candidate

## Candidate Evaluator Hooks
- output-file existence and scalar-format check
- positivity and decimal-place check

## Bundle Interaction Note
- this stage keeps the whole bundle pointed at one final scalar deliverable
