"""Command line interface for Marmo-Core v1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import argparse
import importlib
import json
import sys

from .formatting import (
    print_json,
    render_inspection,
    render_policy_decision,
    render_resource_table,
    render_search_table,
    render_selected_set,
)
from .audit import AuditLog
from .connectors import (
    Connector,
    ConnectorConfig,
    FileSystemConnector,
    HTTPConnector,
    SQLiteConnector,
    ShellConnector,
)
from .errors import MarmoError
from .hitl import ConsoleHitlBroker, HitlPolicy, HitlResponse, PendingHitlBroker
from .kernel import Kernel
from .llm import MockLLMProvider
from .loader import load_registry, validate_resource_paths
from .models import KINDS, SIDE_EFFECTS, TRUST_LEVELS, SearchQuery
from .package import verify_local_package, write_package_lock
from .planner import LLMPlanner, Planner, RuleBasedPlanner
from .policy import PolicyContext, PolicyGateway
from .recovery import CircuitBreaker, RecoveryManager, RetryPolicy
from .retriever import LexicalRetriever
from .selector import DEFAULT_SET_LIMITS, RuleBasedSetSelector
from .security import ISOLATION_LEVELS
from .state import InMemoryStateStore, JsonFileStateStore


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (MarmoError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marmo", description="Marmo-Core v1 unified resource CLI")
    subparsers = parser.add_subparsers(required=True)

    validate_parser = subparsers.add_parser("validate", help="validate local resource definition files")
    validate_parser.add_argument("paths", nargs="*", help="resource files or directories")
    validate_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    validate_parser.set_defaults(func=_cmd_validate)

    list_parser = subparsers.add_parser("list", help="list resources from local definition files")
    _add_path_arg(list_parser)
    _add_common_filters(list_parser)
    list_parser.add_argument("--format", choices=("table", "json"), default="table")
    list_parser.set_defaults(func=_cmd_list)

    search_parser = subparsers.add_parser("search", help="search across Memory, Skill, Tool, and Agent resources")
    _add_path_arg(search_parser)
    _add_common_filters(search_parser)
    search_parser.add_argument("--task", default="", help="natural-language task description")
    search_parser.add_argument("--keyword", action="append", default=[], help="required keyword filter; repeatable")
    search_parser.add_argument("--granted-permission", action="append", default=[], help="permission granted to the search context; repeatable")
    search_parser.add_argument("--require-permissions", action="store_true", help="drop resources whose permissions are not fully granted")
    search_parser.add_argument("--top-k", type=int, default=10, help="maximum number of search results to display")
    search_parser.add_argument("--per-kind-limit", action="append", default=[], metavar="KIND=N", help="limit displayed results per kind; repeatable")
    search_parser.add_argument("--set-limit", action="append", default=[], metavar="KIND=N", help="limit selected set per kind; repeatable")
    search_parser.add_argument("--min-score", type=float, default=0.0, help="drop results below this score")
    search_parser.add_argument("--no-set", action="store_true", help="do not print rule-based selected set")
    search_parser.add_argument("--format", choices=("table", "json"), default="table")
    search_parser.set_defaults(func=_cmd_search)

    inspect_parser = subparsers.add_parser("inspect", help="inspect one resource definition including v1 extras")
    inspect_parser.add_argument("resource", help="resource id or id@version")
    _add_path_arg(inspect_parser)
    inspect_parser.add_argument("--version", help="version to inspect when resource id is ambiguous")
    inspect_parser.add_argument("--format", choices=("text", "json"), default="text")
    inspect_parser.set_defaults(func=_cmd_inspect)

    policy_parser = subparsers.add_parser("policy-check", help="evaluate a resource against the Policy Gateway")
    policy_parser.add_argument("resource", help="resource id or id@version")
    _add_path_arg(policy_parser)
    policy_parser.add_argument("--version", help="version to check when resource id is ambiguous")
    policy_parser.add_argument("--gate", choices=("activation", "execution", "output"), default="activation")
    policy_parser.add_argument("--granted-permission", action="append", default=[], help="permission granted to the current context; repeatable")
    policy_parser.add_argument("--max-cost", type=float, help="deny resources whose cost_estimate exceeds this value")
    policy_parser.add_argument("--allow-trust-level", action="append", choices=TRUST_LEVELS, help="allowed trust level; repeatable")
    policy_parser.add_argument("--allow-side-effect", action="append", choices=SIDE_EFFECTS, help="allowed side effect; repeatable")
    policy_parser.add_argument(
        "--escalate-side-effect",
        action="append",
        choices=SIDE_EFFECTS,
        help="side effect that requires human approval; repeatable",
    )
    policy_parser.add_argument("--human-approved", action="store_true", help="treat escalation-class risks as already approved")
    policy_parser.add_argument("--dry-run", action="store_true", help="record that no side effects will be executed by this check")
    _add_isolation_args(policy_parser)
    policy_parser.add_argument(
        "--arguments",
        default="",
        metavar="JSON",
        help="tool arguments to inspect at the execution gate",
    )
    _add_safety_args(policy_parser)
    policy_parser.add_argument("--audit-log", help="append a hash-chained JSONL audit record to this path")
    policy_parser.add_argument("--format", choices=("text", "json"), default="text")
    policy_parser.set_defaults(func=_cmd_policy_check)

    run_parser = subparsers.add_parser(
        "run",
        help="run a goal through the guarded kernel loop (mock LLM, v2 preview)",
    )
    run_parser.add_argument("--task", required=True, help="natural-language goal to execute")
    _add_path_arg(run_parser)
    run_parser.add_argument("--granted-permission", action="append", default=[], help="permission granted to the task context; repeatable")
    run_parser.add_argument("--max-cost", type=float, help="deny resources whose cost_estimate exceeds this value")
    run_parser.add_argument("--allow-trust-level", action="append", choices=TRUST_LEVELS, help="allowed trust level; repeatable")
    run_parser.add_argument("--allow-side-effect", action="append", choices=SIDE_EFFECTS, help="allowed side effect; repeatable")
    run_parser.add_argument("--escalate-side-effect", action="append", choices=SIDE_EFFECTS, help="side effect that requires human approval; repeatable")
    run_parser.add_argument("--human-approved", action="store_true", help="treat escalation-class risks as already approved")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and record tool calls without invoking any tool handler",
    )
    _add_safety_args(run_parser)
    _add_isolation_args(run_parser)
    _add_connector_args(run_parser)
    run_parser.add_argument(
        "--tool-impl",
        action="append",
        default=[],
        metavar="ID=MODULE:FUNC",
        help="bind a tool resource id to an importable callable; repeatable",
    )
    run_parser.add_argument(
        "--agent-impl",
        action="append",
        default=[],
        metavar="ID=MODULE:FUNC",
        help="bind an agent resource id to a synchronous callable; repeatable",
    )
    run_parser.add_argument(
        "--tool-args",
        default="",
        metavar="JSON",
        help='mock-LLM arguments per tool id, e.g. \'{"tool.files.read-text": {"path": "README.md"}}\'',
    )
    run_parser.add_argument("--top-k", type=int, default=8, help="search candidates considered before set selection")
    run_parser.add_argument("--set-limit", action="append", default=[], metavar="KIND=N", help="limit selected set per kind; repeatable")
    run_parser.add_argument("--max-tool-calls", type=int, default=5, help="tool call budget before the task fails")
    run_parser.add_argument("--max-agent-depth", type=int, default=1, help="maximum synchronous delegation depth")
    run_parser.add_argument("--max-agent-cost", type=float, help="maximum cumulative estimated Agent cost")
    run_parser.add_argument(
        "--context-token-budget",
        type=int,
        help="maximum estimated tokens for the compiled execution context",
    )
    run_parser.add_argument("--timeout", type=float, default=30.0, help="per-tool execution timeout in seconds")
    run_parser.add_argument("--audit-log", help="write this run's hash-chained audit records to a JSONL file (overwrites)")
    _add_state_args(run_parser)
    _add_hitl_args(run_parser)
    _add_recovery_args(run_parser)
    _add_planner_args(run_parser)
    run_parser.add_argument(
        "--confirm",
        action="store_true",
        help="ask for confirmations on this terminal instead of pausing the task",
    )
    run_parser.add_argument("--format", choices=("text", "json"), default="text")
    run_parser.set_defaults(func=_cmd_run)

    resume_parser = subparsers.add_parser(
        "resume",
        help="answer a paused task's confirmation and continue it",
    )
    resume_parser.add_argument("--task-id", required=True, help="id of the paused task")
    _add_path_arg(resume_parser)
    verdict = resume_parser.add_mutually_exclusive_group(required=True)
    verdict.add_argument("--approve", action="store_true", help="approve the pending operation")
    verdict.add_argument("--reject", action="store_true", help="reject it and end the task")
    verdict.add_argument("--defer", action="store_true", help="leave the task paused for later")
    verdict.add_argument(
        "--modify",
        metavar="JSON",
        help='approve with replacement tool arguments, e.g. \'{"path": "safe.txt"}\'',
    )
    resume_parser.add_argument("--responder", default="", help="who is answering (checked against --approver)")
    resume_parser.add_argument("--note", default="", help="free-text reason recorded in the audit log")
    resume_parser.add_argument("--granted-permission", action="append", default=[], help="permission granted to the task context; repeatable")
    resume_parser.add_argument("--max-cost", type=float, help="deny resources whose cost_estimate exceeds this value")
    resume_parser.add_argument("--allow-trust-level", action="append", choices=TRUST_LEVELS, help="allowed trust level; repeatable")
    resume_parser.add_argument("--allow-side-effect", action="append", choices=SIDE_EFFECTS, help="allowed side effect; repeatable")
    resume_parser.add_argument("--escalate-side-effect", action="append", choices=SIDE_EFFECTS, help="side effect that requires human approval; repeatable")
    resume_parser.add_argument("--human-approved", action="store_true", help="treat escalation-class risks as already approved")
    resume_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and record tool calls without invoking any tool handler",
    )
    _add_safety_args(resume_parser)
    _add_isolation_args(resume_parser)
    _add_connector_args(resume_parser)
    resume_parser.add_argument("--tool-impl", action="append", default=[], metavar="ID=MODULE:FUNC", help="bind a tool resource id to an importable callable; repeatable")
    resume_parser.add_argument("--agent-impl", action="append", default=[], metavar="ID=MODULE:FUNC", help="bind an agent resource id to a synchronous callable; repeatable")
    resume_parser.add_argument("--tool-args", default="", metavar="JSON", help="mock-LLM arguments per tool id")
    resume_parser.add_argument("--top-k", type=int, default=8, help="search candidates considered before set selection")
    resume_parser.add_argument("--set-limit", action="append", default=[], metavar="KIND=N", help="limit selected set per kind; repeatable")
    resume_parser.add_argument("--max-tool-calls", type=int, default=5, help="tool call budget before the task fails")
    resume_parser.add_argument("--max-agent-depth", type=int, default=1, help="maximum synchronous delegation depth")
    resume_parser.add_argument("--max-agent-cost", type=float, help="maximum cumulative estimated Agent cost")
    resume_parser.add_argument(
        "--context-token-budget",
        type=int,
        help="maximum estimated tokens for the compiled execution context",
    )
    resume_parser.add_argument("--timeout", type=float, default=30.0, help="per-tool execution timeout in seconds")
    resume_parser.add_argument("--audit-log", help="JSONL audit file to continue the hash chain in")
    _add_state_args(resume_parser, required=True)
    _add_hitl_args(resume_parser)
    _add_recovery_args(resume_parser)
    _add_planner_args(resume_parser)
    resume_parser.add_argument("--format", choices=("text", "json"), default="text")
    resume_parser.set_defaults(func=_cmd_resume, confirm=False)

    tasks_parser = subparsers.add_parser("tasks", help="list tasks held in a state store")
    _add_state_args(tasks_parser, required=True)
    tasks_parser.add_argument("--status", help="only show tasks in this status")
    tasks_parser.add_argument("--format", choices=("text", "json"), default="text")
    tasks_parser.set_defaults(func=_cmd_tasks)

    package_parser = subparsers.add_parser(
        "package",
        help="lock, verify, and inspect a local resource package",
    )
    package_subparsers = package_parser.add_subparsers(dest="package_command", required=True)
    package_lock_parser = package_subparsers.add_parser(
        "lock",
        help="pin the manifest and resource files by SHA-256",
    )
    package_lock_parser.add_argument("path", help="directory containing marmo-package.json")
    package_lock_parser.add_argument(
        "--source",
        default=".",
        help="portable local acquisition path to record in the lock (default: .)",
    )
    package_lock_parser.add_argument("--format", choices=("text", "json"), default="text")
    package_lock_parser.set_defaults(func=_cmd_package_lock)

    package_verify_parser = package_subparsers.add_parser(
        "verify",
        help="verify compatibility, source metadata, and all pinned hashes",
    )
    package_verify_parser.add_argument("path", help="directory containing marmo-package.json")
    package_verify_parser.add_argument("--format", choices=("text", "json"), default="text")
    package_verify_parser.set_defaults(func=_cmd_package_verify)

    package_inspect_parser = package_subparsers.add_parser(
        "inspect",
        help="show the verified manifest and lock metadata",
    )
    package_inspect_parser.add_argument("path", help="directory containing marmo-package.json")
    package_inspect_parser.add_argument("--format", choices=("text", "json"), default="text")
    package_inspect_parser.set_defaults(func=_cmd_package_inspect)

    return parser


def _add_state_args(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    parser.add_argument(
        "--state-dir",
        required=required,
        help="directory holding durable task state; without it, state lives in memory only",
    )


def _add_safety_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-external-host",
        action="append",
        default=[],
        metavar="HOST",
        help="allow this external hostname and its subdomains; repeatable",
    )
    parser.add_argument(
        "--block-external-host",
        action="append",
        default=[],
        metavar="HOST",
        help="deny this external hostname and its subdomains; repeatable",
    )


def _add_isolation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--minimum-isolation-level",
        choices=ISOLATION_LEVELS,
        default="L0",
        help="deny tools whose declared isolation is below this level",
    )
    parser.add_argument(
        "--available-isolation-level",
        action="append",
        choices=ISOLATION_LEVELS,
        help="isolation level supplied by this runtime; repeatable (core default: L0-L2)",
    )


def _add_planner_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--planner",
        choices=("none", "rule", "llm"),
        default="none",
        help="plan the goal up front instead of letting the model choose call by call",
    )
    parser.add_argument(
        "--max-parallel-steps",
        type=int,
        default=4,
        help="independent plan steps to run at the same time",
    )
    parser.add_argument("--max-replans", type=int, default=2, help="plan revisions allowed after a failure")


def _add_recovery_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-attempts", type=int, default=3, help="executions per step before recovery gives up")
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=0.1,
        help="initial exponential backoff in seconds between retries",
    )
    parser.add_argument(
        "--circuit-threshold",
        type=int,
        default=3,
        help="consecutive failures of one resource before it is cut off",
    )
    parser.add_argument(
        "--no-compensate",
        action="store_true",
        help="do not run declared compensating tools when a task fails",
    )


def _add_hitl_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--always-confirm",
        action="append",
        default=[],
        metavar="ID",
        help="resource id that always needs a human before it runs; repeatable",
    )
    parser.add_argument(
        "--approver",
        action="append",
        default=[],
        metavar="NAME",
        help="restrict who may approve; repeatable",
    )


def _add_path_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", nargs="*", help="resource files or directories")


def _add_common_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kind", action="append", choices=KINDS, default=[], help="resource kind filter; repeatable")
    parser.add_argument("--trust-level", action="append", choices=TRUST_LEVELS, default=[], help="trust level filter; repeatable")
    parser.add_argument("--side-effect", action="append", choices=SIDE_EFFECTS, default=[], help="side-effect filter; repeatable")
    parser.add_argument("--tag", action="append", default=[], help="required tag filter; repeatable")


def _cmd_validate(args: argparse.Namespace) -> int:
    paths = _default_paths(args.paths)
    issues = validate_resource_paths(paths)
    payload = {
        "paths": [str(path) for path in paths],
        "valid": not any(issue.severity == "error" for issue in issues),
        "issues": [issue.to_dict() for issue in issues],
    }
    if args.json:
        print_json(payload)
    else:
        if payload["valid"]:
            registry = load_registry(paths)
            summary = registry.summary()
            print(
                "valid: "
                f"{summary['total']} resources "
                f"(memory={summary['memory']}, skill={summary['skill']}, tool={summary['tool']}, agent={summary['agent']})"
            )
        else:
            for issue in issues:
                print(f"{issue.severity}: {issue.path}: {issue.message}", file=sys.stderr)
    return 0 if payload["valid"] else 1


def _cmd_package_lock(args: argparse.Namespace) -> int:
    lock = write_package_lock(args.path, source_path=args.source)
    payload = lock.to_dict()
    if args.format == "json":
        print_json(payload)
    else:
        print(f"locked: {lock.package}")
        print(f"source: {lock.source_type}:{lock.source_path}")
        print(f"files: {len(lock.files)}")
    return 0


def _cmd_package_verify(args: argparse.Namespace) -> int:
    package = verify_local_package(args.path)
    if args.format == "json":
        print_json(package.to_dict())
    else:
        print(f"verified: {package.manifest.identity}")
        print(f"kernel: {package.manifest.kernel}")
        print(f"source: {package.lock.source_type}:{package.lock.source_path}")
        print(f"files: {len(package.resource_files)}")
    return 0


def _cmd_package_inspect(args: argparse.Namespace) -> int:
    package = verify_local_package(args.path)
    payload = package.to_dict()
    if args.format == "json":
        print_json(payload)
    else:
        print(f"package: {package.manifest.identity}")
        print(f"description: {package.manifest.description or '-'}")
        print(f"kernel: {package.manifest.kernel}")
        print(f"namespace: {package.manifest.namespace}")
        print(f"source: {package.lock.source_type}:{package.lock.source_path}")
        print("resources:")
        for relative in package.manifest.resources:
            print(f"  - {relative}  {package.lock.files[relative]}")
        if package.manifest.dependencies:
            print("dependencies:")
            for dependency in package.manifest.dependencies:
                print(f"  - {dependency.name} {dependency.version}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    registry = load_registry(_default_paths(args.paths))
    resources = registry.list(kinds=args.kind, trust_levels=args.trust_level, side_effects=args.side_effect, tags=args.tag)
    if args.format == "json":
        print_json([resource.to_dict(include_extras=False) for resource in resources])
    else:
        print(render_resource_table(resources))
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    registry = load_registry(_default_paths(args.paths))
    per_kind_limits = _parse_limits(args.per_kind_limit)
    set_limits = _parse_limits(args.set_limit)
    query = SearchQuery(
        task=args.task,
        keywords=tuple(args.keyword),
        tags=tuple(args.tag),
        kinds=tuple(args.kind),
        trust_levels=tuple(args.trust_level),
        side_effects=tuple(args.side_effect),
        granted_permissions=tuple(args.granted_permission),
        require_permissions=args.require_permissions,
        top_k=args.top_k,
        per_kind_limits=per_kind_limits,
        min_score=args.min_score,
    )
    results = LexicalRetriever().search(registry, query)
    selected = RuleBasedSetSelector(default_limits=DEFAULT_SET_LIMITS).select(results, limits=set_limits)
    if args.format == "json":
        payload: dict[str, Any] = {"results": [result.to_dict() for result in results]}
        if not args.no_set:
            payload["selected_set"] = selected.to_dict()
        print_json(payload)
    else:
        print(render_search_table(results))
        if not args.no_set:
            print()
            print(render_selected_set(selected))
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    registry = load_registry(_default_paths(args.paths))
    resource = registry.get(args.resource, version=args.version)
    if args.format == "json":
        print_json(resource.to_dict(include_extras=True))
    else:
        print(render_inspection(resource))
    return 0


def _cmd_policy_check(args: argparse.Namespace) -> int:
    registry = load_registry(_default_paths(args.paths))
    resource = registry.get(args.resource, version=args.version)
    context = PolicyContext(
        granted_permissions=tuple(args.granted_permission),
        max_cost=args.max_cost,
        allowed_trust_levels=tuple(args.allow_trust_level) if args.allow_trust_level else PolicyContext().allowed_trust_levels,
        allowed_side_effects=tuple(args.allow_side_effect) if args.allow_side_effect else PolicyContext().allowed_side_effects,
        escalate_side_effects=(
            tuple(args.escalate_side_effect) if args.escalate_side_effect else PolicyContext().escalate_side_effects
        ),
        human_approved=args.human_approved,
        allowed_external_hosts=tuple(args.allow_external_host),
        blocked_external_hosts=tuple(args.block_external_host),
        minimum_isolation_level=args.minimum_isolation_level,
        available_isolation_levels=(
            tuple(args.available_isolation_level)
            if args.available_isolation_level
            else PolicyContext().available_isolation_levels
        ),
        dry_run=args.dry_run,
    )
    arguments = None
    if args.arguments:
        parsed = json.loads(args.arguments)
        if not isinstance(parsed, dict):
            raise ValueError("--arguments must be a JSON object")
        arguments = parsed
    decision = PolicyGateway().evaluate(resource, context, gate=args.gate, arguments=arguments)
    audit_record = None
    if args.audit_log:
        audit_record = AuditLog.append_jsonl(args.audit_log, "policy", decision.to_dict())
    if args.format == "json":
        payload = {"decision": decision.to_dict()}
        if audit_record is not None:
            payload["audit_record"] = audit_record.to_dict()
        print_json(payload)
    else:
        print(render_policy_decision(decision))
        if audit_record is not None:
            print(f"  audit_hash: {audit_record.hash}")
    return 0 if decision.allowed else 1


def _build_kernel(args: argparse.Namespace, *, continue_audit: bool) -> Kernel:
    """Assemble the kernel that ``run`` and ``resume`` share."""

    registry = load_registry(_default_paths(args.paths))
    context = PolicyContext(
        granted_permissions=tuple(args.granted_permission),
        max_cost=args.max_cost,
        allowed_trust_levels=tuple(args.allow_trust_level) if args.allow_trust_level else PolicyContext().allowed_trust_levels,
        allowed_side_effects=tuple(args.allow_side_effect) if args.allow_side_effect else PolicyContext().allowed_side_effects,
        escalate_side_effects=(
            tuple(args.escalate_side_effect) if args.escalate_side_effect else PolicyContext().escalate_side_effects
        ),
        human_approved=args.human_approved,
        allowed_external_hosts=tuple(args.allow_external_host),
        blocked_external_hosts=tuple(args.block_external_host),
        minimum_isolation_level=args.minimum_isolation_level,
        available_isolation_levels=(
            tuple(args.available_isolation_level)
            if args.available_isolation_level
            else PolicyContext().available_isolation_levels
        ),
        dry_run=args.dry_run,
    )
    tool_arguments: dict[str, Any] = {}
    if args.tool_args:
        parsed = json.loads(args.tool_args)
        if not isinstance(parsed, dict):
            raise ValueError("--tool-args must be a JSON object mapping tool ids to argument objects")
        tool_arguments = parsed
    hitl_policy = HitlPolicy(
        approvers=tuple(args.approver),
        always_confirm_resources=tuple(args.always_confirm),
    )
    broker = ConsoleHitlBroker(hitl_policy) if args.confirm else PendingHitlBroker(hitl_policy)
    recovery = RecoveryManager(
        retry_policy=RetryPolicy(
            max_attempts=args.max_attempts,
            initial_backoff_seconds=args.retry_backoff,
        ),
        circuit_breaker=CircuitBreaker(failure_threshold=args.circuit_threshold),
    )
    audit_log = AuditLog.from_jsonl(args.audit_log) if continue_audit and args.audit_log else AuditLog()
    llm = MockLLMProvider(tool_arguments=tool_arguments)
    planner: Planner | None = None
    if args.planner == "rule":
        planner = RuleBasedPlanner(step_arguments=tool_arguments)
    elif args.planner == "llm":
        planner = LLMPlanner(llm)
    return Kernel(
        registry,
        llm,
        policy_context=context,
        tool_implementations=_parse_tool_impls(args.tool_impl),
        agent_implementations=_parse_implementations(args.agent_impl, "agent"),
        connectors=_build_connectors(args),
        audit_log=audit_log,
        state_store=JsonFileStateStore(args.state_dir) if args.state_dir else InMemoryStateStore(),
        hitl=broker,
        recovery=recovery,
        planner=planner,
        max_parallel_steps=args.max_parallel_steps,
        max_replans=args.max_replans,
        compensate_on_failure=not args.no_compensate,
        top_k=args.top_k,
        set_limits=_parse_limits(args.set_limit) or None,
        max_tool_calls=args.max_tool_calls,
        max_agent_depth=args.max_agent_depth,
        max_agent_cost=args.max_agent_cost,
        context_token_budget=args.context_token_budget,
        timeout_seconds=args.timeout,
    )


def _report_task(args: argparse.Namespace, kernel: Kernel, result) -> int:
    if args.audit_log:
        kernel.audit_log.write_jsonl(args.audit_log)
    if args.format == "json":
        payload = result.to_dict()
        payload["audit_records"] = [record.to_dict() for record in kernel.audit_log.records]
        print_json(payload)
        return 0 if result.completed else 1
    print(f"task: {result.task_id}")
    print(f"status: {result.status}")
    if result.output:
        print(f"output: {result.output}")
    if result.detail:
        print(f"detail: {result.detail}")
    for tool_result in result.tool_results:
        print(
            f"  tool: {tool_result.tool_id} status={tool_result.status} "
            f"elapsed_ms={tool_result.elapsed_ms:.1f}"
        )
    for agent_result in result.agent_results:
        print(
            f"  agent: {agent_result.agent_id} status={agent_result.status} "
            f"elapsed_ms={agent_result.elapsed_ms:.1f} cost={agent_result.cost:g}"
        )
    for skipped in result.skipped_resources:
        print(f"  skipped: {skipped['resource']} ({skipped['reason']})")
    if result.paused:
        request = kernel.pending_request(result.task_id)
        if request is not None:
            print("awaiting confirmation:")
            print(request.describe())
            if args.state_dir:
                print(
                    f"  answer with: marmo resume --task-id {result.task_id} "
                    f"--state-dir {args.state_dir} --approve"
                )
            else:
                print("  pass --state-dir to keep the pause resumable across processes")
    chain = kernel.audit_log.records
    print(f"audit: {len(chain)} records, last_hash={chain[-1].hash[:16]}…" if chain else "audit: empty")
    return 0 if result.completed else 1


def _cmd_run(args: argparse.Namespace) -> int:
    kernel = _build_kernel(args, continue_audit=False)
    return _report_task(args, kernel, kernel.run_goal(args.task))


def _cmd_resume(args: argparse.Namespace) -> int:
    kernel = _build_kernel(args, continue_audit=True)
    if args.modify:
        arguments = json.loads(args.modify)
        if not isinstance(arguments, dict):
            raise ValueError("--modify must be a JSON object of replacement tool arguments")
        response = HitlResponse(
            kind="modify", responder=args.responder, note=args.note, arguments=arguments
        )
    else:
        kind = "approve" if args.approve else "reject" if args.reject else "defer"
        response = HitlResponse(kind=kind, responder=args.responder, note=args.note)
    return _report_task(args, kernel, kernel.resume(args.task_id, response))


def _cmd_tasks(args: argparse.Namespace) -> int:
    store = JsonFileStateStore(args.state_dir)
    states = store.list_tasks(status=args.status)
    if args.format == "json":
        print_json({"tasks": [state.to_dict() for state in states]})
        return 0
    if not states:
        print("no tasks found")
        return 0
    for state in states:
        line = f"{state.task_id}  {state.status:<10}  {state.goal}"
        if state.pending:
            line += f"  (awaiting: {state.pending.get('operation', '')})"
        print(line)
    return 0


def _parse_tool_impls(values: list[str]) -> dict[str, Callable[..., Any]]:
    return _parse_implementations(values, "tool")


def _parse_implementations(
    values: list[str], resource_kind: str
) -> dict[str, Callable[..., Any]]:
    implementations: dict[str, Callable[..., Any]] = {}
    for value in values:
        if "=" not in value or ":" not in value.split("=", 1)[1]:
            raise ValueError(f"{resource_kind} impl must be ID=MODULE:FUNC: {value}")
        resource_id, target = value.split("=", 1)
        module_name, _, attribute = target.rpartition(":")
        module = importlib.import_module(module_name)
        handler = getattr(module, attribute, None)
        if not callable(handler):
            raise ValueError(f"{target} is not a callable")
        implementations[resource_id] = handler
    return implementations


def _add_connector_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--connector-http",
        action="store_true",
        help="enable the built-in HTTP Connector",
    )
    parser.add_argument(
        "--connector-http-allow-private",
        action="store_true",
        help="allow HTTP destinations on private/loopback networks (unsafe unless intentional)",
    )
    parser.add_argument(
        "--connector-file-root",
        help="enable the File Connector confined to this directory",
    )
    parser.add_argument(
        "--connector-shell-root",
        help="root directory for the Shell Connector (requires --connector-shell-command)",
    )
    parser.add_argument(
        "--connector-shell-command",
        action="append",
        default=[],
        metavar="EXECUTABLE",
        help="allow one executable in the Shell Connector; repeatable",
    )
    parser.add_argument(
        "--connector-sqlite",
        metavar="DATABASE",
        help="enable the SQLite Connector for one database path",
    )
    parser.add_argument(
        "--connector-max-attempts",
        type=int,
        default=1,
        help="Connector-local attempts for retry-safe read operations",
    )
    parser.add_argument(
        "--connector-rate-limit",
        type=float,
        help="maximum calls per second for each Connector operation",
    )
    parser.add_argument(
        "--connector-circuit-threshold",
        type=int,
        default=3,
        help="consecutive transient failures before a Connector circuit opens",
    )


def _build_connectors(args: argparse.Namespace) -> tuple[Connector, ...]:
    config = ConnectorConfig(
        timeout_seconds=args.timeout,
        max_attempts=args.connector_max_attempts,
        rate_limit_per_second=args.connector_rate_limit,
        circuit_failure_threshold=args.connector_circuit_threshold,
    )
    connectors: list[Connector] = []
    if args.connector_http_allow_private and not args.connector_http:
        raise ValueError("--connector-http-allow-private requires --connector-http")
    if args.connector_http:
        connectors.append(
            HTTPConnector(
                config=config,
                allowed_hosts=args.allow_external_host,
                allow_private_networks=args.connector_http_allow_private,
            )
        )
    if args.connector_file_root:
        connectors.append(FileSystemConnector(args.connector_file_root, config=config))
    if args.connector_shell_command:
        connectors.append(
            ShellConnector(
                args.connector_shell_root or ".",
                args.connector_shell_command,
                config=config,
            )
        )
    elif args.connector_shell_root:
        raise ValueError("--connector-shell-root requires at least one --connector-shell-command")
    if args.connector_sqlite:
        connectors.append(SQLiteConnector(args.connector_sqlite, config=config))
    return tuple(connectors)


def _parse_limits(values: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"limit must be KIND=N: {value}")
        kind, raw_limit = value.split("=", 1)
        if kind not in KINDS:
            raise ValueError(f"invalid kind in limit: {kind}")
        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise ValueError(f"invalid numeric limit for {kind}: {raw_limit}") from exc
        if limit < 0:
            raise ValueError(f"limit for {kind} must be non-negative")
        parsed[kind] = limit
    return parsed


def _default_paths(paths: list[str]) -> list[Path]:
    if paths:
        return [Path(path) for path in paths]
    for candidate in (Path("resources"), Path("skills"), Path("examples/resources")):
        if candidate.exists():
            return [candidate]
    return [Path(".")]


if __name__ == "__main__":
    raise SystemExit(main())
