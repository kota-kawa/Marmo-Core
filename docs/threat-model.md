# Marmo-Core threat model

Last reviewed: 2026-07-23

## Scope and assets

This document covers the in-process kernel, Policy Gateway, Context Compiler,
State Store, audit log, LLM adapters, Tool Runtime, and connector contracts.
Protected assets are user intent, credentials, private data, files and network
destinations, execution permissions, persisted state, and audit integrity.

## Trust boundaries

- The user goal and locally reviewed Skill instructions are trusted instructions.
- Memory bodies, external/file/Web content, Tool results, and Agent results are
  untrusted content, independent of the resource's package `trust_level`.
- LLM output is a proposal. Tool calls are valid only when the resource was
  activated and the activation/execution gates allow the exact operation.
- Tool handlers and secret resolvers stay beyond the LLM boundary. Secret values
  are materialized only immediately before the handler call.

Untrusted content is serialized inside a delimiter that payload text cannot
close. High-signal override, prompt-extraction, tool-instruction, and secret
exfiltration patterns are audited without retaining the matching text. When a
model has consumed untrusted content, a subsequent write/external/irreversible
call requires an argument-scoped human approval even if the resource itself was
previously or globally approved.

## Isolation contract

Connectors and tools declare `isolation_level`:

- `L0`: no isolation; only low-risk/read-only use is appropriate.
- `L1`: process separation, timeout, and resource limits.
- `L2`: L1 plus filesystem/network restrictions.
- `L3`: container or VM isolation supplied by an optional extension.

The Policy Gateway compares the declaration with
`PolicyContext.minimum_isolation_level` and audits both values. Core accepts
L0-L2 declarations; L3 is denied unless the runtime explicitly advertises an
L3 extension. A declaration is a connector contract, not proof by itself. The
built-in Shell Connector supplies L1 through an executable allowlist,
`shell=False`, bounded cwd/env/output, and timeout. File and SQLite supply L2
by constraining filesystem roots or the database path. HTTP supplies L2 with a
Connector host allowlist and L1 without one. Connector tests and deployment
controls must continue to verify these guarantees.

## Threats and controls

| Threat | Primary controls | Residual risk |
| --- | --- | --- |
| Direct/indirect prompt injection | content/instruction labels, escaped boundaries, detector audit, operation-scoped HITL for induced side effects | Models may still use hostile data in a final answer; detectors are intentionally not complete |
| Secret or private-data exfiltration | `SecretRef`, late resolution, output/error redaction, host allow/block lists, sensitive external-input HITL | A malicious handler receives secrets explicitly passed to it |
| Destructive operations | argument-aware deny/escalate rules, exact-operation approval, dry-run, compensation through the same gates | Novel command encodings may evade lexical rules |
| Excess privilege | declared permissions, deny-by-default trust policy, activation and execution gates, Agent delegated-permission subset check | A malicious in-process handler can misuse permissions explicitly granted to it |
| Weak execution isolation | L0-L3 declaration, minimum-level gate, built-in L1/L2 Connector restrictions, L3 unavailable by default | DNS rebinding and filesystem TOCTOU remain deployment concerns; L1 is not a filesystem sandbox |
| Malicious resource package | trust levels, explicit permissions, local validation | Package signatures and distribution registry remain pending |
| State/audit leakage or tampering | `SecretRef` persistence checks, redaction, hash-chained audit log | Hash chaining detects changes but does not provide remote attestation |

## Release review

Before each release, review new connectors, trust-boundary crossings, detector
rules, permission defaults, isolation claims, and any open Critical/High finding.
The release must not proceed with an unmitigated Critical/High risk. Add a dated
entry here whenever the threat model or its accepted residual risks change.

## Review history

- 2026-07-23: completed the 0.4.0 v2 release-candidate review of new
  execution paths, permission defaults, trust boundaries, and isolation
  claims; no open unmitigated Critical or High finding was identified.
- 2026-07-23: reviewed Agent delegation and built-in HTTP/File/Shell/SQLite
  Connectors; documented their concrete L1/L2 controls and residual risks.
- 2026-07-22: initial documented model; added Memory/Tool content boundaries,
  prompt-injection audit and side-effect HITL, and L0-L3 policy contracts.
