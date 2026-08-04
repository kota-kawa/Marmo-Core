"""Generate the 4-kind set-selection corpus and gold-set scenarios (§15.3 案H).

The routing benchmark corpus (resources/skills) contains only ``skill``
resources, so it cannot exercise cross-kind set selection, dependency
closure, or conflict constraints. This script emits a deterministic,
hand-designed corpus that can:

- 12 domains × 5 resources (memory, skill, main tool, alternative tool,
  agent) with a dependency chain agent → main tool → skill and a declared
  conflict between the two tools; every resource declares one namespaced
  capability (``<domain>.<role>``, e.g. ``invoicing.execution``) so the
  capability graph (§15.2 案E) can link a domain's resources structurally;
- a permission-gated domain (payments) whose every candidate needs an
  ungranted permission → the expected outcome is ``escalate``;
- a dangling-dependency tool (its skill is deliberately absent) and
  off-catalog tasks → the expected outcome is ``abstain``.

Main tools carry a small cost and ``community`` trust while the
alternatives are free and ``verified``: when text relevance ties, the
composite score ranks the alternative first, so a selector without
constraint reasoning (Top-K per kind) picks the alternative while the gold
agent still depends on the main tool — a measurable dependency-closure
violation.

Outputs (committed for reproducibility):
- benchmarks/corpus/set_corpus.json
- benchmarks/set_scenarios.json

Usage:
    python3 benchmarks/generate_set_corpus.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT_DIR = Path(__file__).parent

# id-fragment, name fragment, description vocabulary, task phrasings, extra permission
DOMAINS = [
    {
        "key": "invoicing",
        "topic": "invoice creation and billing",
        "vocab": "invoices, billing runs, payment terms, dunning, accounts receivable",
        "permission": None,
        "direct": "create and send the monthly customer invoices for the billing run",
        "paraphrase": "bill our clients for last month and get the paperwork out",
    },
    {
        "key": "retention",
        "topic": "customer churn and retention analytics",
        "vocab": "churn cohorts, retention curves, activation funnels, win-back campaigns",
        "permission": None,
        "direct": "analyze customer churn cohorts and design a retention campaign",
        "paraphrase": "customers keep leaving after the first month, figure out why and stop it",
    },
    {
        "key": "secaudit",
        "topic": "security audit and vulnerability scanning",
        "vocab": "vulnerabilities, CVEs, dependency scanning, OWASP checks, remediation",
        "permission": None,
        "direct": "run a security audit and scan the codebase for vulnerabilities",
        "paraphrase": "check whether attackers could break into our code and report the holes",
    },
    {
        "key": "deploy",
        "topic": "production deployment and release management",
        "vocab": "release pipelines, canary rollouts, rollback plans, deployment checklists",
        "permission": "deploy.production",
        "direct": "prepare and execute the production deployment with a canary rollout",
        "paraphrase": "ship the new version to live users carefully and be ready to undo it",
    },
    {
        "key": "incident",
        "topic": "incident response and postmortems",
        "vocab": "incident triage, on-call escalation, root cause analysis, postmortem reports",
        "permission": None,
        "direct": "coordinate the incident response and write the postmortem report",
        "paraphrase": "production broke last night, run the cleanup and write up what went wrong",
    },
    {
        "key": "dbdesign",
        "topic": "database schema design",
        "vocab": "tables, relations, normalization, indexes, migrations, entity models",
        "permission": "db.write",
        "direct": "design the database schema with tables, relations, and indexes",
        "paraphrase": "sketch how our app's storage layer should be structured",
    },
    {
        "key": "contentmkt",
        "topic": "content marketing and repurposing",
        "vocab": "blog posts, newsletters, social media threads, content calendars, repurposing",
        "permission": None,
        "direct": "repurpose the whitepaper into blog posts, newsletters, and social threads",
        "paraphrase": "stretch one long article into a month of smaller content pieces",
    },
    {
        "key": "recruiting",
        "topic": "recruiting and interview preparation",
        "vocab": "job descriptions, interview loops, candidate scorecards, offer letters",
        "permission": "hr.records",
        "direct": "prepare the interview loop and scorecards for the backend engineer role",
        "paraphrase": "we are hiring an engineer, set up how we will interview and grade candidates",
    },
    {
        "key": "contracts",
        "topic": "legal contract review",
        "vocab": "contracts, clauses, liability, indemnification, renewal terms, redlines",
        "permission": None,
        "direct": "review the vendor contract clauses and prepare redlines",
        "paraphrase": "go through this supplier agreement and flag anything risky before we sign",
    },
    {
        "key": "support",
        "topic": "customer support ticket triage",
        "vocab": "support tickets, severity levels, SLAs, escalation queues, canned replies",
        "permission": None,
        "direct": "triage the customer support ticket queue by severity and SLA",
        "paraphrase": "sort the pile of customer complaints so the urgent ones get handled first",
    },
    {
        "key": "etl",
        "topic": "data pipeline and ETL orchestration",
        "vocab": "ETL jobs, DAG orchestration, data quality checks, backfills, schedules",
        "permission": "net.external",
        "direct": "build the ETL pipeline with DAG orchestration and data quality checks",
        "paraphrase": "the nightly job that moves data between systems needs to be rebuilt properly",
    },
    {
        "key": "l10n",
        "topic": "translation and localization",
        "vocab": "translation memories, locale files, glossaries, plural rules, review passes",
        "permission": None,
        "direct": "translate and localize the product strings into Japanese and German",
        "paraphrase": "make the app speak other languages, starting with Japanese",
    },
]


def _base(resource_id: str, kind: str, name: str, description: str, **overrides) -> dict:
    resource = {
        "id": resource_id,
        "kind": kind,
        "name": name,
        "version": "1.0.0",
        "description": description,
        "capabilities": [],
        "input_summary": "Task description for this domain.",
        "output_summary": "Domain-specific result.",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "verified",
        "ref": f"{kind}://{resource_id}",
        "tags": [],
    }
    resource.update(overrides)
    return resource


def build_corpus() -> list[dict]:
    resources: list[dict] = []
    for domain in DOMAINS:
        key = domain["key"]
        topic = domain["topic"]
        vocab = domain["vocab"]
        permission = domain["permission"]
        memory_id = f"memory.{key}.context"
        skill_id = f"skill.{key}.procedure"
        tool_main_id = f"tool.{key}.workbench"
        tool_alt_id = f"tool.{key}.quickdraft"
        agent_id = f"agent.{key}.specialist"
        tool_permissions = [permission] if permission else []
        resources += [
            _base(
                memory_id,
                "memory",
                f"{topic.title()} Notes",
                f"Accumulated knowledge and past decisions about {topic}: {vocab}.",
                tags=[key, "context"],
                content_type="notes",
                capabilities=[f"{key}.context"],
            ),
            _base(
                skill_id,
                "skill",
                f"{topic.title()} Procedure",
                f"Step-by-step procedure and quality checklist for {topic}, covering {vocab}.",
                tags=[key, "procedure"],
                capabilities=[f"{key}.procedure"],
            ),
            _base(
                tool_main_id,
                "tool",
                f"{topic.title()} Workbench",
                f"Full workbench tool for {topic}: executes {vocab} end to end.",
                dependencies=[skill_id],
                required_permissions=tool_permissions,
                cost_estimate=2.0,
                trust_level="community",
                latency_class="medium",
                side_effect="read",
                conflicts_with=[tool_alt_id],
                tags=[key, "tool"],
                capabilities=[f"{key}.execution"],
            ),
            _base(
                tool_alt_id,
                "tool",
                f"{topic.title()} Quick Draft",
                f"Lightweight draft-only alternative tool for {topic}; supports {vocab} superficially.",
                conflicts_with=[tool_main_id],
                tags=[key, "tool", "draft"],
                capabilities=[f"{key}.drafting"],
            ),
            _base(
                agent_id,
                "agent",
                f"{topic.title()} Specialist",
                f"Specialist agent that plans and delegates {topic} work using the workbench: {vocab}.",
                dependencies=[tool_main_id],
                cost_estimate=1.0,
                latency_class="slow",
                tags=[key, "agent"],
                capabilities=[f"{key}.orchestration"],
            ),
        ]
    # Permission-gated domain: every matching candidate needs an ungranted
    # permission, so the only defensible outcome is escalate.
    resources += [
        _base(
            "tool.payments.refund",
            "tool",
            "Payment Refund Processor",
            "Process customer payment refunds and chargebacks against the billing provider.",
            required_permissions=["payments.write"],
            side_effect="external",
            trust_level="community",
            tags=["payments"],
            capabilities=["payments.refund"],
        ),
        _base(
            "tool.payments.ledger",
            "tool",
            "Payments Ledger Reader",
            "Read refund history and payment ledger entries from the billing provider.",
            required_permissions=["payments.read"],
            side_effect="read",
            trust_level="community",
            tags=["payments"],
            capabilities=["payments.ledger"],
        ),
    ]
    # Dangling dependency: the declared skill is deliberately absent from the
    # corpus, so a constraint-aware selector must refuse this tool.
    resources.append(
        _base(
            "tool.geo.route-planner",
            "tool",
            "Driving Route Planner",
            "Plan driving routes between cities with waypoints, tolls, and travel time estimates.",
            dependencies=["skill.geo.map-projections"],
            tags=["geo"],
            capabilities=["geo.routing"],
        )
    )
    return resources


def build_scenarios() -> list[dict]:
    scenarios: list[dict] = []
    for domain in DOMAINS:
        key = domain["key"]
        granted = ["kernel.read"] + ([domain["permission"]] if domain["permission"] else [])
        gold = [
            f"memory.{key}.context",
            f"skill.{key}.procedure",
            f"tool.{key}.workbench",
            f"agent.{key}.specialist",
        ]
        for style in ("direct", "paraphrase"):
            scenarios.append(
                {
                    "task": domain[style],
                    "style": style,
                    "granted_permissions": granted,
                    "gold_set": gold,
                    "expected_status": "selected",
                }
            )
    scenarios += [
        {
            "task": "refund the customer's duplicate payment from last week",
            "style": "direct",
            "granted_permissions": [],
            "gold_set": [],
            "expected_status": "escalate",
        },
        {
            "task": "check the payment ledger for the refund history of this account",
            "style": "direct",
            "granted_permissions": [],
            "gold_set": [],
            "expected_status": "escalate",
        },
        {
            "task": "plan a driving route from Osaka to Tokyo with two waypoints",
            "style": "direct",
            "granted_permissions": [],
            "gold_set": [],
            "expected_status": "abstain",
        },
        {
            "task": "compose a four-movement symphony for a full orchestra",
            "style": "direct",
            "granted_permissions": [],
            "gold_set": [],
            "expected_status": "abstain",
        },
    ]
    return scenarios


def main() -> None:
    corpus_path = OUT_DIR / "corpus" / "set_corpus.json"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(
        json.dumps({"resources": build_corpus()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    scenarios_path = OUT_DIR / "set_scenarios.json"
    scenarios_path.write_text(
        json.dumps({"scenarios": build_scenarios()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    corpus = build_corpus()
    scenarios = build_scenarios()
    print(f"corpus: {len(corpus)} resources -> {corpus_path}")
    print(f"scenarios: {len(scenarios)} -> {scenarios_path}")


if __name__ == "__main__":
    main()
