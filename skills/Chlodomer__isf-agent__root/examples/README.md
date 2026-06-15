# Synthetic Grant Examples

These are **fictional examples** created for educational and demonstration purposes. They show how the grant agent learns from past proposals and reviewer feedback.

---

## Files Included

### Unsuccessful Proposal + Reviews

| File | Description |
|------|-------------|
| `unsuccessful/2024_cognitive_training_rejected.md` | A rejected grant proposal with **12 deliberate weaknesses** |
| `reviews/2024_cognitive_training_reviews.md` | Reviewer feedback highlighting those weaknesses |

**Use these to demonstrate:**
- How the agent detects red flag phrases
- How the agent extracts weaknesses from unsuccessful proposals
- How the agent builds a reviewer concerns database
- The `/learn-from-grant` and `/learn-from-reviews` commands

**Weaknesses embedded in the unsuccessful proposal:**
1. No power analysis ("sufficient to detect effects")
2. Vague statistics ("appropriate statistical methods")
3. Aim interdependence (Aims 2-4 depend on Aim 1)
4. Weak preliminary data (non-significant "trends")
5. Speculation language ("we anticipate" × 4)
6. Front-loaded timeline
7. Vague abstract
8. Missing sample size calculation
9. Passive control group (no active control)
10. Disconnected fMRI aim
11. Unclear innovation
12. Thin budget justification

---

### Successful Proposal

| File | Description |
|------|-------------|
| `successful/2023_decision_making_funded.md` | A funded proposal demonstrating **12 best practices** |

**Use this to demonstrate:**
- How the agent extracts successful patterns
- How the agent applies those patterns to new proposals
- The contrast between good and weak grant writing

**Best practices demonstrated:**
1. Clear power analysis with specific numbers
2. Named statistical methods (Bayesian, WAIC, etc.)
3. Independent aims with standalone value
4. Strong preliminary data (N=45, specific statistics)
5. Explicit contingency plans for each aim
6. Realistic, distributed timeline
7. Specific, informative abstract
8. Detailed budget justification
9. Clear innovation statement
10. Appropriate control conditions
11. Formal model comparison approach
12. Reproducibility practices

---

## How to Use in Workshop

### Demo 1: Learning from Unsuccessful Proposal

```
1. Start the agent: "Help me write an ISF grant"
2. Use: /learn-from-grant
3. Say: "Unsuccessful"
4. Point to: examples/unsuccessful/2024_cognitive_training_rejected.md
5. Watch the agent identify weaknesses
```

### Demo 2: Learning from Reviews

```
1. Use: /learn-from-reviews
2. Point to: examples/reviews/2024_cognitive_training_reviews.md
3. Watch the agent build concerns database
```

### Demo 3: Learning from Successful Proposal

```
1. Use: /learn-from-grant
2. Say: "Successful"
3. Point to: examples/successful/2023_decision_making_funded.md
4. Watch the agent extract patterns
```

### Demo 4: Comparison

```
1. Use: /show-learnings
2. See patterns to replicate vs. weaknesses to avoid
3. Use: /compare when drafting sections
```

---

## Participant Exercise Setup

For the hands-on exercise, participants should:

1. Copy the `examples/` folder to their project
2. Rename folders:
   - `examples/unsuccessful/` → `past-proposals/unsuccessful/`
   - `examples/successful/` → `past-proposals/successful/`
   - `examples/reviews/` → `past-proposals/reviews/`

This gives them a working example without needing their own past proposals.

---

## Note on Realism

These proposals are:
- **Realistic enough** to demonstrate the agent's capabilities
- **Clearly fictional** (fictional PI names, noted as synthetic)
- **Deliberately flawed** (unsuccessful) or **deliberately strong** (successful)
- **Not actual ISF proposals** - used only for educational purposes

---

*Created for the AI Grant Writing Workshop*
