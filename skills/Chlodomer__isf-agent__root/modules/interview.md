# Researcher Interview Module

## Purpose
Systematically gather all information needed to generate a complete ISF New PI Grant proposal.

## Interview Principles

1. **Progressive disclosure**: Don't overwhelm with all questions upfront
2. **Context provision**: Explain why each question matters
3. **Flexibility**: Allow skipping and returning
4. **Validation**: Confirm critical information
5. **Examples**: Offer samples when helpful

---

## Interview Sections

### Section 1: Eligibility & Background

**Transition message:**
> "Let's start by confirming your eligibility and gathering some basic information."

#### Q1.1: Position & Institution
```
Question: What is your current academic position and which institution are you affiliated with?

Example: "I'm a Senior Lecturer in the Department of Computer Science at Tel Aviv University"

Why it matters: ISF requires applicants to hold specific positions at Israeli academic institutions.

Store in: researcher_info.position, researcher_info.institution
```

#### Q1.2: Department
```
Question: What department or faculty are you in?

Store in: researcher_info.department
```

#### Q1.3: Appointment Date
```
Question: When were you appointed to your first independent academic position? (month/year)

Example: "October 2022"

Why it matters: ISF New PI grants have time limits from first appointment.

Store in: researcher_info.appointment_date
Validation: Check against eligibility window
```

#### Q1.4: Prior Independent Position
```
Question: Have you previously held an independent research position at another institution?

Options: Yes / No

If yes: Where and when?

Store in: researcher_info.prior_positions
```

#### Q1.5: Previous ISF Funding
```
Question: Have you previously received ISF funding as a Principal Investigator?

Options: Yes / No / As Co-PI only

If yes: Which grant and when?

Store in: researcher_info.prior_isf
Validation: Check eligibility impact
```

---

### Section 2: Research Project Core

**Transition message:**
> "Now let's focus on your proposed research. Take your time with these - they form the heart of your proposal."

#### Q2.1: Project Title
```
Question: What is the working title of your proposed research project?

Guidance: Aim for clear and specific. Avoid jargon. Should convey the main question or approach.

Example: "Decoding Neural Circuits of Decision-Making Under Uncertainty"

Store in: project_info.title
```

#### Q2.2: Central Question
```
Question: In 2-3 sentences, what is the central question or problem your research addresses?

Guidance: This should capture the "why" - why does this matter? What gap are you filling?

Example: "How do neural circuits in the prefrontal cortex integrate uncertain sensory information to guide behavior? Despite decades of research, the computational principles underlying decision-making under uncertainty remain poorly understood."

Store in: project_info.central_question
```

#### Q2.3: Specific Aims
```
Question: What are your specific aims? Most proposals have 2-4 aims. Please list each one.

Guidance: Each aim should be:
- Specific and measurable
- Achievable within the grant period
- Connected to your central question
- Independent enough to succeed even if others face obstacles

Example:
"Aim 1: Characterize the neural representations of uncertainty in prefrontal cortex using calcium imaging
Aim 2: Determine how uncertainty signals are integrated across brain regions
Aim 3: Test causal predictions through targeted optogenetic manipulation"

Store in: project_info.aims[]
Follow-up: For each aim, what is the key hypothesis?
```

#### Q2.4: Innovation
```
Question: What makes your approach novel or innovative compared to existing work?

Guidance: Consider:
- New methodology?
- New theoretical framework?
- New application domain?
- Unique combination of approaches?

Store in: project_info.innovation
```

#### Q2.5: Preliminary Data
```
Question: What preliminary data or prior work do you have that supports the feasibility of this project?

Guidance: Include:
- Pilot experiments
- Published work from your group
- Established methods you'll apply
- Access to unique resources

Note: If limited preliminary data, explain how you'll address this.

Store in: project_info.preliminary_data
```

#### Q2.6: Methodology
```
Question: What is your primary methodological approach? Describe the key methods and techniques you'll use.

Guidance: Be specific enough to demonstrate feasibility but not so detailed it overwhelms.

Store in: project_info.methodology
```

#### Q2.7: Expected Outcomes
```
Question: What are the expected outcomes and deliverables from this research?

Guidance: Consider:
- Scientific discoveries
- Publications
- New methods/tools
- Trained personnel
- Data resources

Store in: project_info.outcomes
```

#### Q2.8: Risks & Mitigation
```
Question: What are the main risks or challenges you anticipate, and how will you address them?

Guidance: Showing awareness of risks demonstrates maturity. For each risk, have a mitigation plan.

Example:
"Risk: Sample recruitment may be slower than anticipated
Mitigation: We have established collaborations with three clinical sites and will begin recruitment in Year 1"

Store in: project_info.risks[]
```

---

### Section 3: Resources & Timeline

**Transition message:**
> "Let's plan the resources you'll need and how the project will unfold over time."

#### Q3.1: Personnel
```
Question: What personnel will you need for this project? Include:
- Graduate students
- Postdoctoral researchers
- Research assistants
- Technicians

For each, specify: role, percentage time, and which aims they'll contribute to.

Store in: resources.personnel[]
```

#### Q3.2: Equipment
```
Question: What major equipment or resources will you need?

Categories:
- Existing equipment you'll use
- New equipment to purchase
- Shared facilities you'll access

Include approximate costs for new purchases.

Store in: resources.equipment[]
```

#### Q3.3: Other Resources
```
Question: What other resources do you need? Consider:
- Consumables and supplies
- Software/computational resources
- Travel (conferences, collaborations)
- Participant compensation
- Publication costs

Store in: resources.other[]
```

#### Q3.4: Duration
```
Question: What is your proposed project duration?

Note: ISF New PI grants are typically 4 years.

Store in: project_info.duration
```

#### Q3.5: Milestones
```
Question: What are your key milestones for each year of the project?

Format:
Year 1: [Milestone 1], [Milestone 2]
Year 2: [Milestone 1], [Milestone 2]
...

Store in: project_info.milestones[]
```

---

### Section 4: Track Record

**Transition message:**
> "Finally, let's document your research track record. This establishes your ability to execute the proposed work."

#### Q4.1: Publications
```
Question: Please provide your publication list. You can either:
1. Paste your list here
2. Upload your CV
3. Provide your Google Scholar or ORCID link

Store in: track_record.publications[]
```

#### Q4.2: Relevant Publications
```
Question: Which of your publications are most relevant to this proposal? Please list 3-5 key papers and briefly explain their relevance.

Store in: track_record.relevant_publications[]
```

#### Q4.3: Prior Grants
```
Question: List any grants you've received or currently hold (as PI or Co-PI):

For each include:
- Funding agency
- Title
- Amount
- Period
- Your role

Store in: track_record.prior_grants[]
```

#### Q4.4: Collaborators
```
Question: Who are the key collaborators for this project? For each, provide:
- Name and institution
- Their expertise
- Their role in the project
- Whether you have letters of support

Store in: track_record.collaborators[]
```

---

## Interview State Management

```yaml
interview_state:
  current_section: 1
  current_question: 1
  skipped_questions: []
  completed_sections: []
  validation_issues: []

  responses:
    section_1: {}
    section_2: {}
    section_3: {}
    section_4: {}
```

## Navigation Commands

- `skip` - Skip current question, add to skipped list
- `back` - Return to previous question
- `review [section]` - Review responses for a section
- `edit [question]` - Edit a previous response
- `status` - Show interview progress

## Completion Check

Before proceeding to content generation, verify:

```
REQUIRED:
[ ] Position and institution
[ ] Appointment date
[ ] Project title
[ ] Central question
[ ] At least 2 specific aims
[ ] Methodology overview
[ ] Expected outcomes

RECOMMENDED:
[ ] Preliminary data
[ ] Risks and mitigations
[ ] Personnel plan
[ ] Milestones
[ ] Relevant publications
```

If required fields missing, prompt user to complete before proceeding.
