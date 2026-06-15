# ISF Website Documentation Snapshot

This module describes how to keep a complete local copy of ISF grant-linked documentation and how to explain the ISF submission process on request.

## What Is Collected

From `https://www.isf.org.il` the snapshot script pulls:
- Grant program metadata for all listed programs (`api/grant/getGrantTypeData`)
- Per-program page content (`api/grant/GetAllGrantsPageContent`)
- Per-program linked files (`api/grant/GetFilesToGrants`)
- Deadlines (`api/innerPages/GetGrantsDeadlines`)
- Linked files from `https://www.isf.org.il/Files/<filename>`

## Run

```bash
node scripts/fetch-isf-grants-docs.mjs
```

Output directory:
- `.context/isf-grants-docs/manifest.json`
- `.context/isf-grants-docs/grant-types.en-US.json`
- `.context/isf-grants-docs/grant-types.he-IL.json`
- `.context/isf-grants-docs/grant-pages.en-US.json`
- `.context/isf-grants-docs/grant-pages.he-IL.json`
- `.context/isf-grants-docs/deadlines.en-US.json`
- `.context/isf-grants-docs/deadlines.he-IL.json`
- `.context/isf-grants-docs/files/` (PDFs)
- `.context/isf-grants-docs/text/` (PDF text extraction)

## How To Explain The Process

When a user asks for the ISF process, explain in this order:
1. Eligibility and program fit (researcher status, institution eligibility, submission limits).
2. Account setup vs proposal registration (these are separate steps).
3. Proposal package preparation (abstract, research plan, bibliography, budget, required approvals).
4. Institutional approval and final submission in the ISF system.
5. Review pipeline (administrative screening, peer review, committee decision).
6. Resubmission policy and what to revise after rejection.

If the user asks for exact dates or numbers, answer from the latest local snapshot and explicitly state the cycle year/date.

## Snapshot Notes

- A snapshot run on `2026-02-13` indexed 52 grant programs and 27 linked files.
- The personal research grant file set includes both English and Hebrew guidelines and user guides.
- The latest captured personal grant cycle in this snapshot is submission window `November 2025`.
