"""Pick the few function-calling tools a goal needs out of thousands.

Agent applications often define their tools as OpenAI / Anthropic / MCP
JSON. Sending all of them with every request is expensive and, past a few
dozen, hurts the model's tool choice. This example indexes 3,000 OpenAI-style
function definitions, splits a multi-part goal into sub-tasks, searches each
one, and selects a set that covers every sub-task once — then prints the
handful of definitions to pass to the model.

Offline and deterministic: the decomposition reply is scripted with
``MockLLMProvider``. In production, pass ``OpenAICompatibleLLMProvider()`` or
``AnthropicLLMProvider()`` to ``LLMQueryDecomposer`` instead (see README).
"""

from __future__ import annotations

import json

from marmo_core import (
    CoverageSetSelector,
    DecomposedRetriever,
    LexicalRetriever,
    LLMQueryDecomposer,
    LLMResponse,
    MockLLMProvider,
    ResourceRegistry,
    SearchQuery,
    SelectionContext,
    estimate_tokens,
    function_tool_resources,
)


def function(name: str, description: str, **properties: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {key: {"type": "string", "description": text} for key, text in properties.items()},
                "required": list(properties),
            },
        },
    }


TOOLS = [
    function("search_flights", "Search airline flights between two cities on a date", origin="Departure city", destination="Arrival city", date="Travel date"),
    function("compare_flight_prices", "Compare airline flight prices across carriers for a route", route="Origin and destination"),
    function("flight_status", "Live status of an airline flight by flight number", flight_number="Flight number"),
    function("book_hotel", "Reserve a hotel room in a city for given dates", city="City", check_in="Check-in date", nights="Number of nights"),
    function("weather_forecast", "Weather forecast for a city for the next days", city="City name"),
    function("currency_convert", "Convert an amount between currencies at today's rate", amount="Amount", target="Target currency"),
    function("send_email", "Send an email message to a recipient", to="Recipient address", body="Message text"),
]
# Thousands of unrelated functions, as in a large enterprise catalog.
DOMAINS = ["invoice", "inventory", "payroll", "ticket", "contract", "shipment", "survey", "lead", "asset", "audit"]
ACTIONS = ["create", "update", "archive", "export", "list", "approve", "assign", "merge", "tag", "count"]
for index in range(3000):
    domain, action = DOMAINS[index % 10], ACTIONS[(index // 10) % 10]
    TOOLS.append(function(f"{action}_{domain}_{index}", f"{action.title()} a {domain} record in workspace {index // 100}", record_id="Record id"))

GOAL = "Find a flight from Tokyo to Paris on May 3, book a hotel there for three nights, and tell me the weather."
SCRIPTED_DECOMPOSITION = json.dumps(
    ["search flights from Tokyo to Paris on May 3", "reserve a hotel room in Paris for three nights", "get the weather forecast for Paris"]
)


def main() -> None:
    registry = ResourceRegistry()
    for definition in function_tool_resources(TOOLS, namespace="travel-app"):
        registry.add(definition)

    decomposer = LLMQueryDecomposer(MockLLMProvider(script=[LLMResponse(content=SCRIPTED_DECOMPOSITION)]))
    retriever = DecomposedRetriever(LexicalRetriever(), decomposer)
    candidates = retriever.search(registry, SearchQuery(task=GOAL, top_k=50))
    selection = CoverageSetSelector().select(
        candidates,
        # Imported functions require the namespace permission by default.
        context=SelectionContext(task=GOAL, granted_permissions=("tools.travel-app",)),
    )

    by_name = {tool["function"]["name"]: tool for tool in TOOLS}
    chosen = [by_name[result.resource.metadata.name] for result in selection.results]
    all_tokens = estimate_tokens(json.dumps(TOOLS))
    chosen_tokens = estimate_tokens(json.dumps(chosen))
    print(f"catalog: {len(TOOLS)} functions (~{all_tokens:,} tokens of definitions)")
    print(f"sub-tasks: {retriever.last_subtasks}")
    print(f"status: {selection.status}")
    print("selected functions: " + ", ".join(tool["function"]["name"] for tool in chosen))
    print(f"definitions sent to the model: ~{chosen_tokens:,} tokens ({100 * (1 - chosen_tokens / all_tokens):.2f}% fewer)")
    assert sorted(tool["function"]["name"] for tool in chosen) == ["book_hotel", "search_flights", "weather_forecast"]


if __name__ == "__main__":
    main()
