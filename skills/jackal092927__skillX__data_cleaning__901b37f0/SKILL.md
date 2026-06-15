---
skillx:
  name: data_cleaning
  purpose: Clean the dirty survey and purchase tables so downstream anomaly detection and DiD analysis use logically consistent IDs, dates, categories, and spending values.
  scope_in:
    - duplicate rows, missing values, inconsistent text formatting, and implausible numeric values in the provided survey and transaction tables
    - tasks where cleaned outputs must still support joins, date filtering, and per-category aggregation
  scope_out:
    - not for changing the research question or redefining treatment windows
    - not for aggressive row dropping that destroys category or respondent coverage without justification
    - not for final feature engineering or causal estimation
  requires:
    - visibility into raw column names, IDs, dates, categories, and spend fields
    - ability to preserve keys needed by later outputs
  preferred_tools:
    - pandas
    - explicit date parsing and normalization
    - targeted deduplication and column-wise imputation
  risks:
    - dropping rows that carry needed Survey ResponseID or category information
    - normalizing text in a way that breaks later joins or category grouping
    - silently changing date semantics that define baseline vs treatment
    - overcleaning outliers that are actually real spending events
  examples:
    - input: Clean survey_dirty.csv and amazon-purchases-2019-2020_dirty.csv for March-vs-baseline anomaly and DiD analysis.
      expected_behavior: produce cleaned tables that remain joinable, time-valid, and suitable for category aggregation and respondent-level analysis.
---

# Guidance

Preserve downstream semantics first. The cleaned tables must still support:
- Survey ResponseID joins
- daily or period-based purchase aggregation
- category-level anomaly ranking
- respondent-level DiD analysis

Treat dates, IDs, categories, and spending columns as critical fields.
If a cleaning choice would change the March 2020 treatment split or break respondent linkage, prefer a more conservative fix.

Use imputation only when it preserves the analysis question.
For critical missing keys or dates, dropping rows is often safer than invented values.

# Notes for Agent

This skill is a staging skill.
Its job is to make later analysis possible, not to maximize superficial cleanliness.


# Derived Execution Layer

## Candidate Preconditions
- dirty survey and purchase tables are readable and cover the required date range
- key ID and date columns can be preserved through cleaning

## Candidate Postconditions
- cleaned tables remain joinable and time-valid
- cleaned outputs preserve keys needed by later stages

## Candidate Failure Modes
- dropping or corrupting Survey ResponseID or category linkage
- changing date semantics used for treatment vs baseline splits
- overcleaning rows that carry real analysis signal

## Candidate Evaluator Hooks
- cleaned file existence check
- key-column preservation check
- date parse and joinability sanity check

## Bundle Interaction Note
- this stage prepares valid inputs for anomaly detection and DiD; do not optimize it in isolation
