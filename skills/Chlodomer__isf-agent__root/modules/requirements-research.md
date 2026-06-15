# Requirements Research Module

## Purpose
Load ISF Personal Research Grant requirements from local authoritative source, or fetch from official sources if unavailable.

---

## Execution Flow

### Step 0: Check Local Requirements Module (FIRST)

**Before searching the web, check for local requirements file:**

```
LOOK FOR: modules/isf-requirements-[YEAR].md

Example: modules/isf-requirements-2026.md

If found:
1. Read the file
2. Extract all requirements data
3. Present summary to user
4. Skip Steps 1-3 (no web search needed)

If not found:
→ Proceed to Step 1 (web search)
```

**The local module is authoritative** - it was created from the official ISF guidelines PDF and contains accurate, structured data.

---

### Step 0b: Refresh ISF Website Snapshot (Optional)

When you need the latest grant-linked files and deadlines directly from ISF:

```bash
node scripts/fetch-isf-grants-docs.mjs
```

Use `.context/isf-grants-docs/manifest.json` as the master index for the downloaded site snapshot.

---

### Step 1: Primary Source Search (only if local module not found)

```
SEARCH QUERIES (execute in order):
1. "ISF Israel Science Foundation personal research grant guidelines 2024 2025"
2. "site:isf.org.il new investigator grant"
3. "ISF קרן לאומית למדע מענק חוקר חדש"
```

### Step 2: Official Site Navigation

Navigate to: `https://www.isf.org.il`

Look for:
- "Programs" or "Grant Programs" section
- "Personal Research Grants" category
- "New Investigators" or "First Grant" subcategory
- Current year's call for proposals

### Step 3: Extract Requirements

Parse and extract the following data points:

#### Eligibility Criteria
```yaml
eligibility:
  position_requirement: # e.g., "Senior Lecturer or equivalent"
  years_since_appointment: # e.g., "Within 7 years of first appointment"
  institution_requirement: # e.g., "Israeli academic institution"
  citizenship: # e.g., "Israeli citizen or permanent resident"
  prior_isf_funding: # e.g., "Not currently PI on ISF grant"
  teaching_load: # If specified
  other_restrictions: []
```

#### Budget Parameters
```yaml
budget:
  annual_maximum: # NIS amount
  total_maximum: # NIS amount over grant period
  categories:
    personnel: {allowed: true, notes: ""}
    equipment: {allowed: true, limit: null}
    consumables: {allowed: true, notes: ""}
    travel: {allowed: true, limit: null}
    other: {allowed: true, notes: ""}
  overhead: # Percentage if applicable
  restrictions: []
```

#### Proposal Structure
```yaml
proposal:
  duration: # e.g., "4 years"
  language: # "English" or "Hebrew"
  page_limits:
    total: null
    scientific_background: null
    research_plan: null
    cv: null
  required_sections:
    - "Abstract"
    - "Scientific Background"
    - "Research Objectives"
    - "Research Plan and Methodology"
    - "Preliminary Results"
    - "Expected Outcomes"
    - "Timetable"
    - "Budget"
    - "Bibliography"
    - "CV"
  attachments:
    - "Letters of collaboration"
    - "Equipment quotes"
```

#### Formatting Requirements
```yaml
formatting:
  font: # e.g., "Times New Roman 12pt"
  margins: # e.g., "2.5cm all sides"
  line_spacing: # e.g., "1.5"
  file_format: # e.g., "PDF"
  naming_convention: # If specified
```

#### Timeline
```yaml
timeline:
  call_opens: # Date
  submission_deadline: # Date
  review_period: # Description
  decision_announcement: # Date
  funding_start: # Date
```

### Step 4: Validation

Cross-reference extracted information:
- Check that budget limits are consistent
- Verify page limits add up
- Confirm deadline hasn't passed
- Note any ambiguities for user clarification

### Step 5: Output Summary

Generate user-friendly summary:

```markdown
## ISF New PI Grant Requirements Summary

### Are You Eligible?
- [ ] Position: [requirement]
- [ ] Years since appointment: [requirement]
- [ ] Institution: [requirement]
- [ ] No current ISF grant as PI

### Key Numbers
- **Budget**: Up to NIS [X] per year (NIS [Y] total)
- **Duration**: [X] years
- **Deadline**: [Date]

### What You'll Need to Write
1. Abstract ([X] words max)
2. Scientific Background ([X] pages)
3. Research Plan ([X] pages)
4. Methodology
5. Timeline
6. Budget & Justification
7. CV ([X] pages)

### Formatting
- Language: [English/Hebrew]
- Font: [specification]
- File format: [PDF/Word]
```

## Fallback Behavior

If official source unavailable:

1. Use cached/known requirements from previous cycles
2. Inform user: "I couldn't access the latest ISF guidelines. The following is based on typical requirements, but please verify against the official call."
3. Provide links for manual verification
4. Flag all outputs as "NEEDS VERIFICATION"

## Known ISF URLs

- Main site: https://www.isf.org.il
- English: https://www.isf.org.il/english
- Forms: https://www.isf.org.il/forms
- FAQ: https://www.isf.org.il/faq

---

## Available Local Requirements Modules

| Cycle | File | Status |
|-------|------|--------|
| 2026 (תשפ"ז) | `modules/isf-requirements-2026.md` | Current |

When new ISF guidelines are released, create a new module following the same structure.
