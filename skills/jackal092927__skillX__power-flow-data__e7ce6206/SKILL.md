---
skillx:
  name: power-flow-data
  purpose: Parse the MATPOWER-style network data correctly so the AC OPF model uses the right buses, generators, branches, costs, and per-unit scaling.
  scope_in:
    - loading and summarizing network.json
    - building bus-number to index mappings
    - identifying bus, generator, branch, and reserve fields correctly
  scope_out:
    - not for solving the optimization by itself
    - not for approximating away AC network structure
    - not for manual line-by-line inspection of huge JSON files
  requires:
    - readable network.json
    - JSON parsing support
    - consistent baseMVA handling
  preferred_tools:
    - json
    - numpy
    - explicit bus-id mapping dictionaries
  risks:
    - assuming bus numbering is contiguous
    - mixing MW/MVAr/MVA with per-unit values
    - misreading branch or generator columns
  examples:
    - input: Load a large MATPOWER-style network and prepare data structures for AC OPF modeling.
      expected_behavior: parse the arrays safely, map buses correctly, and expose the data needed for equations and solver setup.
---

# Guidance

Get the data model right before touching the optimizer.
The downstream AC OPF will be wrong if:
- bus numbering is misindexed
- baseMVA conversions are inconsistent
- branch or generator fields are misread

Parse with a JSON loader, summarize the network quickly, and build explicit bus mappings.

# Notes for Agent

This skill establishes the ground truth data interface for the whole task.

