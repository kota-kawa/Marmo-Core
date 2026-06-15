---
skillx:
  name: feature_engineering
  purpose: Turn cleaned survey data into numeric respondent-level features that can be used safely in the later Difference-in-Differences analysis.
  scope_in:
    - cleaned demographic survey tables that still contain categorical, binary, and numeric respondent attributes
    - tasks where the final engineered table must be keyed by Survey ResponseID
  scope_out:
    - not for modeling outcomes directly
    - not for leaking purchase outcome columns into the feature table
    - not for leaving string/object columns in the engineered output
  requires:
    - a cleaned survey table with stable respondent IDs
    - knowledge of which columns are respondent descriptors vs identifiers
  preferred_tools:
    - pandas
    - explicit binary conversion
    - categorical encoding
    - numeric validation before export
  risks:
    - nonnumeric features breaking DID regressions
    - constant or degenerate columns bloating the model without information gain
    - accidentally encoding identifiers as predictive features
    - dropping Survey ResponseID or misaligning rows
  examples:
    - input: Build survey_feature_engineered.csv for later DiD driver analysis.
      expected_behavior: export respondent-keyed, numeric, analysis-ready features without contaminating the table with outcomes or string columns.
---

# Guidance

The main contract is simple: all usable engineered features must be numeric, and the table must stay keyed by `Survey ResponseID`.

Convert binary semantics cleanly, encode categorical variables explicitly, and validate types before exporting.
Do not assume a visually tidy table is regression-ready.

Prefer understandable encodings over clever transformations when interpretability affects the final report.

# Notes for Agent

If you leave object/string columns in the final engineered output, the downstream DiD step is already at risk.


# Derived Execution Layer

## Candidate Preconditions
- cleaned survey data exists and still includes Survey ResponseID
- categorical vs identifier columns are distinguishable

## Candidate Postconditions
- engineered survey features are numeric and keyed by Survey ResponseID
- constant or obviously useless columns are not left unexamined

## Candidate Failure Modes
- object/string columns leaking into the final engineered table
- identifier columns treated as predictive features
- row misalignment between IDs and engineered values

## Candidate Evaluator Hooks
- numeric dtype validation
- ID-column preservation check
- constant-column sanity scan

## Bundle Interaction Note
- this stage feeds DiD directly; malformed numeric outputs will poison later analysis
