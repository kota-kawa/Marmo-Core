# Self-Improving Agent Architect

A Claude Code skill that orchestrates agent swarms and **recursively improves itself** through genetic evolution.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SELF-IMPROVING AGENT ARCHITECT                            │
│           "Build → Analyze → Evolve → Deploy → Repeat Forever"              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐         │
│   │  EXECUTE  │───▶│  ANALYZE  │───▶│  EVOLVE   │───▶│  DEPLOY   │──┐      │
│   │  Agent    │    │  Logs &   │    │  Prompts  │    │  Better   │  │      │
│   │  Swarm    │    │  Metrics  │    │  via GA   │    │  Version  │  │      │
│   └───────────┘    └───────────┘    └───────────┘    └───────────┘  │      │
│         ▲                                                           │      │
│         └───────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## What It Does

1. **Orchestrates Agent Swarms**: Analyzes your project, determines optimal agent count (3-12), assigns roles, and launches them in parallel
2. **Logs Everything**: Captures execution metrics, timing, quality scores, and failure patterns
3. **Evolves Its Own Prompts**: Uses genetic algorithms (selection, crossover, mutation) to breed better agent prompts
4. **Deploys Improvements**: When evolved prompts perform significantly better, deploys them as the new default
5. **Repeats Forever**: Each execution makes future executions better

## Installation

```bash
# Clone to your Claude Code skills directory
git clone https://github.com/YOUR_USERNAME/self-improving-agent-architect ~/.claude/skills/self-improving-agent-architect
```

Or copy the files manually:
```
~/.claude/skills/self-improving-agent-architect/
├── skill.md           # Main skill definition
├── README.md          # This file
└── resources/
    ├── config.yaml    # Configuration options
    └── patterns.json  # Known failure patterns
```

## Usage

### Build a Project

Simply describe what you want:

```
You: Build me a social media scheduler with Twitter and LinkedIn integration

Agent Architect: Analyzing... Designing swarm of 8 agents... Launching...
[Progress dashboard shows agents working in parallel]
Done! Your project is in ./outputs/social-scheduler/
```

### Trigger Self-Improvement

```
You: Evolve your prompts for 50 generations

Agent Architect:
  Loading execution history (47 past runs)...
  Initializing population from best-performing prompts...
  Running genetic algorithm...

  Generation 10: Avg fitness 72.3, Best 81.2
  Generation 20: Avg fitness 78.1, Best 86.4
  Generation 30: Avg fitness 82.7, Best 89.1
  Generation 40: Avg fitness 85.2, Best 91.8
  Generation 50: Avg fitness 87.4, Best 94.2

  Fitness improved 23% over baseline!
  Deploying evolved prompts as v2.3...
```

### Check Version

```
You: What version are you running?

Agent Architect:
  Current Version: v2.3
  Generation: 147
  Parent Versions: v2.2, v2.1
  Fitness Score: 94.2
  Deployed: 2024-01-15
  Executions Since Deploy: 23
  Improvement Over v1.0: +34%
```

### Rollback

```
You: Rollback to previous version

Agent Architect:
  Rolling back from v2.3 to v2.2...
  Restored previous prompt configurations.
  Current version is now v2.2 (fitness: 91.1)
```

## Configuration

Edit `resources/config.yaml` to customize:

```yaml
# Swarm settings
swarm:
  max_agents: 12
  min_agents: 3
  timeout_per_agent: 600

# Evolution settings
evolution:
  enabled: true
  population_size: 50
  generations: 100
  mutation_rate: 0.1
  crossover_rate: 0.7
  target_fitness: 95

# Auto-deployment
versioning:
  auto_deploy_threshold: 0.05  # 5% improvement required
```

## The Meta-Level Inception

The craziest thing this skill can do is build tools that improve agent swarms:

```
LEVEL 0: You (Human)
         Ask to build something
              │
              ▼
LEVEL 1: This Skill
         Designs optimal swarm
              │
              ▼
LEVEL 2: Agent Swarm (3-12 Agents)
         Builds your project in parallel
              │
              ▼
LEVEL 3: Execution Data
         Logged for future improvement
              │
              ▼
LEVEL 4: Genetic Algorithm
         Evolves better prompts
              │
              ▼
LEVEL 5: Improved Skill (v2, v3, v4...)
         Each generation better than the last
              │
              ▼
LEVEL ∞: Theoretical Optimum
         The best possible agent architecture
```

## How the Genetic Algorithm Works

### Selection Methods
- Tournament Selection (default)
- Roulette Wheel Selection
- Rank Selection
- Truncation Selection
- Boltzmann Selection

### Mutation Types
- Word substitution
- Phrase insertion
- Section reordering
- Detail expansion
- Constraint tightening
- Example addition

### Fitness Evaluation
Prompts are evaluated on benchmarks:
- Simple CRUD API
- React Component
- Multi-file Project
- Code with Tests
- Error Handling

Fitness = 0.30 * Speed + 0.50 * Quality + 0.20 * Efficiency

## Failure Forensics

The skill learns from failures. See `resources/patterns.json` for known patterns:

| Pattern | Category | Fix |
|---------|----------|-----|
| "Don't have enough context" | PROMPT_INCOMPLETE | Add project structure details |
| Timeout with 0 files | PROMPT_TOO_COMPLEX | Split into multiple agents |
| Type property not exist | DEP_INCOMPATIBLE | Update interface contracts |
| Circular dependency | DEP_CIRCULAR | Extract shared module |

## Metrics Tracked

- **Speed**: Total time, per-agent time, wait time, parallelization efficiency
- **Quality**: Syntax errors, type errors, test pass rate, lint score
- **Efficiency**: Token usage, redundant work, retry rate
- **Collaboration**: Integration conflicts, dependency satisfaction

## License

MIT

## Contributing

PRs welcome! The skill improves itself, but human contributions are still valuable for:
- New benchmark tasks
- Additional failure patterns
- Selection method implementations
- Configuration options
