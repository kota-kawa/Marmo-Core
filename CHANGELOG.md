# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

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

[Unreleased]: https://github.com/kota-kawa/Marmo-Core/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/kota-kawa/Marmo-Core/releases/tag/v0.4.0
