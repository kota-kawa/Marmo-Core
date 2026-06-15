# UI Guidelines

## Target Users
Primary users are non-technical research faculty. The UI must be intuitive and prevent users from getting lost.

## Interaction Design
- **Chat-first, commands-never**: Users interact through clickable actions (pill buttons in a "Suggested Actions Bar"), not slash commands.
- **Constant orientation**: Always show users where they are and what's next — use a persistent "What's Next" banner and a phase stepper with sub-progress.
- **Soft guardrails**: Never hard-lock users. When they try to skip steps, show gentle warnings explaining trade-offs and offer an option to proceed anyway.
- **Dynamic elements**: The Suggested Actions Bar, Next Action Banner, and other UI elements adapt based on the current workflow phase and context.

## Content & Feedback
- **Instructive empty states**: Empty panels should show helpful guidance (e.g., "Your proposal will appear here...").
- **Context Panel**: Surface important information (draft viewer, learnings, compliance results, interview tracker) in a dedicated side panel so users don't lose context.
- **Structured message cards**: Use 9 visually differentiated card types with color-coded borders to provide clear context for different interaction types.

## State Management
- Ensure client-side state persists across navigations. Use URL parameters, localStorage, or SSR rehydration — state must not reset when the user navigates between pages.
