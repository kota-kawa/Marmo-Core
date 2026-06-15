# Past Proposals Analysis Module

## Purpose
Extract patterns, best practices, and lessons from past grant proposals to inform and improve the current proposal.

---

## Repository Structure

The agent expects past proposals in this structure:

```
past-proposals/
├── successful/           # Funded proposals
│   ├── proposal1.pdf
│   └── proposal2.docx
├── unsuccessful/         # Rejected proposals
│   └── rejected1.pdf
└── reviews/              # Reviewer feedback
    ├── proposal1_reviews.pdf
    └── rejected1_reviews.txt
```

---

## Analysis Protocol

### Phase 1: Discovery

When initializing, scan the past-proposals directory:

```
ACTION: Scan past proposals repository

1. List all files in past-proposals/successful/
2. List all files in past-proposals/unsuccessful/
3. List all files in past-proposals/reviews/
4. Match reviews to their corresponding proposals by filename patterns
5. Report findings to user:

"I found [n] past proposals in your repository:
- Successful: [list with filenames]
- Unsuccessful: [list with filenames]
- Reviews available for: [list]

I'll analyze these to learn what works and what to avoid."
```

---

### Phase 2: Successful Proposal Analysis

For each successful proposal, extract:

#### 2.1 Structural Patterns

```yaml
structure_analysis:
  abstract:
    pattern: "[Problem statement] → [Gap identified] → [Proposed approach] → [Innovation claim] → [Expected impact]"
    length: "[word count]"
    key_phrases: ["addresses critical gap", "novel approach", etc.]

  aims_section:
    number_of_aims: [n]
    aim_structure: "Each aim follows: Hypothesis → Method → Prediction → Alternative interpretation"
    interdependence: "[low/medium/high] - aims can succeed independently"

  methods:
    organization: "[by aim / by technique / chronological]"
    detail_level: "[high specificity with citations]"
    feasibility_indicators: ["preliminary data referenced", "existing collaborations cited"]

  preliminary_data:
    number_of_studies: [n]
    sample_sizes: "[typical range]"
    presentation: "[figures with statistics / narrative summary]"

  budget:
    personnel_justification: "[specific role descriptions]"
    equipment_rationale: "[tied to specific aims]"
```

#### 2.2 Narrative Qualities

```yaml
narrative_analysis:
  argumentation_flow:
    - "Establishes significance before methodology"
    - "Links each method to specific aim"
    - "Addresses potential criticisms proactively"

  confidence_level:
    self_description: "[confident but not overselling]"
    hedging_frequency: "[when used appropriately]"

  innovation_framing:
    type: "[methodological / theoretical / application]"
    strength: "[explicit comparison to existing approaches]"
```

#### 2.3 Extractable Best Practices

Generate specific, actionable patterns:

```
BEST PRACTICE: Aim Independence
Source: successful/2024_cognitive_intervention.pdf
Pattern: "Each aim explicitly states: 'Even if [other aim] yields unexpected results,
this aim will produce [specific deliverable] that advances the field.'"
Application: Use this exact framing in the current proposal's aims section.

BEST PRACTICE: Preliminary Data Presentation
Source: successful/2024_cognitive_intervention.pdf
Pattern: "Pilot Study 1 (N=25): [Result with p-value]. This establishes [specific claim]."
Application: Format preliminary data with explicit N, statistical result, and
what it demonstrates for feasibility.
```

---

### Phase 3: Unsuccessful Proposal Analysis

For each unsuccessful proposal, extract:

#### 3.1 Structural Weaknesses

```yaml
weakness_patterns:
  aims:
    - "Aims 2 and 3 dependent on Aim 1 success"
    - "Aim 4 overly ambitious for timeline"

  methods:
    - "Sample size not justified with power analysis"
    - "No contingency for recruitment challenges"

  timeline:
    - "Year 1 overloaded, Year 4 underspecified"
    - "Milestones not measurable"

  budget:
    - "Equipment costs underestimated"
    - "No justification for travel budget"
```

#### 3.2 Red Flag Indicators

Patterns that predict rejection:

```yaml
red_flags:
  scope_issues:
    - phrase: "addresses this and related questions"
      meaning: "Too broad, unfocused"
    - phrase: "if time permits"
      meaning: "Overpromising, will trigger reviewer concern"

  feasibility_issues:
    - phrase: "we anticipate" without preliminary data
      meaning: "Speculation, not grounded"
    - phrase: "straightforward" for complex procedures
      meaning: "Underestimating challenges"

  vagueness:
    - phrase: "appropriate statistical methods"
      meaning: "Doesn't know which tests to use"
    - phrase: "sufficient sample size"
      meaning: "No power analysis"
```

---

### Phase 4: Review Analysis

When reviewer feedback is available:

#### 4.1 Categorize Feedback

```yaml
review_analysis:
  critical_concerns:
    - concern: "Sample size justification unclear"
      frequency: "2 of 3 reviewers"
      severity: "high"
      addressable: true

  moderate_concerns:
    - concern: "Timeline aggressive"
      frequency: "1 reviewer"
      severity: "medium"
      addressable: true

  positive_notes:
    - praise: "Innovative approach"
      frequency: "all reviewers"
    - praise: "Strong preliminary data"
      frequency: "2 reviewers"

  improvement_opportunities:
    - from_criticism: "Sample size unclear"
      action: "Add explicit power analysis section"
    - from_criticism: "Equipment costs seem low"
      action: "Request vendor quotes, include in justification"
```

#### 4.2 Reviewer Concerns Database

Build a searchable database of concerns to avoid:

```yaml
reviewer_concerns_database:
  methodology:
    - concern: "How will you handle attrition?"
      context: "Longitudinal designs"
      prevention: "Include attrition analysis and contingency"

    - concern: "What if the intervention has no effect?"
      context: "Intervention studies"
      prevention: "Define clinically meaningful effect sizes, include manipulation checks"

  feasibility:
    - concern: "Is this achievable in the proposed timeline?"
      context: "Ambitious scope"
      prevention: "Add explicit contingency aims, prioritize deliverables"

  significance:
    - concern: "How does this advance beyond existing work?"
      context: "Incremental innovation"
      prevention: "Explicit comparison table with existing approaches"
```

---

### Phase 5: Synthesis and Application

#### 5.1 Generate Learning Summary

Present to user at session start:

```markdown
## What I Learned from Your Past Proposals

### Successful Patterns to Replicate
1. **Aim Structure**: Your funded proposal used independent aims with explicit
   contingencies. I'll ensure your new aims follow this pattern.

2. **Preliminary Data**: The successful proposal cited 3 pilot studies with
   N > 20 each. I'll prompt for equivalent support.

3. **Budget Justification**: Personnel roles were tied to specific techniques.
   I'll structure your budget similarly.

### Weaknesses to Avoid
1. **Aim Interdependence**: Your 2023 rejection was partly due to cascading aims.
   I'll flag any dependencies in your new proposal.

2. **Timeline Compression**: Year 1 was overloaded. I'll help distribute
   milestones realistically.

3. **Missing Power Analysis**: This was cited by 2 reviewers. I'll require
   explicit sample size justification.

### Reviewer Concerns to Preempt
- Attrition handling (mentioned in reviews)
- Equipment cost realism (mentioned in reviews)
- Innovation compared to existing approaches (common concern)
```

#### 5.2 Active Application During Drafting

When generating each section, reference learned patterns:

```
When drafting AIMS:
- Check: Are aims independent? (Learned: dependency was criticized)
- Check: Does each aim have explicit contingency? (Learned: successful proposal had this)
- Apply: Use the framing pattern from successful/2024_cognitive_intervention.pdf

When drafting METHODS:
- Check: Is sample size justified with power analysis? (Learned: missing in rejection)
- Check: Are statistical tests named explicitly? (Learned: vagueness was flagged)
- Apply: Format methodology by aim, as in successful proposals

When drafting BUDGET:
- Check: Is each personnel role justified with specific skills needed?
- Check: Are equipment costs realistic? (Learned: underestimation noted in reviews)
- Apply: Use role-specific justification pattern from successful proposals
```

---

## Integration with Main Agent

### At Session Initialization

```
1. Run repository scan
2. Execute analysis protocol
3. Store patterns in session state
4. Present learning summary to user
5. Proceed with interview, applying patterns
```

### During Interview

```
For each question:
1. Check if past proposals inform this area
2. Reference specific learned patterns
3. Warn if user response matches weakness patterns
4. Suggest improvements based on successful examples
```

### During Content Generation

```
For each section:
1. Apply structural patterns from successful proposals
2. Check for red flag phrases
3. Verify against reviewer concerns database
4. Note when deviating from successful patterns
```

---

## Commands

| Command | Action |
|---------|--------|
| `/patterns` | Display learned patterns summary |
| `/concerns` | Show reviewer concerns database |
| `/compare` | Compare current draft to successful examples |
| `/redflags` | Check current content for warning phrases |
