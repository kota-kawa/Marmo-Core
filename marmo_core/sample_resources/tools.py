"""Safe, standard-library implementations for the bundled Tool samples.

The filesystem helpers deliberately confine paths to the current working
directory. Applications that need a different boundary should wrap these
examples with their own configured workspace root.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import os
import re
import subprocess
import sys
import zipfile


_MAX_HTTP_BYTES = 1_048_576
_MAX_SEARCH_FILE_BYTES = 1_048_576
_MAX_LIST_RESULTS = 1_000
_SUITE_RE = re.compile(r"^[A-Za-z0-9_./:-]+$")
_DESTINATION_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def read_text(path: str, max_bytes: int = 65_536) -> dict[str, Any]:
    """Read bounded UTF-8 text from a file inside the current workspace."""

    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1")
    target = _workspace_path(path, must_exist=True)
    if not target.is_file():
        raise ValueError(f"path is not a file: {path}")
    with target.open("rb") as handle:
        payload = handle.read(max_bytes + 1)
    truncated = len(payload) > max_bytes
    content = payload[:max_bytes].decode("utf-8", errors="replace")
    return {
        "path": _relative(target),
        "content": content,
        "truncated": truncated,
    }


def write_text(path: str, content: str, overwrite: bool = False) -> dict[str, Any]:
    """Write UTF-8 text inside the workspace without implicit overwrites."""

    target = _workspace_path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = content.encode("utf-8")
    mode = "wb" if overwrite else "xb"
    with target.open(mode) as handle:
        handle.write(payload)
    return {"path": _relative(target), "bytes_written": len(payload)}


def list_files(directory: str = ".", pattern: str = "*") -> dict[str, Any]:
    """List at most 1,000 matching files under a workspace directory."""

    root = _workspace_path(directory, must_exist=True)
    if not root.is_dir():
        raise ValueError(f"directory is not a directory: {directory}")
    _validate_pattern(pattern)
    files: list[str] = []
    for candidate in sorted(root.glob(pattern)):
        resolved = _workspace_path(str(candidate), must_exist=True)
        if resolved.is_file():
            files.append(_relative(resolved))
        if len(files) >= _MAX_LIST_RESULTS:
            break
    return {"files": files, "truncated": len(files) >= _MAX_LIST_RESULTS}


def search_text(query: str, root: str = ".", limit: int = 100) -> dict[str, Any]:
    """Search UTF-8 text files under the workspace without loading large files."""

    if not query:
        raise ValueError("query must not be empty")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    search_root = _workspace_path(root, must_exist=True)
    candidates = [search_root] if search_root.is_file() else search_root.rglob("*")
    needle = query.casefold()
    matches: list[dict[str, Any]] = []
    for candidate in sorted(candidates):
        if not candidate.is_file() or candidate.stat().st_size > _MAX_SEARCH_FILE_BYTES:
            continue
        try:
            lines = candidate.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            if needle in line.casefold():
                matches.append(
                    {"path": _relative(candidate), "line": line_number, "text": line}
                )
                if len(matches) >= limit:
                    return {"matches": matches, "truncated": True}
    return {"matches": matches, "truncated": False}


def http_get(url: str, timeout_seconds: float = 10) -> dict[str, Any]:
    """Fetch bounded text from HTTPS without forwarding local credentials."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("url must be an HTTPS URL without embedded credentials")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    request = Request(url, headers={"Accept": "text/*, application/json", "User-Agent": "Marmo-Core/0.4"})
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - HTTPS is enforced above
        payload = response.read(_MAX_HTTP_BYTES + 1)
        truncated = len(payload) > _MAX_HTTP_BYTES
        charset = response.headers.get_content_charset() or "utf-8"
        body = payload[:_MAX_HTTP_BYTES].decode(charset, errors="replace")
        headers = {str(key): str(value) for key, value in response.headers.items()}
        return {
            "status": int(response.status),
            "headers": headers,
            "body": body,
            "truncated": truncated,
        }


def validate_json(value: Any, schema: Mapping[str, Any]) -> dict[str, Any]:
    """Validate JSON-compatible data against a practical JSON Schema subset."""

    if not isinstance(schema, Mapping):
        raise ValueError("schema must be an object")
    errors: list[str] = []
    _validate_json_value(value, schema, "$", errors)
    return {"valid": not errors, "errors": errors}


def run_tests(suite: str, timeout_seconds: float = 120) -> dict[str, Any]:
    """Run Python unittest discovery or one safe unittest target."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if suite == "discover":
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    else:
        if not _SUITE_RE.fullmatch(suite) or suite.startswith("-") or ".." in Path(suite).parts:
            raise ValueError("suite must be 'discover' or a safe unittest module/file target")
        if suite.endswith(".py") or "/" in suite:
            target = _workspace_path(suite, must_exist=True)
            if not target.is_file() or target.suffix != ".py":
                raise ValueError("file-based unittest targets must be Python files")
            command = [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(target.parent),
                "-p",
                target.name,
            ]
        else:
            command = [sys.executable, "-m", "unittest", suite]
    return _run_command(command, timeout_seconds)


def format_code(paths: Sequence[str]) -> dict[str, Any]:
    """Format selected workspace files with the project's Ruff formatter."""

    if not paths:
        raise ValueError("paths must not be empty")
    targets = [_workspace_path(path, must_exist=True) for path in paths]
    if any(not target.is_file() for target in targets):
        raise ValueError("every formatting target must be a file")
    before = {target: sha256(target.read_bytes()).hexdigest() for target in targets}
    command = [sys.executable, "-m", "ruff", "format", *(str(target) for target in targets)]
    result = _run_command(command, 120)
    changed = [
        _relative(target)
        for target in targets
        if target.exists() and sha256(target.read_bytes()).hexdigest() != before[target]
    ]
    return {"changed": changed, "diagnostics": result["output"], "exit_code": result["exit_code"]}


def create_archive(paths: Sequence[str], output: str) -> dict[str, Any]:
    """Create a ZIP archive from explicit files or directories in the workspace."""

    if not paths:
        raise ValueError("paths must not be empty")
    output_path = _workspace_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sources: dict[str, Path] = {}
    for raw_path in paths:
        source = _workspace_path(raw_path, must_exist=True)
        candidates = [source] if source.is_file() else source.rglob("*")
        for candidate in candidates:
            if candidate.is_file() and candidate.resolve() != output_path:
                sources[_relative(candidate)] = candidate
    if not sources:
        raise ValueError("paths did not contain any files")
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, source in sorted(sources.items()):
            archive.write(source, arcname=relative)
    return {
        "path": _relative(output_path),
        "file_count": len(sources),
        "bytes": output_path.stat().st_size,
    }


def send_notification(destination: str, message: str, subject: str = "") -> dict[str, Any]:
    """Send JSON to an HTTPS webhook configured by destination alias.

    For destination ``ops``, configure ``MARMO_NOTIFICATION_OPS_URL``. Keeping
    the URL out of tool arguments prevents webhook credentials from entering
    model-visible state and audit records.
    """

    if not _DESTINATION_RE.fullmatch(destination):
        raise ValueError("destination must contain only letters, digits, '_' or '-'")
    if not message:
        raise ValueError("message must not be empty")
    env_key = f"MARMO_NOTIFICATION_{destination.upper().replace('-', '_')}_URL"
    webhook_url = os.environ.get(env_key, "")
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"configure {env_key} with an HTTPS webhook URL")
    payload = json.dumps({"subject": subject, "message": message}).encode("utf-8")
    request = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Marmo-Core/0.4"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310 - HTTPS is enforced above
        response.read(65_536)
        message_id = response.headers.get("X-Message-Id")
        if not message_id:
            message_id = sha256(destination.encode("utf-8") + payload).hexdigest()[:16]
        return {"message_id": message_id, "status": str(response.status)}


def _workspace_path(raw_path: str, *, must_exist: bool = False) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("path must be a non-empty string")
    workspace = Path.cwd().resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise ValueError(f"path escapes the current workspace: {raw_path}") from exc
    if must_exist and not resolved.exists():
        raise ValueError(f"workspace path does not exist: {raw_path}")
    return resolved


def _relative(path: Path) -> str:
    return path.resolve().relative_to(Path.cwd().resolve()).as_posix()


def _validate_pattern(pattern: str) -> None:
    if not pattern or Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        raise ValueError("pattern must be a non-empty workspace-relative glob")


def _run_command(command: list[str], timeout_seconds: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=Path.cwd(),
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        parts: list[str] = []
        for part in (exc.stdout, exc.stderr):
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, bytes):
                parts.append(part.decode("utf-8", errors="replace"))
        output = "\n".join(parts)
        return {"exit_code": 124, "output": output or f"timed out after {timeout_seconds:g}s"}
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return {"exit_code": completed.returncode, "output": output}


def _validate_json_value(value: Any, schema: Mapping[str, Any], path: str, errors: list[str]) -> None:
    expected = schema.get("type")
    if isinstance(expected, str) and not _matches_json_type(value, expected):
        errors.append(f"{path}: expected {expected}")
        return
    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        errors.append(f"{path}: value is not in enum")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            errors.append(f"{path}: value is below minimum {minimum}")
        if isinstance(maximum, (int, float)) and value > maximum:
            errors.append(f"{path}: value is above maximum {maximum}")
    if isinstance(value, Mapping):
        required = schema.get("required")
        if isinstance(required, list):
            for name in required:
                if name not in value:
                    errors.append(f"{path}.{name}: required property is missing")
        properties = schema.get("properties")
        properties = properties if isinstance(properties, Mapping) else {}
        for name, item in value.items():
            item_schema = properties.get(name)
            if isinstance(item_schema, Mapping):
                _validate_json_value(item, item_schema, f"{path}.{name}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{name}: additional property is not allowed")
    if isinstance(value, list) and isinstance(schema.get("items"), Mapping):
        for index, item in enumerate(value):
            _validate_json_value(item, schema["items"], f"{path}[{index}]", errors)


def _matches_json_type(value: Any, expected: str) -> bool:
    checks = {
        "null": value is None,
        "boolean": isinstance(value, bool),
        "object": isinstance(value, Mapping),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }
    return checks.get(expected, True)
