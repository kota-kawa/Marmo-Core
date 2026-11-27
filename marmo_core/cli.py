"""Command line interface for Marmo-Core v1."""

from __future__ import annotations

from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, NoReturn
import argparse
import importlib
import json
import os
import shlex
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
from .cli_locale import CLIInputError, JapaneseHelpFormatter, japanese_parser_error, translate
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
from ._version import __version__
from .kernel import NO_CALLABLE_SELECTED_DETAIL, NO_RESOURCE_MATCHED_DETAIL, Kernel
from .llm import LLMProvider, MockLLMProvider
from .llm_routing import HydeRetriever
from .loader import load_registry, validate_resource_paths
from .models import KINDS, SIDE_EFFECTS, TRUST_LEVELS, SearchQuery
from .package import verify_local_package, write_package_lock
from .planner import LLMPlanner, Planner, RuleBasedPlanner
from .policy import PolicyContext, PolicyGateway
from .providers import AnthropicLLMProvider, BedrockLLMProvider, OpenAICompatibleLLMProvider
from .recovery import CircuitBreaker, RecoveryManager, RetryPolicy
from .safety import redact_sensitive_arguments
from .registry import ResourceRegistry
from .retriever import LexicalRetriever, Retriever
from .selector import DEFAULT_SET_LIMITS, RuleBasedSetSelector
from .security import ISOLATION_LEVELS
from .state import InMemoryStateStore, JsonFileStateStore

LLM_CHOICES = ("mock", "openai", "anthropic", "bedrock")
RETRIEVER_CHOICES = ("lexical", "hyde")


class _ArgumentParser(argparse.ArgumentParser):
    language = "en"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if self.language == "ja":
            kwargs["formatter_class"] = JapaneseHelpFormatter
            kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        if self.language == "ja":
            self.add_argument("-h", "--help", action="help", help=self.translate("show this help message and exit"))

    def translate(self, message: str) -> str:
        return translate(self.language, message)

    def error(self, message: str) -> NoReturn:
        if self.language == "ja":
            self.print_usage(sys.stderr)
            detail = japanese_parser_error(message)
            self.exit(2, f"{self.prog}: 引数エラー。使用方法は --help を参照してください。\n  {detail}\n")
        super().error(message)


class _JapaneseArgumentParser(_ArgumentParser):
    language = "ja"


def main(argv: list[str] | None = None) -> int:
    language = os.getenv("MARMO_CLI_LANGUAGE", "en")
    parser = build_parser(language=language)
    _ = parser.translate
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (MarmoError, ValueError, OSError) as exc:
        if isinstance(exc, CLIInputError):
            detail = _(exc.template).format(**exc.fields)
        elif isinstance(exc, json.JSONDecodeError):
            detail = _("invalid JSON: {detail}").format(detail=exc) if language == "ja" else str(exc)
        elif isinstance(exc, ValueError):
            detail = _(str(exc))
        else:
            detail = str(exc)
        print(f"{_('error')}: {detail}", file=sys.stderr)
        return 2


def build_parser(*, language: str = "en") -> _ArgumentParser:
    parser_type = _JapaneseArgumentParser if language == "ja" else _ArgumentParser
    _ = partial(translate, language)
    parser = parser_type(prog="marmo", description=_("Marmo-Core v1 unified resource CLI"))
    parser.set_defaults(language=language)
    version_action = parser.add_argument("--version", action="version", version=f"marmo-core {__version__}")
    if language == "ja":
        version_action.help = "バージョンを表示して終了する"
    subparsers = parser.add_subparsers(required=True)

    validate_parser = subparsers.add_parser("validate", help=_("validate local resource definition files"))
    _add_path_arg(validate_parser)
    validate_parser.add_argument("--json", action="store_true", help=_("emit machine-readable JSON"))
    validate_parser.set_defaults(func=_cmd_validate)

    list_parser = subparsers.add_parser("list", help=_("list resources from local definition files"))
    _add_path_arg(list_parser)
    _add_common_filters(list_parser)
    list_parser.add_argument("--format", choices=("table", "json"), default="table")
    list_parser.set_defaults(func=_cmd_list)

    search_parser = subparsers.add_parser("search", help=_("search across Memory, Skill, Tool, and Agent resources"))
    _add_path_arg(search_parser)
    _add_common_filters(search_parser)
    search_parser.add_argument("--task", default="", help=_("natural-language task description"))
    search_parser.add_argument("--keyword", action="append", default=[], help=_("required keyword filter; repeatable"))
    search_parser.add_argument("--granted-permission", action="append", default=[], help=_("permission granted to the search context; repeatable"))
    search_parser.add_argument("--require-permissions", action="store_true", help=_("drop resources whose permissions are not fully granted"))
    search_parser.add_argument("--top-k", type=int, default=10, help=_("maximum number of search results to display"))
    search_parser.add_argument("--per-kind-limit", action="append", default=[], metavar="KIND=N", help=_("limit displayed results per kind; repeatable"))
    search_parser.add_argument("--set-limit", action="append", default=[], metavar="KIND=N", help=_("limit selected set per kind; repeatable"))
    search_parser.add_argument("--min-score", type=float, default=0.0, help=_("drop results below this score"))
    search_parser.add_argument("--no-set", action="store_true", help=_("do not print rule-based selected set"))
    search_parser.add_argument("--format", choices=("table", "json"), default="table")
    search_parser.set_defaults(func=_cmd_search)

    inspect_parser = subparsers.add_parser("inspect", help=_("inspect one resource definition including v1 extras"))
    inspect_parser.add_argument("resource", help=_("resource id or id@version"))
    _add_path_arg(inspect_parser)
    inspect_parser.add_argument("--version", help=_("version to inspect when resource id is ambiguous"))
    inspect_parser.add_argument("--format", choices=("text", "json"), default="text")
    inspect_parser.set_defaults(func=_cmd_inspect)

    policy_parser = subparsers.add_parser("policy-check", help=_("evaluate a resource against the Policy Gateway"))
    policy_parser.add_argument("resource", help=_("resource id or id@version"))
    _add_path_arg(policy_parser)
    policy_parser.add_argument("--version", help=_("version to check when resource id is ambiguous"))
    policy_parser.add_argument("--gate", choices=("activation", "execution", "output"), default="activation")
    policy_parser.add_argument("--granted-permission", action="append", default=[], help=_("permission granted to the current context; repeatable"))
    policy_parser.add_argument("--max-cost", type=float, help=_("deny resources whose cost_estimate exceeds this value"))
    policy_parser.add_argument("--allow-trust-level", action="append", choices=TRUST_LEVELS, help=_("allowed trust level; repeatable"))
    policy_parser.add_argument("--allow-side-effect", action="append", choices=SIDE_EFFECTS, help=_("allowed side effect; repeatable"))
    policy_parser.add_argument(
        "--escalate-side-effect",
        action="append",
        choices=SIDE_EFFECTS,
        help=_("side effect that requires human approval; repeatable"),
    )
    policy_parser.add_argument("--human-approved", action="store_true", help=_("treat escalation-class risks as already approved"))
    policy_parser.add_argument("--dry-run", action="store_true", help=_("record that no side effects will be executed by this check"))
    _add_isolation_args(policy_parser)
    policy_parser.add_argument(
        "--arguments",
        default="",
        metavar="JSON",
        help=_("tool arguments to inspect at the execution gate"),
    )
    _add_safety_args(policy_parser)
    policy_parser.add_argument("--audit-log", help=_("append a hash-chained JSONL audit record to this path"))
    policy_parser.add_argument("--format", choices=("text", "json"), default="text")
    policy_parser.set_defaults(func=_cmd_policy_check)

    run_parser = subparsers.add_parser(
        "run",
        help=_("run a goal through the guarded kernel loop with the mock LLM or a real provider (--llm)"),
    )
    run_parser.add_argument("--task", required=True, help=_("natural-language goal to execute"))
    run_parser.add_argument(
        "--llm",
        choices=LLM_CHOICES,
        default="mock",
        help=_(
            "model that drives the run: 'mock' replays --tool-args offline (default); "
            "'openai' and 'anthropic' read OPENAI_MODEL/OPENAI_API_KEY or "
            "ANTHROPIC_MODEL/ANTHROPIC_API_KEY/ANTHROPIC_MAX_TOKENS; 'bedrock' reads "
            "BEDROCK_MODEL/BEDROCK_API_KEY/BEDROCK_REGION from the environment or .env"
        ),
    )
    run_parser.add_argument(
        "--retriever",
        choices=RETRIEVER_CHOICES,
        default="lexical",
        help=_(
            "how resources are matched to the goal: 'lexical' is offline word matching (default); "
            "'hyde' first asks the --llm to restate the goal in the registry's English vocabulary, "
            "which lets goals written in other languages find English-documented resources"
        ),
    )
    _add_path_arg(run_parser)
    run_parser.add_argument("--granted-permission", action="append", default=[], help=_("permission granted to the task context; repeatable"))
    run_parser.add_argument("--max-cost", type=float, help=_("deny resources whose cost_estimate exceeds this value"))
    run_parser.add_argument("--allow-trust-level", action="append", choices=TRUST_LEVELS, help=_("allowed trust level; repeatable"))
    run_parser.add_argument("--allow-side-effect", action="append", choices=SIDE_EFFECTS, help=_("allowed side effect; repeatable"))
    run_parser.add_argument("--escalate-side-effect", action="append", choices=SIDE_EFFECTS, help=_("side effect that requires human approval; repeatable"))
    run_parser.add_argument("--human-approved", action="store_true", help=_("treat escalation-class risks as already approved"))
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=_("validate and record tool calls without invoking any tool handler"),
    )
    run_parser.add_argument(
        "--strict",
        action="store_true",
        help=_(
            "return non-zero when a resource is skipped or a tool named in --tool-args is not evaluated "
            "(--tool-args counts only where it is used, see its help)"
        ),
    )
    _add_safety_args(run_parser)
    _add_isolation_args(run_parser)
    _add_connector_args(run_parser)
    run_parser.add_argument(
        "--tool-impl",
        action="append",
        default=[],
        metavar="ID=MODULE:FUNC",
        help=_("bind a tool resource id to an importable callable; repeatable"),
    )
    run_parser.add_argument(
        "--agent-impl",
        action="append",
        default=[],
        metavar="ID=MODULE:FUNC",
        help=_("bind an agent resource id to a synchronous callable; repeatable"),
    )
    run_parser.add_argument(
        "--tool-args",
        default="",
        metavar="JSON",
        help=_(
            'arguments per tool id, e.g. \'{"tool.files.read-text": {"path": "README.md"}}\'; used by '
            "--llm mock and by --planner rule, ignored otherwise (a real provider chooses its own arguments)"
        ),
    )
    run_parser.add_argument("--top-k", type=int, default=8, help=_("search candidates considered before set selection"))
    run_parser.add_argument("--set-limit", action="append", default=[], metavar="KIND=N", help=_("limit selected set per kind; repeatable"))
    run_parser.add_argument("--max-tool-calls", type=int, default=5, help=_("tool call budget before the task fails"))
    run_parser.add_argument(
        "--max-input-repairs",
        type=int,
        default=2,
        help=_("times the model may be handed a tool-argument error and asked to call again"),
    )
    run_parser.add_argument(
        "--max-tool-output-tokens",
        type=int,
        default=8000,
        help=_("estimated tokens kept from one tool result before it is truncated (0 to keep all)"),
    )
    run_parser.add_argument("--max-agent-depth", type=int, default=1, help=_("maximum synchronous delegation depth"))
    run_parser.add_argument("--max-agent-cost", type=float, help=_("maximum cumulative estimated Agent cost"))
    run_parser.add_argument(
        "--context-token-budget",
        type=int,
        help=_("maximum estimated tokens for the compiled execution context"),
    )
    run_parser.add_argument("--timeout", type=float, default=30.0, help=_("per-tool execution timeout in seconds"))
    run_parser.add_argument("--timeout-mode", choices=("thread", "process"), default="thread", help=_("process mode stops importable handlers at the deadline"))
    run_parser.add_argument(
        "--audit-log",
        help=_(
            "append this run's hash-chained audit records to a JSONL file; an existing file's chain "
            "is verified and continued, and a broken chain is refused"
        ),
    )
    _add_state_args(run_parser)
    _add_hitl_args(run_parser)
    _add_recovery_args(run_parser)
    _add_planner_args(run_parser)
    run_parser.add_argument(
        "--confirm",
        action="store_true",
        help=_("ask for confirmations on this terminal instead of pausing the task"),
    )
    run_parser.add_argument("--format", choices=("text", "json"), default="text")
    run_parser.set_defaults(func=_cmd_run)

    resume_parser = subparsers.add_parser(
        "resume",
        help=_("answer a paused task's confirmation and continue it"),
    )
    resume_parser.add_argument(
        "--llm",
        choices=LLM_CHOICES,
        default="mock",
        help=_("model that continues the task; use the same choice as the original run"),
    )
    resume_parser.add_argument(
        "--retriever",
        choices=RETRIEVER_CHOICES,
        default="lexical",
        help=_("retriever used when the resumed task re-selects resources; match the original run"),
    )
    resume_parser.add_argument("--task-id", required=True, help=_("id of the paused task"))
    _add_path_arg(resume_parser)
    verdict = resume_parser.add_mutually_exclusive_group(required=True)
    verdict.add_argument("--approve", action="store_true", help=_("approve the pending operation"))
    verdict.add_argument("--reject", action="store_true", help=_("reject it and end the task"))
    verdict.add_argument("--defer", action="store_true", help=_("leave the task paused for later"))
    verdict.add_argument(
        "--modify",
        metavar="JSON",
        help=_('approve with replacement tool arguments, e.g. \'{"path": "safe.txt"}\''),
    )
    resume_parser.add_argument(
        "--responder",
        default="",
        help=_("who is answering; required to approve or modify when --approver is set (checked against --approver)"),
    )
    resume_parser.add_argument("--note", default="", help=_("free-text reason recorded in the audit log"))
    resume_parser.add_argument("--granted-permission", action="append", default=[], help=_("permission granted to the task context; repeatable"))
    resume_parser.add_argument("--max-cost", type=float, help=_("deny resources whose cost_estimate exceeds this value"))
    resume_parser.add_argument("--allow-trust-level", action="append", choices=TRUST_LEVELS, help=_("allowed trust level; repeatable"))
    resume_parser.add_argument("--allow-side-effect", action="append", choices=SIDE_EFFECTS, help=_("allowed side effect; repeatable"))
    resume_parser.add_argument("--escalate-side-effect", action="append", choices=SIDE_EFFECTS, help=_("side effect that requires human approval; repeatable"))
    resume_parser.add_argument("--human-approved", action="store_true", help=_("treat escalation-class risks as already approved"))
    resume_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=_("validate and record tool calls without invoking any tool handler"),
    )
    resume_parser.add_argument(
        "--strict",
        action="store_true",
        help=_(
            "return non-zero when a resource is skipped or a tool named in --tool-args is not evaluated "
            "(--tool-args counts only where it is used, see its help)"
        ),
    )
    _add_safety_args(resume_parser)
    _add_isolation_args(resume_parser)
    _add_connector_args(resume_parser)
    resume_parser.add_argument("--tool-impl", action="append", default=[], metavar="ID=MODULE:FUNC", help=_("bind a tool resource id to an importable callable; repeatable"))
    resume_parser.add_argument("--agent-impl", action="append", default=[], metavar="ID=MODULE:FUNC", help=_("bind an agent resource id to a synchronous callable; repeatable"))
    resume_parser.add_argument(
        "--tool-args",
        default="",
        metavar="JSON",
        help=_("arguments per tool id for --llm mock or --planner rule; ignored otherwise"),
    )
    resume_parser.add_argument("--top-k", type=int, default=8, help=_("search candidates considered before set selection"))
    resume_parser.add_argument("--set-limit", action="append", default=[], metavar="KIND=N", help=_("limit selected set per kind; repeatable"))
    resume_parser.add_argument("--max-tool-calls", type=int, default=5, help=_("tool call budget before the task fails"))
    resume_parser.add_argument(
        "--max-input-repairs",
        type=int,
        default=2,
        help=_("times the model may be handed a tool-argument error and asked to call again"),
    )
    resume_parser.add_argument(
        "--max-tool-output-tokens",
        type=int,
        default=8000,
        help=_("estimated tokens kept from one tool result before it is truncated (0 to keep all)"),
    )
    resume_parser.add_argument("--max-agent-depth", type=int, default=1, help=_("maximum synchronous delegation depth"))
    resume_parser.add_argument("--max-agent-cost", type=float, help=_("maximum cumulative estimated Agent cost"))
    resume_parser.add_argument(
        "--context-token-budget",
        type=int,
        help=_("maximum estimated tokens for the compiled execution context"),
    )
    resume_parser.add_argument("--timeout", type=float, default=30.0, help=_("per-tool execution timeout in seconds"))
    resume_parser.add_argument("--timeout-mode", choices=("thread", "process"), default="thread", help=_("match the run's timeout mode"))
    resume_parser.add_argument("--audit-log", help=_("JSONL audit file to continue the hash chain in"))
    _add_state_args(resume_parser, required=True)
    _add_hitl_args(resume_parser)
    _add_recovery_args(resume_parser)
    _add_planner_args(resume_parser)
    resume_parser.add_argument("--format", choices=("text", "json"), default="text")
    resume_parser.set_defaults(func=_cmd_resume, confirm=False)

    tasks_parser = subparsers.add_parser("tasks", help=_("list tasks held in a state store"))
    _add_state_args(tasks_parser, required=True)
    tasks_parser.add_argument("--status", help=_("only show tasks in this status"))
    tasks_parser.add_argument("--format", choices=("text", "json"), default="text")
    tasks_parser.set_defaults(func=_cmd_tasks)

    package_parser = subparsers.add_parser(
        "package",
        help=_("lock, verify, and inspect a local resource package"),
    )
    package_subparsers = package_parser.add_subparsers(dest="package_command", required=True)
    package_lock_parser = package_subparsers.add_parser(
        "lock",
        help=_("pin the manifest and resource files by SHA-256"),
    )
    package_lock_parser.add_argument("path", help=_("directory containing marmo-package.json"))
    package_lock_parser.add_argument(
        "--source",
        default=".",
        help=_("portable local acquisition path to record in the lock (default: .)"),
    )
    package_lock_parser.add_argument("--format", choices=("text", "json"), default="text")
    package_lock_parser.set_defaults(func=_cmd_package_lock)

    package_verify_parser = package_subparsers.add_parser(
        "verify",
        help=_("verify compatibility, source metadata, and all pinned hashes"),
    )
    package_verify_parser.add_argument("path", help=_("directory containing marmo-package.json"))
    package_verify_parser.add_argument("--format", choices=("text", "json"), default="text")
    package_verify_parser.set_defaults(func=_cmd_package_verify)

    package_inspect_parser = package_subparsers.add_parser(
        "inspect",
        help=_("show the verified manifest and lock metadata"),
    )
    package_inspect_parser.add_argument("path", help=_("directory containing marmo-package.json"))
    package_inspect_parser.add_argument("--format", choices=("text", "json"), default="text")
    package_inspect_parser.set_defaults(func=_cmd_package_inspect)

    return parser


def _add_state_args(parser: _ArgumentParser, *, required: bool = False) -> None:
    _ = parser.translate
    parser.add_argument(
        "--state-dir",
        required=required,
        help=_("directory holding durable task state; without it, state lives in memory only"),
    )


def _add_safety_args(parser: _ArgumentParser) -> None:
    _ = parser.translate
    parser.add_argument(
        "--allow-external-host",
        action="append",
        default=[],
        metavar="HOST",
        help=_("allow this external hostname and its subdomains; repeatable"),
    )
    parser.add_argument(
        "--block-external-host",
        action="append",
        default=[],
        metavar="HOST",
        help=_("deny this external hostname and its subdomains; repeatable"),
    )


def _add_isolation_args(parser: _ArgumentParser) -> None:
    _ = parser.translate
    parser.add_argument(
        "--minimum-isolation-level",
        choices=ISOLATION_LEVELS,
        default="L0",
        help=_("deny tools whose declared isolation is below this level"),
    )
    parser.add_argument(
        "--available-isolation-level",
        action="append",
        choices=ISOLATION_LEVELS,
        help=_("isolation level supplied by this runtime; repeatable (core default: L0-L2)"),
    )


def _add_planner_args(parser: _ArgumentParser) -> None:
    _ = parser.translate
    parser.add_argument(
        "--planner",
        choices=("none", "rule", "llm"),
        default="none",
        help=_("plan the goal up front instead of letting the model choose call by call"),
    )
    parser.add_argument(
        "--max-parallel-steps",
        type=int,
        default=4,
        help=_("independent plan steps to run at the same time"),
    )
    parser.add_argument("--max-replans", type=int, default=2, help=_("plan revisions allowed after a failure"))


def _add_recovery_args(parser: _ArgumentParser) -> None:
    _ = parser.translate
    parser.add_argument("--max-attempts", type=int, default=3, help=_("executions per step before recovery gives up"))
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=0.1,
        help=_("initial exponential backoff in seconds between retries"),
    )
    parser.add_argument(
        "--circuit-threshold",
        type=int,
        default=3,
        help=_("consecutive failures of one resource before it is cut off"),
    )
    parser.add_argument(
        "--no-compensate",
        action="store_true",
        help=_("do not run declared compensating tools when a task fails"),
    )


def _add_hitl_args(parser: _ArgumentParser) -> None:
    _ = parser.translate
    parser.add_argument(
        "--always-confirm",
        action="append",
        default=[],
        metavar="ID",
        help=_("resource id that always needs a human before it runs; repeatable"),
    )
    parser.add_argument(
        "--approver",
        action="append",
        default=[],
        metavar="NAME",
        help=_("restrict who may approve; repeatable"),
    )


def _add_path_arg(parser: _ArgumentParser) -> None:
    _ = parser.translate
    parser.add_argument("paths", nargs="*", help=_("resource files or directories"))
    parser.add_argument(
        "--no-default-resources",
        action="store_true",
        help=_("do not auto-discover resources, skills, examples/resources, or the current directory"),
    )


def _add_common_filters(parser: _ArgumentParser) -> None:
    _ = parser.translate
    parser.add_argument("--kind", action="append", choices=KINDS, default=[], help=_("resource kind filter; repeatable"))
    parser.add_argument("--trust-level", action="append", choices=TRUST_LEVELS, default=[], help=_("trust level filter; repeatable"))
    parser.add_argument("--side-effect", action="append", choices=SIDE_EFFECTS, default=[], help=_("side-effect filter; repeatable"))
    parser.add_argument("--tag", action="append", default=[], help=_("required tag filter; repeatable"))


def _cmd_validate(args: argparse.Namespace) -> int:
    paths = _default_paths(args.paths, no_defaults=args.no_default_resources)
    issues = validate_resource_paths(paths)
    payload = {
        "paths": [str(path) for path in paths],
        "valid": not any(issue.severity == "error" for issue in issues),
        "issues": [issue.to_dict() for issue in issues],
    }
    if args.json:
        print_json(payload)
    else:
        # Warnings are printed whether or not the tree is valid: the common one
        # is a .json file that could not be parsed and was therefore skipped,
        # and staying quiet about that is how a typo in someone's own resource
        # file used to read as "valid: 0 resources".
        for issue in issues:
            if issue.severity != "error":
                print(f"{issue.severity}: {issue.path}: {issue.message}", file=sys.stderr)
        if payload["valid"]:
            registry = load_registry(paths)
            summary = registry.summary()
            skipped = sum(1 for issue in issues if issue.severity != "error")
            line = (
                "valid: "
                f"{summary['total']} resources "
                f"(memory={summary['memory']}, skill={summary['skill']}, tool={summary['tool']}, agent={summary['agent']})"
            )
            if skipped:
                line += f"; {skipped} file(s) skipped, see the warnings above"
            print(line)
        else:
            for issue in issues:
                if issue.severity == "error":
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
    paths = _default_paths(args.paths, no_defaults=args.no_default_resources)
    registry = load_registry(paths)
    _warn_if_empty(registry, paths, args.language)
    resources = registry.list(kinds=args.kind, trust_levels=args.trust_level, side_effects=args.side_effect, tags=args.tag)
    if args.format == "json":
        print_json([resource.to_dict(include_extras=False) for resource in resources])
    else:
        print(render_resource_table(resources))
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    paths = _default_paths(args.paths, no_defaults=args.no_default_resources)
    registry = load_registry(paths)
    _warn_if_empty(registry, paths, args.language)
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
    registry = load_registry(_default_paths(args.paths, no_defaults=args.no_default_resources))
    resource = registry.get(args.resource, version=args.version)
    if args.format == "json":
        print_json(resource.to_dict(include_extras=True))
    else:
        print(render_inspection(resource))
    return 0


def _cmd_policy_check(args: argparse.Namespace) -> int:
    registry = load_registry(_default_paths(args.paths, no_defaults=args.no_default_resources))
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
            raise CLIInputError("--arguments must be a JSON object")
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


def _build_kernel(args: argparse.Namespace) -> Kernel:
    """Assemble the kernel that ``run`` and ``resume`` share."""

    registry = load_registry(_default_paths(args.paths, no_defaults=args.no_default_resources))
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
    tool_arguments = _effective_tool_arguments(args)
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
    audit_log = _load_audit_log(args.audit_log)
    llm_choice = getattr(args, "llm", "mock")
    llm = _build_llm(llm_choice, tool_arguments)
    retriever_choice = getattr(args, "retriever", "lexical")
    if retriever_choice == "hyde" and llm_choice == "mock":
        message = translate(
            args.language,
            "note: --retriever hyde rewrites the goal with --llm, and the mock model replies with a "
            "canned script; the rewrite will steer retrieval at random. Pass --llm openai or "
            "--llm anthropic, or use the default --retriever lexical.",
        )
        print(message, file=sys.stderr)
    retriever = _build_retriever(retriever_choice, llm)
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
        retriever=retriever,
        max_parallel_steps=args.max_parallel_steps,
        max_replans=args.max_replans,
        compensate_on_failure=not args.no_compensate,
        top_k=args.top_k,
        set_limits=_parse_limits(args.set_limit) or None,
        max_tool_calls=args.max_tool_calls,
        max_input_repairs=args.max_input_repairs,
        max_tool_output_tokens=args.max_tool_output_tokens or None,
        max_agent_depth=args.max_agent_depth,
        max_agent_cost=args.max_agent_cost,
        context_token_budget=args.context_token_budget,
        timeout_seconds=args.timeout,
        timeout_mode=args.timeout_mode,
    )


@contextmanager
def _audit_log_preserved(args: argparse.Namespace, kernel: Kernel) -> Iterator[None]:
    """Write ``--audit-log`` even when the run raises before it can report.

    The file was only written after a successful return, so a provider error
    or an interrupt discarded the whole trail -- including the records for
    tools that had already run and left side effects behind. An audit log
    that survives only the happy path is not an audit log.
    """

    try:
        yield
    except BaseException:
        # A failed write must not replace the failure being reported: an
        # unwritable --audit-log path would otherwise surface as a bare
        # PermissionError and hide the provider error or the interrupt.
        try:
            _write_audit_log(args, kernel)
        except Exception as exc:  # noqa: BLE001 - reported, never raised over the original
            message = translate(getattr(args, "language", "en"), "warning: could not write {path}: {detail}")
            print(message.format(path=args.audit_log, detail=exc), file=sys.stderr)
        raise


def _load_audit_log(path: str | None) -> AuditLog:
    """Read the chain ``--audit-log`` already holds so this run continues it.

    A run that started a new chain over an existing file used to replace the
    file and drop the history. A chain that does not verify is refused rather
    than extended or replaced: appending to it would bury the tampering.
    """

    if not path:
        return AuditLog()
    try:
        return AuditLog.from_jsonl(path)
    except ValueError as exc:
        raise CLIInputError(
            "cannot continue the audit log {path}: {detail}; fix or move the file, or choose another --audit-log",
            path=path,
            detail=str(exc),
        ) from exc


def _write_audit_log(args: argparse.Namespace, kernel: Kernel) -> None:
    # Only the records the file lacks are appended; the file is never replaced,
    # so neither an interrupted run nor a second writer can shorten the chain.
    if getattr(args, "audit_log", None) and kernel.audit_log.records:
        try:
            kernel.audit_log.extend_jsonl(args.audit_log)
        except ValueError as exc:
            raise CLIInputError(
                "cannot write the audit log {path}: {detail}", path=args.audit_log, detail=str(exc)
            ) from exc


def _report_task(args: argparse.Namespace, kernel: Kernel, result) -> int:
    strict_violations = _strict_violations(args, result)
    _write_audit_log(args, kernel)
    if args.format == "json":
        payload = result.to_dict()
        payload["audit_records"] = [record.to_dict() for record in kernel.audit_log.records]
        if args.strict:
            payload["strict_violations"] = list(strict_violations)
        print_json(payload)
        return 0 if result.completed and not strict_violations else 1
    _ = partial(translate, args.language)
    print(f"{_('task')}: {result.task_id}")
    print(f"{_('status')}: {result.status}")
    if result.output:
        print(f"{_('output')}: {result.output}")
    if result.detail:
        print(f"{_('detail')}: {result.detail}")
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
        print(f"  {_('skipped')}: {skipped['resource']} ({skipped['reason']})")
    for violation in strict_violations:
        print(f"  strict: {violation}")
    if result.paused:
        request = kernel.pending_request(result.task_id)
        if request is not None:
            print(_("awaiting confirmation:"))
            print(request.describe())
            if args.state_dir:
                print(_("  answer with: {command}").format(command=resume_command(args, result.task_id)))
            else:
                print(_("  pass --state-dir to keep the pause resumable across processes"))
    chain = kernel.audit_log.records
    audit_summary = (
        _("{count} records, last_hash={last_hash}…").format(count=len(chain), last_hash=chain[-1].hash[:16])
        if chain else _("empty")
    )
    print(f"{_('audit')}: {audit_summary}")
    return 0 if result.completed and not strict_violations else 1


def _cmd_run(args: argparse.Namespace) -> int:
    kernel = _build_kernel(args)
    with _audit_log_preserved(args, kernel):
        result = kernel.run_goal(args.task)
    return _report_task(args, kernel, result)


def _cmd_resume(args: argparse.Namespace) -> int:
    kernel = _build_kernel(args)
    if args.modify is not None:
        if not args.modify.strip():
            raise CLIInputError("--modify must not be empty; pass replacement tool arguments as a JSON object")
        arguments = json.loads(args.modify)
        if not isinstance(arguments, dict):
            raise CLIInputError("--modify must be a JSON object of replacement tool arguments")
        response = HitlResponse(
            kind="modify", responder=args.responder, note=args.note, arguments=arguments
        )
    else:
        kind = "approve" if args.approve else "reject" if args.reject else "defer"
        response = HitlResponse(kind=kind, responder=args.responder, note=args.note)
    with _audit_log_preserved(args, kernel):
        result = kernel.resume(args.task_id, response)
    return _report_task(args, kernel, result)


def _cmd_tasks(args: argparse.Namespace) -> int:
    store = JsonFileStateStore(args.state_dir)
    states = store.list_tasks(status=args.status)
    if args.format == "json":
        print_json({"tasks": [state.to_dict() for state in states]})
        return 0
    if not states:
        print(translate(args.language, "no tasks found"))
        return 0
    for state in states:
        line = f"{state.task_id}  {state.status:<10}  {state.goal}"
        if state.pending:
            line += f"  (awaiting: {state.pending.get('operation', '')})"
        print(line)
    return 0


def _parse_tool_impls(values: list[str]) -> dict[str, Callable[..., Any]]:
    return _parse_implementations(values, "tool")


def _parse_tool_arguments(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or not all(isinstance(value, dict) for value in parsed.values()):
        raise CLIInputError("--tool-args must be a JSON object mapping tool ids to argument objects")
    return parsed


def _tool_args_apply(args: argparse.Namespace) -> bool:
    """True when something consumes ``--tool-args``.

    The mock model replays them as its tool calls and the rule-based planner
    copies them into its steps. A real provider chooses its own arguments, so
    with ``--llm`` set to one and no ``--planner rule`` the option is inert.
    """

    return getattr(args, "llm", "mock") == "mock" or getattr(args, "planner", "none") == "rule"


def _effective_tool_arguments(args: argparse.Namespace) -> dict[str, Any]:
    """The parsed ``--tool-args``, or nothing when no component would use them.

    Inert arguments are neither parsed nor counted by ``--strict``; otherwise
    an ignored option could turn a successful run into a failing one.
    """

    return _parse_tool_arguments(args.tool_args) if _tool_args_apply(args) else {}


# Options that ``marmo resume`` accepts and that a paused run must be resumed
# with. A resume that drops them runs under a different authorization than the
# run a person just reviewed: without the original ``--granted-permission`` the
# approved tool fails its activation gate, is reported as "skipped", and the
# task still ends "completed". The printed hint therefore repeats whatever the
# run was invoked with. ``tests/test_cli_release.py`` round-trips the rendered
# command back through the parser so an option cannot silently fall out.
_RESUME_FORWARDED_OPTIONS: tuple[tuple[str, str], ...] = (
    ("no_default_resources", "--no-default-resources"),
    ("llm", "--llm"),
    ("retriever", "--retriever"),
    ("granted_permission", "--granted-permission"),
    ("max_cost", "--max-cost"),
    ("allow_trust_level", "--allow-trust-level"),
    ("allow_side_effect", "--allow-side-effect"),
    ("escalate_side_effect", "--escalate-side-effect"),
    ("human_approved", "--human-approved"),
    ("dry_run", "--dry-run"),
    ("strict", "--strict"),
    ("allow_external_host", "--allow-external-host"),
    ("block_external_host", "--block-external-host"),
    ("minimum_isolation_level", "--minimum-isolation-level"),
    ("available_isolation_level", "--available-isolation-level"),
    ("connector_http", "--connector-http"),
    ("connector_http_allow_private", "--connector-http-allow-private"),
    ("connector_file_root", "--connector-file-root"),
    ("connector_shell_root", "--connector-shell-root"),
    ("connector_shell_command", "--connector-shell-command"),
    ("connector_sqlite", "--connector-sqlite"),
    ("connector_max_attempts", "--connector-max-attempts"),
    ("connector_rate_limit", "--connector-rate-limit"),
    ("connector_circuit_threshold", "--connector-circuit-threshold"),
    ("tool_impl", "--tool-impl"),
    ("agent_impl", "--agent-impl"),
    ("tool_args", "--tool-args"),
    ("top_k", "--top-k"),
    ("set_limit", "--set-limit"),
    ("max_tool_calls", "--max-tool-calls"),
    ("max_input_repairs", "--max-input-repairs"),
    ("max_tool_output_tokens", "--max-tool-output-tokens"),
    ("max_agent_depth", "--max-agent-depth"),
    ("max_agent_cost", "--max-agent-cost"),
    ("context_token_budget", "--context-token-budget"),
    ("timeout", "--timeout"),
    ("timeout_mode", "--timeout-mode"),
    ("audit_log", "--audit-log"),
    ("always_confirm", "--always-confirm"),
    ("approver", "--approver"),
    ("max_attempts", "--max-attempts"),
    ("retry_backoff", "--retry-backoff"),
    ("circuit_threshold", "--circuit-threshold"),
    ("no_compensate", "--no-compensate"),
    ("planner", "--planner"),
    ("max_parallel_steps", "--max-parallel-steps"),
    ("max_replans", "--max-replans"),
    ("format", "--format"),
)


def _redacted_tool_args(raw: str) -> str:
    """Mask credential-shaped values in ``--tool-args`` before echoing them.

    Every other forwarded option is a configuration knob; this one carries
    free-form payload data, and the hint is printed on a pause -- the moment
    the output is most likely to end up in a ticket or a CI log. Arguments
    shown to a human for approval are masked the same way (``_confirmation``),
    so the hint follows suit.
    """

    try:
        parsed = json.loads(raw)
    except ValueError:
        return raw
    return json.dumps(redact_sensitive_arguments(parsed), ensure_ascii=False, sort_keys=True)


def resume_command(args: argparse.Namespace, task_id: str) -> str:
    """Render the ``marmo resume`` command that continues this exact run.

    Only options that differ from their defaults are repeated, so the hint
    stays readable on a simple run and complete on a configured one.
    """

    defaults = vars(build_parser().parse_args(["resume", "--task-id", "_", "--state-dir", "_", "--approve"]))
    parts = ["marmo", "resume", "--task-id", task_id, "--state-dir", str(args.state_dir), "--approve"]
    approvers = tuple(args.approver)
    if approvers:
        # The policy refuses an anonymous approval, so the hint must name who answers.
        # With several approvers the person picks; a placeholder cannot pass the check by accident.
        parts.extend(("--responder", approvers[0] if len(approvers) == 1 else "<APPROVER>"))
    for dest, option in _RESUME_FORWARDED_OPTIONS:
        value = getattr(args, dest, None)
        if value is None or value == defaults.get(dest):
            continue
        if isinstance(value, bool):
            if value:
                parts.append(option)
        elif isinstance(value, (list, tuple)):
            for item in value:
                parts.extend((option, str(item)))
        elif dest == "tool_args":
            parts.extend((option, _redacted_tool_args(str(value))))
        else:
            parts.extend((option, str(value)))
    if any(str(path).startswith("-") for path in args.paths):
        parts.append("--")
    parts.extend(str(path) for path in args.paths)
    return " ".join(shlex.quote(part) for part in parts)


def _strict_violations(args: argparse.Namespace, result: Any) -> tuple[str, ...]:
    if not args.strict:
        return ()
    violations = [f"resource was skipped: {item['resource']}" for item in result.skipped_resources]
    if result.detail == NO_RESOURCE_MATCHED_DETAIL:
        violations.append("no resource matched the goal; the model answered without tools")
    if result.detail == NO_CALLABLE_SELECTED_DETAIL:
        violations.append("no Tool or Agent reached the model; the answer used no guarded call")
    requested = set(_effective_tool_arguments(args))
    evaluated = {item.tool_id for item in result.tool_results}
    violations.extend(f"requested tool was not evaluated: {tool_id}" for tool_id in sorted(requested - evaluated))
    return tuple(dict.fromkeys(violations))


def _parse_implementations(
    values: list[str], resource_kind: str
) -> dict[str, Callable[..., Any]]:
    implementations: dict[str, Callable[..., Any]] = {}
    for value in values:
        resource_id, _, target = value.partition("=")
        module_name, _, attribute = target.rpartition(":")
        if not resource_id or not module_name or module_name.startswith(".") or not attribute:
            raise CLIInputError("{resource_kind} impl must be ID=MODULE:FUNC: {value}", resource_kind=resource_kind, value=value)
        try:
            module = importlib.import_module(module_name)
        except (ImportError, SyntaxError) as exc:
            raise CLIInputError(
                "cannot load {target}: {detail}", target=target, detail=f"{type(exc).__name__}: {exc}"
            ) from exc
        handler = getattr(module, attribute, None)
        if not callable(handler):
            raise CLIInputError("{target} is not a callable", target=target)
        implementations[resource_id] = handler
    return implementations


def _add_connector_args(parser: _ArgumentParser) -> None:
    _ = parser.translate
    parser.add_argument(
        "--connector-http",
        action="store_true",
        help=_("enable the built-in HTTP Connector"),
    )
    parser.add_argument(
        "--connector-http-allow-private",
        action="store_true",
        help=_("allow HTTP destinations on private/loopback networks (unsafe unless intentional)"),
    )
    parser.add_argument(
        "--connector-file-root",
        help=_("enable the File Connector confined to this directory"),
    )
    parser.add_argument(
        "--connector-shell-root",
        help=_("root directory for the Shell Connector (requires --connector-shell-command)"),
    )
    parser.add_argument(
        "--connector-shell-command",
        action="append",
        default=[],
        metavar="EXECUTABLE",
        help=_("allow one executable in the Shell Connector; repeatable"),
    )
    parser.add_argument(
        "--connector-sqlite",
        metavar="DATABASE",
        help=_("enable the SQLite Connector for one database path"),
    )
    parser.add_argument(
        "--connector-max-attempts",
        type=int,
        default=1,
        help=_("Connector-local attempts for retry-safe read operations"),
    )
    parser.add_argument(
        "--connector-rate-limit",
        type=float,
        help=_("maximum calls per second for each Connector operation"),
    )
    parser.add_argument(
        "--connector-circuit-threshold",
        type=int,
        default=3,
        help=_("consecutive transient failures before a Connector circuit opens"),
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
        raise CLIInputError("--connector-http-allow-private requires --connector-http")
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
        raise CLIInputError("--connector-shell-root requires at least one --connector-shell-command")
    if args.connector_sqlite:
        connectors.append(SQLiteConnector(args.connector_sqlite, config=config))
    return tuple(connectors)


def _parse_limits(values: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise CLIInputError("limit must be KIND=N: {value}", value=value)
        kind, raw_limit = value.split("=", 1)
        if kind not in KINDS:
            raise CLIInputError("invalid kind in limit: {kind}", kind=kind)
        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise CLIInputError("invalid numeric limit for {kind}: {raw_limit}", kind=kind, raw_limit=raw_limit) from exc
        if limit < 0:
            raise CLIInputError("limit for {kind} must be non-negative", kind=kind)
        parsed[kind] = limit
    return parsed


def _build_llm(choice: str, tool_arguments: Mapping[str, Mapping[str, Any]]) -> LLMProvider:
    """Construct the model behind ``run``/``resume``; real providers configure themselves from .env."""

    if choice == "openai":
        return OpenAICompatibleLLMProvider()
    if choice == "anthropic":
        return AnthropicLLMProvider()
    if choice == "bedrock":
        return BedrockLLMProvider()
    return MockLLMProvider(tool_arguments=tool_arguments)


def _build_retriever(choice: str, llm: LLMProvider) -> Retriever:
    lexical = LexicalRetriever()
    if choice == "hyde":
        return HydeRetriever(llm, lexical)
    return lexical


def _warn_if_empty(registry: ResourceRegistry, paths: list[Path], language: str) -> None:
    """Tell a first-time user why a listing or search is empty instead of printing nothing."""

    if registry.list():
        return
    shown = ", ".join(str(path) for path in paths) or translate(language, "(no paths)")
    message = translate(
        language,
        "note: no resource definitions were found under {paths}. Pass a file or directory of "
        "resource JSON, or run from a checkout that has a resources/ or examples/resources/ directory.",
    )
    print(message.format(paths=shown), file=sys.stderr)


def _default_paths(paths: list[str], *, no_defaults: bool = False) -> list[Path]:
    if paths:
        return [Path(path) for path in paths]
    if no_defaults:
        return []
    for candidate in (Path("resources"), Path("skills"), Path("examples/resources")):
        if candidate.exists():
            return [candidate]
    return [Path(".")]


if __name__ == "__main__":
    raise SystemExit(main())
