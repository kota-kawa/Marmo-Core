# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-09-17

Everything under "Added" here was already on `main` but had never been
released: the published 0.4.0 predates real LLM providers, so a `pip install`
and a checkout reported the same version with very different behaviour. This
release separates them, and fixes what a full pass over the library with a
real model (Groq, OpenAI-compatible) turned up.

### Fixed

- Retrieval no longer lets one crowded kind starve the others. A single global
  `top_k` meant a catalog of a thousand Skills could take every candidate slot
  next to ten Tools, so the set selector reported `tool=0/3`, no callable ever
  reached the model, and the run still ended `completed`. Each kind that comes
  back short of its set limit now gets one kind-filtered search of its own.
- `marmo run --strict` fails when the registry holds Tools or Agents but none
  of them reached the model (`NO_CALLABLE_SELECTED_DETAIL`), instead of
  exiting 0 on an answer that could not have used a guarded call.
- The `marmo resume` command printed with a pause now repeats the flags the
  run was authorized with. Copying the old hint dropped
  `--granted-permission` and `--allow-side-effect`, so the approved tool
  failed its activation gate, was reported as "skipped", and the task still
  ended `completed` with exit 0.
- Tool arguments that fail the input schema go back to the model, which may
  call again (`--max-input-repairs`, default 2), rather than ending the task
  on the first mistake. The same applies when the model names a callable that
  is not available: it is told which ones are.
- A provider error ends the task as `failed` instead of escaping the kernel,
  so the audit log, the terminal task status, and any side effects already
  executed stay on record; `--audit-log` is now written even when the run
  raises. A crashed run no longer strands its task in `running`. Two
  consequences worth noting: `marmo run` exits 1 rather than 2 for a provider
  failure, and the provider's message is now recorded in the audit log and the
  task state rather than only printed.
- One tool result can no longer overflow the model's context.
  `--max-tool-output-tokens` (default 8000) truncates an oversized result and
  says so in the text; `context_token_budget` only ever bounded the compiled
  context, not what a tool handed back.
- Planned runs answer the goal again. `_finish_plan` sent the step results as
  `tool` messages with no assistant tool call to answer, which both the OpenAI
  and Anthropic APIs reject, so every plan fell back to the canned
  "Plan complete over N step(s)" summary.
- Pause messages name a remedy that actually works. The fixed wording always
  suggested `PolicyContext(human_approved=True)`, which deliberately does not
  clear a safety finding or an always-confirm rule -- the two escalations
  scoped to the exact reviewed call.
- `OpenAICompatibleEmbeddingProvider` honours `OPENAI_BASE_URL` like the chat
  provider does. It was pinned to `api.openai.com`, so a Groq/vLLM/Ollama
  setup sent its API key to OpenAI.
- Provider error bodies are redacted before they reach an exception message or
  a log line; a 401 from OpenAI echoes part of the key that was sent.
- A 401/403 with no API key configured says so, instead of only relaying the
  server's "invalid API key".
- `HydeRetriever`, `LLMRerankRetriever`, and `LLMSetSelector` still degrade
  gracefully when the model call fails, but now warn once through `logging`
  and keep the exception on `last_failure`. A misconfigured provider used to
  make `--retriever hyde` silently do nothing.
- SKILL.md frontmatter understands block scalars with chomping and
  indentation indicators (`>-`, `|-`, `>+`, ...). `description: >-` was read as
  the literal string `">-"` and the continuation lines became junk keys, which
  removed those skills from retrieval.
- A Markdown skill inside a local resource package derives its id inside the
  package namespace, so the layout documented in
  `docs/local-resource-packages.md` loads without an explicit `id:`.
- Malformed JSON found while scanning a directory is reported as a warning and
  named in `marmo validate`'s summary instead of being skipped in silence,
  which made a typo in a resource file read as "valid: 0 resources" with exit
  0. A directory scan cannot know which unparsable file was meant to be a
  resource, so the file is skipped rather than failing the load -- naming it
  explicitly still raises. Valid JSON that is not a resource definition is
  ignored as before, and a byte-order mark or a non-UTF-8 encoding no longer
  aborts the scan.
- Credential-shaped values are redacted from audit records, not only from keys
  whose *name* looks sensitive, so a provider message reaching the log through
  a custom transport cannot carry a key into the hash chain. The pattern set
  moved to `marmo_core.secrets` and grew the vendor shapes it was missing
  (`github_pat_`, `AIza…`, `xox[baprs]-`, `Basic …`), and a key carried in a
  URL query string is redacted too.
- The `marmo resume` hint masks credential-shaped values inside `--tool-args`,
  the one forwarded option that carries free-form payload rather than
  configuration.
- `.env.example` no longer ships `OPENAI_REASONING_EFFORT=none`, which Groq
  rejects with HTTP 400 on the first request of the documented setup.
- `benchmarks/run_benchmark.py` explains how to obtain the skill corpus
  instead of raising `ResourceLoadError` when it is absent, as it is in the
  sdist.

### Changed

- Filling the per-kind candidate slots means a goal can be offered a Tool that
  a crowded pool used to hide from it. The exposure is not new -- the same Tool
  is selected today in any registry small enough not to crowd, because no
  selector applies a relevance floor -- but removing the crowding removes the
  mask. Top-ups skip anything the activation gate would deny and honour a
  selector's `min_score`; the gates, the HITL escalation for side-effecting
  resources, and `set_limits` remain the controls.

### Added

- `Kernel(max_input_repairs=..., max_tool_output_tokens=...)` and the matching
  `marmo run` / `marmo resume` flags.
- `TaskResult.hitl` returns the pending confirmation as a `HitlRequest`, and
  `ResourceDefinition.id` / `.kind` read the common metadata fields directly.
- A note on stderr when `--retriever hyde` is paired with `--llm mock`, whose
  canned reply steers retrieval at random.

- Real providers can call tools again: resource ids contain dots
  (`tool.files.read-text`), which the OpenAI and Anthropic tool-name grammars
  reject. `AnthropicLLMProvider` and `OpenAICompatibleLLMProvider` now encode
  tool names on the wire through `ToolNameCodec` and map the model's calls back
  to the original ids, so the kernel and audit log keep seeing resource ids.
- `OpenAICompatibleLLMProvider` sends `max_completion_tokens` to `openai.com`
  (current OpenAI models reject `max_tokens`), keeps `max_tokens` for other
  OpenAI-compatible servers, and switches once if the server reports the chosen
  parameter as unsupported. `max_tokens_parameter` pins either name.
- Provider HTTP failures raise `ProviderHTTPError` with the status and the
  response body's message instead of a bare `urllib` `HTTP Error 400`, and
  network failures raise `ProviderError`.
- Provider requests carry a `marmo-core/<version>` User-Agent; gateways such as
  Groq's return 403 (Cloudflare error 1010) for urllib's default agent.
- When retrieval matches no resource and the model answers without tools, the
  completed `TaskResult.detail` now says so (`NO_RESOURCE_MATCHED_DETAIL`) and
  `marmo run --strict` treats it as a violation instead of a silent success.
- The compiled system prompt states explicitly when no tools are available, so
  models that would otherwise emit a spurious tool call (gpt-oss on Groq) answer
  directly instead of failing the request.

### Changed

- The default set limit for Tools is now 3 (Memory, Skill, and Agent stay at 1),
  so goals that need more than one tool (list files, then read one) can finish.
  Lower-ranked candidates the Policy Gateway would deny are left out of the
  set; the best match of each kind is still reported as skipped when denied.
- The HyDE rewrite prompt asks for English so goals stated in other languages
  (for example Japanese) match the English-documented registry.

### Added

- `marmo run --llm {mock,openai,anthropic}` runs a goal with a real provider
  configured from the environment or `.env`, and `--retriever {lexical,hyde}`
  rewrites the goal with that provider before lexical retrieval.
- `OPENAI_BASE_URL` selects any OpenAI-compatible endpoint (Groq, vLLM, Ollama)
  for `OpenAICompatibleLLMProvider` and `--llm openai`.
- `marmo --version`, and a hint on stderr when `list` or `search` finds no
  resource definitions.
- A Python quickstart in the README.

## [0.4.0] - 2026-08-16

First release published to PyPI.

### Added

- Unified resource model covering Memory, Tool, and Agent resources, with a
  registry, retriever, reranker, and selector for task-driven activation.
- `marmo` / `marmo-core` CLI with `validate`, `list`, `search`, and `run`
  commands, including `--strict` runs for automation and release gates.
- Guarded execution: permission declarations, exact side-effect allowlists
  (`--allow-side-effect`), policy evaluation, audit logging, secret handling,
  and human-in-the-loop approval.
- Built-in connectors and MCP support, plus an executable tool and agent
  runtime backed by `python:` refs.
- Thirty bundled resource samples (ten each for Memory, Tool, and Agent) that
  run against the standard library without manual binding.
- Provider configuration read from `.env` (`OPENAI_MODEL`, `ANTHROPIC_MODEL`,
  `OPENAI_EMBEDDING_MODEL`, and related settings) instead of hard-coded
  defaults.
- Typed distribution (`py.typed`) and an optional `benchmark` extra for the
  embedding and cross-encoder integration.

[Unreleased]: https://github.com/kota-kawa/Marmo-Core/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/kota-kawa/Marmo-Core/releases/tag/v0.5.0
[0.4.0]: https://github.com/kota-kawa/Marmo-Core/releases/tag/v0.4.0
