#!/usr/bin/env python
"""Find model parameters from models.dev registry."""

import asyncio
import sys

from nanocode.llm.registry import get_registry


async def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <provider> <model>")
        print(f"Example: {sys.argv[0]} opencode big-pickle")
        sys.exit(1)

    provider_id = sys.argv[1]
    model_id = sys.argv[2]

    registry = get_registry()
    await registry.load()

    provider = registry._providers.get(provider_id)
    if not provider:
        print(f"Provider '{provider_id}' not found")
        available = list(registry._providers.keys())
        print(f"Available providers: {', '.join(available[:20])}...")
        sys.exit(1)

    model_info = provider.models.get(model_id)
    if not model_info:
        print(f"Model '{model_id}' not found in provider '{provider_id}'")
        available = list(provider.models.keys())[:20]
        print(f"Available models: {', '.join(available)}...")
        sys.exit(1)

    print(f"=== Model Info ===")
    print(f"ID: {model_info.id}")
    print(f"Name: {model_info.name}")
    print(f"Description: {model_info.description}")
    print(f"Model URL: {model_info.model_url}")
    print()
    print(f"=== Provider Info ===")
    print(f"Provider ID: {model_info.provider_id}")
    print(f"Provider Name: {model_info.provider_name}")
    print(f"Provider URL: {model_info.provider_url}")
    print(f"Provider Logo: {model_info.provider_logo}")
    print()
    print(f"=== API Endpoint ===")
    print(f"API Endpoint: {model_info.api_endpoint}")
    print()
    print(f"=== Limits ===")
    print(f"Context Limit: {model_info.context_limit:,}")
    print(f"Max Output Tokens: {model_info.max_output_tokens:,}")
    print()
    print(f"=== Pricing (per 1M tokens) ===")
    print(f"Input Cost: ${model_info.input_cost}")
    print(f"Output Cost: ${model_info.output_cost}")
    print(f"Is Free: {model_info.is_free}")
    print()
    print(f"=== Capabilities ===")
    print(f"Supports Tools: {model_info.supports_tools}")
    print(f"Supports Vision: {model_info.supports_vision}")
    print(f"Supports Streaming: {model_info.supports_streaming}")
    print()
    print(f"=== Performance ===")
    print(f"Latency Tier: {model_info.latency_tier or 'N/A'}")
    print(f"Throughput Tier: {model_info.throughput_tier or 'N/A'}")
    print(f"Reasoning Effort: {model_info.reasoning_effort or 'N/A'}")
    print()
    print(f"=== Auth ===")
    print(f"Provider Env Vars: {provider.env_vars}")
    print(f"Auth Type: {provider.auth_type}")


if __name__ == "__main__":
    asyncio.run(main())