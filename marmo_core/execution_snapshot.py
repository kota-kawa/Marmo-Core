"""Persist the selected execution set so a resumed task keeps its route."""

from __future__ import annotations

from typing import Any, Mapping
import hashlib
import json
import math

from .errors import MarmoError, ResourceNotFoundError
from .activator import InjectedMemory, LoadedSkill
from .compiler import CompiledContext
from .models import ResourceDefinition, SearchResult, SelectionResult
from .registry import ResourceRegistry


class SnapshotMismatchError(MarmoError):
    """The selected resources changed while a task was paused."""


def capture_selection(
    selection: SelectionResult,
    *,
    candidate_count: int,
    callable_candidates: bool,
    catalog_nonempty: bool,
) -> dict[str, Any]:
    return {
        "version": 1,
        "status": selection.status,
        "reason": selection.reason,
        "candidate_count": candidate_count,
        "callable_candidates": callable_candidates,
        "catalog_nonempty": catalog_nonempty,
        "activation_fingerprints": {},
        "selected": [
            {
                "identity": result.resource.identity,
                "fingerprint": _fingerprint(result.resource),
                "score": result.score,
                "reasons": list(result.reasons),
                "components": dict(result.components),
            }
            for result in selection.results
        ],
    }


def restore_selection(
    snapshot: Mapping[str, Any], registry: ResourceRegistry
) -> tuple[SelectionResult, int, bool, bool]:
    if snapshot.get("version") != 1 or not isinstance(snapshot.get("selected"), list):
        raise SnapshotMismatchError("saved execution snapshot has an unsupported format")
    selected: list[SearchResult] = []
    for item in snapshot["selected"]:
        if not isinstance(item, Mapping) or not isinstance(item.get("identity"), str):
            raise SnapshotMismatchError("saved execution snapshot has an invalid resource entry")
        identity = item["identity"]
        try:
            definition = registry.get(identity)
        except ResourceNotFoundError as exc:
            raise SnapshotMismatchError(
                f"selected resource {identity} is no longer available; resume with the original catalog"
            ) from exc
        if _fingerprint(definition) != item.get("fingerprint"):
            raise SnapshotMismatchError(
                f"selected resource {identity} changed; resume with the original catalog"
            )
        try:
            score = float(item["score"])
            components = {str(key): float(value) for key, value in item["components"].items()}
            if not math.isfinite(score) or any(not math.isfinite(value) for value in components.values()):
                raise SnapshotMismatchError("saved execution snapshot has a non-finite score")
            selected.append(
                SearchResult(
                    definition,
                    score,
                    tuple(str(reason) for reason in item["reasons"]),
                    components,
                )
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise SnapshotMismatchError("saved execution snapshot has an invalid score entry") from exc
    status = snapshot.get("status")
    reason = snapshot.get("reason")
    candidate_count = snapshot.get("candidate_count")
    if status not in ("selected", "abstain") or not isinstance(reason, str):
        raise SnapshotMismatchError("saved execution snapshot has an invalid selection result")
    if type(candidate_count) is not int or candidate_count < len(selected):
        raise SnapshotMismatchError("saved execution snapshot has an invalid candidate count")
    if type(snapshot.get("callable_candidates")) is not bool or type(snapshot.get("catalog_nonempty")) is not bool:
        raise SnapshotMismatchError("saved execution snapshot has invalid routing flags")
    activation_fingerprints = snapshot.get("activation_fingerprints", {})
    if not isinstance(activation_fingerprints, Mapping) or any(
        not isinstance(identity, str) or not isinstance(fingerprint, str)
        for identity, fingerprint in activation_fingerprints.items()
    ):
        raise SnapshotMismatchError("saved execution snapshot has invalid activation fingerprints")
    return (
        SelectionResult(tuple(selected), reason, status=status),
        candidate_count,
        bool(snapshot.get("callable_candidates")),
        bool(snapshot.get("catalog_nonempty")),
    )


def _fingerprint(definition: ResourceDefinition) -> str:
    metadata = definition.metadata.to_dict()
    metadata.pop("stats", None)
    payload = {"metadata": metadata, "extras": definition.extras}
    try:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise SnapshotMismatchError(
            f"resource {definition.identity} cannot be saved in an execution snapshot"
        ) from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def compiled_fingerprint(compiled: CompiledContext) -> str:
    payload = {
        "system_prompt": compiled.system_prompt,
        "messages": [message.to_dict() for message in compiled.messages],
        "tools": [tool.to_dict() for tool in compiled.tools],
        "resource_ids": list(compiled.resource_ids),
        "omitted_resource_ids": list(compiled.omitted_resource_ids),
        "trimmed_resource_ids": list(compiled.trimmed_resource_ids),
        "token_budget": compiled.token_budget,
        "agent_ids": list(compiled.agent_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def activated_context_fingerprint(activated: InjectedMemory | LoadedSkill) -> str:
    """Fingerprint loaded text as soon as policy allows it to be read."""

    content = activated.content if isinstance(activated, InjectedMemory) else activated.instructions
    payload = {
        "identity": activated.metadata.identity,
        "kind": activated.metadata.kind,
        "content": content,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
