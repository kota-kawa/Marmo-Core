# Grant Learning Module

## Purpose

Enable users to upload past grant proposals (successful or unsuccessful) and reviewer feedback, then have the agent analyze them, extract learnings, and apply those learnings when building new proposals.

---

## User Commands

### `/learn-from-grant`

Initiates the grant learning workflow.

**Usage:**
```
/learn-from-grant
```

**Agent Response:**
```
I'll help you teach me from a past grant proposal.

Please tell me:
1. Is this a SUCCESSFUL (funded) or UNSUCCESSFUL (rejected) proposal?
2. Do you have reviewer feedback for this proposal?

Then share the proposal - you can either:
- Paste the text directly
- Upload a PDF/Word document
- Point me to a file path

I'll analyze it and show you what I learned.
```

---

### `/learn-from-reviews`

Add reviewer feedback for a proposal already in the system.

**Usage:**
```
/learn-from-reviews [proposal_name]
```

---

### `/show-learnings`

Display all accumulated learnings from past proposals.

**Usage:**
```
/show-learnings
```

---

## Analysis Protocol

### For Successful Proposals

When user provides a successful proposal:

**Step 1: Structural Analysis**
```
Analyzing structure...

ABSTRACT:
- Length: [X] words
- Structure: [Problem → Gap → Approach → Innovation → Impact]
- Opening strategy: [How it hooks the reader]

AIMS:
- Number of aims: [X]
- Independence: [Can each aim succeed alone?]
- Specificity: [How measurable are the outcomes?]

METHODS:
- Organization: [By aim / By technique / Chronological]
- Detail level: [High / Medium / Low]
- Feasibility indicators: [What establishes this is doable?]

PRELIMINARY DATA:
- Number of studies cited: [X]
- Sample sizes: [Range]
- How it's used: [To establish feasibility / To show expertise / Both]
```

**Step 2: Narrative Analysis**
```
Analyzing narrative qualities...

ARGUMENTATION FLOW:
- How significance is established: [description]
- How methods link to aims: [description]
- How criticisms are preempted: [description]

CONFIDENCE CALIBRATION:
- Hedging patterns: [When used, when avoided]
- Certainty language: [Examples]

INNOVATION FRAMING:
- Type: [Methodological / Theoretical / Application / Combination]
- How differentiated from existing work: [description]
```

**Step 3: Extract Actionable Patterns**
```
LEARNINGS FROM: [Proposal Name] (Successful)

PATTERN 1: [Name]
What I found: [Description]
Example from proposal: "[Quote]"
How I'll apply this: [Specific action for new proposal]

PATTERN 2: [Name]
What I found: [Description]
Example from proposal: "[Quote]"
How I'll apply this: [Specific action for new proposal]

[Continue for all significant patterns...]
```

**Step 4: Store Learnings**
Save to `learnings/successful_patterns.yaml`:

```yaml
proposal_name: "[Name]"
analyzed_date: "[Date]"
outcome: "funded"
score: "[If known]"

patterns:
  - id: "SP-001"
    category: "abstract_structure"
    description: "Opens with societal impact before scientific gap"
    example: "[Quote from proposal]"
    application: "Use impact-first opening in abstracts"

  - id: "SP-002"
    category: "aim_independence"
    description: "Each aim explicitly states contingency"
    example: "Even if Aim 1 yields unexpected results, Aim 2 will produce..."
    application: "Add explicit contingency statement to each aim"

strengths:
  - "Clear power analysis with literature-based effect sizes"
  - "Preliminary data from 3 pilot studies (N > 20 each)"
  - "Budget tied to specific personnel expertise"
```

---

### For Unsuccessful Proposals

When user provides an unsuccessful proposal:

**Step 1: Structural Analysis**
Same as successful, but looking for gaps and weaknesses.

**Step 2: Weakness Identification**
```
Analyzing potential weaknesses...

STRUCTURAL ISSUES:
- [ ] Aims appear interdependent (cascading failure risk)
- [ ] Timeline front-loaded (Year 1 overloaded)
- [ ] Methods section vague on statistical approach
- [ ] Sample size not justified

RED FLAG PHRASES DETECTED:
- "We anticipate..." (appears X times without supporting data)
- "Straightforward" (used for complex procedures)
- "Appropriate statistical methods" (doesn't name specific tests)
- "If time permits" (signals overambitious scope)

MISSING ELEMENTS:
- No power analysis
- No contingency plans
- No preliminary data for Aim 3
```

**Step 3: Extract Anti-Patterns**
```
LEARNINGS FROM: [Proposal Name] (Unsuccessful)

WEAKNESS 1: [Name]
What I found: [Description]
Problem: [Why this likely hurt the proposal]
How I'll help you avoid this: [Specific prevention]

WEAKNESS 2: [Name]
What I found: [Description]
Problem: [Why this likely hurt the proposal]
How I'll help you avoid this: [Specific prevention]

[Continue for all significant weaknesses...]
```

**Step 4: Store Learnings**
Save to `learnings/weaknesses_to_avoid.yaml`:

```yaml
proposal_name: "[Name]"
analyzed_date: "[Date]"
outcome: "rejected"

weaknesses:
  - id: "WK-001"
    category: "aim_structure"
    description: "Aims 2 and 3 depend on Aim 1 success"
    quote: "[Example from proposal]"
    prevention: "Ensure each aim has independent deliverables"

  - id: "WK-002"
    category: "feasibility"
    description: "No power analysis provided"
    prevention: "Always include explicit sample size calculation"

red_flags:
  - phrase: "we anticipate"
    count: 5
    problem: "Speculation without data"

  - phrase: "straightforward"
    count: 3
    problem: "Underestimates complexity"
```

---

### For Reviewer Feedback

When user provides reviewer comments:

**Step 1: Categorize Concerns**
```
Analyzing reviewer feedback...

CRITICAL CONCERNS (mentioned by 2+ reviewers):
1. "[Concern]" - Reviewers 1, 3
2. "[Concern]" - Reviewers 2, 3

MODERATE CONCERNS (mentioned by 1 reviewer):
1. "[Concern]" - Reviewer 2

POSITIVE NOTES:
1. "[Praise]" - Reviewers 1, 2, 3
2. "[Praise]" - Reviewer 1
```

**Step 2: Extract Actionable Insights**
```
LEARNINGS FROM REVIEWER FEEDBACK: [Proposal Name]

MUST ADDRESS IN NEW PROPOSAL:
1. [Concern]: [How to address it]
2. [Concern]: [How to address it]

STRENGTHS TO MAINTAIN:
1. [What was praised]: [How to replicate]
```

**Step 3: Store in Concerns Database**
Save to `learnings/reviewer_concerns.yaml`:

```yaml
proposal_name: "[Name]"
review_cycle: "[Year]"
number_of_reviewers: 3

concerns:
  - concern: "Sample size justification unclear"
    frequency: 2
    severity: "critical"
    addressable: true
    prevention: "Include explicit power analysis with literature-based effect sizes"

  - concern: "Timeline aggressive for Year 1"
    frequency: 1
    severity: "moderate"
    addressable: true
    prevention: "Distribute milestones more evenly; add buffer time"

praises:
  - praise: "Innovative approach to significant problem"
    frequency: 3
    replicate: "Lead with innovation framing in background section"
```

---

## Applying Learnings

### During Interview Phase

When gathering information, reference learnings:

```
You mentioned your Aim 2 depends on results from Aim 1.

⚠️ LEARNING FROM PAST: Your 2023 proposal was criticized for aim
interdependence. Reviewer 2 wrote: "If Aim 1 fails, the entire
proposal collapses."

Let's make sure each aim has independent value. What would Aim 2
deliver even if Aim 1 yields unexpected results?
```

### During Content Generation

When drafting sections, apply patterns:

```
Drafting your Abstract...

APPLYING LEARNINGS:
✓ Using impact-first opening (from 2024 successful proposal)
✓ Structuring as Problem → Gap → Approach → Innovation → Impact
✓ Avoiding "we anticipate" without supporting data

---
[Generated abstract]
---

This follows the structure that worked in your funded 2024 proposal.
```

### During Validation

Check against learned weaknesses:

```
CHECKING AGAINST PAST LEARNINGS...

⚠️ WARNING: Your methods section uses "appropriate statistical methods"
   without naming specific tests.

   LEARNING: Your 2023 rejection cited this exact issue.
   Reviewer 1: "What statistical tests will be used?"

   SUGGESTION: Replace with: "We will use [specific test] to analyze..."

✓ GOOD: Each aim has explicit contingency language
   (Addresses weakness from 2023 proposal)

✓ GOOD: Power analysis included with effect size justification
   (Addresses concern from 2023 reviewer feedback)
```

---

## Storage Structure

```
grant-agent/
└── learnings/
    ├── successful_patterns.yaml    # Patterns from funded proposals
    ├── weaknesses_to_avoid.yaml    # Anti-patterns from rejections
    ├── reviewer_concerns.yaml      # Concerns database from feedback
    └── analysis_log.md             # Record of all analyzed proposals
```

---

## Commands Summary

| Command | Action |
|---------|--------|
| `/learn-from-grant` | Start learning workflow for a new proposal |
| `/learn-from-reviews` | Add reviewer feedback |
| `/show-learnings` | Display all accumulated learnings |
| `/apply-learning [ID]` | Apply a specific learned pattern |
| `/check-learnings` | Check current draft against all learnings |
| `/clear-learnings` | Reset learning database (with confirmation) |

---

## Interactive Learning Session Example

```
User: /learn-from-grant

Agent: I'll help you teach me from a past grant proposal.

       Is this a SUCCESSFUL (funded) or UNSUCCESSFUL (rejected) proposal?

User: Unsuccessful. It was rejected last year.

Agent: I'm sorry to hear that - but rejected proposals are incredibly
       valuable for learning. Do you have the reviewer feedback?

User: Yes, I have the reviews too.

Agent: Perfect. Please share the proposal first. You can paste the text,
       upload a file, or give me a file path.

User: [Pastes proposal text or uploads file]

Agent: Analyzing your proposal...

       [Shows structural analysis]
       [Shows weakness identification]
       [Shows red flag phrases detected]

       I found 4 significant patterns to learn from. Here's what I'll
       watch for when we build your new proposal:

       1. AIM INTERDEPENDENCE
          Your Aim 3 couldn't succeed without Aim 2.
          → I'll prompt you to ensure each aim has independent value.

       2. TIMELINE COMPRESSION
          70% of work was scheduled for Year 1.
          → I'll check for realistic distribution across years.

       3. VAGUE STATISTICS
          "Appropriate methods" appeared 3 times without specifics.
          → I'll ask for specific test names when drafting methods.

       4. MISSING POWER ANALYSIS
          No sample size justification was provided.
          → I'll require explicit power analysis before drafting.

       Now please share the reviewer feedback so I can learn what
       specifically concerned them.

User: [Shares reviewer comments]

Agent: Analyzing reviewer feedback...

       CRITICAL (2+ reviewers mentioned):
       • "Sample size not justified" - R1, R3
       • "Aims too interdependent" - R1, R2

       This confirms my analysis. These will be top priorities
       for your new proposal.

       ✓ Learnings saved. When we work on your new proposal, I'll
         actively check against these issues.

       Ready to start your new proposal? Or would you like to add
       more past proposals first?
```

---

## Integration with Main Agent Workflow

### At Session Start
```
Agent checks: learnings/ folder exists?
  → Yes: Load all learned patterns and concerns
  → No: Create folder, note no prior learnings

Report to user:
"I have learnings from [X] past proposals:
 - [N] successful patterns to apply
 - [N] weaknesses to avoid
 - [N] reviewer concerns to address"
```

### Throughout Session
- Reference specific learnings when relevant
- Flag when user's input matches a known weakness pattern
- Apply successful patterns in content generation
- Validate against learned concerns before finalizing

### At Session End
```
Summary of learnings applied:
- Used [N] patterns from successful proposals
- Avoided [N] weaknesses from unsuccessful proposals
- Addressed [N] known reviewer concerns
```
