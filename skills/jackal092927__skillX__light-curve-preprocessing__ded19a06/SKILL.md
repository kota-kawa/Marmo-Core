---
skillx:
  name: light-curve-preprocessing
  purpose: Clean and detrend the TESS light curve enough to reveal the transit signal without erasing the underlying planet signature.
  scope_in:
    - quality-flag filtering
    - outlier removal
    - long-term variability removal and flattening before transit search
  scope_out:
    - not for aggressive smoothing that can remove shallow transit dips
    - not for returning a final period by itself
    - not for ignoring flux uncertainties or quality semantics
  requires:
    - time, flux, quality, and flux uncertainty columns
    - awareness of the quality-flag convention in the provided file
  preferred_tools:
    - sigma-clipped outlier removal
    - conservative flattening or detrending
    - visual or statistical sanity checks after preprocessing
  risks:
    - treating bad flags as good data
    - flattening with a window that suppresses the planet signal
    - dropping too many data points and creating aliasing artifacts
  examples:
    - input: Prepare a TESS light curve with strong stellar activity for transit search.
      expected_behavior: filter bad points, remove the dominant long-term variability conservatively, and preserve transit-like dips for the next step.
---

# Guidance

Always verify the quality-flag meaning before filtering.
For this task, a preprocessing pipeline that looks smooth but erases transits is worse than a noisier but transit-preserving one.

Use preprocessing to help the transit search, not to make the curve cosmetically flat.

# Notes for Agent

The hidden failure here is over-detrending.
If the downstream search sees only stellar-noise leftovers, the task will still fail cleanly.

