"""Local resource package loader for Marmo-Core v1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping
import json

from .errors import PackageError, ResourceLoadError, ResourceValidationError
from .markdown_skill import is_skill_markdown, load_markdown_skill
from .models import ResourceDefinition, ValidationIssue
from .package import (
    KERNEL_VERSION,
    LocalResourcePackage,
    discover_package_roots,
    validate_package_dependencies,
    validate_resource_namespace,
    verify_local_package,
)
from .registry import ResourceRegistry


SUPPORTED_SUFFIXES = {".json", ".md"}


def discover_resource_files(paths: Iterable[str | Path]) -> list[Path]:
    """Discover JSON resource definition files from explicit files or directories."""

    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise ResourceLoadError(f"resource path does not exist: {path}")
        if path.is_file():
            if path.suffix.lower() == ".json" or is_skill_markdown(path):
                files.append(path)
            continue
        for candidate in sorted(path.rglob("*.json")):
            if candidate.name.startswith("."):
                continue
            if not _looks_like_resource_json(candidate):
                continue
            files.append(candidate)
        seen_skill_dirs: set[Path] = set()
        for candidate in sorted(path.rglob("*.md"), key=lambda item: (str(item.parent), item.name != "SKILL.md", item.name)):
            if is_skill_markdown(candidate):
                parent = candidate.parent.resolve()
                if parent in seen_skill_dirs:
                    continue
                seen_skill_dirs.add(parent)
                files.append(candidate)
    return sorted(dict.fromkeys(files))


def load_resource_definitions(
    paths: Iterable[str | Path],
    *,
    validate: bool = True,
    kernel_version: str = KERNEL_VERSION,
) -> list[ResourceDefinition]:
    """Load local resource definitions.

    Supported JSON shapes:
    - {"resources": [{...}, {...}]}
    - [{...}, {...}]
    - {...single resource...}
    """

    input_paths = list(paths)
    package_roots, loose_files = _discover_sources(input_paths)
    packages = [verify_local_package(root, kernel_version=kernel_version) for root in package_roots]
    validate_package_dependencies(packages)
    definitions: list[ResourceDefinition] = []
    issues: list[ValidationIssue] = []
    for file_path in loose_files:
        loaded, file_issues = _load_definition_file(file_path, validate=validate)
        definitions.extend(loaded)
        issues.extend(file_issues)
    for package in packages:
        for file_path in package.resource_files:
            loaded, file_issues = _load_definition_file(file_path, validate=validate, root=package.root)
            for definition in loaded:
                try:
                    validate_resource_namespace(
                        package,
                        definition.metadata.id,
                        definition.metadata.kind,
                    )
                except PackageError as exc:
                    if not validate:
                        raise
                    file_issues.append(ValidationIssue(str(exc), definition.source))
            definitions.extend(loaded)
            issues.extend(file_issues)
    if validate:
        duplicate_issues = _find_duplicate_issues(definitions)
        issues.extend(duplicate_issues)
        errors = [issue for issue in issues if issue.severity == "error"]
        if errors:
            joined = "\n".join(f"{issue.path}: {issue.message}" for issue in errors)
            raise ResourceValidationError(joined)
    return definitions


def load_registry(
    paths: Iterable[str | Path],
    *,
    validate: bool = True,
    kernel_version: str = KERNEL_VERSION,
) -> ResourceRegistry:
    registry = ResourceRegistry()
    for definition in load_resource_definitions(paths, validate=validate, kernel_version=kernel_version):
        registry.add(definition)
    return registry


def validate_resource_paths(
    paths: Iterable[str | Path],
    *,
    kernel_version: str = KERNEL_VERSION,
) -> list[ValidationIssue]:
    """Return validation issues without raising."""

    definitions: list[ResourceDefinition] = []
    issues: list[ValidationIssue] = []
    try:
        package_roots, files = _discover_sources(list(paths))
    except ResourceLoadError as exc:
        return [ValidationIssue(str(exc), "paths")]
    packages: list[LocalResourcePackage] = []
    for root in package_roots:
        try:
            packages.append(verify_local_package(root, kernel_version=kernel_version))
        except PackageError as exc:
            issues.append(ValidationIssue(str(exc), str(root)))
    try:
        validate_package_dependencies(packages)
    except PackageError as exc:
        issues.append(ValidationIssue(str(exc), "packages"))
    for file_path in files:
        if is_skill_markdown(file_path):
            try:
                definition = load_markdown_skill(file_path, root=Path.cwd())
            except OSError as exc:
                issues.append(ValidationIssue(f"cannot read {file_path}: {exc}", str(file_path)))
                continue
            definitions.append(definition)
            issues.extend(definition.validate(str(file_path)))
            continue
        try:
            payload = _read_json(file_path)
            entries = _extract_entries(payload, file_path)
        except ResourceLoadError as exc:
            issues.append(ValidationIssue(str(exc), str(file_path)))
            continue
        for index, entry in enumerate(entries):
            source = f"{file_path}#{index}"
            try:
                definition = ResourceDefinition.from_mapping(entry, source=source)
            except (TypeError, ValueError) as exc:
                issues.append(ValidationIssue(str(exc), source))
                continue
            definitions.append(definition)
            issues.extend(definition.validate(source))
    for package in packages:
        for file_path in package.resource_files:
            loaded, file_issues = _load_definition_file(file_path, validate=True, root=package.root)
            for definition in loaded:
                try:
                    validate_resource_namespace(package, definition.metadata.id, definition.metadata.kind)
                except PackageError as exc:
                    file_issues.append(ValidationIssue(str(exc), definition.source))
            definitions.extend(loaded)
            issues.extend(file_issues)
    issues.extend(_find_duplicate_issues(definitions))
    return issues


def _discover_sources(paths: list[str | Path]) -> tuple[list[Path], list[Path]]:
    package_roots = discover_package_roots(paths)
    files = discover_resource_files(paths)
    loose_files = [
        file_path
        for file_path in files
        if not any(_is_within(file_path.resolve(), root) for root in package_roots)
    ]
    return package_roots, loose_files


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _load_definition_file(
    file_path: Path,
    *,
    validate: bool,
    root: Path | None = None,
) -> tuple[list[ResourceDefinition], list[ValidationIssue]]:
    definitions: list[ResourceDefinition] = []
    issues: list[ValidationIssue] = []
    if is_skill_markdown(file_path):
        try:
            definition = load_markdown_skill(file_path, root=root or Path.cwd())
        except OSError as exc:
            return [], [ValidationIssue(f"cannot read {file_path}: {exc}", str(file_path))]
        definitions.append(definition)
        if validate:
            issues.extend(definition.validate(str(file_path)))
        return definitions, issues
    try:
        payload = _read_json(file_path)
        entries = _extract_entries(payload, file_path)
    except ResourceLoadError as exc:
        return [], [ValidationIssue(str(exc), str(file_path))]
    for index, entry in enumerate(entries):
        source = f"{file_path}#{index}"
        try:
            definition = ResourceDefinition.from_mapping(entry, source=source)
        except (TypeError, ValueError) as exc:
            issues.append(ValidationIssue(str(exc), source))
            continue
        definitions.append(definition)
        if validate:
            issues.extend(definition.validate(source))
    return definitions, issues


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ResourceLoadError(f"invalid JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise ResourceLoadError(f"cannot read {path}: {exc}") from exc


def _looks_like_resource_json(path: Path) -> bool:
    try:
        payload = _read_json(path)
    except ResourceLoadError:
        return False
    if isinstance(payload, Mapping):
        if isinstance(payload.get("resources"), list):
            return True
        if isinstance(payload.get("metadata"), Mapping):
            metadata = payload["metadata"]
            return "id" in metadata and "kind" in metadata
        return "id" in payload and "kind" in payload
    if isinstance(payload, list):
        return all(isinstance(item, Mapping) and _entry_has_resource_shape(item) for item in payload)
    return False


def _entry_has_resource_shape(item: Mapping[str, Any]) -> bool:
    if isinstance(item.get("metadata"), Mapping):
        metadata = item["metadata"]
        if "id" in metadata and "kind" in metadata:
            return True
    return "id" in item and "kind" in item


def _extract_entries(payload: Any, path: Path) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping) and isinstance(payload.get("resources"), list):
        entries = payload["resources"]
    elif isinstance(payload, list):
        entries = payload
    elif isinstance(payload, Mapping):
        entries = [payload]
    else:
        raise ResourceLoadError(f"{path} must contain an object, list, or object with resources list")
    invalid = [index for index, item in enumerate(entries) if not isinstance(item, Mapping)]
    if invalid:
        raise ResourceLoadError(f"{path} has non-object resource entries at indexes: {invalid}")
    return list(entries)


def _find_duplicate_issues(definitions: Iterable[ResourceDefinition]) -> list[ValidationIssue]:
    seen: dict[str, str] = {}
    issues: list[ValidationIssue] = []
    for definition in definitions:
        identity = definition.identity
        if identity in seen:
            issues.append(
                ValidationIssue(
                    f"duplicate resource identity {identity}; first seen at {seen[identity]}",
                    definition.source,
                )
            )
        else:
            seen[identity] = definition.source
    return issues
