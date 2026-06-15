# Compliance Validation Module

## Purpose
Ensure the proposal meets all ISF New PI Grant requirements before submission.

---

## Validation Categories

### 1. Eligibility Validation

```yaml
eligibility_checks:
  - id: ELIG-01
    name: "Academic Position"
    check: "Applicant holds Senior Lecturer or equivalent position"
    source: researcher_info.position
    required: true

  - id: ELIG-02
    name: "Years Since Appointment"
    check: "Within eligibility window from first appointment"
    source: researcher_info.appointment_date
    required: true
    rule: "current_date - appointment_date <= max_years"

  - id: ELIG-03
    name: "Institution"
    check: "Affiliated with recognized Israeli academic institution"
    source: researcher_info.institution
    required: true

  - id: ELIG-04
    name: "No Current ISF Grant"
    check: "Not currently PI on active ISF grant"
    source: researcher_info.prior_isf
    required: true
```

### 2. Proposal Structure Validation

```yaml
structure_checks:
  - id: STRUCT-01
    name: "Abstract Present"
    check: "Abstract section exists and is complete"
    source: proposal_sections.abstract
    required: true

  - id: STRUCT-02
    name: "Abstract Length"
    check: "Abstract within word limit"
    rule: "word_count(abstract) <= max_abstract_words"
    required: true

  - id: STRUCT-03
    name: "Scientific Background Present"
    check: "Background section exists"
    source: proposal_sections.background
    required: true

  - id: STRUCT-04
    name: "Specific Aims Present"
    check: "At least 2 specific aims defined"
    source: project_info.aims
    rule: "count(aims) >= 2"
    required: true

  - id: STRUCT-05
    name: "Research Plan Present"
    check: "Methods section exists"
    source: proposal_sections.methods
    required: true

  - id: STRUCT-06
    name: "Timeline Present"
    check: "Project milestones defined"
    source: project_info.milestones
    required: true

  - id: STRUCT-07
    name: "Budget Present"
    check: "Budget section complete"
    source: proposal_sections.budget
    required: true

  - id: STRUCT-08
    name: "CV Present"
    check: "CV/publication list provided"
    source: track_record.publications
    required: true

  - id: STRUCT-09
    name: "Bibliography Present"
    check: "References section exists"
    source: proposal_sections.bibliography
    required: true
```

### 3. Page Limit Validation

```yaml
page_limit_checks:
  - id: PAGE-01
    name: "Total Proposal Length"
    check: "Total pages within limit"
    rule: "total_pages <= max_pages"
    required: true

  - id: PAGE-02
    name: "Scientific Background Length"
    check: "Background within section limit"
    rule: "background_pages <= max_background_pages"
    required: true

  - id: PAGE-03
    name: "Research Plan Length"
    check: "Methods within section limit"
    rule: "methods_pages <= max_methods_pages"
    required: true

  - id: PAGE-04
    name: "CV Length"
    check: "CV within page limit"
    rule: "cv_pages <= max_cv_pages"
    required: true
```

### 4. Budget Validation

```yaml
budget_checks:
  - id: BUDGET-01
    name: "Annual Budget Limit"
    check: "Each year within annual maximum"
    rule: "for each year: budget_year <= max_annual"
    required: true

  - id: BUDGET-02
    name: "Total Budget Limit"
    check: "Total budget within maximum"
    rule: "sum(all_years) <= max_total"
    required: true

  - id: BUDGET-03
    name: "Category Compliance"
    check: "All expenses in allowed categories"
    rule: "for each item: category in allowed_categories"
    required: true

  - id: BUDGET-04
    name: "Equipment Limit"
    check: "Equipment within any specific limits"
    rule: "equipment_total <= max_equipment"
    required: false

  - id: BUDGET-05
    name: "Budget Justification"
    check: "All items have justification"
    rule: "for each item: justification.length > 0"
    required: true

  - id: BUDGET-06
    name: "Personnel Reasonable"
    check: "Personnel costs align with roles"
    required: false
    note: "Manual review recommended"
```

### 5. Formatting Validation

```yaml
format_checks:
  - id: FORMAT-01
    name: "Language"
    check: "Proposal in required language"
    rule: "language in [allowed_languages]"
    required: true

  - id: FORMAT-02
    name: "Font Compliance"
    check: "Correct font used"
    required: true
    note: "Manual check in final document"

  - id: FORMAT-03
    name: "Margin Compliance"
    check: "Margins meet requirements"
    required: true
    note: "Manual check in final document"

  - id: FORMAT-04
    name: "Line Spacing"
    check: "Correct line spacing"
    required: true
    note: "Manual check in final document"

  - id: FORMAT-05
    name: "File Format"
    check: "Correct file format for submission"
    rule: "format in [allowed_formats]"
    required: true
```

### 6. Content Quality Validation

```yaml
quality_checks:
  - id: QUAL-01
    name: "Aims Consistency"
    check: "Aims in abstract match aims section"
    required: true

  - id: QUAL-02
    name: "Timeline Feasibility"
    check: "Milestones distributed across project period"
    required: true

  - id: QUAL-03
    name: "Budget-Personnel Alignment"
    check: "Personnel in budget match methodology needs"
    required: true

  - id: QUAL-04
    name: "Methods-Aims Alignment"
    check: "Methods address all specific aims"
    required: true

  - id: QUAL-05
    name: "References Complete"
    check: "All citations have bibliography entries"
    required: true
```

---

## Validation Execution

### Pre-Validation Checklist

Before running validation:

```
[ ] All sections have been drafted
[ ] User has approved all sections
[ ] Budget has been calculated
[ ] CV/publications collected
[ ] ISF requirements have been fetched
```

### Validation Process

```python
def run_validation():
    results = {
        'passed': [],
        'failed': [],
        'warnings': [],
        'manual_review': []
    }

    # Run each check category
    for check in all_checks:
        result = evaluate_check(check)
        if result.status == 'PASS':
            results['passed'].append(check.id)
        elif result.status == 'FAIL' and check.required:
            results['failed'].append({
                'id': check.id,
                'name': check.name,
                'issue': result.issue,
                'fix': result.suggested_fix
            })
        elif result.status == 'WARN':
            results['warnings'].append({
                'id': check.id,
                'name': check.name,
                'note': result.note
            })
        elif result.status == 'MANUAL':
            results['manual_review'].append({
                'id': check.id,
                'name': check.name,
                'instruction': result.instruction
            })

    return results
```

---

## Validation Report Template

```markdown
# ISF New PI Grant - Compliance Validation Report

**Date:** {date}
**Applicant:** {researcher_name}
**Project:** {project_title}

## Summary

| Category | Passed | Failed | Warnings |
|----------|--------|--------|----------|
| Eligibility | {n} | {n} | {n} |
| Structure | {n} | {n} | {n} |
| Page Limits | {n} | {n} | {n} |
| Budget | {n} | {n} | {n} |
| Formatting | {n} | {n} | {n} |
| Quality | {n} | {n} | {n} |
| **Total** | {n} | {n} | {n} |

## Status: {READY / ISSUES FOUND / CRITICAL ISSUES}

---

## Failed Checks (Must Fix)

{For each failed check:}
### {check_id}: {check_name}
**Issue:** {issue_description}
**Required Action:** {fix_instruction}

---

## Warnings (Should Review)

{For each warning:}
- **{check_id}:** {note}

---

## Manual Review Required

{For each manual check:}
- [ ] **{check_id}:** {instruction}

---

## Checklist for Submission

### Required Documents
- [ ] Proposal document (PDF)
- [ ] CV
- [ ] Budget spreadsheet
- [ ] {other required documents}

### Portal Submission Steps
1. Log into ISF submission portal
2. Select "New PI Grant" program
3. Upload required documents
4. Complete online forms
5. Submit before {deadline}

### Final Reminders
- [ ] Save copy of all submitted materials
- [ ] Note confirmation number
- [ ] Calendar reminder for decision date
```

---

## Issue Resolution Helpers

### Common Issues and Fixes

| Issue | Automatic Fix | Manual Fix |
|-------|---------------|------------|
| Abstract too long | Suggest cuts | User edits |
| Missing section | Generate draft | User provides |
| Budget over limit | Highlight excess | User adjusts |
| Page limit exceeded | Count and flag | User cuts |
| Missing justification | Prompt for input | User writes |

### Fix Workflow

1. **Identify** all issues
2. **Prioritize** by severity (Critical > Required > Warning)
3. **Present** to user with context
4. **Assist** with fixes where possible
5. **Re-validate** after fixes
6. **Confirm** resolution

---

## Deadline Monitoring

```yaml
deadline_alerts:
  - days_before: 30
    message: "ISF deadline in 30 days. Recommended: Complete all drafts."

  - days_before: 14
    message: "ISF deadline in 2 weeks. Recommended: Finalize and validate."

  - days_before: 7
    message: "ISF deadline in 1 week. Final review period."

  - days_before: 3
    message: "ISF deadline in 3 days. Complete submission."

  - days_before: 1
    message: "ISF deadline tomorrow. Submit now."
```
