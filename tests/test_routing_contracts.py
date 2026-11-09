from __future__ import annotations

import unittest

from marmo_core.routing_contracts import (
    AllOf,
    OneOf,
    Requirement,
    RequirementExpression,
    ResourceContract,
    TaskSpec,
    TruthValue,
    evaluate_expression,
    match_requirement,
)


def _contract(**overrides):
    value = {
        "schema_version": 1,
        "observed": True,
        "complete": True,
        "affordances": [
            {
                "action": "read",
                "entity_type": "document",
                "supported_scope": "workspace",
                "output_type": "text",
                "mode": "effect",
            }
        ],
        "context": {"all_of": [], "one_of": []},
        "permissions": [],
        "call_preconditions": [],
        "source_evidence": [{"source": "test", "evidence": "declaration"}],
    }
    value.update(overrides)
    return ResourceContract.from_mapping(value)


def _requirement(**overrides):
    value = {
        "action": "read",
        "entity_type": "document",
        "target_scope": "workspace/team-a",
        "output_type": "text",
        "mode": "effect",
    }
    value.update(overrides)
    return Requirement.from_mapping(value)


class RoutingContractsTests(unittest.TestCase):
    def test_missing_scope_output_or_contract_components_are_unknown(self) -> None:
        contract = _contract()
        for field in ("target_scope", "output_type"):
            value = {"action": "read", "entity_type": "document", "target_scope": "workspace",
                     "output_type": "text", "mode": "effect"}
            del value[field]
            requirement = Requirement.from_mapping(value)
            self.assertTrue(requirement.unknown_items)
            self.assertEqual(match_requirement(requirement, contract, "tool"), TruthValue.UNKNOWN)
        self.assertEqual(match_requirement(Requirement("read", "document"), contract, "tool"), TruthValue.UNKNOWN)
        for field in ("schema_version", "permissions", "context", "call_preconditions", "affordances"):
            value = {"schema_version": 1, "observed": True, "complete": True,
                     "affordances": [], "permissions": [], "context": {}, "call_preconditions": [],
                     "source_evidence": [{"source": "test", "evidence": "declaration"}]}
            del value[field]
            self.assertTrue(ResourceContract.from_mapping(value).unknown_items, field)

    def test_scopes_are_containment_checked_and_unknown_is_preserved(self) -> None:
        contract = _contract()
        self.assertEqual(match_requirement(_requirement(), contract, "tool"), TruthValue.TRUE)
        self.assertEqual(
            match_requirement(_requirement(target_scope="workspace/team-b"), contract, "tool"),
            TruthValue.TRUE,
        )
        narrow = _contract(
            affordances=[
                {
                    "action": "read",
                    "entity_type": "document",
                    "supported_scope": "workspace/team-a/private",
                    "output_type": "text",
                    "mode": "effect",
                }
            ]
        )
        self.assertEqual(match_requirement(_requirement(), narrow, "tool"), TruthValue.FALSE)
        unsupported_version = _contract(schema_version=2)
        self.assertEqual(match_requirement(_requirement(), unsupported_version, "tool"), TruthValue.UNKNOWN)

    def test_malformed_or_unsupported_modes_are_unknown(self) -> None:
        contract = _contract()
        self.assertEqual(match_requirement(_requirement(mode="operate"), contract, "tool"), TruthValue.UNKNOWN)
        explicit_null = _requirement(target_scope=None)
        self.assertTrue(explicit_null.unknown_items)
        self.assertEqual(match_requirement(explicit_null, contract, "tool"), TruthValue.UNKNOWN)
        missing_mode = Requirement.from_mapping({"action": "read", "entity_type": "document"})
        self.assertEqual(match_requirement(missing_mode, contract, "tool"), TruthValue.UNKNOWN)

    def test_malformed_permissions_and_all_of_are_not_empty_declarations(self) -> None:
        permissions = _contract(permissions=None)
        self.assertTrue(permissions.unknown_items)
        all_of = _contract(context={"all_of": None, "one_of": []})
        self.assertTrue(all_of.unknown_items)

    def test_unversioned_and_versioned_vocabulary_behavior_is_explicit(self) -> None:
        task = TaskSpec.from_mapping({"requirements": _requirement() .__dict__})
        self.assertIsNone(task.vocabulary_version)
        self.assertIsNone(task.vocabulary_hash)
        bound = TaskSpec.from_mapping(
            {
                "requirements": {
                    "action": "read",
                    "entity_type": "document",
                    "target_scope": "workspace",
                    "mode": "effect",
                },
                "vocabulary_version": "ontology-v1",
                "vocabulary_hash": "f" * 64,
            }
        )
        self.assertEqual(bound.vocabulary_version, "ontology-v1")
        self.assertEqual(len(bound.vocabulary_hash or ""), 64)
        incomplete_binding = TaskSpec.from_mapping(
            {"requirements": {"action": "read", "entity_type": "document", "mode": "effect"},
             "vocabulary_version": "ontology-v1"}
        )
        self.assertTrue(incomplete_binding.unknown_items)

    def test_empty_and_unsupported_direct_expression_nodes_are_unknown(self) -> None:
        def matcher(_requirement):
            return TruthValue.TRUE

        self.assertEqual(evaluate_expression(AllOf(()), matcher), TruthValue.UNKNOWN)
        self.assertEqual(evaluate_expression(OneOf(()), matcher), TruthValue.UNKNOWN)
        self.assertEqual(
            evaluate_expression(AllOf((RequirementExpression(),)), matcher),  # type: ignore[arg-type]
            TruthValue.UNKNOWN,
        )

    def test_task_spec_round_trip_preserves_and_or_provenance_and_unknown_items(self) -> None:
        original = TaskSpec.from_mapping(
            {
                "requirements": {
                    "all_of": [
                        {"action": "read", "entity_type": "document", "mode": "effect"},
                        {
                            "one_of": [
                                {"action": "send", "entity_type": "document", "output_type": "email", "mode": "effect"},
                                {"action": "send", "entity_type": "document", "output_type": "portal", "mode": "effect"},
                            ]
                        },
                    ]
                },
                "unknown_items": ["target account unresolved"],
                "provenance": [{"source": "prompt", "evidence": "send after reading"}],
            }
        )
        restored = TaskSpec.from_mapping(original.to_mapping())
        self.assertEqual(restored, original)


if __name__ == "__main__":
    unittest.main()
