---
skillx:
  name: data_cleaning
  purpose: Clean survey and transaction tables into analysis-safe artifacts while preserving respondent IDs, date semantics, category labels, and spend fields required by later stages.
  scope_in:
    - raw survey and purchase tables with duplicates, missing values, inconsistent text, and invalid formats
    - preparation for March-2020 anomaly ranking and downstream DiD analysis
  scope_out:
    - not for feature engineering
    - not for anomaly ranking or causal estimation
    - not for redefining baseline/treatment windows
  requires:
    - access to raw survey and transaction tables
    - identifiable key columns (Survey ResponseID, dates, category, spend/value)
  preferred_tools:
    - pandas
    - explicit datetime parsing
    - targeted deduplication and column-wise imputation
  risks:
    - key loss (Survey ResponseID/date/category) during cleaning
    - changing date semantics that break pre-March vs March split
    - over-aggressive outlier removal that deletes true spending signals
    - text normalization that breaks grouping/join behavior
  examples:
    - input: Clean survey_dirty.csv and amazon-purchases-2019-2020_dirty.csv for anomaly + DiD pipeline.
      expected_behavior: produce join-safe cleaned tables with valid IDs/dates/categories/spend and no stage-leaking transformations.
---

# Stage Contract

## Input Artifact
- Raw survey table
- Raw transaction table

## Output Artifact
- `survey_cleaned.csv`
- `transactions_cleaned.csv`

Both outputs must preserve fields needed by later stages:
- respondent key: `Survey ResponseID`
- transaction time field parsed as datetime
- product/category grouping field
- numeric spend/value field

## Handoff Rule to Feature Engineering + Anomaly Detection
- Feature stage consumes `survey_cleaned.csv` (respondent descriptors only).
- Anomaly stage consumes `transactions_cleaned.csv` (date/category/value integrity required).
- Do not add derived modeling features in this stage.

# Execution Guidance

1. Parse and standardize critical columns first (IDs, dates, categories, spend/value).
2. Deduplicate with key-aware logic; keep records that preserve analysis semantics.
3. Handle missing values by column criticality:
   - critical keys/dates/categories: prefer row drop over fabricated values
   - non-critical descriptive fields: conservative imputation allowed
4. Normalize text only where needed for stable joins/grouping.
5. Handle outliers conservatively; avoid deleting true high-spend events without evidence.

# Pre-Handoff Checks (Required)

- `Survey ResponseID` exists and is non-null for retained survey rows.
- Transaction date column is valid datetime and supports pre-March/March filtering.
- Category/group column is non-empty after normalization.
- Spend/value column is numeric and usable for aggregation.
- Outputs are materially joinable/aggregable by downstream stages.

# Common Failure Modes

- Cleaning choices that silently alter March-vs-baseline comparability.
- Dropping rows that collapse category coverage used by anomaly ranking.
- Converting IDs/categories in ways that break merge/group operations.
- Treating this stage as feature engineering (stage leakage).