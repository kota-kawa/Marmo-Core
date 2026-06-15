---
skillx:
  name: power-flow-data
  purpose: Parse MATPOWER-style network data into a deterministic, index-safe artifact that preserves units, topology, and field semantics required by AC branch modeling and NLP solve stages.
  scope_in:
    - loading network.json and required arrays/fields
    - bus-number to index mapping
    - extraction of bus/gen/branch/cost/reserve structures for AC OPF
    - per-unit conversion boundaries via baseMVA
  scope_out:
    - not for solving OPF
    - not for modifying physical assumptions or approximating topology
    - not for manual line-by-line parsing of large JSON files
  requires:
    - readable MATPOWER-style JSON input
    - deterministic parser behavior
  preferred_tools:
    - json loader
    - numpy arrays with explicit dtype control
    - explicit mapping dictionaries for non-contiguous bus IDs
  risks:
    - assuming bus IDs are contiguous 0..N-1
    - column misalignment across bus/gen/branch matrices
    - MW/MVAr/MVA vs per-unit confusion at parse boundary
    - dropping optional-but-task-relevant reserve/cost fields
  examples:
    - input: Large PGLib-style network.json for AC OPF benchmark task.
      expected_behavior: produce complete, index-safe parsed artifact with validated dimensions and units.
---

# Stage Contract

## Input Artifact
- Raw `network.json` in MATPOWER-style structure.

## Output Artifact
- `network_parsed` with deterministic keys:
  - `baseMVA`
  - `bus`, `gen`, `branch`, `gencost`
  - reserve fields when present (`reserve_capacity`, `reserve_requirement`)
  - `bus_id_to_idx` and inverse mapping if needed
  - quick integrity summary (counts + essential dimension checks)

## Handoff Rule to Branch + NLP Stages
- Downstream stages must consume mapped indices, not raw bus numbers.
- `baseMVA` is authoritative for unit conversion boundaries.
- Missing required arrays/columns is a hard-stop parse failure, not a warning.

# Execution Guidance

1. Parse whole JSON with a structured loader (no line-wise scanning).
2. Materialize arrays with stable numeric dtype and documented column ordering.
3. Build explicit bus-ID mappings before constructing any derived indices.
4. Validate row counts and cross-links:
   - generator bus IDs exist in bus table
   - branch endpoint IDs exist in bus table
5. Preserve reserve/cost structures needed by optimization stage.
6. Keep raw power values in source units; define explicit conversion points to per-unit via `baseMVA`.

# Deterministic Pre-Handoff Checks (Required)

- Structure checks:
  - required top-level keys exist
  - array shapes are non-empty where required
- Index checks:
  - all generator/branch bus references resolve through `bus_id_to_idx`
  - mapping is one-to-one for unique bus numbers
- Unit checks:
  - `baseMVA` exists and is positive
  - conversion helpers produce finite outputs for representative fields
- Completeness checks:
  - parser summary includes bus/gen/branch counts
  - downstream-required fields are present and typed

# Common Failure Modes

- Using row index as bus ID without mapping.
- Quietly accepting malformed references and deferring failure to solver stage.
- Converting some fields to per-unit while leaving coupled fields in MW/MVAr without annotation.
- Dropping reserve/cost information needed for objective/constraint completeness.