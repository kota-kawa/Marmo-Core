# Development Practices

## State Management
- `state-template.yaml` is the single source of truth for session state. The frontend Zustand store must mirror this structure exactly (1:1 mapping).

## Demo & Testing
- Curate demo data carefully to avoid duplicates or visual bugs (e.g., duplicate welcome cards from overlapping demo data).
- Include a "Load Demo Flow" button for verifying all UI components and interaction types.
- Be aware of tool-specific limitations (e.g., GIF recording requires the browser tab to be in the MCP tab group). Have fallback methods ready (screenshots, textual descriptions).

## Planning & Documentation
- Create a comprehensive UI plan before implementation covering: tech stack, layout, components, interaction flows, and verification steps.
- Provide detailed build summaries and PR descriptions including file lists and instructions for running locally.

## Parallelization
- Avoid using team agents for parallel development without first verifying environment compatibility and permissions. When team agents are blocked, it's more efficient to complete tasks directly rather than debugging agent tooling.
