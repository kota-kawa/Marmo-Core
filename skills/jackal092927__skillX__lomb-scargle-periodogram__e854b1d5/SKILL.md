---
skillx:
  name: lomb-scargle-periodogram
  purpose: Use Lomb-Scargle as an exploratory periodicity check to understand dominant variability or candidate aliases before final transit-focused period selection.
  scope_in:
    - unevenly sampled light curves with strong periodic variability
    - cases where stellar rotation or other broad periodic structure may obscure the transit search
  scope_out:
    - not for directly replacing transit-specific detection as the final answer path
    - not for returning the strongest generic period without checking whether it is the planet
  requires:
    - cleaned light curve
    - willingness to distinguish stellar variability from transit periodicity
  preferred_tools:
    - lightkurve or equivalent Lomb-Scargle periodogram support
    - candidate comparison against transit-focused methods
  risks:
    - returning a stellar-rotation period instead of the planet period
    - overtrusting the strongest generic power peak
  examples:
    - input: Inspect periodic structure in a noisy light curve before final transit selection.
      expected_behavior: use LS to understand the data and possible aliases, then hand final period selection back to the transit-focused workflow.
---

# Guidance

Use Lomb-Scargle to learn about the light curve, not to shortcut the output contract.
If LS and TLS disagree, prefer the transit-shaped evidence unless there is a strong reason not to.

# Notes for Agent

LS is diagnostic support here.
It is most useful when it helps avoid choosing a stellar-variability period by mistake.


# Derived Execution Layer

## Candidate Preconditions
- cleaned light curve is available for exploratory periodicity inspection

## Candidate Postconditions
- LS findings help interpret aliases or stellar variability without replacing the transit answer path

## Candidate Failure Modes
- returning the strongest generic variability period as the planet period
- spending time on LS without improving final candidate selection

## Candidate Evaluator Hooks
- compare LS peak with the final transit candidate to detect obvious mismatches

## Bundle Interaction Note
- LS is diagnostic support only in this task
