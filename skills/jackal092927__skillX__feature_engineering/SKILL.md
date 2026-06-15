---
skillx:
  name: feature_engineering
  purpose: Transform cleaned survey descriptors into respondent-keyed numeric features that are DiD-ready and free of nonnumeric leakage.
  scope_in:
    - cleaned survey data with respondent demographics/attributes
    - stage where categorical and binary descriptors are converted into numeric features
  scope_out:
    - not for creating treatment/outcome variables from transactions
    - not for anomaly ranking
    - not for running causal estimation
  requires:
    - `survey_cleaned.csv` with stable `Survey ResponseID`
    - clear separation between identifier columns and candidate feature columns
  preferred_tools:
    - pandas
    - explicit binary conversion and categorical encoding
    - numeric-type validation before export
  risks:
    - object/string columns left in engineered output
    - identifier leakage as model feature
    - degenerate/constant columns polluting DiD regressions
    - row misalignment against `Survey ResponseID`
  examples:
    - input: Build DID-ready features from cleaned survey demographics.
      expected_behavior: output respondent-keyed numeric feature table suitable for intensive/extensive DiD joins.
---

# Stage Contract

## Input Artifact
- `survey_cleaned.csv`

## Output Artifact
- `survey_feature_engineered.csv`

Expected properties:
- one row per `Survey ResponseID` (or stable respondent-keyed structure)
- all usable feature columns numeric (`int`/`float`)
- identifier columns preserved but not encoded as predictors

## Handoff Rule to DiD Stage
- DiD stage consumes this file as respondent covariates only.
- Do not inject transaction outcomes or anomaly labels into this artifact.

# Execution Guidance

1. Keep `Survey ResponseID` as the anchor key.
2. Convert binary semantics to 0/1 consistently.
3. Encode categorical columns with explicit, reproducible mapping.
4. Retain/scale numeric columns only as needed for stability and interpretability.
5. Remove constant or unusable columns after validation.

# Pre-Handoff Checks (Required)

- `Survey ResponseID` present and unique under intended panel grain.
- No object/string columns in final feature set (excluding explicit ID if retained as string).
- No accidental use of identifier columns as predictors.
- Engineered columns are finite and regression-usable.
- Output aligns with respondent keys expected by DiD table construction.

# Common Failure Modes

- Leaving text labels unencoded (downstream regression breakage).
- One-hot/encoding operations that drop or duplicate respondent keys.
- Encoding IDs/high-cardinality identifiers as meaningful features.
- Mixing in post-outcome information (causal leakage).