---
skillx:
  name: docx
  purpose: Generate a filled .docx artifact from a template and structured inputs while preserving template structure and placeholder integrity.
  scope_in:
    - fill a template-based Word document (for example an offer letter) from known field values
    - replace placeholders like {{FIELD_NAME}} across body text, tables, nested tables, headers, and footers
    - keep the original template layout and clauses unless conditional markers explicitly control inclusion
  scope_out:
    - not for inventing missing legal/HR terms or policy clauses
    - not for drafting a brand-new letter without a template/output contract
    - not for PDF/OCR-only document editing workflows
  requires:
    - template .docx file
    - structured input values for required placeholders (or explicit missing-field policy)
    - python-docx runtime and permission to write output .docx
  preferred_tools:
    - python-docx
    - regex
    - json
  risks:
    - split placeholders across XML runs causing silent replacement misses
    - missed replacements in headers/footers or nested tables
    - template drift from run-level edits that break structure/formatting
    - invented values when required inputs are missing
  examples:
    - input: Fill an offer-letter template from candidate_data.json with relocation conditional blocks.
      expected_behavior: Replace placeholders robustly across all document regions, resolve conditionals, preserve structure, and save a valid .docx with no unresolved required tokens.
---

# Guidance

Preserve the output contract: keep template structure, section ordering, and wording unless the template’s own markers require changes.

Use paragraph-level replacement logic (not naive run-level matching) so split placeholders are still detected and replaced.

Process all template regions:
- main body paragraphs
- tables and nested tables (recursive)
- headers and footers for each section

For conditional blocks like `{{IF_X}}...{{END_IF_X}}`:
- include content only when condition is true
- remove control markers in all cases
- avoid leaving raw markers in final output

Missing-input policy:
- do not invent required values
- if required fields are absent, request them or leave an explicit unresolved marker per task instruction

# Acceptance

- Output remains a valid `.docx` and preserves template structure.
- Required placeholders are resolved or explicitly flagged (not silently dropped).
- Repeated fields are consistent across all regions.
- No stray control markers (`{{IF_*}}`, `{{END_IF_*}}`) remain.
- No invented clauses/values beyond provided inputs and explicit rules.