"""Portable, hash-locked local resource packages (F-DIST-01--05)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import total_ordering
from pathlib import Path
from typing import Any, Iterable, Mapping
import hashlib
import json
import os
import re
import tempfile

from ._version import __version__ as KERNEL_VERSION
from .errors import PackageCompatibilityError, PackageError, PackageIntegrityError


MANIFEST_FILENAME = "marmo-package.json"
LOCK_FILENAME = "marmo-package.lock.json"
PACKAGE_SCHEMA_VERSION = 1
LOCK_SCHEMA_VERSION = 1

_IDENTIFIER_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_NAMESPACE_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*$"
)
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@total_ordering
@dataclass(frozen=True)
class SemanticVersion:
    """A small SemVer 2.0 value object with correct prerelease ordering."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = field(default=(), compare=False)

    @classmethod
    def parse(cls, value: str) -> "SemanticVersion":
        match = _SEMVER_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"invalid SemVer: {value!r}")
        prerelease = tuple(match.group(4).split(".")) if match.group(4) else ()
        build = tuple(match.group(5).split(".")) if match.group(5) else ()
        for part in prerelease:
            if part.isdigit() and len(part) > 1 and part.startswith("0"):
                raise ValueError(f"invalid SemVer numeric prerelease identifier: {part!r}")
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)), prerelease, build)

    def __str__(self) -> str:
        value = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            value += "-" + ".".join(self.prerelease)
        if self.build:
            value += "+" + ".".join(self.build)
        return value

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        left = (self.major, self.minor, self.patch)
        right = (other.major, other.minor, other.patch)
        if left != right:
            return left < right
        return _prerelease_less(self.prerelease, other.prerelease)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return (
            self.major,
            self.minor,
            self.patch,
            self.prerelease,
        ) == (
            other.major,
            other.minor,
            other.patch,
            other.prerelease,
        )


@dataclass(frozen=True)
class VersionRange:
    """A comma-separated SemVer range supporting exact, comparison, ^ and ~."""

    expression: str
    constraints: tuple[tuple[str, SemanticVersion], ...] = ()

    @classmethod
    def parse(cls, expression: str) -> "VersionRange":
        normalized = expression.strip()
        if normalized in ("", "*"):
            return cls(normalized or "*", ())
        if "||" in normalized:
            raise ValueError("SemVer range unions (||) are not supported")
        constraints: list[tuple[str, SemanticVersion]] = []
        for raw in normalized.split(","):
            token = raw.strip()
            if not token:
                raise ValueError(f"invalid SemVer range: {expression!r}")
            if token.startswith("^"):
                version = SemanticVersion.parse(token[1:])
                constraints.extend(((">=", version), ("<", _caret_upper(version))))
                continue
            if token.startswith("~"):
                version = SemanticVersion.parse(token[1:])
                constraints.extend(((">=", version), ("<", SemanticVersion(version.major, version.minor + 1, 0))))
                continue
            match = re.fullmatch(r"(>=|<=|>|<|==|=)?\s*(.+)", token)
            if not match:
                raise ValueError(f"invalid SemVer constraint: {token!r}")
            constraints.append((match.group(1) or "==", SemanticVersion.parse(match.group(2))))
        return cls(normalized, tuple(constraints))

    def contains(self, version: str | SemanticVersion) -> bool:
        candidate = SemanticVersion.parse(version) if isinstance(version, str) else version
        for operator, expected in self.constraints:
            if operator in ("=", "==") and candidate != expected:
                return False
            if operator == ">=" and candidate < expected:
                return False
            if operator == ">" and candidate <= expected:
                return False
            if operator == "<=" and candidate > expected:
                return False
            if operator == "<" and candidate >= expected:
                return False
        return True


@dataclass(frozen=True)
class PackageDependency:
    name: str
    version: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PackageDependency":
        name = _required_string(data, "name")
        version = _required_string(data, "version")
        _validate_qualified_name(name)
        VersionRange.parse(version)
        return cls(name=name, version=version)

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True)
class PackageManifest:
    namespace: str
    name: str
    version: str
    kernel: str
    resources: tuple[str, ...]
    dependencies: tuple[PackageDependency, ...] = ()
    description: str = ""
    schema_version: int = PACKAGE_SCHEMA_VERSION

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}/{self.name}"

    @property
    def identity(self) -> str:
        return f"{self.qualified_name}@{self.version}"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PackageManifest":
        schema_version = data.get("schema_version")
        if schema_version != PACKAGE_SCHEMA_VERSION:
            raise PackageError(
                f"unsupported package schema_version {schema_version!r}; expected {PACKAGE_SCHEMA_VERSION}"
            )
        namespace = _required_string(data, "namespace")
        name = _required_string(data, "name")
        version = _required_string(data, "version")
        kernel = _required_string(data, "kernel")
        if not _NAMESPACE_RE.fullmatch(namespace):
            raise PackageError(f"invalid package namespace: {namespace!r}")
        if not _IDENTIFIER_RE.fullmatch(name):
            raise PackageError(f"invalid package name: {name!r}")
        SemanticVersion.parse(version)
        VersionRange.parse(kernel)
        resources = _string_list(data.get("resources"), "resources", require_nonempty=True)
        if len(set(resources)) != len(resources):
            raise PackageError("package resources must not contain duplicate paths")
        for resource in resources:
            _validate_relative_path(resource, field_name="resource")
            if Path(resource).suffix.lower() not in (".json", ".md"):
                raise PackageError(f"unsupported package resource file: {resource}")
        dependencies_data = data.get("dependencies", [])
        if not isinstance(dependencies_data, list):
            raise PackageError("package dependencies must be a list")
        dependencies: list[PackageDependency] = []
        for index, item in enumerate(dependencies_data):
            if not isinstance(item, Mapping):
                raise PackageError(f"package dependency at index {index} must be an object")
            dependencies.append(PackageDependency.from_mapping(item))
        names = [dependency.name for dependency in dependencies]
        if len(set(names)) != len(names):
            raise PackageError("package dependencies must not contain duplicate names")
        description = data.get("description", "")
        if not isinstance(description, str):
            raise PackageError("package description must be a string")
        return cls(
            namespace=namespace,
            name=name,
            version=version,
            kernel=kernel,
            resources=resources,
            dependencies=tuple(dependencies),
            description=description,
            schema_version=schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "namespace": self.namespace,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "kernel": self.kernel,
            "resources": list(self.resources),
            "dependencies": [dependency.to_dict() for dependency in self.dependencies],
        }


@dataclass(frozen=True)
class PackageLock:
    package: str
    source_type: str
    source_path: str
    manifest_sha256: str
    files: Mapping[str, str]
    schema_version: int = LOCK_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PackageLock":
        if data.get("schema_version") != LOCK_SCHEMA_VERSION:
            raise PackageIntegrityError(
                f"unsupported lock schema_version {data.get('schema_version')!r}; expected {LOCK_SCHEMA_VERSION}"
            )
        package = _required_string(data, "package", error_type=PackageIntegrityError)
        manifest_sha256 = _required_string(data, "manifest_sha256", error_type=PackageIntegrityError)
        source = data.get("source")
        if not isinstance(source, Mapping):
            raise PackageIntegrityError("lock source must be an object")
        source_type = _required_string(source, "type", error_type=PackageIntegrityError)
        source_path = _required_string(source, "path", error_type=PackageIntegrityError)
        if source_type != "local":
            raise PackageIntegrityError(f"unsupported lock source type: {source_type!r}")
        if source_path != ".":
            _validate_relative_path(source_path, field_name="lock source path", error_type=PackageIntegrityError)
        files = data.get("files")
        if not isinstance(files, Mapping) or not files:
            raise PackageIntegrityError("lock files must be a non-empty object")
        normalized_files: dict[str, str] = {}
        for raw_path, raw_digest in files.items():
            if not isinstance(raw_path, str) or not isinstance(raw_digest, str):
                raise PackageIntegrityError("lock file paths and digests must be strings")
            _validate_relative_path(raw_path, field_name="lock file", error_type=PackageIntegrityError)
            _validate_digest(raw_digest)
            normalized_files[raw_path] = raw_digest
        _validate_digest(manifest_sha256)
        return cls(
            package=package,
            source_type=source_type,
            source_path=source_path,
            manifest_sha256=manifest_sha256,
            files=normalized_files,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "package": self.package,
            "source": {"type": self.source_type, "path": self.source_path},
            "manifest_sha256": self.manifest_sha256,
            "files": dict(sorted(self.files.items())),
        }


@dataclass(frozen=True)
class LocalResourcePackage:
    root: Path
    manifest: PackageManifest
    lock: PackageLock
    resource_files: tuple[Path, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "manifest": self.manifest.to_dict(),
            "lock": self.lock.to_dict(),
            "compatible_kernel": KERNEL_VERSION,
            "verified": True,
        }


def read_package_manifest(path: str | Path) -> PackageManifest:
    root = package_root(path)
    payload = _read_object(root / MANIFEST_FILENAME, PackageError)
    try:
        return PackageManifest.from_mapping(payload)
    except ValueError as exc:
        raise PackageError(str(exc)) from exc


def build_package_lock(path: str | Path, *, source_path: str = ".") -> PackageLock:
    """Build an in-memory lock from the exact manifest resource list."""

    root = package_root(path)
    manifest = read_package_manifest(root)
    if source_path != ".":
        _validate_relative_path(source_path, field_name="source path")
    files: dict[str, str] = {}
    for relative in manifest.resources:
        resource_path = _safe_package_path(root, relative)
        if not resource_path.is_file():
            raise PackageError(f"package resource does not exist: {relative}")
        files[relative] = _sha256(resource_path)
    return PackageLock(
        package=manifest.identity,
        source_type="local",
        source_path=source_path,
        manifest_sha256=_sha256(root / MANIFEST_FILENAME),
        files=files,
    )


def write_package_lock(path: str | Path, *, source_path: str = ".") -> PackageLock:
    """Atomically create or refresh ``marmo-package.lock.json``."""

    root = package_root(path)
    lock = build_package_lock(root, source_path=source_path)
    destination = root / LOCK_FILENAME
    serialized = json.dumps(lock.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{LOCK_FILENAME}.", dir=root, text=True)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, destination)
    except OSError as exc:
        raise PackageError(f"cannot write package lock {destination}: {exc}") from exc
    return lock


def verify_local_package(
    path: str | Path,
    *,
    kernel_version: str = KERNEL_VERSION,
) -> LocalResourcePackage:
    """Verify schema, compatibility, source record, and every pinned hash."""

    root = package_root(path)
    manifest = read_package_manifest(root)
    try:
        compatible = VersionRange.parse(manifest.kernel).contains(kernel_version)
    except ValueError as exc:
        raise PackageCompatibilityError(str(exc)) from exc
    if not compatible:
        raise PackageCompatibilityError(
            f"package {manifest.identity} requires kernel {manifest.kernel}; current kernel is {kernel_version}"
        )
    lock_path = root / LOCK_FILENAME
    if not lock_path.is_file():
        raise PackageIntegrityError(
            f"package {manifest.identity} is not locked; run 'marmo package lock {root}'"
        )
    lock = PackageLock.from_mapping(_read_object(lock_path, PackageIntegrityError))
    if lock.package != manifest.identity:
        raise PackageIntegrityError(
            f"lock package is {lock.package!r}, expected {manifest.identity!r}; refresh the lock"
        )
    expected_paths = set(manifest.resources)
    locked_paths = set(lock.files)
    if expected_paths != locked_paths:
        missing = sorted(expected_paths - locked_paths)
        stale = sorted(locked_paths - expected_paths)
        raise PackageIntegrityError(f"lock file set differs from manifest; missing={missing}, stale={stale}")
    actual_manifest = _sha256(root / MANIFEST_FILENAME)
    if actual_manifest != lock.manifest_sha256:
        raise PackageIntegrityError("package manifest hash mismatch; refresh the lock after reviewing changes")
    resource_files: list[Path] = []
    for relative in manifest.resources:
        resource_path = _safe_package_path(root, relative)
        if not resource_path.is_file():
            raise PackageIntegrityError(f"locked resource does not exist: {relative}")
        actual = _sha256(resource_path)
        if actual != lock.files[relative]:
            raise PackageIntegrityError(f"resource hash mismatch: {relative}")
        resource_files.append(resource_path)
    return LocalResourcePackage(root=root, manifest=manifest, lock=lock, resource_files=tuple(resource_files))


def discover_package_roots(paths: Iterable[str | Path]) -> list[Path]:
    """Find direct or nested local package roots deterministically."""

    roots: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.name in (MANIFEST_FILENAME, LOCK_FILENAME):
            roots.append(path.parent.resolve())
        elif path.is_dir() and (path / MANIFEST_FILENAME).is_file():
            roots.append(path.resolve())
        elif path.is_dir():
            roots.extend(candidate.parent.resolve() for candidate in sorted(path.rglob(MANIFEST_FILENAME)))
    return sorted(dict.fromkeys(roots))


def package_root(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_file():
        candidate = candidate.parent
    root = candidate.resolve()
    if not (root / MANIFEST_FILENAME).is_file():
        raise PackageError(f"package manifest not found: {root / MANIFEST_FILENAME}")
    return root


def validate_package_dependencies(packages: Iterable[LocalResourcePackage]) -> None:
    """Require every local dependency to be present at a compatible version."""

    available: dict[str, list[PackageManifest]] = {}
    package_list = list(packages)
    for package in package_list:
        available.setdefault(package.manifest.qualified_name, []).append(package.manifest)
    failures: list[str] = []
    for package in package_list:
        for dependency in package.manifest.dependencies:
            candidates = available.get(dependency.name, [])
            version_range = VersionRange.parse(dependency.version)
            if not any(version_range.contains(candidate.version) for candidate in candidates):
                found = ", ".join(candidate.version for candidate in candidates) or "not loaded"
                failures.append(
                    f"{package.manifest.identity} requires {dependency.name} {dependency.version}; found {found}"
                )
    if failures:
        raise PackageCompatibilityError("package dependency check failed:\n" + "\n".join(failures))


def validate_resource_namespace(package: LocalResourcePackage, resource_id: str, kind: str) -> None:
    prefix = f"{kind}.{package.manifest.namespace}."
    if not resource_id.startswith(prefix) or len(resource_id) == len(prefix):
        raise PackageError(
            f"resource {resource_id!r} must be inside package namespace {prefix + '*'}"
        )


def _prerelease_less(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    if not left:
        return False
    if not right:
        return True
    for left_part, right_part in zip(left, right):
        if left_part == right_part:
            continue
        left_numeric = left_part.isdigit()
        right_numeric = right_part.isdigit()
        if left_numeric and right_numeric:
            return int(left_part) < int(right_part)
        if left_numeric != right_numeric:
            return left_numeric
        return left_part < right_part
    return len(left) < len(right)


def _caret_upper(version: SemanticVersion) -> SemanticVersion:
    if version.major > 0:
        return SemanticVersion(version.major + 1, 0, 0)
    if version.minor > 0:
        return SemanticVersion(0, version.minor + 1, 0)
    return SemanticVersion(0, 0, version.patch + 1)


def _validate_qualified_name(value: str) -> None:
    parts = value.split("/", 1)
    if len(parts) != 2 or not _NAMESPACE_RE.fullmatch(parts[0]) or not _IDENTIFIER_RE.fullmatch(parts[1]):
        raise ValueError(f"invalid qualified package name: {value!r}; expected namespace/name")


def _required_string(
    data: Mapping[str, Any],
    key: str,
    *,
    error_type: type[PackageError] = PackageError,
) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"{key} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field_name: str, *, require_nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (require_nonempty and not value):
        suffix = " and non-empty" if require_nonempty else ""
        raise PackageError(f"{field_name} must be a list{suffix}")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise PackageError(f"{field_name} entries must be non-empty strings")
    return tuple(item.strip() for item in value)


def _validate_relative_path(
    value: str,
    *,
    field_name: str,
    error_type: type[PackageError] = PackageError,
) -> None:
    path = Path(value)
    if path.is_absolute() or value in ("", ".") or ".." in path.parts:
        raise error_type(f"{field_name} must be a safe relative path: {value!r}")


def _safe_package_path(root: Path, relative: str) -> Path:
    _validate_relative_path(relative, field_name="package path")
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PackageError(f"package path escapes its root: {relative}") from exc
    return target


def _read_object(path: Path, error_type: type[PackageError]) -> Mapping[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise error_type(f"cannot read {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise error_type(f"{path} must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise PackageIntegrityError(f"cannot hash {path}: {exc}") from exc
    return "sha256:" + digest.hexdigest()


def _validate_digest(value: str) -> None:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise PackageIntegrityError(f"invalid SHA-256 digest: {value!r}")
