# 0014. Selectors neither select nor escalate on a candidate the gate always denies (opt-in)

[日本語](0014-gate-aware-selection.md)

- Status: Accepted (opt-in; not made the default)
- Date: 2026-11-26
- Evidence: `static_denials` in `marmo_core/policy.py`, `_gate_admissible` in `marmo_core/selector.py`,
  `benchmarks/run_forgery_benchmark.py`, `benchmarks/results/forgery.json`, the forged-metadata
  section of [`benchmarks/README.en.md`](../../benchmarks/README.en.md)

## Context

Responsibilities are split: retrieval ranks, selection satisfies constraints, the gates decide
whether a resource may run. Selection read declared permissions only; trust level, side effect,
and isolation level were read by the activation gate alone. The forged-metadata measurements
(#38, #46) showed two consequences.

1. A selector picks a resource the gate denies, and it takes the slot of a legitimate one. A Tool
   that forged only its permissions was selected and then denied, and the gold Tool stopped
   reaching the model in 37% of cases.
2. A resource that stuffs its description with the task's words and declares its permissions
   honestly escalates as "the top unit blocked only by permissions". A person is asked for grants
   that would not get the resource past the gate.

Pushing the permission filter down into retrieval broke escalation before (policy ablation,
100% to 50%).

## Decision

- `policy.static_denials` collects the gate's deny reasons that no permission grant or human
  approval lifts: a trust level or side effect outside the policy, and an isolation level that is
  unavailable or below the minimum. `PolicyGateway.evaluate` uses the same checks, so selection and
  the gate cannot drift.
- With the gate's policy in `SelectionContext.policy`, the rule-based, greedy, beam,
  branch-and-bound, coverage, and top-k selectors drop such candidates before units are built. They are
  not selected, not counted as available dependencies, and not a reason to escalate. The selection
  reason names them.
- Missing permissions and side effects that wait for human approval are not included and escalate
  as before. Retrieval ranking is unchanged.
- `Kernel(gate_aware_selection=True)` passes the Kernel's own policy. It is off by default.

## Consequences

The conditions fixed before implementing (commit 5ea1990b) were an effect (gold Tool loss under
partial forgery and status changes under honest declarations both fall) and no regression on the
existing benchmarks.

- The effect holds. For greedy on Tools, gold Tool loss under partial forgery falls from 0.374 to
  0.170 and status changes under honest declarations from 0.307 to 0.170. No `tracked` aggregate got
  worse. In the finer `by_kind_content_attack` cells, status changes rose by one variant in 50 in six
  stuffed cells that forge the trust level.
- There is one regression. In the evidence case `dev-escalate` the notification Tool needs
  isolation level L3, which the default runtime does not have, as well as permissions, so the
  outcome changes from escalate to abstain (status accuracy 0.955 to 0.909). Granting the
  permissions would not get that Tool past the gate, so the new outcome matches what would happen,
  but the label says escalate and conditions are not changed after the fact. It is therefore not
  the default.
- Status accuracy on the 28 set-selection scenarios without a decoy (0.714; 0.857 for rule-based)
  and the share of evidence tasks whose gold Tool reaches the model (0.929) are unchanged
  (`suites.*.configs.*.clean` in `forgery.json`).
- With the option off, existing selections and public API compatibility are unchanged. Only
  optional fields were added.

`TopKSetSelector` and `RepairingSetSelector` leave out the same candidates. The LLM-based selectors
do not read `policy`.
Denials by `max_cost` are not included.

## Alternatives

- Do not select such candidates but keep them as reasons to escalate: tried as the other of the two
  variants fixed before implementing. It caused no regression, but status changes under honest
  declarations did not fall, so it missed the effect condition (the trial's results are not
  committed).
- Drop every gate denial in retrieval or the candidate pool: dropping missing permissions too
  removes the ability to escalate.
- Make it the default: to be reconsidered if the one case is resolved or its label is revisited.
