# 0009. Manage task budgets with pre-execution reservations and append-only settlement

[日本語](0009-task-budget-reservations.md)

- Status: Accepted
- Date: 2026-09-25
- Evidence: `marmo_core/budget.py`, `marmo_core/kernel.py`

## Context

`SelectionContext.budget_cost` existed for set selection, but Kernel did not pass it a value. Model calls after selection, Tool retries, and Agent execution also did not share the same limit.

## Decision

- Use `TaskBudget` to make the currency, the unit of Resource `cost_estimate`, model input and output rates, and the maximum tokens per call explicit. Reject a mismatch between the currency and Resource unit.
- Set the output token limit in the provider's wire request. Before each call, check the input token limit using an estimate from the serialized input, including messages and Tool schemas. Custom `LLMProvider` implementations must implement `complete_bounded()` and `supports_output_token_limit=True`.
- Fix the budget configuration in a state event when the task is created. Reject a different configuration on resume.
- Reserve budget before each model call and each Resource execution attempt, then settle it when the result is available. If model usage is unavailable, treat the full reservation as the charge. If the provider raises an exception, the call may have reached it, so settle the full reservation to avoid undercounting.
- A rollback may restore the state projection of execution results, but must not roll back budget events.
- The default RuleBased selector uses the remaining budget for set selection. Kernel rechecks the output of other selectors as well.

## Consequences

A Resource's `cost_estimate` is treated as an estimate for one execution in the explicitly specified currency. If a Resource calls another paid API internally, users must include that cost in the estimate. If a model's actual cost exceeds the reservation, record the actual amount and stop further work. Input token estimates do not use a provider-specific tokenizer, so actual costs may exceed the reservation. This budget is not a guarantee of the billed amount; it is a pre-authorization limit on costs that Kernel can account for.

## Alternatives

- Set only the selector's `budget_cost`: rejected because it cannot limit retries or model calls.
- Decrease the budget only after usage is confirmed: rejected because parallel execution could exceed the limit.
