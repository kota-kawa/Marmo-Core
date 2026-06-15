# guobiao-writing

Claude Code skill for writing Chinese national standards (GB/T).

## Features

- Full workflow guidance from topic selection to submission
- Three standard type templates:
  - **Method standards** (方法类标准) - for measurement/testing/characterization methods
  - **Terminology standards** (术语类标准) - for domain vocabulary and definitions
  - **Technical requirement standards** (技术要求类标准) - for product/system specifications
- Application material templates (project proposal, project application form, drafting team plan)
- Format specification checklist following GB/T 1.1-2020
- TC279 (Nanotechnology) specific information

## Installation

Copy the `guobiao-writing` directory to your Claude Code skills directory:

```bash
cp -r guobiao-writing ~/.claude/skills/
```

## Usage

In Claude Code, the skill activates when you mention:
- Writing/drafting national standards (国家标准, GB/T)
- Standard proposals (标准草案, 标准申报, 标准立项)
- Nanotechnology standards (纳米技术标准, TC279)

## Structure

```
guobiao-writing/
├── skill.md          # Main skill file
└── README.md         # This file
```

## References

- GB/T 1.1-2020 - Directives for standardization work
- GB/T 44935-2024 - MoS2 layer measurement (method standard example)
- GB/T 30544.13-2018 - Graphene terminology (terminology standard example)
- ISO/TS 80004-13:2024 - Graphene and 2D materials vocabulary

## License

MIT
