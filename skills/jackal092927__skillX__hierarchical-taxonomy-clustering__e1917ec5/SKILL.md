---
skillx:
  name: hierarchical-taxonomy-clustering
  purpose: Build a unified multi-level taxonomy from multi-source hierarchical category paths using recursive clustering, representative naming, and structural quality constraints.
  scope_in:
    - tasks merge hierarchical product category paths from multiple sources into one shared taxonomy
    - the output must be a bounded-depth hierarchy with representative category naming
    - clustering, naming, and structural constraints all matter, not just embedding similarity
  scope_out:
    - not for trivial one-source category cleaning only
    - not for exact mapping into a pre-existing gold taxonomy when a fixed target taxonomy is already given
    - not for open-ended ontology design without concrete category-path inputs
  requires:
    - input files with category_path-like hierarchical text
    - enough compute/memory to build embeddings and cluster at scale
    - libraries for tabular processing, embeddings, clustering, and text normalization
  preferred_tools:
    - pandas
    - sentence-transformers
    - scipy clustering
    - nltk or equivalent text normalization tools
  risks:
    - over-prescriptive clustering choices that do not fit the actual data distribution
    - parent/child name overlap or sibling name collision
    - source imbalance where one platform dominates the unified taxonomy
    - producing clusters that look mathematically tidy but violate representativeness or usability constraints
    - runtime-heavy pipelines that fail before producing valid outputs
  examples:
    - input: unify Amazon, Facebook, and Google Shopping category paths into a five-level shared taxonomy with representative names.
      expected_behavior: standardize paths, build weighted hierarchical representations, cluster recursively, generate distinct names, and export both full assignments and hierarchy outputs.
---

# Guidance

Treat this as a full pipeline task, not just an embedding step.
The output must satisfy both structural and naming constraints.

Recommended flow:
1. standardize and normalize category text across sources
2. split and clean hierarchical levels
3. build weighted representations where higher levels matter more than deeper levels
4. cluster recursively by level rather than collapsing everything into one flat pass
5. generate names from representative terms while excluding ancestor duplication
6. export both record-level assignments and the unique hierarchy

Keep the target constraints visible during implementation:
- top-level category count should stay within the requested range
- deeper levels should remain reasonably bounded
- sibling names should remain distinct
- parent/child names should not collapse into duplicates
- cross-source distribution should remain reasonably balanced

# Notes for Agent

The original skill is technically rich but heavy.
Do not blindly treat every implementation detail as mandatory if the data or runtime makes it brittle.
What matters most is producing a valid, representative, multi-source hierarchy that satisfies the stated task constraints.
