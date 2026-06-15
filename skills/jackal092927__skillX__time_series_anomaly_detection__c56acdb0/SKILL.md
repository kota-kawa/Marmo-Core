---
skillx:
  name: time_series_anomaly_detection
  purpose: Rank product categories by unusual March 2020 spending behavior using historical data before the treatment window to compute anomaly indices.
  scope_in:
    - category-level daily spending anomaly detection
    - tasks where March 2020 is the target window and pre-March history is the training basis
    - outputs that must identify top surge and top slump categories by anomaly index
  scope_out:
    - not for causal attribution
    - not for training on treatment-period data and calling it counterfactual
    - not for replacing the anomaly index with an unrelated ranking rule
  requires:
    - cleaned transaction data with valid dates, categories, and spending values
    - a clear cutoff between training history and March 2020 evaluation
  preferred_tools:
    - Prophet-based daily forecasting
    - explicit cutoff_date and prediction_end handling
    - per-category aggregation with signed anomaly ranking
  risks:
    - contaminating the forecast with treatment-window data
    - aggregating with the wrong value column or wrong granularity
    - returning only positive anomalies or only surges
    - misinterpreting the anomaly index sign
  examples:
    - input: Detect unusual March 2020 category surges and slumps from pre-March transaction history.
      expected_behavior: produce category_anomaly_index.csv with signed anomaly indices and enough information to select top 10 surge and top 10 slump categories.
---

# Guidance

Keep the time split honest:
- pre-March data is for model fitting
- March 2020 is the evaluation window

The anomaly index must remain directional.
Positive means unusual increase; negative means unusual decrease.

Use this skill to rank categories, not to explain them.
The causal stage comes later.

# Notes for Agent

The easiest silent failure here is a plausible-looking ranking built from the wrong time split or wrong aggregation target.

