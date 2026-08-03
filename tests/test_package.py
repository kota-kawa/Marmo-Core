from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import unittest

from marmo_core import (
    PackageCompatibilityError,
    PackageError,
    PackageIntegrityError,
    KERNEL_VERSION,
    SemanticVersion,
    VersionRange,
    load_registry,
    verify_local_package,
    write_package_lock,
)
from marmo_core.loader import validate_resource_paths


ROOT = Path(__file__).resolve().parents[1]


class SemanticVersionTests(unittest.TestCase):
    def test_semver_prerelease_order_and_build_equivalence(self) -> None:
        self.assertLess(SemanticVersion.parse("1.0.0-alpha.1"), SemanticVersion.parse("1.0.0"))
        self.assertLess(SemanticVersion.parse("1.0.0-alpha.2"), SemanticVersion.parse("1.0.0-alpha.10"))
        self.assertEqual(SemanticVersion.parse("1.0.0+first"), SemanticVersion.parse("1.0.0+second"))

    def test_ranges_support_comparisons_caret_and_tilde(self) -> None:
        self.assertTrue(VersionRange.parse(">=0.3.0,<1.0.0").contains("0.4.0"))
        self.assertFalse(VersionRange.parse(">=0.3.0,<1.0.0").contains("1.0.0"))
        self.assertTrue(VersionRange.parse("^1.2.3").contains("1.9.0"))
        self.assertFalse(VersionRange.parse("^1.2.3").contains("2.0.0"))
        self.assertTrue(VersionRange.parse("^0.3.0").contains("0.3.9"))
        self.assertFalse(VersionRange.parse("^0.3.0").contains("0.4.0"))
        self.assertTrue(VersionRange.parse("~1.2.3").contains("1.2.99"))
        self.assertFalse(VersionRange.parse("~1.2.3").contains("1.3.0"))


class LocalPackageTests(unittest.TestCase):
    def test_locked_package_loads_all_four_resource_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root)
            lock = write_package_lock(root)

            package = verify_local_package(root)
            registry = load_registry([root])

        self.assertEqual(package.manifest.identity, "example.local/catalog@1.0.0")
        self.assertEqual(lock.source_type, "local")
        self.assertEqual(lock.source_path, ".")
        self.assertTrue(lock.manifest_sha256.startswith("sha256:"))
        self.assertEqual(registry.summary(), {"memory": 1, "skill": 1, "tool": 1, "agent": 1, "total": 4})

    def test_tampering_is_rejected_before_resources_are_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root)
            write_package_lock(root)
            resources_path = root / "resources.json"
            resources_path.write_text(resources_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

            with self.assertRaisesRegex(PackageIntegrityError, "resource hash mismatch"):
                verify_local_package(root)
            issues = validate_resource_paths([root])

        self.assertTrue(any("resource hash mismatch" in issue.message for issue in issues))

    def test_manifest_change_requires_lock_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root)
            write_package_lock(root)
            manifest_path = root / "marmo-package.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["description"] = "reviewed change"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(PackageIntegrityError, "manifest hash mismatch"):
                verify_local_package(root)

    def test_missing_lock_is_rejected_with_actionable_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root)

            with self.assertRaisesRegex(PackageIntegrityError, "marmo package lock"):
                load_registry([root])

    def test_incompatible_kernel_is_rejected_before_loading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root, kernel=">=9.0.0,<10.0.0")
            write_package_lock(root)

            with self.assertRaisesRegex(
                PackageCompatibilityError,
                rf"current kernel is {re.escape(KERNEL_VERSION)}",
            ):
                load_registry([root])

    def test_resource_cannot_escape_declared_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            resources = _resources("another.namespace")
            _write_package(root, resources=resources)
            write_package_lock(root)

            issues = validate_resource_paths([root])

        self.assertTrue(any("must be inside package namespace" in issue.message for issue in issues))

    def test_namespace_cannot_be_bypassed_by_disabling_resource_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root, resources=_resources("another.namespace"))
            write_package_lock(root)

            with self.assertRaisesRegex(PackageError, "must be inside package namespace"):
                load_registry([root], validate=False)

    def test_packaged_markdown_skill_uses_explicit_namespaced_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root)
            manifest_path = root / "marmo-package.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["resources"] = ["skills/review/SKILL.md"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            skill_path = root / "skills" / "review" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text(
                """---
id: skill.example.local.review
name: review
version: 1.2.0
description: Review a local package.
dependencies: [memory.example.local.policy@1.0.0]
---

# Review

Review package metadata and pinned hashes.
""",
                encoding="utf-8",
            )
            write_package_lock(root)

            resource = load_registry([root]).get("skill.example.local.review")

        self.assertEqual(resource.metadata.version, "1.2.0")
        self.assertEqual(resource.metadata.dependencies, ("memory.example.local.policy@1.0.0",))

    def test_manifest_rejects_parent_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root)
            manifest_path = root / "marmo-package.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["resources"] = ["../resources.json"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(PackageError, "safe relative path"):
                write_package_lock(root)

    def test_local_package_dependencies_are_resolved_by_semver(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            base = parent / "base"
            app = parent / "app"
            _write_package(base, namespace="example.base", name="foundation", version="1.4.0")
            _write_package(
                app,
                namespace="example.app",
                name="consumer",
                dependencies=[{"name": "example.base/foundation", "version": "^1.2.0"}],
            )
            write_package_lock(base)
            write_package_lock(app)

            registry = load_registry([parent])

        self.assertEqual(len(registry), 8)

    def test_missing_local_dependency_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "app"
            _write_package(
                root,
                dependencies=[{"name": "example.base/foundation", "version": "^1.0.0"}],
            )
            write_package_lock(root)

            with self.assertRaisesRegex(PackageCompatibilityError, "not loaded"):
                load_registry([root])


class PackageCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "marmo_core.cli", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_cli_lock_verify_and_inspect(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "catalog"
            _write_package(root)

            locked = self.run_cli("package", "lock", str(root))
            verified = self.run_cli("package", "verify", str(root))
            inspected = self.run_cli("package", "inspect", str(root), "--format", "json")

        self.assertEqual(locked.returncode, 0, locked.stderr)
        self.assertIn("locked: example.local/catalog@1.0.0", locked.stdout)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertIn("verified: example.local/catalog@1.0.0", verified.stdout)
        self.assertEqual(inspected.returncode, 0, inspected.stderr)
        self.assertTrue(json.loads(inspected.stdout)["verified"])


def _write_package(
    root: Path,
    *,
    namespace: str = "example.local",
    name: str = "catalog",
    version: str = "1.0.0",
    kernel: str = ">=0.3.0,<1.0.0",
    dependencies: list[dict[str, str]] | None = None,
    resources: list[dict[str, object]] | None = None,
) -> None:
    root.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "namespace": namespace,
        "name": name,
        "version": version,
        "description": "Test package",
        "kernel": kernel,
        "resources": ["resources.json"],
        "dependencies": dependencies or [],
    }
    (root / "marmo-package.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (root / "resources.json").write_text(
        json.dumps({"resources": resources or _resources(namespace)}, indent=2),
        encoding="utf-8",
    )


def _resources(namespace: str) -> list[dict[str, object]]:
    return [_resource(kind, namespace) for kind in ("memory", "skill", "tool", "agent")]


def _resource(kind: str, namespace: str) -> dict[str, object]:
    resource: dict[str, object] = {
        "id": f"{kind}.{namespace}.demo",
        "kind": kind,
        "name": f"Demo {kind}",
        "version": "1.0.0",
        "description": f"A packaged {kind} resource.",
        "capabilities": ["demo"],
        "input_summary": "demo input",
        "output_summary": "demo output",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "verified",
        "ref": f"{kind}://{namespace}/demo",
        "tags": ["package"],
        "dependencies": [],
    }
    if kind == "memory":
        resource["content"] = "Packaged memory content."
    elif kind == "skill":
        resource["instructions"] = "Follow the packaged instructions."
    elif kind == "tool":
        resource["input_schema"] = {"type": "object", "properties": {}}
    else:
        resource["delegation_interface"] = "tool_wrap"
    return resource


if __name__ == "__main__":
    unittest.main()
