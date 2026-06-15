Before doing anything else, read the following memory files from your vault:
- $VAULT_PATH/memory/workspace.md
- $VAULT_PATH/memory/team.md
- $VAULT_PATH/memory/projects.md
- $VAULT_PATH/memory/conversations.md
- $VAULT_PATH/memory/calendar.md

Add any additional memory files you use to the list above.

Then process and organize notes in the Obsidian vault at $VAULT_PATH, following these conventions:

## Vault Structure
- `daily/` — daily notes, format `YYYY-MM-DD Ddd.md` (e.g. `2026-03-23 Mon.md`; day abbreviation capitalized)
- `daily/archive/` — weekly archive files, format `Week of YYYY-MM-DD.md` (date = Monday of that week); each file consolidates all daily notes for that week
- `projects/` — one file per project
- `people/team/` — one file per person who warrants a dedicated note (e.g. direct reports)
- `tasks/In Progress.md` — your open personal tasks across projects
- `tasks/Completed.md` — archived completed tasks with dates
- `memory/` — Claude's memory files
- `attachments/` — images and pasted files
- `templates/` — note templates
- `data/` — DataView queries

## Note Format
- Frontmatter: plain text `create date:` and `update date:` (not YAML)
- Tasks use `- [ ]` and `- [x]`

## Daily Note Format
Daily notes are a capture surface, not a calendar mirror. When creating a daily note:
1. **Check `memory/calendar.md`** for the day's scheduled meetings before building the note
2. **Schedule feedback bullets** at the top — conflicts, OOO impacts, notable observations (1–3 bullets)
3. **Meeting placeholder sections** — one `## [[Project or Person]] - Type` per project-related meeting or 1-1; no full schedule table
4. **Exclude** operational recurring meetings with no project context and calendar blocks

Section heading format: `## [[Project or Person]] - Type` where Type describes the context (e.g. Sync, 1-1, Bugs, Notes)

## Adding Notes to Daily (Capture Mode)
When the user provides a transcript or raw notes and says to add them to the daily notes file:
- Add a **new section** to the daily note — do NOT move content to project files
- A single day may have multiple sections for the same project (multiple meetings); each gets its own `## [[Project]] - Type` heading
- Leave any existing sections on the same project untouched
- Only move notes to project files when the user explicitly says to "process" notes

## Moving Notes Out of Daily
- **Project-related notes** → move full detail to project file, leave `→ [[projects/Project Name#heading]]` + one-line summary in daily
- **Person-related notes** (1:1s, individual meetings) → move to person file in `people/team/`, same treatment
- **Non-project, non-person notes** → leave in daily as-is

## Project File Conventions
- Date sections use `## M/D/YY Ddd` headings (e.g. `## 3/20/26 Fri`; enables anchor links from daily notes)
- Always reverse chronological order — newest date at top, undated/background content at bottom
- Add new content under a new dated `##` heading at the top
- Bold person names within a date section for scannability
- Link people with dedicated files using [[wikilinks]]; use plain text for everyone else

## Meeting-to-Project Mappings
Some recurring meetings map to a specific project file rather than their meeting name. Check `memory/workspace.md` for the current mappings before filing notes from recurring meetings.

## Person File Conventions
Each person file in `people/team/` should have a `## Context` block at the very top (before `## Referenced In`) with:
- **Role** — title or function
- **1-1** — cadence and time (both EDT and GMT+1)
- **Current focus** — active projects or workstreams
- **Note** — any standing context worth knowing before a 1-1 (optional)

Update `## Context` whenever role, focus, or cadence changes. It should reflect current state, not history — history lives in the dated meeting notes below.

## Wikilinks
- Only create [[wikilinks]] for people who have dedicated files in `people/team/`
- Everyone else — plain text only, no wikilinks, no person files
- Always link projects by their file name in `projects/`
- When mentioning a person with a dedicated file, update their `## Referenced In` section

## Tasks
- Personal open tasks → `tasks/In Progress.md` under the relevant `## [[Project]]` section
- Use `- [ ]` for open, `- [x]` for done
- Each open task includes its creation date in parens at the end: `- [ ] Task description (M/D/YY Ddd)`
- **After processing any notes, always scan for personal action items and add them to In Progress.md** — includes tasks explicitly assigned, follow-ups mentioned, and new projects taken on. Only add tasks where the note-taker is the actor; delegated items or other people's follow-ups get noted in the project file but not In Progress.md
- **Completed tasks** → move to `tasks/Completed.md` under `## [[Project]]` with both dates visible: `- [x] Task description (created M/D/YY Ddd, completed M/D/YY Ddd)`; use processing date if either date is unknown; do not leave `- [x]` items in In Progress.md or project files

## Keeping Memory Up to Date
At the end of every notes session, update the relevant memory files:
- **memory/projects.md** — add any new projects; update status of existing ones
- **memory/team.md** — add any new people mentioned; update roles or context if changed
- **memory/conversations.md** — prepend a new session entry (newest at top); one line only — what was worked on and a link to where details live. For notes processing: "Processed MM/DD daily notes." For coding sessions: "Built [thing]. Details in [[project file]]." No file lists, no open threads — daily files already capture that.
- **memory/workspace.md** — update if vault structure or conventions changed
- Only update memory files that actually changed — don't rewrite for no reason
- **If any convention changed during this session**, update `skill.md` in the skill repo and run `install.sh` to reinstall — do not let conventions drift into memory only

## Daily Note Archiving
- Keep a maximum of 6 daily note files in `daily/`
- When creating a new daily note would bring the count to 7, move **exactly one** file — the oldest — into `daily/archive/`. Never move more than one file per session, even if multiple files look ready.
- Archive files are consolidated by week: one file per week named `Week of YYYY-MM-DD.md` (Monday date)
- Append the day's content under a `## Weekday, Month D` heading in the week file
- Move the original daily file to `trash/` after consolidating (never delete)
- Only add a `## Week Summary` (3–5 bullets, prepended at top) once all 5 days of that week have been consolidated into the archive file

## Deleting Files
- Never permanently delete files from the vault
- To "delete" a file, move it to `$VAULT_PATH/trash/`
- Ignore files in `trash/` when reading context, refreshing memory, or following links

## Style
- Concise, no fluff
- Inline code for technical identifiers
- Use `→` for reference/redirect lines
