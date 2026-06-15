---
skillx:
  name: docx
  purpose: Fill template-based Word documents with python-docx while handling split placeholders, headers/footers, nested tables, and simple conditional sections.
  scope_in:
    - tasks ask to fill an existing .docx template from structured input data
    - the template uses placeholder tokens like {{FIELD_NAME}}
    - placeholders may appear in normal paragraphs, tables, nested tables, headers, or footers
    - the task requires preserving the original document structure rather than rewriting the document from scratch
  scope_out:
    - not for drafting legal or HR language from scratch
    - not for PDF/image-form editing or OCR-heavy workflows
    - not for final legal sign-off or policy interpretation
  requires:
    - python-docx is available
    - access to the template .docx file and structured source data
    - ability to write the final output as a .docx file
  preferred_tools:
    - python-docx
    - regex for placeholder detection
    - json for structured source data
  risks:
    - placeholders may be split across multiple XML runs
    - placeholders may appear in headers, footers, or nested tables and be missed by naive body-only logic
    - conditional markers may remain in the final document if not explicitly handled
    - guessing missing values or inventing contract language can silently corrupt the output
  examples:
    - input: Fill an offer-letter Word template from employee_data.json and remove conditional relocation markers correctly.
      expected_behavior: Read the template and source data, replace placeholders robustly, preserve document structure, resolve conditional sections, and save a valid output .docx.
---

# Guidance

Use paragraph-level replacement rather than run-level replacement whenever placeholders may be split across runs.

Treat the document as more than `doc.paragraphs`:
- process body paragraphs
- recurse through tables and nested tables
- process headers and footers for each section

For conditional sections like `{{IF_RELOCATION}} ... {{END_IF_RELOCATION}}`:
- include the content only when the condition is satisfied
- remove the markers themselves from the final document
- do not leave raw control tags in the output

When rebuilding text, prefer preserving the first run’s formatting and clearing later runs rather than editing runs one by one.

Before saving, do a final pass to ensure:
- no expected placeholders remain unresolved unless intentionally flagged
- no IF/END_IF markers remain
- the result stays in `.docx` form and follows the template structure

# Notes for Agent

The most common failure is a naive run-level search that misses split placeholders.
A close second is forgetting headers/footers or nested tables.
If required data is missing, prefer explicit flagging over silent invention.


# Derived Execution Layer

## Candidate Preconditions
- template `.docx` is available and readable
- structured employee data is available and key placeholders can be mapped to fields
- output path is writable

## Candidate Postconditions
- final `.docx` exists at the required output path
- expected placeholders are replaced or explicitly surfaced as missing
- no raw conditional markers remain in final content
- core template structure is preserved

## Candidate Failure Modes
- split placeholder missed due to run-level replacement
- header/footer placeholder left unresolved
- nested-table placeholder left unresolved
- relocation block incorrectly removed or incorrectly retained
- invented value inserted for missing field

## Candidate Evaluator Hooks
- unresolved-placeholder scan
- marker-removal scan for `IF_RELOCATION` / `END_IF_RELOCATION` tags
- existence and readability check on output `.docx`
- targeted spot-checks for header/footer and nested-table replacement

## Suspected Negative-Transfer Risk
- low to medium
- this task seems genuinely helped by the skill; the main risk is overconfidence or missed edge surfaces rather than over-prescriptive strategy
