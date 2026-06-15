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

