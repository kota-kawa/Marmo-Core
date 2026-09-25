"""Marmo-Core kernel: the guarded, resumable execution loop (§6).

One task runs the full pipeline:
retrieve -> select -> activation gate -> activate -> compile -> LLM ->
execution gate -> Tool / Agent execution -> audit, with every phase recorded on a
hash-chained audit log under one trace id (F-LOG-03).

The loop is re-entrant. Whenever a gate escalates, the kernel builds a
confirmation request, persists it with enough of the run to continue later,
and returns ``escalated`` (F-HITL-04 / F-STATE-02). ``resume`` replays the
pure phases -- retrieval, selection, and activation have no side effects --
and restores the conversation frame, so callables that already ran are never run
twice. Approvals are recorded per resource, scoped to what the person was
actually shown, rather than as a blanket ``human_approved`` flag.

A failing Tool or Agent goes to the Recovery Manager (4.10), which decides between
retry, falling back where supported, asking a human, or aborting. An abort
runs declared compensating tools for side effects that already happened, in
reverse order and through the normal gates.

With a ``Planner`` injected the kernel decomposes the goal up front and runs
the resulting step DAG instead of letting the model choose call by call --
independent steps run in parallel, and a failed step is re-planned around
(4.6). Both paths execute callables through the same guarded runtimes, so neither can
end up with weaker checks than the other.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace as dataclass_replace
from typing import Any, Callable, Iterable, Mapping, Sequence
import uuid

from .activator import BoundAgent, BoundTool, InjectedMemory, LoadedSkill, ResourceActivator
from .agent_runtime import AgentResult, AgentRuntime
from .audit import AuditLog
from .compiler import AgentInterface, ContextCompiler
from .connectors import Connector, connector_tools
from .errors import ProviderError, ResourceNotFoundError, SecretResolutionError, ToolInputError
from .hitl import HitlBroker, HitlError, HitlRequest, HitlResponse, PendingHitlBroker
from .llm import ChatMessage, LLMProvider, ToolCall, characters_for_tokens
from .models import ResourceDefinition, ResourceMetadata, SearchQuery, SearchResult
from .planner import Plan, PlanStep, Planner, resources_by_id, validate_plan
from .policy import PolicyContext, PolicyGateway, PolicyRejectedError
from .recovery import Failure, RecoveryDecision, RecoveryManager, compensation_for, needs_compensation
from .registry import ResourceRegistry
from .retriever import LexicalRetriever, Retriever
from .selector import DEFAULT_SET_LIMITS, RuleBasedSetSelector, SelectionContext, SetSelector
from .safety import redact_sensitive_arguments
from .security import PromptInjectionInspector, label_untrusted_content
from .secrets import SecretResolver, ensure_secret_refs, serialize_secret_refs
from .state import InMemoryStateStore, StateStore, TaskState
from .tool_runtime import ToolResult, ToolRuntime, validate_arguments


TASK_STATUSES = ("completed", "denied", "escalated", "failed", "cancelled")


@dataclass(frozen=True)
class TaskResult:
    """Terminal or paused state of one kernel task."""

    task_id: str
    goal: str
    status: str
    output: str = ""
    detail: str = ""
    tool_results: tuple[ToolResult, ...] = ()
    skipped_resources: tuple[dict[str, str], ...] = ()
    trace_id: str = ""
    hitl_request: dict[str, Any] | None = None
    agent_results: tuple[AgentResult, ...] = ()

    @property
    def completed(self) -> bool:
        return self.status == "completed"

    @property
    def paused(self) -> bool:
        """True while the task waits for a human answer (F-HITL-04)."""

        return self.status == "escalated"

    @property
    def hitl(self) -> HitlRequest | None:
        """The pending confirmation as a :class:`HitlRequest`.

        ``hitl_request`` stays a plain dict because it is persisted and
        serialized as-is; this is the typed view for calling code.
        """

        return HitlRequest.from_dict(self.hitl_request) if self.hitl_request else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": self.status,
            "output": self.output,
            "detail": self.detail,
            "tool_results": [result.to_dict() for result in self.tool_results],
            "agent_results": [result.to_dict() for result in self.agent_results],
            "skipped_resources": [dict(item) for item in self.skipped_resources],
            "trace_id": self.trace_id,
            "hitl_request": dict(self.hitl_request) if self.hitl_request else None,
        }


@dataclass
class _RunState:
    """Everything one execution pass shares between its phases."""

    task_id: str
    state: TaskState
    trace_id: str
    context: PolicyContext
    audit: Callable[[str, Mapping[str, Any]], None]
    tools: list[BoundTool]
    tools_by_name: dict[str, BoundTool]
    tool_results: list[ToolResult]
    agents: list[BoundAgent]
    agents_by_name: dict[str, BoundAgent]
    agent_results: list[AgentResult]
    skipped: list[dict[str, str]]
    recovery_state: dict[str, dict[str, Any]]
    frame: Callable[[], dict[str, Any]]


@dataclass(frozen=True)
class _CallOutcome:
    """Result of one guarded call: a result, a control decision, or a failure.

    ``invalid_input`` is the one failure the model itself can fix: arguments
    that do not satisfy the tool's input schema. It is reported back to the
    caller instead of ending the task, so the model loop can hand the message
    to the model and let it call again. Tool calls only: a delegation whose
    arguments do not fit the Agent interface still ends the task, because the
    sub-agent's own loop -- not this one -- owns how it recovers.
    """

    result: ToolResult | AgentResult | None = None
    control: TaskResult | None = None
    failure: Failure | None = None
    tool: BoundTool | None = None
    agent: BoundAgent | None = None
    invalid_input: str | None = None


# Detail attached to a completed task when retrieval matched nothing and the
# model answered from its own knowledge. Callers that need a tool to have run
# (and ``marmo run --strict``) treat it as a failure signal; a genuinely
# tool-free goal such as a translation is still a normal completion.
NO_RESOURCE_MATCHED_DETAIL = (
    "no resource matched the goal, so the model answered without tools; "
    "rephrase the goal in the registry's vocabulary or use HydeRetriever for other languages"
)

# Detail attached to a completed task when Tools or Agents *did* match the goal
# but none of them reached the model, so it could only answer from its own
# knowledge. A goal that simply needs no tool never gets this: the candidates
# have to exist for it to be anomalous. ``marmo run --strict`` treats it as a
# failure because no guarded call could have run.
NO_CALLABLE_SELECTED_DETAIL = (
    "Tools or Agents matched the goal but none reached the model, so it answered "
    "without tools; raise --set-limit for that kind, or --top-k, and check whether "
    "the context token budget dropped them"
)


class Kernel:
    """Synchronous kernel API: submit / run / resume / cancel (§6)."""

    def __init__(
        self,
        registry: ResourceRegistry,
        llm: LLMProvider,
        *,
        policy_context: PolicyContext | None = None,
        tool_implementations: Mapping[str, Callable[..., Any]] | None = None,
        agent_implementations: Mapping[str, Callable[..., Any]] | None = None,
        connectors: Sequence[Connector] = (),
        gateway: PolicyGateway | None = None,
        retriever: Retriever | None = None,
        selector: SetSelector | None = None,
        activator: ResourceActivator | None = None,
        tool_runtime: ToolRuntime | None = None,
        agent_runtime: AgentRuntime | None = None,
        compiler: ContextCompiler | None = None,
        audit_log: AuditLog | None = None,
        state_store: StateStore | None = None,
        hitl: HitlBroker | None = None,
        recovery: RecoveryManager | None = None,
        planner: Planner | None = None,
        session_id: str = "",
        top_k: int = 8,
        set_limits: Mapping[str, int] | None = None,
        min_relevance: float = 0.0,
        max_tool_calls: int = 5,
        max_input_repairs: int = 2,
        max_tool_output_tokens: int | None = 8000,
        max_agent_depth: int = 1,
        max_agent_cost: float | None = None,
        max_hitl_rounds: int = 8,
        max_replans: int = 2,
        max_parallel_steps: int = 4,
        compensate_on_failure: bool = True,
        timeout_seconds: float = 30.0,
        timeout_mode: str = "thread",
        context_token_budget: int | None = None,
        secret_resolver: SecretResolver | None = None,
        prompt_injection_inspector: PromptInjectionInspector | None = None,
    ) -> None:
        gateway = gateway or PolicyGateway()
        self.connectors = tuple(connectors)
        connector_bindings = connector_tools(self.connectors)
        merged_tool_implementations = dict(tool_implementations or {})
        connector_definitions_to_add: list[ResourceDefinition] = []
        for binding in connector_bindings:
            try:
                existing = registry.get(
                    binding.definition.metadata.id,
                    binding.definition.metadata.version,
                )
            except ResourceNotFoundError:
                connector_definitions_to_add.append(binding.definition)
            else:
                if existing.to_dict() != binding.definition.to_dict():
                    raise ValueError(
                        f"Connector resource conflicts with registered definition: "
                        f"{binding.definition.identity}"
                    )
            existing_handler = merged_tool_implementations.get(binding.resource_id)
            if existing_handler is not None and existing_handler is not binding.handler:
                raise ValueError(
                    f"Connector handler conflicts with tool_implementations: {binding.resource_id}"
                )
            merged_tool_implementations[binding.resource_id] = binding.handler
        registry.extend(connector_definitions_to_add)

        self.registry = registry
        self.llm = llm
        self.policy_context = policy_context or PolicyContext()
        self.gateway = gateway
        self.retriever = retriever or LexicalRetriever()
        self.selector = selector or RuleBasedSetSelector()
        if activator is None:
            self.activator = ResourceActivator(
                gateway,
                tool_implementations=merged_tool_implementations,
                agent_implementations=agent_implementations,
            )
        else:
            self.activator = activator
            for binding in connector_bindings:
                self.activator.bind_tool(binding.resource_id, binding.handler)
        self.tool_runtime = tool_runtime or ToolRuntime(
            gateway,
            timeout_seconds=timeout_seconds,
            secret_resolver=secret_resolver,
            timeout_mode=timeout_mode,
        )
        self.agent_runtime = agent_runtime or AgentRuntime(
            self.tool_runtime,
            max_depth=max_agent_depth,
            max_total_cost=max_agent_cost,
        )
        self.compiler = compiler or ContextCompiler()
        self.audit_log = audit_log or AuditLog()
        self.state_store = state_store or InMemoryStateStore()
        self.hitl = hitl or PendingHitlBroker()
        self.recovery = recovery or RecoveryManager()
        self.planner = planner
        self.session_id = session_id
        self.top_k = top_k
        self.set_limits = dict(set_limits) if set_limits else None
        # Floor on the text-relevance component, passed to the selector: the
        # gate that keeps a resource matching nothing in the goal out of the
        # compiled context. It is off by default because the right value
        # depends on the catalog -- relevance is absolute (1.0 = a resource
        # naming every term of the goal), so measure it against your own
        # resources before setting one.
        self.min_relevance = min_relevance
        self.max_tool_calls = max_tool_calls
        if max_input_repairs < 0:
            raise ValueError("max_input_repairs must be >= 0")
        self.max_input_repairs = max_input_repairs
        if max_tool_output_tokens is not None and max_tool_output_tokens <= 0:
            raise ValueError("max_tool_output_tokens must be positive or None")
        self.max_tool_output_tokens = max_tool_output_tokens
        self.max_hitl_rounds = max_hitl_rounds
        self.max_replans = max_replans
        self.max_parallel_steps = max(1, max_parallel_steps)
        self.compensate_on_failure = compensate_on_failure
        if context_token_budget is not None and context_token_budget <= 0:
            raise ValueError("context_token_budget must be positive or None")
        self.context_token_budget = context_token_budget
        self.prompt_injection_inspector = prompt_injection_inspector or PromptInjectionInspector()
        self._results: dict[str, TaskResult] = {}

    # -- lifecycle -----------------------------------------------------------

    def submit(self, goal: str) -> str:
        return self.state_store.create(goal, session_id=self.session_id).task_id

    def run(self, task_id: str) -> TaskResult:
        state = self.state_store.load(task_id)
        if state.terminal:
            return self._results.get(task_id) or self._result_from_state(state)
        return self._drive(state)

    def run_goal(self, goal: str) -> TaskResult:
        return self.run(self.submit(goal))

    def resume(self, task_id: str, hitl_response: HitlResponse | Mapping[str, Any] | None = None) -> TaskResult:
        """Continue a paused task, optionally applying a human answer (F-HITL-04)."""

        state = self.state_store.load(task_id)
        if state.terminal:
            return self._results.get(task_id) or self._result_from_state(state)
        if hitl_response is not None:
            if state.pending is None:
                raise HitlError(
                    f"task {task_id} is not waiting for a human answer (status {state.status}); "
                    "call run() to start or continue it"
                )
            request = HitlRequest.from_dict(state.pending)
            response = self.hitl.accept(_coerce_response(hitl_response), request)
            outcome = self._apply_response(state, request, response)
            if isinstance(outcome, TaskResult):
                return outcome
            state = outcome
        return self._drive(state)

    def cancel(self, task_id: str) -> None:
        """Stop a task for good; the state and audit trail are kept."""

        state = self.state_store.load(task_id)
        if state.terminal:
            return
        self._finish(state, state.trace_id or uuid.uuid4().hex, "cancelled", detail="cancelled by the caller")

    def get_state(self, task_id: str) -> dict[str, Any]:
        return self.state_store.load(task_id).to_dict()

    def rollback(self, task_id: str, target: int | str) -> dict[str, Any]:
        """Return a task's state to a checkpoint (F-RECOV-04).

        The kernel checkpoints before every tool call as ``before:<call id>``.
        Re-planning from the restored point needs the Planner, so for now this
        is an operator tool and a building block, not an automatic path.
        """

        return self.state_store.rollback(task_id, target).to_dict()

    def checkpoints(self, task_id: str) -> list[dict[str, Any]]:
        return [checkpoint.to_dict() for checkpoint in self.state_store.checkpoints(task_id)]

    def pending_request(self, task_id: str) -> HitlRequest | None:
        """Return the confirmation this task is waiting on, if any."""

        pending = self.state_store.load(task_id).pending
        return HitlRequest.from_dict(pending) if pending else None

    # -- HITL round-trip -----------------------------------------------------

    def _drive(self, state: TaskState) -> TaskResult:
        """Run the task, letting the broker answer any escalation it can.

        A task that is already paused is re-offered to the channel as-is
        rather than re-executed, so the request id an operator is holding
        stays valid.
        """

        result: TaskResult | None = None
        for _ in range(self.max_hitl_rounds + 1):
            if state.pending is not None:
                request = HitlRequest.from_dict(state.pending)
                response = self.hitl.request(request)
                if response is None:
                    return result or self._result_from_state(state)
                outcome = self._apply_response(state, request, response)
                if isinstance(outcome, TaskResult):
                    return outcome
                state = outcome
            result = self._execute(state)
            if not result.paused:
                return result
            state = self.state_store.load(state.task_id)
        return result or self._result_from_state(state)

    def _apply_response(
        self,
        state: TaskState,
        request: HitlRequest,
        response: HitlResponse,
    ) -> TaskState | TaskResult:
        """Fold a human answer into the task, or end it (F-HITL-03)."""

        trace_id = state.trace_id or uuid.uuid4().hex
        self.audit_log.append(
            "hitl",
            {"event": "responded", "request": request.to_dict(), "response": response.to_dict()},
            trace_id=trace_id,
        )
        if response.kind == "reject":
            note = f": {response.note}" if response.note else ""
            return self._finish(
                state,
                trace_id,
                "denied",
                detail=(
                    f"{response.responder or 'a reviewer'} rejected {request.operation}{note}; "
                    "adjust the goal or the resource set and submit a new task"
                ),
            )
        if response.kind == "defer":
            return self._result_from_state(self.state_store.load(state.task_id), hitl_request=request.to_dict())

        approvals = [request.resource] if request.resource else []
        operation_token = request.decision.get("approval_token") if request.decision else None
        payload: dict[str, Any] = {"approvals": approvals}
        if operation_token:
            payload["operation_approvals"] = [str(operation_token)]
        if request.stage == "selection":
            granted = response.arguments.get("granted_permissions") if response.arguments else None
            if granted is None and request.arguments:
                granted = request.arguments.get("missing_permissions")
            payload["granted_permissions"] = list(granted or ())
        # The escalated call is the head of the saved queue.
        call_id = (state.frame.get("calls") or [{}])[0].get("id", "")
        frame = dict(state.frame)
        touched = False
        if response.kind == "modify" and response.arguments is not None and request.stage == "execution":
            # Tag the replacement to that call id so it can apply to nothing else.
            frame["override"] = {"call_id": call_id, "arguments": dict(response.arguments)}
            touched = True
        if request.decision and "recovery" in request.decision:
            # Approving a recovery escalation means "try it properly again",
            # so the step gets its retry budget back (F-RECOV-06).
            recovery_state = {str(key): dict(value) for key, value in (frame.get("recovery") or {}).items()}
            if call_id in recovery_state:
                recovery_state[call_id]["attempts"] = 0
                frame["recovery"] = recovery_state
                touched = True
            # The circuit breaker is deliberately NOT reset here. It is the
            # runaway guard, and an approving channel (or a person clicking
            # through) must not be able to turn it off (F-RECOV-07).
        if touched:
            payload["frame"] = frame
        return self.state_store.append(state.task_id, "resumed", payload)

    # -- execution loop --------------------------------------------------------

    def _policy_feasible_candidates(
        self, results: list[SearchResult], context: PolicyContext
    ) -> list[SearchResult]:
        """Drop lower-ranked candidates the Policy Gateway would deny outright.

        The set selector may take several Tools per goal. A denied resource
        that is the *best* match of its kind stays in the pool so the run can
        report it as skipped (that tells the caller which permission is
        missing); a denied resource that would only fill a spare slot is
        left out, so widening the set never turns a clean read-only run into
        a strict failure because an unrelated write tool was pulled in.
        """

        kept: list[SearchResult] = []
        seen_kinds: set[str] = set()
        for result in results:
            kind = result.resource.metadata.kind
            first_of_kind = kind not in seen_kinds
            seen_kinds.add(kind)
            if first_of_kind or not self.gateway.evaluate(result.resource, context, gate="activation").denied:
                kept.append(result)
        return kept

    def _tool_message_content(self, value: Any, *, source: str) -> str:
        """Label one tool result for the model, capped so it cannot overflow it.

        ``context_token_budget`` bounds the *compiled* context -- instructions,
        memories, skills, tool specs -- and nothing bounded what a tool handed
        back, so one 200KB file read could push the whole request past the
        model's window and end the task with a provider error. The cap is
        applied to the payload inside the untrusted-content delimiters, so the
        boundary is always closed, and the cut is announced, because a
        silently shortened result is one the model reasons about as complete.
        The budget bounds the payload; the constant-size envelope around it is
        not counted, so the labelled message runs a few dozen tokens over.
        """

        budget = self.max_tool_output_tokens
        return label_untrusted_content(
            value,
            source=source,
            max_characters=None if budget is None else characters_for_tokens(budget),
        )

    def _candidate_pool(self, goal: str, context: PolicyContext) -> list[SearchResult]:
        """Rank candidates for the goal, leaving every kind a fillable share.

        Retrieval returns one globally ranked ``top_k``, so a kind holding
        many entries -- a thousand-skill catalog next to ten Tools -- can take
        every slot and leave the set selector nothing to fill its per-kind
        limits with. The run then reports ``tool=0/3`` and the model answers
        with no tools at all, which reads as a clean completion. The kinds
        that come back short therefore get *one* extra search between them,
        restricted to those kinds and limited per kind, over the same cached
        index. One, not one per kind: with an embedding-backed or LLM-backed
        retriever each search is a paid round trip on the same goal string.

        Top-ups drop candidates the activation gate would deny, and respect
        the selector's ``min_score`` floor when it has one: the point is to
        give the selector something it can actually use, and reporting an
        unrelated denied resource as "skipped" would turn a clean read-only
        run into a strict failure. Kinds that surface on their own merit keep
        the existing rule, where the best match is reported even when denied.

        Filling the Tool slots does mean a goal can now be offered a Tool that
        a crowded pool used to hide from it. That exposure is not new -- the
        same Tool is selected today in any registry small enough not to crowd,
        because no selector applies a relevance floor -- but the crowding was
        masking it, so removing the crowding removes the mask. The activation
        and execution gates, the HITL escalation for side-effecting resources,
        ``set_limits``, and a selector ``min_score`` remain the controls.
        """

        query = SearchQuery(
            task=goal,
            granted_permissions=tuple(context.granted_permissions),
            top_k=self.top_k,
        )
        results = self._policy_feasible_candidates(self.retriever.search(self.registry, query), context)
        # The selector starts from its own defaults and layers ``set_limits`` on
        # top, so topping up against ``set_limits`` alone would leave every kind
        # the caller did not mention starved -- the exact failure this guards.
        limits = dict(getattr(self.selector, "default_limits", None) or DEFAULT_SET_LIMITS)
        limits.update(self.set_limits or {})
        counts = Counter(result.resource.metadata.kind for result in results)
        seen = {result.resource.identity for result in results}
        shortfalls = {
            kind: limits[kind] - counts.get(kind, 0)
            for kind in sorted(limits)
            if limits[kind] - counts.get(kind, 0) > 0 and self.registry.count(kind)
        }
        if not shortfalls:
            return results
        floor = float(getattr(self.selector, "min_score", 0.0) or 0.0)
        # Each starved kind gets its own depth to walk (candidates already in
        # the pool, or denied at the activation gate, do not count against the
        # shortfall), which is what the per-kind search gave it before.
        topup = dataclass_replace(
            query,
            kinds=tuple(shortfalls),
            per_kind_limits={kind: self.top_k for kind in shortfalls},
            top_k=self.top_k * len(shortfalls),
        )
        for result in self.retriever.search(self.registry, topup):
            kind = result.resource.kind
            if shortfalls.get(kind, 0) <= 0 or result.resource.identity in seen:
                continue
            if result.score < floor:
                continue
            if self.gateway.evaluate(result.resource, context, gate="activation").denied:
                continue
            seen.add(result.resource.identity)
            results.append(result)
            shortfalls[kind] -= 1
        return results

    def _execute(self, state: TaskState) -> TaskResult:
        task_id = state.task_id
        goal = state.goal
        trace_id = state.trace_id or uuid.uuid4().hex
        context = self._effective_context(state)
        state = self.state_store.append(task_id, "status", {"status": "running", "trace_id": trace_id})

        def audit(kind: str, payload: Mapping[str, Any]) -> None:
            self.audit_log.append(kind, payload, trace_id=trace_id)

        # Phase 1 - retrieval and set selection. Pure, so a resume redoes it.
        results = self._candidate_pool(goal, context)
        callable_candidates = any(result.resource.kind in ("tool", "agent") for result in results)
        selection_context = SelectionContext(
            task=goal,
            granted_permissions=tuple(context.granted_permissions),
            per_kind_limits=dict(self.set_limits) if self.set_limits else {},
            min_relevance=self.min_relevance,
        )
        selected = self.selector.select(results, context=selection_context)
        audit(
            "retrieve",
            {
                "task": goal,
                "candidates": len(results),
                "selection_status": selected.status,
                "selected": [result.resource.identity for result in selected.results],
                "selection_reason": selected.reason,
            },
        )
        if selected.status == "escalate":
            missing = _missing_permissions(results, context.granted_permissions)
            return self._pause(
                state,
                trace_id,
                HitlRequest.create(
                    task_id=task_id,
                    stage="selection",
                    operation=f"grant permissions so a resource set exists for: {goal}",
                    impact=selected.reason,
                    alternatives=(
                        "reject to end the task",
                        "modify with {'granted_permissions': [...]} to grant a narrower set",
                    ),
                    recommendation="reject",
                    arguments={"missing_permissions": list(missing)},
                ),
                detail=f"set selection escalated: {selected.reason}",
            )

        # Phase 2 - activation. Also pure: loading text and binding callables
        # has no side effects, so replaying it on resume is safe.
        memories: list[InjectedMemory] = []
        skills: list[LoadedSkill] = []
        tools: list[BoundTool] = []
        agents: list[BoundAgent] = []
        skipped: list[dict[str, str]] = []
        for search_result in selected.results:
            definition = search_result.resource
            metadata = definition.metadata
            activation = self.activator.activate(definition, context)
            audit("policy", activation.decision.to_dict())
            if activation.decision.escalated:
                return self._pause(
                    state,
                    trace_id,
                    self._confirmation(task_id, "activation", metadata, decision=activation.decision.to_dict()),
                    detail=(
                        f"paused for human approval: activate {metadata.identity} "
                        f"(side_effect={metadata.side_effect})"
                    ),
                    skipped=skipped,
                )
            if not activation.ok:
                reason = activation.error or activation.decision.reason
                skipped.append({"resource": metadata.identity, "reason": reason})
                audit("activate", {"resource": metadata.identity, "status": "skipped", "reason": reason})
                # Classified for the record (F-ACT-05 / F-RECOV-01); the
                # response stays "carry on without it", since the set selector
                # already judged the rest of the set usable on its own.
                failure = self.recovery.classify_activation(definition, reason)
                audit("recover", {"failure": failure.to_dict(), "action": "skip"})
                continue
            audit("activate", {"resource": metadata.identity, "status": "activated", "kind": metadata.kind})
            self.state_store.append(task_id, "activated", {"resource": metadata.identity})
            activated = activation.activated
            if isinstance(activated, InjectedMemory):
                memories.append(activated)
            elif isinstance(activated, LoadedSkill):
                skills.append(activated)
            elif isinstance(activated, BoundTool):
                tools.append(activated)
            elif isinstance(activated, BoundAgent):
                agents.append(activated)

        context_priorities = {
            result.resource.identity: result.score for result in selected.results
        }
        try:
            compiled = self.compiler.compile(
                goal,
                memories=memories,
                skills=skills,
                tools=tools,
                agents=[AgentInterface.from_definition(agent.definition) for agent in agents],
                token_budget=self.context_token_budget,
                priorities=context_priorities,
            )
        except ValueError as exc:
            audit("compile", {"stage": "execution", "status": "failed", "reason": str(exc)})
            return self._finish(
                state,
                trace_id,
                "failed",
                detail=f"context compilation failed: {exc}",
                skipped=skipped,
            )
        audit("compile", compiled.summary())

        compiled_ids = set(compiled.resource_ids)
        memories = [item for item in memories if item.metadata.identity in compiled_ids]
        skills = [item for item in skills if item.metadata.identity in compiled_ids]
        tools = [item for item in tools if item.metadata.identity in compiled_ids]
        agents = [item for item in agents if item.metadata.identity in compiled_ids]

        memory_sources = [f"memory:{memory.metadata.identity}" for memory in memories]
        memory_findings: list[str] = []
        for memory in memories:
            findings = self.prompt_injection_inspector.inspect(memory.content)
            memory_findings.extend(finding.code for finding in findings)
            if findings:
                audit(
                    "security",
                    {
                        "event": "prompt_injection_detected",
                        "source": f"memory:{memory.metadata.identity}",
                        "trust": "untrusted_content",
                        "findings": [finding.to_dict() for finding in findings],
                    },
                )

        # Phase 3 - the model loop. This one does have side effects, so it is
        # restored from the persisted frame rather than replayed.
        state = self.state_store.load(task_id)
        frame = dict(state.frame)
        tools_by_name = {tool.metadata.id: tool for tool in tools}
        agents_by_name: dict[str, BoundAgent] = {}
        for agent in agents:
            agents_by_name[agent.metadata.id] = agent
            agents_by_name[AgentInterface.from_definition(agent.definition).name] = agent
        messages: list[ChatMessage] = (
            [_message_from_dict(item) for item in frame["messages"]]
            if frame.get("messages")
            else list(compiled.messages)
        )
        pending_calls: list[ToolCall] = [_tool_call_from_dict(item) for item in frame.get("calls", ())]
        llm_calls = int(frame.get("llm_calls", 0))
        # Corrections already handed back to the model, so a pause cannot hand
        # a model that keeps emitting bad arguments a fresh budget on resume.
        input_repairs = int(frame.get("input_repairs", 0))
        # Counts callables actually dispatched, not model rounds: one round can
        # request several calls, and it is the side effects that need bounding.
        executed_calls = int(frame.get("executed_calls", 0))
        tool_results = [ToolResult.from_dict(item) for item in state.step_results if "tool_id" in item]
        agent_results = [AgentResult.from_dict(item) for item in state.step_results if "agent_id" in item]
        # A human's replacement arguments, carried until the call they name runs.
        override: dict[str, Any] | None = frame.get("override")
        # Per-call retry budget and tools already tried, so a pause does not
        # hand a failing step a fresh budget on resume.
        recovery_state: dict[str, dict[str, Any]] = {
            str(key): dict(value) for key, value in (frame.get("recovery") or {}).items()
        }
        untrusted_sources = list(frame.get("untrusted_sources") or memory_sources)
        prompt_findings = list(frame.get("prompt_injection_findings") or memory_findings)
        call_untrusted_sources = tuple(frame.get("call_untrusted_sources") or ())
        call_prompt_findings = tuple(frame.get("call_prompt_injection_findings") or ())

        def current_frame() -> dict[str, Any]:
            saved: dict[str, Any] = {
                "messages": [message.to_dict() for message in messages],
                "calls": [call.to_dict() for call in pending_calls],
                "llm_calls": llm_calls,
                "executed_calls": executed_calls,
            }
            if input_repairs:
                saved["input_repairs"] = input_repairs
            if override is not None:
                saved["override"] = override
            if recovery_state:
                saved["recovery"] = recovery_state
            if untrusted_sources:
                saved["untrusted_sources"] = list(untrusted_sources)
            if prompt_findings:
                saved["prompt_injection_findings"] = list(prompt_findings)
            if call_untrusted_sources:
                saved["call_untrusted_sources"] = list(call_untrusted_sources)
            if call_prompt_findings:
                saved["call_prompt_injection_findings"] = list(call_prompt_findings)
            return saved

        def failed(detail: str) -> TaskResult:
            return self._finish(
                state,
                trace_id,
                "failed",
                detail=detail,
                tool_results=tool_results,
                agent_results=agent_results,
                skipped=skipped,
            )

        run = _RunState(
            task_id=task_id,
            state=state,
            trace_id=trace_id,
            context=context,
            audit=audit,
            tools=tools,
            tools_by_name=tools_by_name,
            tool_results=tool_results,
            agents=agents,
            agents_by_name=agents_by_name,
            agent_results=agent_results,
            skipped=skipped,
            recovery_state=recovery_state,
            frame=current_frame,
        )

        # A Planner decomposes the goal up front; without one the model
        # decides call by call, which is itself a valid plan-as-you-go
        # strategy (F-PLAN-07).
        if self.planner is not None:
            return self._execute_plan(run, compiled)

        while True:
            if not pending_calls:
                call_untrusted_sources = tuple(untrusted_sources)
                call_prompt_findings = tuple(prompt_findings)
                try:
                    response = self.llm.complete(messages, compiled.tools)
                except ProviderError as exc:
                    # Ending the task here (rather than letting the exception
                    # escape) is what keeps the audit log, the terminal task
                    # status, and any side effects already executed on record.
                    audit("llm", {"round": llm_calls, "error": f"{type(exc).__name__}: {exc}"})
                    return failed(f"the model provider failed: {exc}")
                llm_calls += 1
                audit(
                    "llm",
                    {
                        "round": llm_calls - 1,
                        "tool_calls": [call.to_dict() for call in response.tool_calls],
                        "usage": response.usage,
                        "content_chars": len(response.content),
                    },
                )
                if not response.tool_calls:
                    detail = ""
                    if skipped:
                        names = ", ".join(item["resource"] for item in skipped)
                        detail = f"completed without {len(skipped)} skipped resource(s): {names}"
                    elif not selected.results and not tool_results and self.registry.list():
                        detail = NO_RESOURCE_MATCHED_DETAIL
                    elif (
                        not tools
                        and not agents
                        and not tool_results
                        and not agent_results
                        and callable_candidates
                    ):
                        detail = NO_CALLABLE_SELECTED_DETAIL
                    return self._finish(
                        state,
                        trace_id,
                        "completed",
                        output=response.content,
                        detail=detail,
                        tool_results=tool_results,
                        agent_results=agent_results,
                        skipped=skipped,
                    )
                messages.append(
                    ChatMessage(role="assistant", content=response.content, tool_calls=response.tool_calls)
                )
                pending_calls = list(response.tool_calls)

            while pending_calls:
                if executed_calls >= self.max_tool_calls:
                    return failed(
                        f"exceeded max_tool_calls={self.max_tool_calls}; raise the limit or simplify the task"
                    )
                call = pending_calls[0]
                tool = tools_by_name.get(call.name)
                called_agent = agents_by_name.get(call.name)
                if tool is None and called_agent is None:
                    unavailable = (
                        f"the model requested callable {call.name!r} which is not available in the "
                        "compiled context; register and activate it, increase the context token "
                        "budget if it was omitted, or adjust the search so it is selected"
                    )
                    if input_repairs >= self.max_input_repairs:
                        return failed(unavailable)
                    input_repairs += 1
                    pending_calls.pop(0)
                    available = ", ".join(sorted({*tools_by_name, *agents_by_name})) or "(none)"
                    messages.append(
                        ChatMessage(
                            role="tool",
                            name=call.name,
                            content=(
                                f"Error: no callable named {call.name!r} is available. "
                                f"Available callables: {available}. Call one of those, or answer "
                                "without tools."
                            ),
                        )
                    )
                    audit("llm", {"event": "unknown_callable", "requested": call.name, "repair": input_repairs})
                    continue
                arguments = dict(call.arguments)
                if override is not None and override.get("call_id") == call.id:
                    arguments = dict(override["arguments"])
                    audit("hitl", {"event": "arguments_modified", "resource": call.name, "arguments": arguments})
                    override = None
                run.context = dataclass_replace(
                    context,
                    untrusted_content_sources=call_untrusted_sources,
                    prompt_injection_findings=call_prompt_findings,
                )
                if tool is not None:
                    outcome = self._run_tool_call(run, tool, arguments, call.id, label=call.name)
                else:
                    assert called_agent is not None
                    outcome = self._run_agent_call(
                        run, called_agent, arguments, call.id, label=call.name
                    )
                if outcome.control is not None:
                    return outcome.control
                if outcome.invalid_input is not None:
                    # The schema check runs before the handler, so nothing has
                    # happened yet and the model can simply call again.
                    if input_repairs >= self.max_input_repairs:
                        return failed(
                            f"{outcome.invalid_input}; the model did not produce valid arguments "
                            f"within max_input_repairs={self.max_input_repairs}"
                        )
                    input_repairs += 1
                    pending_calls.pop(0)
                    messages.append(
                        ChatMessage(
                            role="tool",
                            name=call.name,
                            content=(
                                f"Error: {outcome.invalid_input}. Call the tool again with "
                                "arguments that match its input_schema."
                            ),
                        )
                    )
                    audit(
                        "llm",
                        {"event": "invalid_arguments", "requested": call.name, "repair": input_repairs},
                    )
                    continue
                result = outcome.result
                assert result is not None  # no control means the call produced a result

                # Counted only once the call ran to a result: a paused call is
                # replayed on resume and must not be charged to the budget twice.
                executed_calls += 1
                pending_calls.pop(0)
                recovery_state.pop(call.id, None)
                if outcome.tool is not None:
                    source = f"tool:{outcome.tool.metadata.identity}"
                elif outcome.agent is not None:
                    source = f"agent:{outcome.agent.metadata.identity}"
                elif tool is not None:
                    source = f"tool:{tool.metadata.identity}"
                else:
                    assert called_agent is not None
                    source = f"agent:{called_agent.metadata.identity}"
                findings = self.prompt_injection_inspector.inspect(result.output)
                if source not in untrusted_sources:
                    untrusted_sources.append(source)
                for finding in findings:
                    if finding.code not in prompt_findings:
                        prompt_findings.append(finding.code)
                if findings:
                    audit(
                        "security",
                        {
                            "event": "prompt_injection_detected",
                            "source": source,
                            "trust": "untrusted_content",
                            "findings": [finding.to_dict() for finding in findings],
                        },
                    )
                messages.append(
                    ChatMessage(
                        role="tool",
                        name=call.name,
                        content=self._tool_message_content(result.output, source=source),
                    )
                )
            self.state_store.append(task_id, "frame", {"frame": current_frame()})

    # -- helpers ---------------------------------------------------------------

    def _effective_context(self, state: TaskState) -> PolicyContext:
        """Fold approvals and grants collected from humans into the context."""

        base = self.policy_context
        return dataclass_replace(
            base,
            granted_permissions=_merge(base.granted_permissions, state.granted_permissions),
            approved_resources=_merge(base.approved_resources, state.approvals),
            approved_operations=_merge(base.approved_operations, state.operation_approvals),
        )

    def _needs_confirmation(self, metadata: ResourceMetadata, context: PolicyContext) -> bool:
        """True when the HITL policy demands a human even though the gate allows it.

        Checked just before execution rather than at activation: that is where
        the arguments exist, so the person reviews the actual call and can
        answer with ``modify`` instead of only yes/no (F-HITL-03/07).

        Only answering this resource's own request clears it. The blanket
        ``human_approved`` flag deliberately does not, or "always confirm"
        would not mean always.
        """

        if context.dry_run:
            return False
        return self.hitl.policy.requires_confirmation(metadata) and not (
            metadata.identity in context.approved_resources or metadata.id in context.approved_resources
        )

    def _run_tool_call(
        self,
        run: "_RunState",
        tool: BoundTool,
        arguments: Mapping[str, Any],
        call_id: str,
        *,
        label: str = "",
        abort_on_failure: bool = True,
    ) -> "_CallOutcome":
        """Execute one tool call under the gates, with recovery (4.7 / 4.10).

        The single implementation both execution paths -- model-driven and
        plan-driven -- go through, so neither can end up with a weaker set of
        checks than the other (F-GATE-01).
        """

        audit = run.audit
        arguments = dict(arguments)
        label = label or tool.metadata.id
        try:
            ensure_secret_refs(arguments)
        except SecretResolutionError as exc:
            failure = self.recovery.classify_validation(tool.metadata, str(exc))
            audit("recover", {"failure": failure.to_dict(), "action": "fail"})
            audit("execute", {"tool": label, "status": "invalid_input", "error": str(exc)})
            if not abort_on_failure:
                return _CallOutcome(failure=failure)
            return _CallOutcome(
                control=self._finish(
                    run.state,
                    run.trace_id,
                    "failed",
                    detail=str(exc),
                    tool_results=run.tool_results,
                    skipped=run.skipped,
                )
            )
        if self._needs_confirmation(tool.metadata, run.context):
            return _CallOutcome(
                control=self._pause(
                    run.state,
                    run.trace_id,
                    self._confirmation(
                        run.task_id,
                        "execution",
                        tool.metadata,
                        arguments=arguments,
                        always_confirm=True,
                    ),
                    detail=(
                        f"paused for human approval: the HITL policy always confirms "
                        f"{tool.metadata.identity} before execution"
                    ),
                    frame=run.frame(),
                    tool_results=run.tool_results,
                    skipped=run.skipped,
                )
            )
        # A rollback target for this step, before it can leave a mark (F-RECOV-04).
        self.state_store.checkpoint(run.task_id, f"before:{call_id}")
        entry = run.recovery_state.setdefault(call_id, {"attempts": 0, "tried": []})
        # Recovery can substitute a stand-in tool after the original already
        # ran, so "nothing happened yet" only holds until this call produces
        # its first result. After that a schema failure is a real failure.
        results_before = len(run.tool_results)
        while True:
            try:
                result = self.tool_runtime.execute(tool, arguments, run.context)
            except PolicyRejectedError as exc:
                if exc.decision is not None:
                    audit("policy", exc.decision.to_dict())
                if exc.decision is not None and exc.decision.escalated:
                    return _CallOutcome(
                        control=self._pause(
                            run.state,
                            run.trace_id,
                            self._confirmation(
                                run.task_id,
                                "execution",
                                tool.metadata,
                                arguments=arguments,
                                decision=exc.decision.to_dict(),
                            ),
                            detail=(
                                f"paused for human approval: execute {tool.metadata.identity} "
                                f"(side_effect={tool.metadata.side_effect})"
                            ),
                            frame=run.frame(),
                            tool_results=run.tool_results,
                            skipped=run.skipped,
                        )
                    )
                failure = self.recovery.classify_denial(tool.metadata, exc.message)
                audit("recover", {"failure": failure.to_dict(), "action": "deny"})
                return _CallOutcome(
                    control=self._finish(
                        run.state,
                        run.trace_id,
                        "denied",
                        detail=(
                            f"{exc.message}; grant the missing permissions via "
                            "PolicyContext(granted_permissions=...) or --granted-permission"
                        ),
                        tool_results=run.tool_results,
                        skipped=run.skipped,
                    )
                )
            except ToolInputError as exc:
                # A SecretRef that cannot be materialized is not a mistake the
                # model can correct, and the resolver names the backing
                # variable -- neither belongs in the conversation.
                repairable = not isinstance(exc, SecretResolutionError) and len(run.tool_results) == results_before
                failure = self.recovery.classify_validation(tool.metadata, str(exc))
                audit("recover", {"failure": failure.to_dict(), "action": "repair" if repairable else "fail"})
                audit("execute", {"tool": label, "status": "invalid_input", "error": str(exc)})
                if not abort_on_failure:
                    return _CallOutcome(failure=failure)
                if repairable:
                    return _CallOutcome(invalid_input=str(exc), tool=tool)
                return _CallOutcome(
                    control=self._finish(
                        run.state,
                        run.trace_id,
                        "failed",
                        detail=str(exc),
                        tool_results=run.tool_results,
                        skipped=run.skipped,
                    )
                )
            audit("execute", result.to_dict())
            self.state_store.append(run.task_id, "step", {"result": result.to_dict()})
            run.tool_results.append(result)
            if result.succeeded:
                self.recovery.circuit_breaker.record_success(tool.metadata.identity)
                return _CallOutcome(result=result, tool=tool)

            failure = self.recovery.classify_tool_result(result, tool.metadata)
            self.recovery.circuit_breaker.record_failure(failure.resource)
            tried = [str(item) for item in entry.get("tried", ())]
            alternatives = self._alternative_tool_ids(tool, arguments, run.tools, tried, run.context)
            decision = self.recovery.decide(
                failure, attempts=int(entry.get("attempts", 0)), alternatives=alternatives
            )
            audit("recover", decision.to_dict())
            if decision.action == "retry":
                entry["attempts"] = int(entry.get("attempts", 0)) + 1
                self.recovery.wait(decision.backoff_seconds)
                continue
            if decision.action == "fallback":
                replacement, reason = self._resolve_fallback(
                    decision.alternative, run.tools_by_name, run.context
                )
                entry["tried"] = tried + [tool.metadata.id]
                if replacement is None:
                    audit(
                        "recover",
                        {"action": "fallback_failed", "resource": decision.alternative, "reason": reason},
                    )
                    extra = f"fallback to {decision.alternative} was not usable: {reason}"
                    if not abort_on_failure:
                        return _CallOutcome(failure=failure)
                    return _CallOutcome(control=self._abort(run, failure, extra=extra))
                audit(
                    "recover",
                    {
                        "action": "fallback_selected",
                        "from": tool.metadata.identity,
                        "to": replacement.metadata.identity,
                    },
                )
                tool = replacement
                run.tools.append(replacement)
                entry["attempts"] = 0
                continue
            if decision.action == "escalate":
                entry["attempts"] = int(entry.get("attempts", 0)) + 1
                return _CallOutcome(
                    control=self._pause(
                        run.state,
                        run.trace_id,
                        self._recovery_confirmation(run.task_id, tool.metadata, arguments, decision),
                        detail=(
                            f"paused after a {failure.kind} failure of {tool.metadata.identity}: "
                            f"{failure.message}"
                        ),
                        frame=run.frame(),
                        tool_results=run.tool_results,
                        skipped=run.skipped,
                    )
                )
            if not abort_on_failure:
                return _CallOutcome(failure=failure)
            return _CallOutcome(control=self._abort(run, failure, extra=decision.reason))

    def _run_agent_call(
        self,
        run: "_RunState",
        agent: BoundAgent | None,
        arguments: Mapping[str, Any],
        call_id: str,
        *,
        label: str = "",
        abort_on_failure: bool = True,
    ) -> "_CallOutcome":
        """Delegate one synchronous Agent call through Agent/Tool Runtime."""

        if agent is None:
            failure = Failure(
                kind="activation",
                message=f"agent {label!r} is not activated",
                resource=label,
                stage="delegation",
            )
            return _CallOutcome(failure=failure)
        audit = run.audit
        arguments = dict(arguments)
        label = label or agent.metadata.id
        try:
            ensure_secret_refs(arguments)
        except SecretResolutionError as exc:
            failure = Failure(
                kind="validation",
                message=str(exc),
                resource=agent.metadata.identity,
                stage="delegation",
            )
            audit("recover", {"failure": failure.to_dict(), "action": "fail"})
            if not abort_on_failure:
                return _CallOutcome(failure=failure)
            return _CallOutcome(
                control=self._finish(
                    run.state,
                    run.trace_id,
                    "failed",
                    detail=str(exc),
                    tool_results=run.tool_results,
                    agent_results=run.agent_results,
                    skipped=run.skipped,
                )
            )
        if self._needs_confirmation(agent.metadata, run.context):
            return _CallOutcome(
                control=self._pause(
                    run.state,
                    run.trace_id,
                    self._confirmation(
                        run.task_id,
                        "execution",
                        agent.metadata,
                        arguments=arguments,
                        always_confirm=True,
                    ),
                    detail=f"paused for human approval: delegate to {agent.metadata.identity}",
                    frame=run.frame(),
                    tool_results=run.tool_results,
                    agent_results=run.agent_results,
                    skipped=run.skipped,
                )
            )

        self.state_store.checkpoint(run.task_id, f"before:{call_id}")
        entry = run.recovery_state.setdefault(call_id, {"attempts": 0, "tried": []})
        while True:
            try:
                result = self.agent_runtime.execute(
                    agent,
                    arguments,
                    run.context,
                    depth=1,
                    cumulative_cost=sum(item.cost for item in run.agent_results),
                    delegated_permissions=agent.metadata.required_permissions,
                )
            except PolicyRejectedError as exc:
                if exc.decision is not None:
                    audit("policy", exc.decision.to_dict())
                if exc.decision is not None and exc.decision.escalated:
                    return _CallOutcome(
                        control=self._pause(
                            run.state,
                            run.trace_id,
                            self._confirmation(
                                run.task_id,
                                "execution",
                                agent.metadata,
                                arguments=arguments,
                                decision=exc.decision.to_dict(),
                            ),
                            detail=f"paused for human approval: delegate to {agent.metadata.identity}",
                            frame=run.frame(),
                            tool_results=run.tool_results,
                            agent_results=run.agent_results,
                            skipped=run.skipped,
                        )
                    )
                failure = self.recovery.classify_denial(agent.metadata, exc.message)
                audit("recover", {"failure": failure.to_dict(), "action": "deny"})
                return _CallOutcome(
                    control=self._finish(
                        run.state,
                        run.trace_id,
                        "denied",
                        detail=exc.message,
                        tool_results=run.tool_results,
                        agent_results=run.agent_results,
                        skipped=run.skipped,
                    )
                )
            except ToolInputError as exc:
                failure = Failure(
                    kind="validation",
                    message=str(exc),
                    resource=agent.metadata.identity,
                    stage="delegation",
                )
                audit("recover", {"failure": failure.to_dict(), "action": "fail"})
                audit("delegate", {"agent": label, "status": "invalid_input", "error": str(exc)})
                if not abort_on_failure:
                    return _CallOutcome(failure=failure)
                return _CallOutcome(
                    control=self._finish(
                        run.state,
                        run.trace_id,
                        "failed",
                        detail=str(exc),
                        tool_results=run.tool_results,
                        agent_results=run.agent_results,
                        skipped=run.skipped,
                    )
                )

            audit("delegate", result.to_dict())
            self.state_store.append(run.task_id, "step", {"result": result.to_dict()})
            run.agent_results.append(result)
            if result.succeeded:
                self.recovery.circuit_breaker.record_success(agent.metadata.identity)
                return _CallOutcome(result=result, agent=agent)

            failure = self.recovery.classify_agent_result(result, agent.metadata)
            self.recovery.circuit_breaker.record_failure(failure.resource)
            tried = [str(item) for item in entry.get("tried", ())]
            alternatives = self._alternative_agent_ids(
                agent, arguments, run.agents, tried, run.context
            )
            decision = self.recovery.decide(
                failure,
                attempts=int(entry.get("attempts", 0)),
                alternatives=alternatives,
            )
            audit("recover", decision.to_dict())
            if decision.action == "retry":
                entry["attempts"] = int(entry.get("attempts", 0)) + 1
                self.recovery.wait(decision.backoff_seconds)
                continue
            if decision.action == "fallback":
                replacement, reason = self._resolve_agent_fallback(
                    decision.alternative, run.agents_by_name, run.context
                )
                entry["tried"] = tried + [agent.metadata.id]
                if replacement is None:
                    audit(
                        "recover",
                        {
                            "action": "fallback_failed",
                            "resource": decision.alternative,
                            "reason": reason,
                        },
                    )
                    if not abort_on_failure:
                        return _CallOutcome(failure=failure)
                    return _CallOutcome(
                        control=self._abort(
                            run,
                            failure,
                            extra=(
                                f"fallback to {decision.alternative} was not usable: {reason}"
                            ),
                        )
                    )
                audit(
                    "recover",
                    {
                        "action": "fallback_selected",
                        "from": agent.metadata.identity,
                        "to": replacement.metadata.identity,
                    },
                )
                agent = replacement
                if replacement not in run.agents:
                    run.agents.append(replacement)
                entry["attempts"] = 0
                continue
            if decision.action == "escalate":
                entry["attempts"] = int(entry.get("attempts", 0)) + 1
                return _CallOutcome(
                    control=self._pause(
                        run.state,
                        run.trace_id,
                        self._recovery_confirmation(run.task_id, agent.metadata, arguments, decision),
                        detail=(
                            f"paused after a {failure.kind} failure of {agent.metadata.identity}: "
                            f"{failure.message}"
                        ),
                        frame=run.frame(),
                        tool_results=run.tool_results,
                        agent_results=run.agent_results,
                        skipped=run.skipped,
                    )
                )
            if not abort_on_failure:
                return _CallOutcome(failure=failure)
            return _CallOutcome(control=self._abort(run, failure, extra=decision.reason))

    # -- plan-driven execution (4.6) -------------------------------------------

    def _execute_plan(self, run: "_RunState", compiled: Any) -> TaskResult:
        """Build (or resume) a plan and run it to completion (F-PLAN-01/04/06)."""

        assert self.planner is not None
        state = self.state_store.load(run.task_id)
        definitions = [
            *(tool.definition for tool in run.tools),
            *(agent.definition for agent in run.agents),
        ]
        resources = resources_by_id(definitions)
        plan = Plan.from_dict(state.plan) if state.plan else None

        if plan is None:
            plan = self.planner.plan(run.state.goal, definitions, context=run.context)
            issues = validate_plan(plan, resources, run.context)
            run.audit(
                "plan",
                {"event": "created", **plan.summary(), "issues": [issue.to_dict() for issue in issues]},
            )
            if issues:
                return self._finish(
                    run.state,
                    run.trace_id,
                    "failed",
                    detail=(
                        "the plan did not validate: "
                        + "; ".join(f"{issue.path}: {issue.message}" for issue in issues[:4])
                        + "; fix the planner or widen the selected resource set"
                    ),
                    tool_results=run.tool_results,
                    skipped=run.skipped,
                )
            if not plan.steps:
                return self._finish(
                    run.state,
                    run.trace_id,
                    "failed",
                    detail=(
                        "the planner produced no steps for this goal; "
                        "check that the selected set contains usable Tool or Agent resources"
                    ),
                    tool_results=run.tool_results,
                    skipped=run.skipped,
                )
            self.state_store.append(run.task_id, "plan", {"plan": plan.to_dict()})

        replans = 0
        while not plan.complete:
            ready = plan.ready()
            if not ready:
                stuck = ", ".join(step.id for step in plan.steps if not step.done)
                return self._finish(
                    run.state,
                    run.trace_id,
                    "failed",
                    detail=f"plan cannot progress; steps blocked by unmet dependencies: {stuck}",
                    tool_results=run.tool_results,
                    skipped=run.skipped,
                )
            plan, control, failure = self._run_wave(run, plan, ready)
            self.state_store.append(run.task_id, "plan", {"plan": plan.to_dict()})
            if control is not None:
                return control
            if failure is None:
                continue

            # F-PLAN-04: revise the plan around the failure instead of ending.
            if replans >= self.max_replans:
                return self._abort(run, failure, extra=f"re-planned {replans} time(s) without success")
            self._rollback_failed_plan_step(run, failure)
            revised = self.planner.replan(
                plan, definitions, context=run.context, failure=failure.to_dict()
            )
            issues = validate_plan(revised, resources, run.context)
            run.audit(
                "plan",
                {
                    "event": "replanned",
                    **revised.summary(),
                    "issues": [issue.to_dict() for issue in issues],
                    "failure": failure.to_dict(),
                },
            )
            pending = [step for step in revised.steps if not step.done]
            if issues or not pending:
                return self._abort(
                    run,
                    failure,
                    extra="re-planning found no usable alternative"
                    if not issues
                    else "the revised plan did not validate",
                )
            replans += 1
            plan = revised
            self.state_store.append(run.task_id, "plan", {"plan": plan.to_dict()})

        return self._finish_plan(run, plan, compiled)

    def _run_wave(
        self,
        run: "_RunState",
        plan: Plan,
        ready: Sequence[PlanStep],
    ) -> tuple[Plan, TaskResult | None, Failure | None]:
        """Run one dependency wave; independent steps go in parallel (F-PLAN-05)."""

        workers = min(self.max_parallel_steps, len(ready))
        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="marmo-step") as pool:
                outcomes = list(pool.map(lambda step: (step, self._run_step(run, step)), ready))
        else:
            outcomes = [(step, self._run_step(run, step)) for step in ready]

        control: TaskResult | None = None
        failure: Failure | None = None
        for step, outcome in outcomes:
            if outcome.control is not None:
                # Two parallel steps can both pause; the operator answers the
                # one left pending and the other re-raises on resume.
                control = control or outcome.control
                continue
            if outcome.failure is not None:
                plan = plan.with_status(step.id, "failed", {"error": outcome.failure.message})
                if failure is None:
                    failure = Failure(
                        kind=outcome.failure.kind,
                        message=outcome.failure.message,
                        resource=outcome.failure.resource,
                        stage=outcome.failure.stage,
                        detail={**outcome.failure.detail, "step_id": step.id},
                    )
                continue
            plan = plan.with_status(
                step.id, "completed", outcome.result.to_dict() if outcome.result else None
            )
        return plan, control, failure

    def _rollback_failed_plan_step(self, run: "_RunState", failure: Failure) -> None:
        """Restore the pre-step state before asking the Planner for a revision.

        Audit records remain append-only. For a parallel wave, successful
        sibling results written after the failed step's checkpoint are
        re-applied after the task-level rollback so completed side effects
        remain represented and are not executed again.
        """

        step_id = str(failure.detail.get("step_id", ""))
        label = f"before:{step_id}" if step_id else ""
        checkpoints = [
            item for item in self.state_store.checkpoints(run.task_id) if item.label == label
        ]
        if not checkpoints:
            run.audit(
                "recover",
                {
                    "action": "rollback_skipped",
                    "reason": f"no checkpoint found for failed plan step {step_id or '<unknown>'}",
                },
            )
            return

        checkpoint = checkpoints[-1]
        failed_id = failure.resource.rsplit("@", 1)[0]
        preserved: list[dict[str, Any]] = []
        for event in self.state_store.events(run.task_id):
            if event.seq <= checkpoint.seq or event.kind != "step":
                continue
            result = event.payload.get("result")
            if not isinstance(result, Mapping):
                continue
            resource_id = str(result.get("tool_id") or result.get("agent_id") or "")
            if resource_id and resource_id != failed_id:
                preserved.append(dict(result))

        self.state_store.rollback(run.task_id, checkpoint.seq)
        for result in preserved:
            self.state_store.append(run.task_id, "step", {"result": result})
        restored = self.state_store.load(run.task_id)
        run.tool_results[:] = [
            ToolResult.from_dict(item) for item in restored.step_results if "tool_id" in item
        ]
        run.agent_results[:] = [
            AgentResult.from_dict(item) for item in restored.step_results if "agent_id" in item
        ]
        run.audit(
            "recover",
            {
                "action": "rollback",
                "checkpoint": checkpoint.to_dict(),
                "failed_step": step_id,
                "preserved_parallel_results": len(preserved),
            },
        )

    def _run_step(self, run: "_RunState", step: PlanStep) -> "_CallOutcome":
        agent = run.agents_by_name.get(step.resource_id)
        if agent is not None:
            run.audit("plan", {"event": "step_started", "step": step.id, "resource": step.resource_id})
            return self._run_agent_call(
                run,
                agent,
                step.arguments,
                step.id,
                label=step.resource_id,
                abort_on_failure=False,
            )
        tool = run.tools_by_name.get(step.resource_id)
        if tool is None:
            resolved, reason = self._resolve_fallback(step.resource_id, run.tools_by_name, run.context)
            if resolved is None:
                return _CallOutcome(
                    failure=Failure(
                        kind="activation",
                        message=f"step {step.id} needs {step.resource_id}, which is not usable: {reason}",
                        resource=step.resource_id,
                        stage="activation",
                    )
                )
            tool = resolved
        run.audit("plan", {"event": "step_started", "step": step.id, "resource": step.resource_id})
        return self._run_tool_call(
            run, tool, step.arguments, step.id, label=step.resource_id, abort_on_failure=False
        )

    def _finish_plan(self, run: "_RunState", plan: Plan, compiled: Any) -> TaskResult:
        """Turn a completed plan into a final answer."""

        messages = list(compiled.messages)
        # The step results are handed over as one user turn, not as ``tool``
        # messages: nothing in this conversation ever requested a tool call, and
        # a tool message without the assistant tool_call it answers is a
        # malformed request that both the OpenAI and Anthropic APIs reject --
        # which used to make every plan run fall back to the canned summary.
        sections: list[str] = []
        for step in plan.steps:
            if step.status != "completed" or not step.result:
                continue
            output = step.result.get("output")
            source_kind = "agent" if "agent_id" in step.result else "tool"
            source = f"{source_kind}:{step.resource_id}"
            findings = self.prompt_injection_inspector.inspect(output)
            if findings:
                run.audit(
                    "security",
                    {
                        "event": "prompt_injection_detected",
                        "source": source,
                        "trust": "untrusted_content",
                        "findings": [finding.to_dict() for finding in findings],
                    },
                )
            sections.append(
                f"Result of step {step.id} ({step.resource_id}):\n"
                + self._tool_message_content(output, source=source)
            )
        if sections:
            messages.append(
                ChatMessage(
                    role="user",
                    content=(
                        "The plan for the goal above has finished. Answer the goal using these "
                        "step results.\n\n" + "\n\n".join(sections)
                    ),
                )
            )
        output = ""
        try:
            response = self.llm.complete(messages, ())
            output = response.content
            run.audit("llm", {"round": "plan-summary", "content_chars": len(output), "usage": response.usage})
        except Exception as exc:  # noqa: BLE001 - the work is done; only the wording is missing
            run.audit("llm", {"round": "plan-summary", "error": f"{type(exc).__name__}: {exc}"})
        if not output:
            done = ", ".join(step.resource_id for step in plan.steps if step.status == "completed")
            output = f"Plan complete over {len(plan.steps)} step(s): {done}"
        detail = f"executed a {len(plan.steps)}-step plan (revision {plan.revision})"
        if run.skipped:
            names = ", ".join(item["resource"] for item in run.skipped)
            detail += f"; skipped {len(run.skipped)} resource(s): {names}"
        return self._finish(
            run.state,
            run.trace_id,
            "completed",
            output=output,
            detail=detail,
            tool_results=run.tool_results,
            skipped=run.skipped,
        )

    def _alternative_tool_ids(
        self,
        failed: BoundTool,
        arguments: Mapping[str, Any],
        activated: Sequence[BoundTool],
        tried: Sequence[str],
        context: PolicyContext,
    ) -> list[str]:
        """Tools that could stand in for ``failed`` with the same arguments (F-RECOV-03).

        Already-activated tools come first because they cost nothing; only if
        none fit does this ask the Retriever for a replacement.
        """

        wanted = set(failed.metadata.capabilities)
        excluded = {failed.metadata.id, *tried}

        def usable(metadata: ResourceMetadata, schema: Mapping[str, Any]) -> bool:
            if metadata.id in excluded or metadata.kind != "tool":
                return False
            if wanted and not wanted & set(metadata.capabilities):
                return False
            # A stand-in that cannot accept the same arguments is no stand-in.
            return not validate_arguments(schema, arguments)

        found = [tool.metadata.id for tool in activated if usable(tool.metadata, tool.input_schema)]
        if found:
            return found
        query = SearchQuery(
            task=" ".join((failed.metadata.name, *failed.metadata.capabilities)),
            kinds=("tool",),
            granted_permissions=tuple(context.granted_permissions),
            top_k=self.top_k,
        )
        for result in self.retriever.search(self.registry, query):
            definition = result.resource
            schema = definition.extras.get("input_schema")
            if usable(definition.metadata, schema if isinstance(schema, Mapping) else {}):
                found.append(definition.metadata.id)
        return found

    def _alternative_agent_ids(
        self,
        failed: BoundAgent,
        arguments: Mapping[str, Any],
        activated: Sequence[BoundAgent],
        tried: Sequence[str],
        context: PolicyContext,
    ) -> list[str]:
        """Agents that can accept the failed delegation without widening it."""

        wanted = set(failed.metadata.capabilities)
        excluded = {failed.metadata.id, *tried}

        def usable(metadata: ResourceMetadata, schema: Mapping[str, Any]) -> bool:
            if metadata.id in excluded or metadata.kind != "agent":
                return False
            if wanted and not wanted & set(metadata.capabilities):
                return False
            return not validate_arguments(schema, arguments)

        found = [
            agent.metadata.id
            for agent in activated
            if usable(agent.metadata, agent.input_schema)
        ]
        if found:
            return found
        query = SearchQuery(
            task=" ".join((failed.metadata.name, *failed.metadata.capabilities)),
            kinds=("agent",),
            granted_permissions=tuple(context.granted_permissions),
            top_k=self.top_k,
        )
        for result in self.retriever.search(self.registry, query):
            definition = result.resource
            card = definition.extras.get("agent_card")
            card = card if isinstance(card, Mapping) else {}
            schema = card.get("input_schema", definition.extras.get("input_schema"))
            if not isinstance(schema, Mapping):
                schema = {
                    "type": "object",
                    "required": ["goal"],
                    "properties": {"goal": {"type": "string"}},
                    "additionalProperties": False,
                }
            if usable(definition.metadata, schema):
                found.append(definition.metadata.id)
        return found

    def _resolve_fallback(
        self,
        tool_id: str,
        tools_by_name: dict[str, BoundTool],
        context: PolicyContext,
    ) -> tuple[BoundTool | None, str]:
        """Activate the stand-in tool, through the gate like any other."""

        existing = tools_by_name.get(tool_id)
        if existing is not None:
            return existing, ""
        try:
            definition = self.registry.get(tool_id)
        except ResourceNotFoundError as exc:
            return None, str(exc)
        activation = self.activator.activate(definition, context)
        if not activation.ok or not isinstance(activation.activated, BoundTool):
            return None, activation.error or activation.decision.reason
        tools_by_name[tool_id] = activation.activated
        return activation.activated, ""

    def _resolve_agent_fallback(
        self,
        agent_id: str,
        agents_by_name: dict[str, BoundAgent],
        context: PolicyContext,
    ) -> tuple[BoundAgent | None, str]:
        """Activate an alternative Agent through the normal activation gate."""

        existing = agents_by_name.get(agent_id)
        if existing is not None:
            return existing, ""
        try:
            definition = self.registry.get(agent_id)
        except ResourceNotFoundError as exc:
            return None, str(exc)
        activation = self.activator.activate(definition, context)
        if not activation.ok or not isinstance(activation.activated, BoundAgent):
            return None, activation.error or activation.decision.reason
        agent = activation.activated
        agents_by_name[agent.metadata.id] = agent
        agents_by_name[AgentInterface.from_definition(agent.definition).name] = agent
        return agent, ""

    def _abort(self, run: "_RunState", failure: Failure, *, extra: str = "") -> TaskResult:
        """End a task that recovery could not save, undoing what it can (F-RECOV-05)."""

        detail = f"{failure.kind} failure of {failure.resource}: {failure.message}"
        if extra:
            detail += f"; {extra}"
        if self.compensate_on_failure:
            performed = self._compensate(run.tool_results, run.context, run.audit)
            if performed:
                undone = [item["step"] for item in performed if item["status"] == "compensated"]
                unresolved = [item["step"] for item in performed if item["status"] != "compensated"]
                if undone:
                    detail += f"; compensated: {', '.join(undone)}"
                if unresolved:
                    detail += f"; NOT undone: {', '.join(unresolved)}"
        return self._finish(
            run.state, run.trace_id, "failed", detail=detail,
            tool_results=run.tool_results, skipped=run.skipped,
        )

    def _compensate(
        self,
        tool_results: Sequence[ToolResult],
        context: PolicyContext,
        audit: Callable[[str, Mapping[str, Any]], None],
    ) -> list[dict[str, str]]:
        """Run declared undo tools for completed side effects, newest first.

        Compensating tools pass the same gates as any other execution, so an
        undo can never do something the task was not allowed to do. A blocked
        or undeclared compensation is reported rather than silently skipped.
        """

        performed: list[dict[str, str]] = []
        tools_by_name: dict[str, BoundTool] = {}
        for result in reversed(tool_results):
            # A dry-run result means validation completed but no side effect
            # happened, so there is nothing to compensate.
            if not result.executed:
                continue
            try:
                definition = self.registry.get(result.tool_id, result.tool_version)
            except ResourceNotFoundError:
                continue
            if not needs_compensation(definition.metadata):
                continue
            undo_id = compensation_for(definition)
            if not undo_id:
                performed.append({"step": result.tool_id, "status": "undeclared"})
                audit("compensate", {"step": result.tool_id, "status": "undeclared"})
                continue
            undo, reason = self._resolve_fallback(undo_id, tools_by_name, context)
            if undo is None:
                performed.append({"step": result.tool_id, "status": "unavailable"})
                audit("compensate", {"step": result.tool_id, "status": "unavailable", "reason": reason})
                continue
            try:
                undo_result = self.tool_runtime.execute(undo, result.arguments, context)
            except (PolicyRejectedError, ToolInputError) as exc:
                performed.append({"step": result.tool_id, "status": "blocked"})
                audit("compensate", {"step": result.tool_id, "status": "blocked", "reason": str(exc)})
                continue
            status = "compensated" if undo_result.succeeded else "failed"
            performed.append({"step": result.tool_id, "status": status})
            audit(
                "compensate",
                {"step": result.tool_id, "undo": undo_id, "status": status, "error": undo_result.error},
            )
        return performed

    def _recovery_confirmation(
        self,
        task_id: str,
        metadata: ResourceMetadata,
        arguments: Mapping[str, Any],
        decision: RecoveryDecision,
    ) -> HitlRequest:
        """Ask a person whether to try a failing step again (F-RECOV-06)."""

        return HitlRequest.create(
            task_id=task_id,
            stage="execution",
            operation=f"retry or abandon {metadata.identity} after a {decision.failure.kind} failure",
            impact=f"{decision.failure.message}; {decision.reason}",
            alternatives=(
                "approve to grant a fresh retry budget for this step",
                "reject to end the task and run any declared compensations",
            ),
            recommendation="reject",
            resource=metadata.identity,
            arguments=dict(arguments),
            decision={"recovery": decision.to_dict()},
        )

    def _confirmation(
        self,
        task_id: str,
        stage: str,
        metadata: ResourceMetadata,
        *,
        arguments: Mapping[str, Any] | None = None,
        decision: Mapping[str, Any] | None = None,
        always_confirm: bool = False,
    ) -> HitlRequest:
        verb = "activate" if stage == "activation" else "execute"
        impact = (
            f"side_effect={metadata.side_effect}, trust_level={metadata.trust_level}, "
            f"cost_estimate={metadata.cost_estimate:g}"
        )
        review: dict[str, Any] = dict(decision) if decision else {}
        if always_confirm:
            impact += "; the HITL policy always confirms this resource"
            # Recorded on the request, not only in the prose, so every pause
            # built this way gets the right remedy without its call site
            # having to remember to pass one.
            review["always_confirm"] = True
        findings = decision.get("risk_findings", ()) if decision else ()
        if findings:
            messages = [str(item.get("message", "")) for item in findings if isinstance(item, Mapping)]
            impact += "; safety findings: " + "; ".join(message for message in messages if message)
        alternatives = [
            "reject to end the task",
            f"skip {metadata.id} by narrowing the goal or the granted permissions",
        ]
        if stage == "execution":
            alternatives.append("modify to replace the tool arguments before it runs")
        recommendation = "approve" if metadata.side_effect in ("none", "read") else "reject"
        review_arguments = serialize_secret_refs(arguments) if arguments is not None else None
        if findings and arguments is not None:
            review_arguments = redact_sensitive_arguments(review_arguments)
        return HitlRequest.create(
            task_id=task_id,
            stage=stage,
            operation=f"{verb} {metadata.kind} {metadata.name} ({metadata.identity})",
            impact=impact,
            alternatives=tuple(alternatives),
            recommendation=recommendation,
            resource=metadata.identity,
            arguments=review_arguments,
            decision=review or None,
        )

    def _pause_remedy(self, request: HitlRequest) -> str:
        """The sentence that tells an operator how to actually clear this pause.

        The remedies are not interchangeable. A blanket
        ``PolicyContext(human_approved=True)`` clears a side-effect
        escalation, but deliberately does not clear a safety finding or an
        "always confirm" rule -- both are scoped to the exact call a person
        was shown. Naming the wrong one sends people round a loop that cannot
        terminate, which is what the old fixed wording did.
        """

        approve = "Answer with Kernel.resume(task_id, HitlResponse(kind='approve'))"
        decision = request.decision or {}
        if "recovery" in decision:
            return f"{approve} to give the step a fresh retry budget, or kind='reject' to end the task"
        if decision.get("always_confirm"):
            return (
                f"{approve}; an always-confirm rule is answered per resource, so "
                "PolicyContext(human_approved=True) does not clear it"
            )
        if decision.get("approval_token"):
            return (
                f"{approve}; the approval is scoped to the exact call under review, so "
                "PolicyContext(human_approved=True) does not clear this one"
            )
        if request.stage == "selection":
            return (
                f"{approve} once the missing permissions are granted, or re-run with "
                "PolicyContext(granted_permissions=...) / --granted-permission"
            )
        return f"{approve}, or re-run with PolicyContext(human_approved=True) after a human review"

    def _pause(
        self,
        state: TaskState,
        trace_id: str,
        request: HitlRequest,
        *,
        detail: str,
        remedy: str | None = None,
        frame: Mapping[str, Any] | None = None,
        tool_results: Iterable[ToolResult] = (),
        agent_results: Iterable[AgentResult] | None = None,
        skipped: Iterable[Mapping[str, str]] = (),
    ) -> TaskResult:
        """Persist the escalation and stop, leaving the task resumable."""

        results = tuple(tool_results)
        agents = (
            tuple(agent_results)
            if agent_results is not None
            else _stored_agent_results(self.state_store.load(state.task_id))
        )
        detail = f"{detail}. {remedy or self._pause_remedy(request)}"
        payload: dict[str, Any] = {"request": request.to_dict(), "detail": detail}
        if frame is not None:
            payload["frame"] = dict(frame)
        state = self.state_store.append(state.task_id, "paused", payload)
        self.audit_log.append("hitl", {"event": "requested", "request": request.to_dict()}, trace_id=trace_id)
        self.audit_log.append(
            "task",
            {
                "task_id": state.task_id,
                "goal": state.goal,
                "status": "escalated",
                "detail": detail,
                "output_chars": 0,
                "tool_calls": len(results),
                "agent_calls": len(agents),
            },
            trace_id=trace_id,
        )
        return TaskResult(
            task_id=state.task_id,
            goal=state.goal,
            status="escalated",
            detail=detail,
            tool_results=results,
            agent_results=agents,
            skipped_resources=tuple(dict(item) for item in skipped),
            trace_id=trace_id,
            hitl_request=request.to_dict(),
        )

    def _finish(
        self,
        state: TaskState,
        trace_id: str,
        status: str,
        *,
        output: str = "",
        detail: str = "",
        tool_results: Iterable[ToolResult] = (),
        agent_results: Iterable[AgentResult] | None = None,
        skipped: Iterable[Mapping[str, str]] = (),
    ) -> TaskResult:
        results = tuple(tool_results)
        agents = (
            tuple(agent_results)
            if agent_results is not None
            else _stored_agent_results(self.state_store.load(state.task_id))
        )
        self.state_store.append(
            state.task_id,
            "status",
            {"status": status, "detail": detail, "output": output, "trace_id": trace_id},
        )
        self.audit_log.append(
            "task",
            {
                "task_id": state.task_id,
                "goal": state.goal,
                "status": status,
                "detail": detail,
                "output_chars": len(output),
                "tool_calls": len(results),
                "agent_calls": len(agents),
            },
            trace_id=trace_id,
        )
        result = TaskResult(
            task_id=state.task_id,
            goal=state.goal,
            status=status,
            output=output,
            detail=detail,
            tool_results=results,
            agent_results=agents,
            skipped_resources=tuple(dict(item) for item in skipped),
            trace_id=trace_id,
        )
        self._results[state.task_id] = result
        return result

    def _result_from_state(self, state: TaskState, hitl_request: Mapping[str, Any] | None = None) -> TaskResult:
        """Rebuild a result from stored state (e.g. after a process restart)."""

        pending = hitl_request if hitl_request is not None else state.pending
        return TaskResult(
            task_id=state.task_id,
            goal=state.goal,
            status=state.status,
            output=state.output,
            detail=state.detail,
            tool_results=tuple(
                ToolResult.from_dict(item) for item in state.step_results if "tool_id" in item
            ),
            agent_results=_stored_agent_results(state),
            trace_id=state.trace_id,
            hitl_request=dict(pending) if pending else None,
        )


def _stored_agent_results(state: TaskState) -> tuple[AgentResult, ...]:
    return tuple(AgentResult.from_dict(item) for item in state.step_results if "agent_id" in item)


def _coerce_response(value: HitlResponse | Mapping[str, Any]) -> HitlResponse:
    if isinstance(value, HitlResponse):
        return value
    if isinstance(value, Mapping):
        return HitlResponse.from_dict(value)
    raise HitlError(
        f"hitl_response must be a HitlResponse or a mapping, got {type(value).__name__}; "
        "e.g. HitlResponse(kind='approve', responder='alice')"
    )


def _merge(base: Sequence[str], addition: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(tuple(base) + tuple(addition)))


def _missing_permissions(results: Sequence[SearchResult], granted: Sequence[str]) -> tuple[str, ...]:
    """Permissions the candidates need that the task context does not hold."""

    held = set(granted)
    missing: list[str] = []
    for result in results:
        for permission in result.resource.metadata.required_permissions:
            if permission not in held and permission not in missing:
                missing.append(permission)
    return tuple(missing)


def _message_from_dict(data: Mapping[str, Any]) -> ChatMessage:
    calls = data.get("tool_calls")
    return ChatMessage(
        role=str(data.get("role", "")),
        content=str(data.get("content", "")),
        name=str(data.get("name", "")),
        tool_calls=tuple(_tool_call_from_dict(item) for item in calls) if isinstance(calls, (list, tuple)) else (),
    )


def _tool_call_from_dict(data: Mapping[str, Any]) -> ToolCall:
    arguments = data.get("arguments")
    return ToolCall(
        id=str(data.get("id", "")),
        name=str(data.get("name", "")),
        arguments=dict(arguments) if isinstance(arguments, Mapping) else {},
    )
