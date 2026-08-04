"""Generate the large-scale hierarchical catalog for 案I (§15.2).

The set-selection corpus (63 resources) and the 1,000-skill distractor
catalog cannot exercise the second research claim (12.1: routing must hold
at 10k+ resources), and neither carries the group structure 案I routes
over. This script emits a deterministic synthetic catalog with an explicit
hierarchy:

- sector × function → domain (e.g. ``logistics-forecasting``); each domain
  declares one capability namespace, mirroring the gold corpus;
- provider → MCP server owning several domains; members carry a
  ``provider:<name>`` tag and an ``mcp://<provider>/<id>`` ref;
- inside a domain, families of five resources reproduce the gold corpus
  shape (memory / skill / workbench tool / draft tool / agent) with the
  same dependency chain (agent → workbench → skill) and tool conflict, so
  the noise is structurally indistinguishable from gold — a router cannot
  win by exploiting malformed noise.

A quarter of the domains require a permission from a small pool, giving
``PermissionGrouping`` non-trivial boundaries.

The catalog JSON is regenerated on demand (deterministic, seeded) and is
.gitignored — only this generator and the cross-domain scenarios are
committed. Cross-domain scenarios pair two gold domains from
``generate_set_corpus.DOMAINS`` into one task whose gold set spans both
(8 resources), the known weak spot of coarse-to-fine routing (§15.2 案I).

Usage:
    python3 benchmarks/generate_scale_corpus.py [--size 10000]
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from generate_set_corpus import DOMAINS as GOLD_DOMAINS, _base

OUT_DIR = Path(__file__).parent
SEED = 20260720

SECTORS = [
    ("logistics", "freight logistics", "shipments, carriers, customs forms, route manifests"),
    ("insurance", "insurance operations", "policies, claims, underwriting, actuarial tables"),
    ("gaming", "game development", "levels, matchmaking, telemetry, monetization loops"),
    ("agritech", "precision agriculture", "soil sensors, irrigation, crop yields, harvest windows"),
    ("fintech", "consumer fintech", "wallets, ledgers, KYC checks, settlement batches"),
    ("healthcare", "clinical workflows", "patient intake, care plans, lab orders, referrals"),
    ("realestate", "property management", "listings, leases, inspections, tenant requests"),
    ("energy", "energy grid operations", "load curves, outages, meter readings, tariffs"),
    ("edtech", "online learning", "courses, cohorts, assessments, completion tracking"),
    ("travel", "travel booking", "itineraries, fares, cancellations, loyalty points"),
    ("manufacturing", "factory operations", "work orders, BOMs, quality gates, downtime logs"),
    ("media", "streaming media", "encodes, playlists, rights windows, watch metrics"),
    ("nonprofit", "nonprofit programs", "donors, grants, campaigns, impact reports"),
    ("automotive", "fleet automotive", "vehicles, maintenance schedules, recalls, telematics"),
    ("biotech", "lab research", "assays, samples, protocols, sequencing runs"),
    ("retailops", "retail operations", "planograms, stock counts, promotions, shrinkage"),
    ("telecom", "telecom provisioning", "SIM activations, coverage maps, port-ins, outage tickets"),
    ("construction", "construction projects", "blueprints, permits, subcontractors, punch lists"),
    ("hospitality", "hotel operations", "reservations, housekeeping, room blocks, folios"),
    ("govtech", "public sector services", "case files, benefit claims, audits, records requests"),
]

FUNCTIONS = [
    ("forecasting", "demand forecasting", "baselines, seasonality, forecast error, horizons"),
    ("compliance", "regulatory compliance", "controls, attestations, evidence, audit trails"),
    ("onboarding", "customer onboarding", "checklists, verifications, welcome flows, activation"),
    ("pricing", "pricing strategy", "price books, discounts, elasticity, margin targets"),
    ("inventory", "inventory planning", "reorder points, safety stock, turns, stockouts"),
    ("scheduling", "shift scheduling", "rosters, availability, swaps, overtime rules"),
    ("procurement", "supplier procurement", "RFQs, purchase orders, vendor scorecards, terms"),
    ("reporting", "executive reporting", "scorecards, variance analysis, narratives, rollups"),
    ("moderation", "content moderation", "flags, review queues, policy rubrics, appeals"),
    ("fraud", "fraud detection", "anomaly signals, chargebacks, velocity rules, blocklists"),
    ("crm", "account management", "pipelines, renewals, health scores, playbooks"),
    ("billing", "usage billing", "meters, rating, proration, dunning notices"),
    ("catalog", "product catalog", "attributes, variants, taxonomies, enrichment"),
    ("warranty", "warranty service", "claims intake, entitlements, repairs, RMAs"),
    ("training", "workforce training", "curricula, certifications, skill gaps, refreshers"),
    ("sustainability", "sustainability tracking", "emissions, offsets, disclosures, footprints"),
    ("capacity", "capacity planning", "utilization, headroom, growth curves, provisioning"),
    ("quality", "quality assurance", "defect triage, test matrices, release gates, escapes"),
    ("localization", "market localization", "regional formats, currencies, holidays, dialects"),
    ("migration", "system migration", "cutover plans, dual writes, backfills, rollbacks"),
]

VARIANTS = [
    "batch", "realtime", "regional", "quarterly", "self-serve", "enterprise",
    "draft", "archival", "priority", "seasonal", "partner", "internal",
]

PERMISSION_POOL = [
    "net.external", "db.write", "hr.records", "deploy.production",
    "finance.ledger", "pii.read",
]

# Gold-domain pairs for cross-domain tasks (§15.2 案I 固有の評価): the gold
# set spans two capability namespaces, so a router that scans one group
# per task must either widen or fail.
CROSS_PAIRS = [
    ("secaudit", "deploy", "run a security audit of the release and then execute the production deployment with a canary rollout"),
    ("invoicing", "retention", "bill the monthly customer invoices and analyze which invoiced customers are churning"),
    ("incident", "support", "coordinate the incident response and triage the customer support tickets it caused"),
    ("dbdesign", "etl", "design the database schema and build the ETL pipeline that loads it"),
    ("contentmkt", "l10n", "repurpose the whitepaper into blog posts and localize them into Japanese"),
    ("recruiting", "contracts", "prepare the interview loop for the engineer role and review the contractor agreement clauses"),
]


def build_scale_corpus(size: int, seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    domain_keys = [(sector, function) for sector, _, _ in SECTORS for function, _, _ in FUNCTIONS]
    rng.shuffle(domain_keys)
    domain_count = max(1, min(len(domain_keys), math.ceil(size / 50)))
    families_per_domain = max(1, math.ceil(size / (domain_count * 5)))
    sector_topics = {key: (topic, vocab) for key, topic, vocab in SECTORS}
    function_topics = {key: (topic, vocab) for key, topic, vocab in FUNCTIONS}

    resources: list[dict] = []
    for domain_index, (sector, function) in enumerate(domain_keys[:domain_count]):
        domain = f"{sector}-{function}"
        provider = f"{sector}-suite-{domain_index % 4}"
        sector_topic, sector_vocab = sector_topics[sector]
        function_topic, function_vocab = function_topics[function]
        topic = f"{sector_topic} {function_topic}"
        vocab = f"{sector_vocab}, {function_vocab}"
        permission = rng.choice(PERMISSION_POOL) if rng.random() < 0.25 else None
        for family_index in range(families_per_domain):
            variant = VARIANTS[family_index % len(VARIANTS)]
            suffix = f"{variant}-{family_index}" if family_index >= len(VARIANTS) else variant
            prefix = f"{domain}.{suffix}"
            memory_id = f"memory.{prefix}.context"
            skill_id = f"skill.{prefix}.procedure"
            tool_main_id = f"tool.{prefix}.workbench"
            tool_alt_id = f"tool.{prefix}.quickdraft"
            agent_id = f"agent.{prefix}.specialist"
            title = f"{variant.title()} {topic.title()}"
            shared = {
                "tags": [domain, f"provider:{provider}", variant],
            }
            members = [
                _base(
                    memory_id, "memory", f"{title} Notes",
                    f"Accumulated knowledge and past decisions about {variant} {topic}: {vocab}.",
                    content_type="notes", capabilities=[f"{domain}.context"], **shared,
                ),
                _base(
                    skill_id, "skill", f"{title} Procedure",
                    f"Step-by-step procedure and quality checklist for {variant} {topic}, covering {vocab}.",
                    capabilities=[f"{domain}.procedure"], **shared,
                ),
                _base(
                    tool_main_id, "tool", f"{title} Workbench",
                    f"Full workbench tool for {variant} {topic}: executes {vocab} end to end.",
                    dependencies=[skill_id],
                    required_permissions=[permission] if permission else [],
                    cost_estimate=2.0, trust_level="community", latency_class="medium",
                    side_effect="read", conflicts_with=[tool_alt_id],
                    capabilities=[f"{domain}.execution"], **shared,
                ),
                _base(
                    tool_alt_id, "tool", f"{title} Quick Draft",
                    f"Lightweight draft-only alternative tool for {variant} {topic}; supports {vocab} superficially.",
                    conflicts_with=[tool_main_id],
                    capabilities=[f"{domain}.drafting"], **shared,
                ),
                _base(
                    agent_id, "agent", f"{title} Specialist",
                    f"Specialist agent that plans and delegates {variant} {topic} work using the workbench: {vocab}.",
                    dependencies=[tool_main_id], cost_estimate=1.0, latency_class="slow",
                    capabilities=[f"{domain}.orchestration"], **shared,
                ),
            ]
            for member in members:
                member["ref"] = f"mcp://{provider}/{member['id']}"
            resources.extend(members)
            if len(resources) >= size:
                return resources[:size]
    return resources[:size]


def build_cross_domain_scenarios() -> list[dict]:
    domains_by_key = {domain["key"]: domain for domain in GOLD_DOMAINS}
    scenarios = []
    for left, right, task in CROSS_PAIRS:
        granted = {"kernel.read"}
        gold: list[str] = []
        for key in (left, right):
            domain = domains_by_key[key]
            if domain["permission"]:
                granted.add(domain["permission"])
            gold += [
                f"memory.{key}.context",
                f"skill.{key}.procedure",
                f"tool.{key}.workbench",
                f"agent.{key}.specialist",
            ]
        scenarios.append(
            {
                "task": task,
                "style": "cross-domain",
                "cross_domain": True,
                "granted_permissions": sorted(granted),
                "gold_set": gold,
                "expected_status": "selected",
            }
        )
    return scenarios


def scale_corpus_path(size: int) -> Path:
    return OUT_DIR / "corpus" / f"scale_corpus_{size}.json"


def ensure_scale_corpus(size: int) -> Path:
    """Write the catalog if absent (deterministic, so regeneration is safe)."""

    path = scale_corpus_path(size)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"resources": build_scale_corpus(size)}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=10_000)
    args = parser.parse_args()

    path = ensure_scale_corpus(args.size)
    corpus = json.loads(path.read_text(encoding="utf-8"))["resources"]
    scenarios_path = OUT_DIR / "scale_scenarios.json"
    scenarios_path.write_text(
        json.dumps({"scenarios": build_cross_domain_scenarios()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    domains = {resource["capabilities"][0].split(".", 1)[0] for resource in corpus}
    providers = {tag for resource in corpus for tag in resource["tags"] if tag.startswith("provider:")}
    print(f"corpus: {len(corpus)} resources, {len(domains)} domains, {len(providers)} providers -> {path}")
    print(f"cross-domain scenarios: {len(build_cross_domain_scenarios())} -> {scenarios_path}")


if __name__ == "__main__":
    main()
