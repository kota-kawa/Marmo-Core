# ISF Grant Proposal Agent

An AI-powered assistant for preparing Israel Science Foundation (ISF) New Principal Investigator Grant proposals. This agent learns from your past proposals and challenges your assumptions like a rigorous reviewer.

## Overview

This agent guides researchers through the complete grant proposal preparation process:

1. **Requirements Research** - Fetches current ISF guidelines
2. **Past Proposal Analysis** - Learns patterns from successful/unsuccessful proposals and reviews
3. **Challenging Questions** - Poses hard questions to surface weaknesses before submission
4. **Structured Interview** - Gathers researcher and project information
5. **Content Generation** - Drafts proposal sections using learned patterns
6. **Compliance Validation** - Ensures all requirements are met
7. **Final Assembly** - Produces submission-ready documents

## What Makes This Agent Different

**Learns from your history:**
- Upload past proposals anytime with `/learn-from-grant`
- Analyzes successful proposals to extract winning patterns
- Studies unsuccessful proposals to identify pitfalls
- Mines reviewer feedback to preempt common concerns
- Shows you exactly what it learned and how it will apply it

**Challenges your thinking:**
- Poses the hard questions reviewers will ask
- Surfaces assumptions you haven't examined
- Identifies logical gaps and weak points early
- Better to face tough questions during drafting than in rejection letters

**Applies learnings actively:**
- Warns you when your input matches a past weakness
- Uses successful patterns when generating content
- Validates your draft against learned concerns
- Shows which learnings were applied in each section

## File Structure

```
grant-agent/
├── README.md                 # This file
├── skill.md                  # Main skill entry point
├── agent.md                  # Core agent instructions
├── state-template.yaml       # Session state structure
├── modules/
│   ├── isf-requirements-2026.md    # Current ISF requirements (authoritative)
│   ├── isf-website-docs.md          # Live ISF docs snapshot workflow
│   ├── requirements-research.md    # How to load/fetch requirements
│   ├── grant-learning.md           # Interactive learning from past proposals
│   ├── past-proposals-analysis.md  # Batch analysis of past proposals
│   ├── challenging-questions.md    # Socratic questioning protocol
│   ├── interview.md                # Structured interview questions
│   └── compliance.md               # Validation checklist
├── scripts/
│   └── fetch-isf-grants-docs.mjs   # Pull all grant-linked docs from isf.org.il
├── examples/                       # Synthetic examples for learning/demo
│   ├── README.md                   # How to use examples
│   ├── successful/                 # Funded proposal example
│   │   └── 2023_decision_making_funded.md
│   ├── unsuccessful/               # Rejected proposal example
│   │   └── 2024_cognitive_training_rejected.md
│   └── reviews/                    # Reviewer feedback example
│       └── 2024_cognitive_training_reviews.md
├── learnings/                      # Accumulated learnings (created by agent)
│   ├── successful_patterns.yaml    # Patterns from funded proposals
│   ├── weaknesses_to_avoid.yaml    # Anti-patterns from rejections
│   └── reviewer_concerns.yaml      # Concerns database
└── templates/
    └── proposal-sections.md        # Section generation templates
```

## Setting Up Your Proposal Repository

Create this structure in your project folder:

```
your-project/
├── CLAUDE.md                # Project context
├── past-proposals/
│   ├── successful/          # Funded proposals (PDFs, docs)
│   │   └── 2024_my_funded_proposal.pdf
│   ├── unsuccessful/        # Rejected proposals
│   │   └── 2023_rejected_proposal.pdf
│   └── reviews/             # Reviewer feedback
│       └── 2023_rejected_reviews.pdf
├── bibliography/
│   ├── foundational/
│   ├── methods/
│   └── recent/
└── output/                  # Agent-generated drafts
```

**The more past proposals you provide, the better the agent learns.**

## Usage

### Starting a Session

Invoke the agent with phrases like:
- "Help me write an ISF grant proposal"
- "Start ISF New PI grant"
- "I need to prepare a grant for the Israel Science Foundation"

### Session Workflow

The agent will guide you through 7 phases:

| Phase | Description | Duration |
|-------|-------------|----------|
| 1. Initialization | Confirm grant type, scan past proposals, pose foundational challenges | 10 min |
| 2. Requirements | Fetch and review ISF guidelines | 10 min |
| 3. Pattern Analysis | Extract best practices from your past proposals and reviews | 15 min |
| 4. Interview | Gather your information with challenging questions interspersed | 60-90 min |
| 5. Content Generation | Draft sections using learned patterns | 2-3 hours |
| 6. Validation | Check compliance, fix issues | 30 min |
| 7. Assembly | Compile final documents | 15 min |

### Commands

Use these during any phase:

| Command | Action |
|---------|--------|
| `/status` | Show current progress |
| `/skip` | Skip current question |
| `/back` | Return to previous question |
| `/preview` | View current proposal draft |
| `/requirements` | Show ISF requirements |
| **Learning** | |
| `/learn-from-grant` | Upload and analyze a past proposal |
| `/learn-from-reviews` | Add reviewer feedback |
| `/show-learnings` | See all accumulated learnings |
| `/check-learnings` | Validate draft against learnings |
| `/patterns` | Show successful patterns to apply |
| `/concerns` | Show reviewer concerns database |
| **Challenges** | |
| `/challenge` | Request harder questions |
| `/challenges` | List all challenges and responses |
| `/compare` | Compare draft to successful examples |
| `/onboarding` | Explain how to use the app and commands |
| `/isf-docs` | Show local ISF documentation bundle location |
| `/isf-process` | Explain the ISF submission process |
| `/help` | List commands |

## What You'll Need

Before starting, have ready:
- Your CV or publication list
- Your research project idea (title, aims, methods)
- Preliminary data or prior work summary
- Budget estimates (personnel, equipment, supplies)
- Collaborator information (if applicable)

**For best results, also provide:**
- Past grant proposals (successful or unsuccessful)
- Reviewer feedback from previous submissions
- Examples of funded proposals from colleagues (if available)

## Output

The agent produces:
- Complete research proposal (formatted per ISF requirements)
- Budget spreadsheet with justifications
- Submission checklist
- Compliance validation report

## ISF-Specific Features

- **Local requirements module** with complete 2026 cycle guidelines
- Falls back to isf.org.il if local module unavailable
- Validates against ISF page limits and budget caps
- Formats according to ISF specifications (font, margins, structure)
- Tracks submission deadlines (Registration: Oct 29, Submission: Nov 12)
- Includes AI/LLM usage policy guidance

## Customization

### Live ISF Website Documentation Snapshot

To pull the latest grant-linked documentation directly from ISF:

```bash
node scripts/fetch-isf-grants-docs.mjs
```

This creates a local snapshot in `.context/isf-grants-docs/` with:
- `manifest.json` (all indexed files + grant mappings)
- Grant metadata and deadlines (`grant-types.*.json`, `deadlines.*.json`)
- Downloaded PDFs under `files/`
- Extracted text under `text/`

Use this snapshot when answering detailed ISF process questions and refresh it when a new cycle opens.

### Updating ISF Requirements Annually

When new ISF guidelines are released:
1. Download the new guidelines PDF from isf.org.il
2. Create `modules/isf-requirements-[YEAR].md` following the existing structure
3. Update the reference in `modules/requirements-research.md`

### Adapting for Other Funders

To adapt for other funders:
1. Create a new requirements module (e.g., `modules/erc-requirements-2026.md`)
2. Modify `modules/requirements-research.md` with new sources
3. Update `modules/compliance.md` with new validation rules
4. Adjust `templates/proposal-sections.md` for different formats

## Session Persistence

Progress is saved in `.grant-session.yaml`. Sessions can be resumed across multiple conversations.

## Synthetic Examples (For Training/Workshops)

The `examples/` folder contains synthetic grant proposals for learning and demonstration:

| Example | Purpose |
|---------|---------|
| `unsuccessful/2024_cognitive_training_rejected.md` | Rejected proposal with 12 deliberate weaknesses |
| `reviews/2024_cognitive_training_reviews.md` | Reviewer feedback highlighting those weaknesses |
| `successful/2023_decision_making_funded.md` | Funded proposal demonstrating 12 best practices |

**To use for practice:**
1. Copy `examples/unsuccessful/` → `past-proposals/unsuccessful/`
2. Copy `examples/successful/` → `past-proposals/successful/`
3. Copy `examples/reviews/` → `past-proposals/reviews/`
4. Use `/learn-from-grant` and `/learn-from-reviews` to see the agent learn

See `examples/README.md` for detailed instructions.

## Support

For issues with the agent, check:
- Are ISF requirements successfully fetched?
- Is all required information collected?
- Are there validation failures to resolve?

---

*Built to help researchers focus on science, not paperwork.*
