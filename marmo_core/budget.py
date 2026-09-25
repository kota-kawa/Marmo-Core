"""Task-scoped cost reservations shared by model and resource execution."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator, Mapping, Sequence
import uuid
import json

from .errors import MarmoError, ProviderError
from .llm import ChatMessage, LLMProvider, LLMResponse, LLMToolSpec, estimate_tokens
from .state import StateStore


class BudgetExceededError(MarmoError):
    """A task cannot authorize another operation within its cost ceiling."""


def _money(value: Decimal | str | float | int, label: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{label} must be a finite non-negative number") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
    return amount


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: Decimal
    output_per_million: Decimal
    max_input_tokens: int
    max_output_tokens: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_per_million", _money(self.input_per_million, "input_per_million"))
        object.__setattr__(self, "output_per_million", _money(self.output_per_million, "output_per_million"))
        if (
            type(self.max_input_tokens) is not int
            or type(self.max_output_tokens) is not int
            or self.max_input_tokens <= 0
            or self.max_output_tokens <= 0
        ):
            raise ValueError("model token ceilings must be positive")

    def cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token usage must be non-negative")
        return (
            Decimal(input_tokens) * self.input_per_million
            + Decimal(output_tokens) * self.output_per_million
        ) / Decimal(1_000_000)

    @property
    def reservation(self) -> Decimal:
        return self.cost(self.max_input_tokens, self.max_output_tokens)


@dataclass(frozen=True)
class TaskBudget:
    amount: Decimal
    currency: str
    resource_cost_unit: str
    model_price: ModelPrice

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", _money(self.amount, "amount"))
        if not self.currency or self.resource_cost_unit != self.currency:
            raise ValueError("resource_cost_unit must explicitly match the budget currency")


class BudgetLedger:
    """Append-only reservations. Rollback never restores a spent budget."""

    def __init__(self, store: StateStore, policy: TaskBudget) -> None:
        self.store = store
        self.policy = policy
        self._task_id: ContextVar[str] = ContextVar("marmo_budget_task_id", default="")

    @contextmanager
    def bind(self, task_id: str) -> Iterator[None]:
        token = self._task_id.set(task_id)
        try:
            yield
        finally:
            self._task_id.reset(token)

    @property
    def active_task_id(self) -> str:
        return self._task_id.get()

    def attach(self, task_id: str) -> None:
        """Fix the budget policy in the task event log before execution."""

        with self.store._mutation_lock:
            if self._policy_event(task_id) is not None:
                self.verify(task_id)
                return
            if len(self.store.events(task_id)) != 1:
                raise ValueError("a task budget must be attached before task execution")
            self.store.append(task_id, "budget", {"action": "configure", "policy": self._policy_data()})

    def verify(self, task_id: str) -> None:
        configured = self._policy_event(task_id)
        if configured is None:
            raise ValueError("task has no fixed budget; submit it with task_budget")
        if configured != self._policy_data():
            raise ValueError("task budget differs from the policy fixed at submission")

    def _policy_event(self, task_id: str) -> dict[str, Any] | None:
        for event in self.store.events(task_id):
            if event.kind == "budget" and event.payload.get("action") == "configure":
                raw = event.payload.get("policy")
                return dict(raw) if isinstance(raw, Mapping) else {}
        return None

    def _policy_data(self) -> dict[str, Any]:
        policy = self.policy
        price = policy.model_price
        return {
            "amount": str(policy.amount),
            "currency": policy.currency,
            "resource_cost_unit": policy.resource_cost_unit,
            "model_price": {
                "input_per_million": str(price.input_per_million),
                "output_per_million": str(price.output_per_million),
                "max_input_tokens": price.max_input_tokens,
                "max_output_tokens": price.max_output_tokens,
            },
        }

    def status(self, task_id: str) -> dict[str, str]:
        with self.store._mutation_lock:
            self.verify(task_id)
            spent, pending = self._totals(task_id)
            remaining = max(Decimal(0), self.policy.amount - spent - pending)
            return {
                "amount": str(self.policy.amount),
                "currency": self.policy.currency,
                "spent": str(spent),
                "reserved": str(pending),
                "remaining": str(remaining),
            }

    def reserve(self, task_id: str, operation: str, amount: Decimal | str | float) -> str:
        charge = _money(amount, "reservation")
        with self.store._mutation_lock:
            self.verify(task_id)
            spent, pending = self._totals(task_id)
            if spent + pending + charge > self.policy.amount:
                raise BudgetExceededError(
                    f"task budget {self.policy.amount} {self.policy.currency} cannot reserve "
                    f"{charge} for {operation}; {max(Decimal(0), self.policy.amount - spent - pending)} remains"
                )
            reservation_id = uuid.uuid4().hex
            self.store.append(
                task_id,
                "budget",
                {"action": "reserve", "id": reservation_id, "operation": operation, "amount": str(charge)},
            )
            return reservation_id

    def settle(
        self,
        task_id: str,
        reservation_id: str,
        amount: Decimal | str | float,
        *,
        usage: Mapping[str, int] | None = None,
    ) -> None:
        charge = _money(amount, "settlement")
        with self.store._mutation_lock:
            self.verify(task_id)
            reservations = self._reservations(task_id)
            if reservation_id not in reservations or reservations[reservation_id][1]:
                raise ValueError(f"unknown or settled budget reservation: {reservation_id}")
            self.store.append(
                task_id,
                "budget",
                {
                    "action": "settle",
                    "id": reservation_id,
                    "amount": str(charge),
                    "usage": dict(usage or {}),
                },
            )

    def _reservations(self, task_id: str) -> dict[str, tuple[Decimal, bool]]:
        reservations: dict[str, tuple[Decimal, bool]] = {}
        for event in self.store.events(task_id):
            if event.kind != "budget":
                continue
            reservation_id = str(event.payload.get("id", ""))
            if event.payload.get("action") == "reserve":
                reservations[reservation_id] = (Decimal(str(event.payload["amount"])), False)
            elif event.payload.get("action") == "settle" and reservation_id in reservations:
                reservations[reservation_id] = (Decimal(str(event.payload["amount"])), True)
        return reservations

    def _totals(self, task_id: str) -> tuple[Decimal, Decimal]:
        reservations = self._reservations(task_id)
        spent = sum((amount for amount, settled in reservations.values() if settled), Decimal(0))
        pending = sum((amount for amount, settled in reservations.values() if not settled), Decimal(0))
        return spent, pending


class BudgetedLLMProvider(LLMProvider):
    """Charge every provider invocation through the active task's ledger."""

    def __init__(self, provider: LLMProvider, ledger: BudgetLedger) -> None:
        self.provider = provider
        self.ledger = ledger

    @property
    def supports_output_token_limit(self) -> bool:
        return True

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        return self._complete(messages, tools, max_output_tokens=None)

    def complete_bounded(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[LLMToolSpec] = (),
        *,
        max_output_tokens: int,
    ) -> LLMResponse:
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")
        return self._complete(messages, tools, max_output_tokens=max_output_tokens)

    def _complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[LLMToolSpec],
        *,
        max_output_tokens: int | None,
    ) -> LLMResponse:
        task_id = self.ledger.active_task_id
        if not task_id:
            raise BudgetExceededError("a budgeted model call requires an active task")
        if not self.provider.supports_output_token_limit:
            raise ProviderError(
                f"{type(self.provider).__name__} does not enforce a per-request output token limit; "
                "implement complete_bounded() to use it with a task budget"
            )
        price = self.ledger.policy.model_price
        serialized_input = json.dumps(
            {
                "messages": [message.to_dict() for message in messages],
                "tools": [spec.to_dict() for spec in tools],
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        estimate = estimate_tokens(serialized_input)
        if estimate > price.max_input_tokens:
            raise BudgetExceededError(
                f"estimated model input {estimate} tokens exceeds the configured "
                f"max_input_tokens={price.max_input_tokens}"
            )
        output_limit = price.max_output_tokens
        if max_output_tokens is not None:
            output_limit = min(output_limit, max_output_tokens)
        reservation = price.cost(price.max_input_tokens, output_limit)
        reservation_id = self.ledger.reserve(task_id, "model", reservation)
        try:
            response = self.provider.complete_bounded(
                messages,
                tools,
                max_output_tokens=output_limit,
            )
        except Exception:
            # A failed transport may still have reached the provider. Charge
            # the reserved ceiling so swallowed provider errors cannot leave
            # an indefinitely pending reservation or understate possible cost.
            self.ledger.settle(task_id, reservation_id, reservation)
            raise
        usage: dict[str, Any] = response.usage
        if not usage or not ("input_tokens" in usage and "output_tokens" in usage):
            actual = reservation
        else:
            actual = price.cost(int(usage["input_tokens"]), int(usage["output_tokens"]))
        self.ledger.settle(task_id, reservation_id, actual, usage=response.usage)
        if actual > reservation:
            raise BudgetExceededError("model reported usage above its reserved token ceiling")
        if usage and ("input_tokens" in usage and "output_tokens" in usage):
            if int(usage["input_tokens"]) > price.max_input_tokens:
                raise BudgetExceededError("model reported input usage above its configured token ceiling")
            if int(usage["output_tokens"]) > output_limit:
                raise BudgetExceededError("model reported output usage above its configured token ceiling")
        return response
