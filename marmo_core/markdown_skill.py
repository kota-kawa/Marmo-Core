"""Markdown skill package adapter for local SKILL.md files."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from .models import ResourceDefinition, ResourceMetadata, ResourceStats


SKILL_MARKDOWN_NAMES = {"skill.md", "SKILL.md"}

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def is_skill_markdown(path: Path) -> bool:
    return path.name in SKILL_MARKDOWN_NAMES


def load_markdown_skill(path: Path, root: Path | None = None) -> ResourceDefinition:
    content = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    skill_name = _clean_str(frontmatter.get("name")) or _humanize(path.parent.name)
    description = _clean_str(frontmatter.get("description")) or _first_paragraph(body) or f"Markdown skill instructions for {skill_name}."
    original_version = _clean_str(frontmatter.get("version"))
    version = original_version if _SEMVER_RE.match(original_version) else "1.0.0"
    tags = _derive_tags(path=path, name=skill_name, description=description, frontmatter=frontmatter)
    capabilities = _derive_capabilities(skill_name, description, tags)
    resource_id = _clean_str(frontmatter.get("id")) or _resource_id_from_path(path, root)
    metadata = ResourceMetadata(
        id=resource_id,
        kind="skill",
        name=skill_name,
        version=version,
        description=description,
        capabilities=tuple(capabilities),
        input_summary=f"Task request that may benefit from the {skill_name} skill.",
        output_summary=f"Loaded Markdown skill instructions for {skill_name}.",
        required_permissions=tuple(_as_str_list(frontmatter.get("required_permissions"))),
        cost_estimate=_as_float(frontmatter.get("cost_estimate"), default=0.0),
        latency_class=_clean_str(frontmatter.get("latency_class")) or "fast",
        side_effect=_clean_str(frontmatter.get("side_effect")) or "none",
        trust_level=_clean_str(frontmatter.get("trust_level")) or "community",
        ref=str(path),
        tags=tuple(tags),
        dependencies=tuple(_as_str_list(frontmatter.get("dependencies"))),
        conflicts_with=tuple(_as_str_list(frontmatter.get("conflicts_with"))),
        stats=ResourceStats(),
    )
    return ResourceDefinition(
        metadata=metadata,
        extras={
            "source_type": "markdown_skill",
            "frontmatter": frontmatter,
            "original_version": original_version or None,
            "content": content,
            "body": body,
        },
        source=str(path),
    )


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---"):
        return {}, content
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, content
    header = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).strip()
    return _parse_simple_yaml(header), body


def _parse_simple_yaml(header: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    current_values: list[str] = []

    def commit() -> None:
        nonlocal current_key, current_values
        if current_key is not None and current_values:
            data[current_key] = " ".join(value.strip() for value in current_values if value.strip()).strip()
        current_key = None
        current_values = []

    for raw_line in header.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line[:1].isspace() and current_key is not None:
            stripped = raw_line.strip()
            if stripped.startswith("- "):
                existing = data.get(current_key)
                if not isinstance(existing, list):
                    data[current_key] = []
                data[current_key].append(_unquote(stripped[2:].strip()))
            else:
                current_values.append(stripped)
            continue
        commit()
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value in {"|", ">"}:
            data[key] = ""
            current_key = key
            current_values = []
        elif value:
            data[key] = _parse_scalar_or_list(value)
        else:
            data[key] = ""
            current_key = key
            current_values = []
    commit()
    return data


def _parse_scalar_or_list(value: str) -> Any:
    value = _unquote(value)
    if value.startswith("[") and value.endswith("]"):
        items = [item.strip() for item in value[1:-1].split(",")]
        return [_unquote(item) for item in items if item]
    return value


def _first_paragraph(body: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    for paragraph in paragraphs:
        cleaned = re.sub(r"^#+\s*", "", paragraph).strip()
        if cleaned:
            return re.sub(r"\s+", " ", cleaned)
    return ""


def _derive_tags(path: Path, name: str, description: str, frontmatter: dict[str, Any]) -> list[str]:
    tags = []
    tags.extend(_as_str_list(frontmatter.get("tags")))
    tags.extend(_tokenize(path.parent.name))
    tags.extend(_tokenize(name))
    tags.extend(_tokenize(description)[:8])
    unique: list[str] = []
    for tag in tags:
        normalized = tag.lower().strip("_-.")
        if normalized and normalized not in unique:
            unique.append(normalized)
        if len(unique) >= 16:
            break
    return unique or ["skill"]


def _derive_capabilities(name: str, description: str, tags: list[str]) -> list[str]:
    capabilities = ["skill instructions", name]
    capabilities.extend(tags[:6])
    for token in _tokenize(description):
        if token not in capabilities:
            capabilities.append(token)
        if len(capabilities) >= 10:
            break
    return capabilities


def _resource_id_from_path(path: Path, root: Path | None) -> str:
    try:
        relative = path.parent.resolve().relative_to((root or Path.cwd()).resolve())
        parts = _strip_resource_prefix(relative.parts)
    except ValueError:
        parts = (path.parent.name,)
    slug = "__".join(parts) if parts else path.parent.name
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", slug).strip("-._").lower()
    if not normalized:
        normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", path.parent.name).strip("-._").lower()
    return f"skill.{normalized}"


def _strip_resource_prefix(parts: tuple[str, ...]) -> tuple[str, ...]:
    if parts and parts[0] == "resources":
        parts = parts[1:]
    if parts and parts[0] == "skills":
        parts = parts[1:]
    return parts


def _humanize(value: str) -> str:
    return re.sub(r"[-_]+", " ", value).strip().title()


def _tokenize(value: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_RE.finditer(value) if len(match.group(0)) > 1]


def _clean_str(value: Any) -> str:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip().strip('"').strip("'")
    return ""


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_clean_str(item) for item in value if _clean_str(item)]
    if isinstance(value, str):
        return [_clean_str(item) for item in value.split(",") if _clean_str(item)]
    return []


def _as_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default
