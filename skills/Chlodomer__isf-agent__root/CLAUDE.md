# ISF Grant Writing Agent

AI-powered assistant for writing Israel Science Foundation (ISF) New Principal Investigator grant proposals. Guides researchers through a 7-phase workflow from requirements research to final assembly.

## Architecture

- **Declarative logic**: Core agent behavior is defined in Markdown (workflows, instructions) and YAML (configuration, state schema), not traditional application code. The Claude skill interprets these at runtime.
- **`state-template.yaml` is the canonical schema** for session state. The frontend Zustand store must map 1:1 to this YAML structure.
- **Modules** (`modules/`): Self-contained knowledge files covering ISF requirements, interview questions, compliance checks, challenging questions, and proposal learning.

## Frontend Tech Stack

- Next.js 14 (App Router), React 18, TypeScript
- Tailwind CSS with logical properties for RTL support
- Zustand for state management (mirrors `state-template.yaml`)
- Vercel AI SDK for backend streaming

## Frontend Component Organization

Components live in `web/src/components/` organized by UI area:
- `left-rail/` — navigation and phase stepper
- `chat/` — main conversation area
- `chat/messages/` — 9 structured message card types with color-coded borders (Challenge, Interview Question, Draft Review, Compliance Report, etc.)
- `context-panel/` — draft viewer, learnings, compliance, interview tracker

## Key Directories

- `modules/` — agent knowledge modules (requirements, interview, compliance, etc.)
- `web/src/components/` — React UI components
- `examples/` — past proposals (successful/, unsuccessful/, reviews/)
- `templates/` — proposal templates
- `.claude/commands/` — Claude skill definitions
