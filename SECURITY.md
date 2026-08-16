# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.4.x   | Yes       |
| < 0.4   | No        |

Only the latest released minor version receives security fixes.

## Reporting a vulnerability

Report vulnerabilities through GitHub's private vulnerability reporting on the
[Security Advisories page](https://github.com/kota-kawa/Marmo-Core/security/advisories/new).
Please do not open a public issue for an unfixed vulnerability.

Include the affected version, a minimal reproduction, and the impact you
observed. We aim to acknowledge a report within 7 days and to publish a fix or
a mitigation plan within 90 days of acknowledgement. Reports are credited in
the resulting advisory unless you ask otherwise.

## Scope

Marmo-Core enforces resource permissions, side-effect allowlists, policy
evaluation, and human-in-the-loop approval before a resource runs. The
isolation contract and the trust boundaries these controls are meant to hold
are documented in [docs/threat-model.md](docs/threat-model.md); read it before
reporting, because it defines what the kernel does and does not promise.

### In scope

- Bypassing a declared permission, a `--allow-side-effect` allowlist, or a
  human-in-the-loop approval gate without the operator granting it.
- Escaping the filesystem confinement that the bundled samples rely on.
- Leaking secrets into model-visible arguments, logs, or audit records.
- Untrusted resource metadata (a downloaded resource package, an MCP server
  response, or a tool result) causing execution the operator did not allow.
- Supply-chain issues in the published `marmo-core` distributions.

### Out of scope

- Behavior the operator explicitly authorized — a side effect permitted via
  `--allow-side-effect`, an approved human-in-the-loop prompt, or an action
  taken by a `python:` ref the operator wrote or installed themselves.
- Anything a resource can do with credentials the operator supplied to it.
- Prompt injection that only changes model output without crossing one of the
  boundaries above. Marmo-Core does not claim to make a model trustworthy; it
  claims to gate what a model's decisions are allowed to execute.
- Vulnerabilities in third-party LLM providers, MCP servers, or the optional
  `benchmark` extra's dependencies. Report those upstream.
- Findings that require an already-compromised host or process.
