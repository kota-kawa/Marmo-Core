# Marmo-Core Architecture

Japanese version: [ARCHITECTURE.md](ARCHITECTURE.md).

This is the canonical reference for the internal design. Public-facing
explanations are in `README.md`, procedures for changing contracts are in
`docs/knowledge/contracts-and-compatibility.md`, and the rationale behind
technical decisions is in [docs/decisions/README.en.md](docs/decisions/README.en.md).
This document describes only how the system works now. If it disagrees with the implementation, decide whether
to update this document or the implementation and bring them into alignment in
the same PR.

Target version: the value in `marmo_core/_version.py`.

## 1. Positioning

Marmo-Core is a Python kernel that registers the **resources** used by AI agents
(four kinds: Memory / Skill / Tool / Agent), searches for and selects only the
resources needed for a goal, and executes them through policy and human-review
gates. Its only runtime dependency is `python-dotenv`; HTTP uses `urllib`, and
persistence uses the standard-library JSONL / SQLite support. LLM providers,
embeddings, and cross-encoders are outside replaceable boundaries.

## 2. Layers

Dependencies flow in one direction, from lower layers to upper layers. `kernel.py`
coordinates nearly all layers. Confirm module responsibilities in the docstrings
in `marmo_core/<module>.py` and the corresponding tests.

| Layer | Module | Responsibility | Dependencies (within `marmo_core`) |
|---|---|---|---|
| Foundation | `errors.py` | Exception hierarchy (`ResourceLoadError`, `PackageError`, `ActivationError`, `ToolInputError`, `ProviderError` → `ProviderHTTPError`, and others beneath `MarmoError`) | None |
| Foundation | `environment.py` | Lazy `.env` loading (`override=False`; OS environment variables take precedence) and `required_environment` helpers | None |
| Foundation | `security.py` | Isolation levels (L0–L3), `PromptInjectionInspector`, `label_untrusted_content` | None |
| Foundation | `secrets.py` | `{"$secret": ...}` references, `SecretResolver`, `redact_credentials` (the sole location for credential-masking patterns) | errors |
| Resource model | `models.py` | `ResourceKind`, `ResourceMetadata`, `ResourceDefinition`, `SearchQuery`, `SearchResult`, `SelectionResult` | security |
| Registry and loading | `registry.py` | `ResourceRegistry` (`revision` and `content_revision`) | errors, models |
| Registry and loading | `markdown_skill.py` | `SKILL.md` front matter → Skill definition | models |
| Registry and loading | `package.py` | `marmo-package.json` / `.lock.json`, SemVer, `verify_local_package` | _version, errors |
| Registry and loading | `function_tools.py` | `function_tool_resources` (converts function definitions in OpenAI / Anthropic / MCP formats into Tool resources; defaults to trust=community, side_effect=external, and `tools.<namespace>` permissions), `FunctionToolkit` (a decorator that builds the same definition from a Python function's signature and docstring and keeps the function as the handler) | models |
| Registry and loading | `loader.py` | Directory traversal (`.json` / `.md`), `load_registry`, `validate_resource_paths` | errors, markdown_skill, models, package, registry |
| Retrieval | `retriever.py` | `Retriever` ABC, `LexicalRetriever` with a BM25F inverted index, combined scores | models, registry |
| Retrieval | `semantic.py` | `EmbeddingProvider` ABC, `HashingEmbeddingProvider`, `OpenAICompatibleEmbeddingProvider`, `HybridRetriever` (nearest-neighbor search can be replaced with `vector_index=`) | environment, errors, models, registry, retriever, secrets, vector_index |
| Retrieval | `vector_index.py` | `VectorIndex` ABC, `ExactVectorIndex` (numpy), `HNSWVectorIndex` (usearch). Both are optional dependencies | None |
| Retrieval | `fusion.py` | `RRFRetriever` (fuses the rankings of two retrievers with Reciprocal Rank Fusion) | models, registry, retriever |
| Retrieval | `decomposition.py` | `QueryDecomposer` ABC, `LLMQueryDecomposer` (gets subtasks and implicit prerequisite steps in one LLM call), `ClauseQueryDecomposer` for comparison, `DecomposedRetriever` (searches for the goal and each subtask, fuses results with a relevance blend by default, and adds `facet.<i>` components; weights the goal side by the share of its words found in the catalog index) | budget, llm, llm_routing, models, registry, retriever |
| Retrieval | `graph_routing.py` | `CapabilityGraphRetriever` (expands candidates using dependencies and capability namespaces) | models, registry, retriever, semantic |
| Retrieval | `hierarchy.py` | `HierarchicalRetriever`, `GroupingStrategy` (namespace / provider / permission / embedding) | models, registry, retriever, semantic |
| Retrieval | `rerank.py` | `CrossEncoderProvider` ABC, `CrossEncoderRerankRetriever` | models, registry, retriever |
| Retrieval | `llm_routing.py` | `HydeRetriever`, `LLMRerankRetriever`, `LLMCatalogRetriever`, `LLMSetSelector` | llm, models, registry, retriever, selector |
| Retrieval | `candidate_pool.py` | `CandidatePool` ABC, `CandidatePoolRequest`, the Kernel default `KindBalancedCandidatePool` (pre-filters by policy and performs additional searches by kind), `RetrieverCandidatePool` (passes search results through as-is) | models, registry, retriever |
| Selection | `selector.py` | `SetSelector` ABC, `SelectionContext`, default `RuleBasedSetSelector`, constrained solvers using Greedy / Beam / BranchAndBound, and `TopKSetSelector` (top K results) and `RepairingSetSelector` (adds dependencies, removes conflicts, and checks permissions for any selection result) for comparison; `_enforce_set_constraints`, which the Kernel applies to results from every Selector | models |
| Selection | `coverage.py` | `CoverageSetSelector` (greedily maximizes facility-location coverage for `facet.<i>` components within each kind, stopping when marginal gain falls below `min_gain` to determine set size. `include_within` can retain candidates close to the top candidate. Units, constraints, abstain, and escalate behavior are shared with Greedy.) | decomposition, models, selector |
| Selection | `routing_contracts.py`, `sufficient_selector.py` | Opt-in TaskSpec and resource contracts, and GoalAwareSetSelector (required coverage, permissions, dependencies, and rendered context size) | models, selector |
| Selection | `adaptive.py` | `CaseBasedRouter`, `RoutingCaseStore` (not integrated into the Kernel) | errors, models, registry, retriever, selector, semantic |
| Selection | `evaluator.py` | `ExecutionEvaluator` (writes `ResourceStats` back from the audit log; not called by the Kernel) | audit, models, registry |
| Policy | `safety.py` | `SafetyInspector` (detects destructive commands and data exfiltration), `redact_sensitive_arguments` | models, secrets |
| Policy | `policy.py` | `PolicyContext`, `PolicyGateway.evaluate(gate=activation/execution/output)`, `PolicyRejectedError` | errors, models, safety, security |
| Execution | `activator.py` | `ResourceActivator` (activation gate → `InjectedMemory` / `LoadedSkill` / `BoundTool` / `BoundAgent`; resolves `python:` references) | errors, models, policy |
| Execution | `tool_runtime.py`, `process_execution.py` | `ToolRuntime.execute` (execution gate, secret resolution, schema validation, dry-run, timeout). Optional process mode runs importable handlers in a child process and stops it | activator, errors, policy, secrets |
| Execution | `agent_runtime.py` | `AgentRuntime` and `AgentExecutionBackend` (`tool_wrap` and Kernel child tasks with `structured_task`, permission reduction, depth and cost limits) | activator, errors, policy, tool_runtime |
| Execution | `compiler.py` | `ContextCompiler` (trims Memory by budget and priority, `AgentInterface`) | activator, llm, models, security |
| Execution | `planner.py` | `Plan` / `PlanStep`, `Planner` ABC, `RuleBasedPlanner`, `LLMPlanner` | errors, llm, models, policy, secrets |
| Execution | `recovery.py` | `RecoveryManager`, `RetryPolicy`, `CircuitBreaker`, compensation | models |
| Execution | `kernel.py` | `Kernel`, `TaskResult`. Coordinates nearly all layers | Almost all |
| Providers | `llm.py` | `LLMProvider` ABC, `ChatMessage`, `ToolCall`, `MockLLMProvider`, `estimate_tokens` | secrets |
| Providers | `providers.py` | `ToolNameCodec`, `AnthropicLLMProvider`, `OpenAICompatibleLLMProvider`, `BedrockLLMProvider` (`urllib`; `transport` can be injected) | environment, errors, llm, semantic |
| State, audit, and HITL | `state.py` | Event-sourced `StateStore` ABC and InMemory / JsonFile / SQLite implementations, `TaskState`, `Checkpoint` | errors, secrets |
| State, audit, and HITL | `audit.py` | `AuditRecord`, `AuditLog` (SHA-256 hash chain), `mask_sensitive` | secrets |
| State, audit, and HITL | `hitl.py` | `HitlRequest` / `HitlResponse` / `HitlPolicy`, `HitlBroker` ABC and Pending / Callback / Console / AutoApprove | errors, models |
| Connectors | `connectors.py` | `Connector` ABC, `ConnectorRuntime` (rate limits, retries, circuit breaker), HTTP / FileSystem / Shell / SQLite | errors, models, registry |
| Connectors | `mcp.py` | `MCPStdioClient`, `connect_mcp_server` (defaults to trust=community, side_effect=external) | _version, errors, models |
| Connectors | `mcp_server.py` | `MCPGatewayServer` (an MCP server over stdio that exposes `search_tools` and `call_tool` and runs the candidate pool, selector, activation gate, and `ToolRuntime` without the Kernel; ADR 0016) | activator, audit, candidate_pool, errors, llm, mcp, models, policy, registry, retriever, security, selector, tool_runtime |
| CLI | `formatting.py`, `cli.py` | Output formatting and the `marmo` command built with argparse | Almost all |
| Samples | `sample_resources/` | Deterministic handlers referenced by `python:` from `resources/*.json` | None |

## 3. Request flow

### 3.1 `Kernel.run_goal(goal)`

1. `run_goal` → `submit` (`created` event) → `run` → `_drive`. If there is a
   `pending` request, `_drive` calls `hitl.request` and repeats `_execute` up to
   `max_hitl_rounds` times.
2. `_execute` records `status=running` and a trace_id, then merges human approvals
   and granted permissions into `PolicyContext`.
3. **Retrieval** `_candidate_pool` builds a `CandidatePoolRequest` and passes it
   to `candidate_pool.build`. By default, `KindBalancedCandidatePool`
   (`candidate_pool.py`) removes results from `retriever.search(registry,
   SearchQuery)` that the activation gate would deny (but retains the top result
   for each kind). If a kind has too few results, it performs exactly **one**
   additional search limited to that kind (at most 2 searches per goal).
   Selectors that require contract validation evaluate policy using a temporary
   context that relaxes only candidates' missing permissions, allowing lower
   ranked candidates that would become available with additional permissions to
   enter set selection. Actual permissions are not changed.
4. **Selection** After `selector.select(results, context=SelectionContext)`,
   `_enforce_set_constraints` makes the set dependency-closed and conflict-free,
   regardless of the Selector type. Dependencies are taken from the candidate
   pool or, if absent there, from the registry. Resources are dropped and
   recorded as skipped and in `audit("retrieve")`'s `constraint_drops` if they
   have a missing dependency, a dependency denied by the activation gate, or a
   conflict with a higher-ranked resource. `escalate` calls `_pause` (a
   selection-stage `HitlRequest`). With `Kernel(gate_aware_selection=True)` the
   gate's policy is passed as `SelectionContext.policy`, and the selectors that
   read it neither select nor escalate on a candidate the gate denies whatever
   is granted or approved (`policy.static_denials`); off by default, ADR 0014.
5. **Activation gate** `activator.activate` → `PolicyGateway.evaluate(gate="activation")`
   → `audit("policy")`. `escalate` calls `_pause`; `deny` adds the resource to
   skipped and calls `recovery.classify_activation`.
6. **Context construction** `compiler.compile(...)` → `audit("compile")`. Memory
   passes through `PromptInjectionInspector` and is recorded in `audit("security")`
   if a pattern is detected. The default compiler preserves dependencies
   (`ContextCompiler(preserve_dependencies=True)`) and excludes resources from
   context if an activation dependency was skipped or a budget would split the
   dependency closure. For a Selector with `requires_contract_verification=True`,
   it also rechecks the actual set after activation and compilation, along with
   resource bodies and schemas. If anything is missing, it fails without calling
   the model.
7. **Restore conversation frame** Restore messages, executed calls, correction
   count, and other data from `state.frame`. If a `planner` is configured, branch
   to `_execute_plan` and run the Plan DAG in waves.
8. **LLM call** `llm.complete(messages, compiled.tools)` → `audit("llm")`.
   `ProviderError` ends the task with `failed` status (the exception is not
   propagated).
9. **Parse Tool calls** The provider maps wire names back to resource IDs with
   `ToolNameCodec.decode`. If there are no calls, the task is `completed`.
   Unknown callables and schema violations are returned to the model in a Tool
   message (up to `max_input_repairs`). `max_tool_calls` counts **executed calls**;
   exceeding the limit sets status to `failed`.
10. **Tool / Agent execution** `_run_tool_call` and `_run_agent_call`: reject
    plaintext secrets → check `always_confirm` → `checkpoint("before:<call_id>")`
    → execution gate and execution. `ToolRuntime` handles secret resolution,
    `SafetyInspector`, schema validation, dry-run, and timeout for Tools.
    `AgentRuntime` checks the execution gate, permission reduction, depth, and
    cumulative cost, then calls `AgentExecutionBackend`. `tool_wrap` continues
    through `ToolRuntime`; `structured_task` runs the child Kernel described
    below. `escalate` calls `_pause`; `deny` is `denied`. A timeout leaves the
    side-effect outcome uncertain, so there is no automatic retry or fallback.
11. **Recovery** Failures go through `recovery.classify_tool_result` → `decide`
    for retry / fallback / escalate / fail (`_abort` and compensation).
12. **Write back** Write `audit("execute")` and `step` events. Tool output passes
    through `PromptInjectionInspector` → `label_untrusted_content` (truncated at
    `max_tool_output_tokens`, always retaining the closing tag) → messages. Save
    `frame` after every round.
13. **Finish** `_finish` writes the `status` event and `audit("task")`, then
    returns `TaskResult`. `_pause` writes the `paused` event and `audit("hitl")`,
    and returns with status=escalated.
14. **Execution statistics** The Kernel does not write these back. The caller
    can update `ResourceStats` by calling `ExecutionEvaluator().ingest_audit(
    kernel.audit_log)` and `.apply(registry)`; this is reflected in the success
    term of `LexicalRetriever`. Updating only `stats` does not change
    `content_revision`, so indexes and embeddings are not rebuilt.

A `structured_task` Agent has a required string `goal` in its Agent Card's
`input_schema`. Only the transitive closure of `metadata.dependencies` is passed
to the child Kernel's registry; the full parent registry is not exposed. The
child Kernel uses the same LLM, Retriever, Selector, Planner, Policy Gateway,
Tool Runtime, State Store, Audit Log, and Recovery Manager as its parent. Its
PolicyContext grants are reduced to the Agent's declared permissions. Child
model / Retriever / Selector / Planner calls and Tool / Agent estimates are
recorded in the parent task's BudgetLedger. HITL requests retain the resource,
operation, and decision and are forwarded to the parent task; approvals and
argument changes return to the original child task under a deterministic child
task ID. A ToolResult completed by the child is recorded in the parent task
exactly once and is also eligible for compensation after a later failure. The
default `max_agent_depth=1` allows direct Agent delegation; raise it explicitly
to allow that Agent's child to call another Agent.

### 3.2 `marmo run` / `marmo resume`

- `run`: `_build_kernel` assembles `load_registry` (default
  paths, in order: `resources/`, `skills/`, `examples/resources/`; disabled by
  `--no-default-resources`), `PolicyContext` and `HitlPolicy` from CLI arguments,
  `ConsoleHitlBroker` (`--confirm`) or `PendingHitlBroker`, `_build_llm` (mock /
  openai / anthropic / bedrock), `_build_retriever` (lexical / hyde), planner,
  connectors, and `JsonFileStateStore(--state-dir)`, then runs
  `kernel.run_goal(--task)`. An existing `--audit-log` is verified with
  `AuditLog.from_jsonl` and continued; `_report_task` appends to it with
  `AuditLog.extend_jsonl` (never replacing the file) and checks `--strict`. A
  broken chain, or a file another writer changed, is left untouched and ends
  with exit code 2. Exit codes: completed=0, all other task results=1, exception=2.
- `resume`: verifies and continues the existing `--audit-log` as `run` does, creates a
  `HitlResponse` from `--approve/--reject/--defer/--modify`, and calls
  `kernel.resume(task_id, response)`. Once selection is confirmed, resource
  identity and content fingerprints are saved in a state `snapshot` event; on
  resume, retrieval and selection are not repeated. If a Resource definition
  or compiled context has changed, the task ends as failed. Fingerprints of
  Memory / Skill bodies loaded before HITL are also saved, and the task ends as
  failed if a body changed after a pause during activation. Activation / execution
  pauses from before snapshot support end as failed because the target cannot be
  restored. The LLM loop is restored from the saved `frame`, so executed calls
  are not run a second time. The resume command shown when pausing reproduces
  the runtime `--granted-permission` / `--allow-side-effect` values.

### 3.3 `marmo mcp-serve`

`_cmd_mcp_serve` builds an `MCPGatewayServer` from `load_registry` and a `PolicyContext` made
from the CLI arguments (`--approve-resource` becomes `approved_resources`), then answers
newline-delimited JSON-RPC until stdin closes. It uses no Kernel, model, or State Store.

- `search_tools`: `KindBalancedCandidatePool` (Tools only; a candidate the activation gate does
  not allow stays only when it ranks first) → `SetSelector` → `_enforce_set_constraints` →
  activation gate. It returns the identity, description, and input schema of each Tool that
  passed, and lists the others under `withheld` with the reason.
- `call_tool`: hands `ToolRuntime.execute` only a Tool that `search_tools` returned in the
  session. An escalation is refused, since nobody can approve it. After a result is returned,
  its source is added to `untrusted_content_sources` for the execution gate of later calls.
- Audit records use the Kernel's kinds (`policy` / `retrieve` / `execute` / `security`) and are
  appended to `--audit-log` after each tool call. While serving, `sys.stdout` points at
  stderr, so stdout carries protocol messages only. An exception inside a request is returned
  as a JSON-RPC error (-32603) and the session continues.

## 4. Contracts and boundaries

Details and change procedures are in
`docs/knowledge/contracts-and-compatibility.md`.

- **Public API**: `__all__` in `marmo_core/__init__.py`.
  `tests/test_compatibility.py` checks that every name in
  `tests/fixtures/compat/v0.3.0/public_api.txt` remains available (removals are
  detected; additions are allowed).
- **ResourceDefinition**: `metadata` (15 required fields plus optional
  `dependencies`, `conflicts_with`, and `stats`) and kind-specific `extras`
  (tool: `input_schema` / `output_schema` / `isolation_level`; agent:
  `delegation_interface` / `agent_card`; memory: `content`; skill:
  `instructions` / `content`). Both flat and `{"metadata": ...}` formats are
  accepted. Identity is `id@version`.
- **State files**: `<state-dir>/<task_id>.jsonl`. Each line is
  `{schema_version: 1, task_id, seq, timestamp, kind, payload}`, with `kind` from
  `state.EVENT_KINDS`. Monotonically increasing `seq` provides optimistic
  locking (`StateConflictError`).
- **Execution Snapshot**: After selection is confirmed, append selected
  identities, scores, and fingerprints to a `snapshot` event. Append fingerprints
  of Memory / Skill bodies when activation reads them. On resume, restore the
  same selection and reject execution if the fingerprints of a selected
  Resource, a loaded body, or the compiled context have changed. For a Selector
  with `resolve_task_spec`, save the requirements before retrieval as well; do
  not extract them again when resuming after a permission pause. See
  `docs/task-sufficient-routing.md` for limits of the research contract.
- **Task budget**: `Kernel(task_budget=TaskBudget(...))` explicitly specifies the
  currency and model unit prices, and appends settings, reservations, and settlement
  to a `budget` event. The same settings are required on resume. Rollback does
  not restore already incurred costs. The remaining budget is passed to the
  selector and reserved before model calls and each Tool / Agent attempt. The
  model output limit is sent in the wire request by `complete_bounded()`; the
  input limit is checked against an estimate of serialized input including
  messages and Tool schemas. A custom `LLMProvider` must implement that method
  and declare `supports_output_token_limit=True`. Include costs for handlers that
  call external services in the Resource estimate. When using a custom Retriever
  / Selector / Planner with a budget, its implementation must declare
  `budget_aware=True` and is responsible for managing its internal paid calls.
- **Agent delegation**: `AgentRuntime` is extended through an
  `AgentExecutionBackend` mapping. `tool_wrap` is the existing local handler;
  `structured_task` is a child Kernel that receives a required string `goal`.
  Child tasks are limited to the transitive closure of declared dependencies and
  inherit the Agent's permissions and `max_agent_depth` / `max_agent_cost`. HITL,
  state, and task budget also coordinate with the parent task.
- **Audit log**: `{trace_id, span_id, timestamp, kind, payload (masked), prev_hash,
  hash}`. `hash` is SHA-256 over normalized JSON of all fields except `hash`;
  `prev_hash` is the preceding record's hash. `verify()` and `from_jsonl`
  verify the chain.
- **ToolNameCodec**: Replaces `[^a-zA-Z0-9_-]` with `_`. Names over 64 characters
  and collisions are replaced with the first 55 characters + `_` + the first 8
  characters of sha1. The Kernel and audit log always use the original resource
  ID.
- **Provider wire contract**: `openai.com` receives `max_completion_tokens`; other
  OpenAI-compatible servers receive `max_tokens`. If a server reports the field
  is unsupported, switch once. Pass error bodies through `redact_credentials`
  before including them in exceptions or logs.
- **CLI exit codes**: `run` / `resume`: completed=0, denied / failed / escalated=1,
  exception=2. `--strict` treats both “no candidate Tool / Agent reached the
  model” and “no resource matched” as failures.

## 5. Extension points

| Extension | Implement | Pass to Kernel |
|---|---|---|
| Retriever | `Retriever.search(registry, query)` | `retriever=` |
| Query decomposition | `QueryDecomposer.decompose(task)` | Through `DecomposedRetriever(inner, decomposer)` as `retriever=` |
| Candidate pool | `CandidatePool.build(CandidatePoolRequest)` (default: `KindBalancedCandidatePool`; `RetrieverCandidatePool` passes search results through as-is) | `candidate_pool=` |
| Selector | `SetSelector.select(results, *, context)` (optionally `default_limits`, `min_score`) | `selector=` |
| LLM | `LLMProvider.complete(messages, tools)` | Positional argument `llm` |
| Embeddings | `EmbeddingProvider.embed(texts)` (and `embed_queries(texts)` for asymmetric models that need an instruction on queries) | Through `HybridRetriever` / `HierarchicalRetriever` / `CaseBasedRouter` |
| Cross-encoder | `CrossEncoderProvider.score` | Through `CrossEncoderRerankRetriever` |
| Grouping | `GroupingStrategy.partition` | Through `HierarchicalRetriever` |
| Connector | `Connector.tools()` | `connectors=` (automatically integrated with the registry and handlers) |
| MCP | Resources / implementations from `connect_mcp_server` | Registry and `tool_implementations=` |
| Python functions | `resources` / `implementations` of functions registered with `FunctionToolkit.tool` | Registry and `tool_implementations=` |
| Policy | Subclass `PolicyGateway` or `SafetyInspector` (there is no rules-only ABC) | `gateway=` |
| HITL | `HitlBroker._ask` | `hitl=` |
| Planner | `Planner.plan` / `replan` | `planner=` |
| Agent execution | `AgentExecutionBackend.execute` | `AgentRuntime(backends={delegation_interface: backend})` |
| State | Five `StateStore` hooks (`_read_events`, `_write_event`, `task_ids`, `_read_session`, `_write_session`) | `state_store=` |
| Secret | `SecretResolver.resolve` | `secret_resolver=` |

Prefer implementing new research methods as one of these extensions so they can
be injected without changing the Kernel defaults. `CaseBasedRouter` (proposal F)
and `ExecutionEvaluator` are components composed outside the Kernel; integrating
them into the Kernel requires an ADR.

## 6. Configuration

`.env.example` is the canonical list of environment variables read at runtime.
`scripts/check_env_documentation.py` checks that the list matches the code.

| Variable | Read by |
|---|---|
| `ANTHROPIC_MODEL` (required), `ANTHROPIC_API_KEY`, `ANTHROPIC_MAX_TOKENS` (required; positive integer) | `providers.py` |
| `BEDROCK_API_KEY` / `AWS_BEARER_TOKEN_BEDROCK`, `BEDROCK_MODEL`, `BEDROCK_REGION` / `AWS_REGION` / `AWS_DEFAULT_REGION`, `BEDROCK_BASE_URL`, `BEDROCK_REASONING_EFFORT` | `providers.py` (reuses OpenAI-compatible Chat Completions) |
| `OPENAI_MODEL` (required), `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_REASONING_EFFORT` | `providers.py` |
| `OPENAI_EMBEDDING_MODEL` (required), `OPENAI_API_KEY`, `OPENAI_BASE_URL` | `semantic.py` |
| `MARMO_NOTIFICATION_<DESTINATION>_URL` | `sample_resources/tools.py` |
| `BENCHMARK_EMBEDDING_MODEL`, `BENCHMARK_CROSS_ENCODER_MODEL` | `benchmarks/run_benchmark.py` |

The names read by `EnvironmentSecretResolver` are chosen by the user and are
outside this list. `ShellConnector` passes child processes only environment
variables on its allowlist (default: `PATH`).

## 7. Repository layout

- `marmo_core/`: The library itself (modules in the table above). Includes
  `py.typed`; checked by `mypy`.
- `tests/`: `unittest`. Module-to-test mapping is in
  `docs/knowledge/development_conventions.md`. `tests/fixtures/compat/` is a
  frozen compatibility contract; `tests/fake_mcp_server.py` is for MCP tests.
- `resources/memory|tools|agents/`: Ten bundled samples of each type. They are
  executable and included in tests. `resources/skills/` is an untracked,
  third-party corpus ([`benchmarks/README.en.md`](benchmarks/README.en.md)).
- `examples/`: Runnable examples corresponding to the README. They are run in a
  separate process by `tests/test_v2_examples.py`.
- `benchmarks/`: Routing, set-selection, scale, and adaptation suites; scenarios;
  committed result JSON; and `_provenance.py` (records the commit SHA in results).
- `scripts/`: Checks called by CI (`release_check.py`, `check_doc_paths.py`,
  `check_env_documentation.py`). Included in the sdist and Docker image.
- `tools/`: Developer-only (collects the Skill corpus). Not included in the sdist,
  the wheel, or the Docker image (the sdist leaves it out of `MANIFEST.in` and lists it
  under `[tool.check-manifest] ignore` in `pyproject.toml`).
- `docs/`: User guides (`connectors.md`, [`local-resource-packages.en.md`](docs/local-resource-packages.en.md)), the
  threat model, `knowledge/`, and `decisions/`.
- `.github/`: CI / Release workflows, Dependabot, branch protection records, and
  the PR template.
