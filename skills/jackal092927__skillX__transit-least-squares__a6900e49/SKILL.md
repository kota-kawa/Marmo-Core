---
skillx:
  name: transit-least-squares
  purpose: Use Transit Least Squares as the primary method for identifying the transiting exoplanet period in the cleaned light curve.
  scope_in:
    - transit-shaped periodic dimming signals
    - tasks where flux uncertainties are available
    - cases where a final orbital period must be selected from transit candidates
  scope_out:
    - not for general stellar variability analysis
    - not for ignoring flux_err when running TLS
    - not for writing an unchecked half-period or double-period alias as the answer
  requires:
    - cleaned or detrended light curve
    - flux uncertainty values
    - ability to search a sensible period range and refine promising candidates
  preferred_tools:
    - transitleastsquares
    - candidate refinement around a promising period
    - phase-folded or metric-based candidate validation
  risks:
    - omitting flux_err
    - accepting a weak candidate without checking SDE or alias alternatives
    - optimizing for intermediate plots rather than the final output file
  examples:
    - input: Find the hidden exoplanet period in a detrended TESS light curve.
      expected_behavior: run TLS as the main search, refine the best candidate if needed, validate it, and return a single final period in days.
---

# Guidance

Use TLS as the main period-selection method for the final answer.
If a broad search finds a plausible candidate, refine around it before writing the final period.

Validate suspicious peaks:
- low significance
- clear half-period or double-period alternatives
- candidate periods that line up better with stellar variability than transits

# Notes for Agent

This is the primary detection skill for this task.
Supporting methods can help, but they should not replace TLS as the final decision maker without a strong reason.

