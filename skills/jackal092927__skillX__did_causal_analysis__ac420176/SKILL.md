---
skillx:
  name: did_causal_analysis
  purpose: Estimate the top intensive and extensive margin demographic drivers behind the selected surge and slump categories using the required DiD setup.
  scope_in:
    - respondent-level demographic drivers for the already selected top anomaly categories
    - tasks requiring both intensive and extensive margin outputs
    - tasks that must emit a structured causal_analysis_report.json
  scope_out:
    - not for selecting categories in the first place
    - not for mixing sparse intensive data with complete extensive panels
    - not for unsupported causal claims beyond the required DiD framing
  requires:
    - cleaned and joinable respondent data
    - numeric engineered features
    - correctly built intensive and extensive intermediate tables for the chosen categories
  preferred_tools:
    - statsmodels-style DiD regression logic
    - explicit separation of intensive and extensive margin tables
    - sorted top-driver extraction
  risks:
    - using the wrong panel structure for intensive vs extensive margins
    - ranking features by the wrong direction for surge vs slump categories
    - emitting valid JSON with inconsistent counts or missing blocks
    - interpreting features from malformed intermediate tables
  examples:
    - input: Explain the top March 2020 surge/slump categories with top 3 intensive and top 3 extensive demographic drivers.
      expected_behavior: produce a structured causal_analysis_report.json and consistent intermediate DiD tables for the chosen categories.
---

# Guidance

Keep the panel logic straight:
- intensive margin uses participant-only sparse data
- extensive margin uses the complete entity-period panel with nonparticipants included

Run this stage only after the anomaly categories and engineered features are already valid.

The final report is not just any JSON blob.
It must align with the intermediate tables, use the required metadata fields, and sort drivers in the task-specified direction.

# Notes for Agent

This skill depends on the previous three stages being correct.
If the inputs are malformed, the report can look polished while still failing the evaluator.

