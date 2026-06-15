# ISF Personal Research Grant Proposal (FUNDED)

**Title:** Neural Mechanisms of Value-Based Decision Making Under Uncertainty: A Computational Approach

**PI:** Dr. Michael Levy (Fictional)
**Institution:** Hebrew University of Jerusalem (Fictional Example)
**Submission Year:** 2023
**Score:** 92/100

---

## Scientific Abstract

How do humans make decisions when outcomes are uncertain? Despite extensive research, the computational mechanisms by which the brain integrates value and probability information remain poorly understood. This proposal addresses this gap by combining behavioral experiments, computational modeling, and neuroimaging to characterize the neural circuits underlying value-based decision making under uncertainty.

We propose three specific aims: (1) Develop and validate a novel behavioral paradigm that dissociates value from probability processing, (2) Use computational modeling to identify the algorithms underlying individual differences in decision making, and (3) Apply model-based fMRI to localize these computations in the brain.

Our preliminary data from 45 participants demonstrates that our paradigm reliably captures individual differences in risk preferences (ICC = 0.78) and identifies distinct computational strategies. This research will advance theoretical understanding of decision making and has implications for disorders characterized by impaired decision making, including addiction and anxiety disorders.

---

## Scientific Background

### 1. The Challenge of Decisions Under Uncertainty

Every day, humans make decisions with uncertain outcomes—from career choices to medical decisions. Understanding how the brain computes and compares uncertain values is fundamental to cognitive neuroscience and has implications for economics, psychiatry, and public policy (Glimcher & Fehr, 2014).

### 2. Current State of Knowledge

Significant progress has established that decisions under uncertainty involve the integration of value and probability information (Tversky & Kahneman, 1992). Neuroimaging studies have implicated the ventromedial prefrontal cortex (vmPFC) in value computation and the anterior insula in processing uncertainty (Levy & Glimcher, 2012). However, critical questions remain unanswered.

### 3. The Gap: Computational Mechanisms Remain Unclear

Despite identifying relevant brain regions, we lack understanding of *how* these regions compute decisions. Current studies typically correlate neural activity with choice outcomes but do not test specific computational hypotheses. This "algorithmic gap" (Marr, 1982) limits both theoretical advancement and clinical translation.

Three specific limitations motivate this proposal:

1. **Task limitations**: Existing paradigms confound value and probability manipulations
2. **Model limitations**: Few studies compare competing computational models
3. **Individual differences**: Most studies average across participants, obscuring meaningful variation

### 4. Our Approach

This proposal addresses these limitations through three innovations:

1. **Novel paradigm**: We have developed a task that orthogonally manipulates value and probability, allowing precise isolation of each component (see Preliminary Data)

2. **Model comparison**: We will formally compare 6 computational models using Bayesian model selection, moving beyond correlation to mechanism

3. **Individual differences**: Our large sample (N=120) and model-based approach will characterize the sources of individual variation in decision strategies

### 5. Preliminary Data

We have conducted a pilot study (N=45) demonstrating feasibility:

**Study 1**: Paradigm Validation (N=25)
- Task reliably dissociates value (β=0.72, p<.001) from probability (β=0.68, p<.001) effects
- Test-retest reliability: ICC=0.78 for risk preference parameters
- Mean accuracy: 94% on comprehension checks

**Study 2**: Computational Modeling (N=20)
- Bayesian model comparison identified three distinct computational subtypes
- Best-fitting model (Prospect Theory variant) outperformed expected utility (BF>100)
- Individual model parameters predict self-reported risk-taking (r=0.54, p<.02)

These results demonstrate that our paradigm and modeling approach are feasible and sensitive.

---

## Research Objectives and Expected Significance

### Primary Objective
To characterize the computational and neural mechanisms underlying value-based decision making under uncertainty.

### Significance
This research will:
1. Resolve competing theories of how the brain computes value under uncertainty
2. Identify neural substrates of specific computations (not just correlates of choice)
3. Explain individual differences in decision making with mechanistic precision
4. Provide a foundation for understanding decision-making pathologies

---

## Specific Aims

### Aim 1: Validate and Extend the Behavioral Paradigm (Months 1-18)

**Rationale**: A robust paradigm is essential for interpretable neuroimaging. We will validate our task in a larger sample and extend it to include social and temporal uncertainty variants.

**Hypothesis**: Value and probability will show dissociable effects on choice, replicating and extending our pilot findings.

**Approach**:
- Recruit 120 participants for behavioral testing
- Administer the decision paradigm (180 trials, ~40 minutes)
- Include three paradigm variants: monetary, social, temporal
- Collect individual difference measures (personality, cognitive ability)

**Expected Outcomes**:
- Replicated paradigm validity
- Extended generalizability across uncertainty types
- Individual difference predictors identified

**Potential Pitfalls and Alternatives**:
If test-retest reliability drops in the larger sample (unlikely given pilot ICC=0.78), we will extend the paradigm to 240 trials based on reliability modeling.

*Even if subsequent aims face obstacles, this aim will produce a validated paradigm and comprehensive behavioral dataset valuable for the field.*

---

### Aim 2: Compare Computational Models of Decision Making (Months 6-30)

**Rationale**: Multiple computational models can explain average behavior. Model comparison in individual participants will identify which algorithms the brain actually implements.

**Hypothesis**: Individual differences in decision making reflect different computational strategies, identifiable through model comparison.

**Approach**:
- Fit 6 candidate models to individual participant data:
  1. Expected Value
  2. Expected Utility (risk-averse)
  3. Expected Utility (risk-seeking)
  4. Prospect Theory (standard)
  5. Prospect Theory (individual parameters)
  6. Reference-dependent model
- Use Bayesian model comparison (bridge sampling)
- Classify participants by best-fitting model
- Validate classifications with out-of-sample prediction

**Expected Outcomes**:
- Quantified evidence for each model
- Participant classification by computational strategy
- Individual parameter estimates for neuroimaging

**Potential Pitfalls and Alternatives**:
If no single model dominates, this itself is informative—it suggests hybrid strategies. We have prepared a model averaging approach for this scenario.

*Even if Aim 1 paradigm extensions fail, this aim uses the validated monetary paradigm and will produce computational insights.*

---

### Aim 3: Identify Neural Substrates Using Model-Based fMRI (Months 12-42)

**Rationale**: Model-based fMRI links computational variables to neural activity, moving beyond brain mapping to mechanism.

**Hypothesis**: Value computation will localize to vmPFC; probability computation to anterior insula; integration to dorsolateral prefrontal cortex.

**Approach**:
- Scan 60 participants (subset of Aim 1 sample) during decision task
- Extract computational variables from individual best-fit models (Aim 2)
- Correlate trial-by-trial model variables with BOLD signal
- Compare neural representations across computational subtypes

**Expected Outcomes**:
- Neural localization of value vs. probability computations
- Evidence for shared vs. distinct neural mechanisms across subtypes
- Computational-neural mapping for decision making

**Potential Pitfalls and Alternatives**:
If behavioral subtypes show identical neural patterns, this suggests that different algorithms are implemented by the same neural architecture—an important finding for theories of neural computation.

*This aim depends on Aims 1-2 but has multiple interpretable outcomes regardless of the specific results.*

---

## Research Plan and Methods

### Participants

**Sample Size Justification**:
- Aim 1: N=120 provides 90% power to detect medium effects (d=0.5) in individual differences analyses (calculated using G*Power)
- Aim 3: N=60 provides 80% power to detect medium correlations (r=0.35) between model parameters and neural activity, based on meta-analysis of model-based fMRI studies (Wilson & Niv, 2015)

**Recruitment**: Participants will be recruited from the university community and through social media. Based on our pilot, we expect to screen 150 to enroll 120 (20% exclusion for attention/comprehension).

**Inclusion Criteria**: Age 18-35, normal or corrected vision, right-handed (for fMRI), no psychiatric history.

### Behavioral Paradigm

**Task Structure**:
- 180 trials per session
- Each trial: See options → Deliberate (2-4s) → Choose → Outcome feedback
- Orthogonal manipulation: Value (3 levels) × Probability (3 levels) × Domain (3 types)
- Compensation: Flat rate + bonus based on 5 randomly selected trials

**Measures**:
- Choice data (RT, selection)
- Eye tracking (subset, N=40) to measure information sampling
- Post-task questionnaires (risk attitudes, decision style)

### Computational Modeling

**Model Fitting**:
- Maximum likelihood estimation with softmax choice rule
- Hierarchical Bayesian estimation for group-level inference
- Model comparison via WAIC and bridge sampling

**Software**: All modeling in R (brms package) and Stan. Code will be publicly available.

### fMRI Protocol

**Acquisition**:
- 3T Siemens Prisma scanner
- T2*-weighted EPI: TR=2000ms, TE=30ms, 3mm isotropic
- 300 volumes per run, 2 runs

**Analysis**:
- Preprocessing: SPM12 standard pipeline
- GLM with model-derived parametric modulators
- ROI analysis: vmPFC, anterior insula, dlPFC (defined from Neurosynth)
- Whole-brain analysis with FWE correction (p<.05)

### Timeline

| Milestone | Y1 | Y2 | Y3 | Y4 |
|-----------|:--:|:--:|:--:|:--:|
| Paradigm validation (N=60) | ██ | | | |
| Full behavioral sample (N=120) | ██ | ██ | | |
| Computational modeling | | ██ | ██ | |
| fMRI data collection (N=60) | | ██ | ██ | |
| fMRI analysis | | | ██ | ██ |
| Manuscripts and dissemination | | ██ | ██ | ██ |

**Year-by-Year Summary**:
- **Year 1**: Paradigm validation, begin full recruitment, establish modeling pipeline
- **Year 2**: Complete behavioral testing, computational modeling, begin fMRI
- **Year 3**: Complete fMRI, integrated analysis, first manuscripts
- **Year 4**: Complete analyses, manuscripts, conference presentations

---

## Innovation

This proposal is innovative in three key ways:

1. **Methodological**: Novel paradigm that dissociates value from probability—previous tasks confounded these variables

2. **Analytical**: Model comparison approach tests *which* algorithms the brain uses, not just *where* activity occurs

3. **Individual differences**: Focus on computational subtypes rather than group averages reveals mechanistically meaningful variation

---

## Risk Assessment and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Recruitment slower than planned | Medium | Medium | Multiple recruitment channels; university + online |
| Paradigm reliability lower in larger sample | Low | High | Pre-registered stopping rule; paradigm extension protocol ready |
| No clear winning model | Medium | Low | Model averaging approach prepared; heterogeneity is itself informative |
| fMRI scanner downtime | Low | Medium | Flexible timeline; backup slots reserved |

---

## Budget

| Category | Year 1 | Year 2 | Year 3 | Year 4 | Total |
|----------|--------|--------|--------|--------|-------|
| Personnel | 120,000 | 140,000 | 140,000 | 100,000 | 500,000 |
| fMRI scanning | - | 80,000 | 60,000 | - | 140,000 |
| Participant compensation | 40,000 | 50,000 | 30,000 | - | 120,000 |
| Equipment | 30,000 | - | - | - | 30,000 |
| Miscellaneous | 15,000 | 15,000 | 15,000 | 15,000 | 60,000 |
| **Total** | 205,000 | 285,000 | 245,000 | 115,000 | 850,000 |

### Budget Justification

**Personnel (500,000 NIS)**:
- PhD student (100%, Years 1-4): Primary data collection, modeling. Candidate identified with computational background. 80,000/year.
- Research assistant (50%, Years 1-3): Participant scheduling, data management, fMRI assistance. 40,000/year.
- Postdoctoral researcher (50%, Years 2-3): Advanced modeling, manuscript preparation. Expertise in Bayesian methods required. 60,000/year.

**fMRI Scanning (140,000 NIS)**:
- 60 participants × 2 sessions × 1,000 NIS/session = 120,000 NIS
- Pilot scanning and technical development: 20,000 NIS

**Participant Compensation (120,000 NIS)**:
- Behavioral: 120 participants × 100 NIS = 12,000 NIS
- Eye tracking subset: 40 participants × 150 NIS = 6,000 NIS
- fMRI: 60 participants × 2 sessions × 300 NIS = 36,000 NIS
- Additional bonus payments based on task performance: ~66,000 NIS

**Equipment (30,000 NIS)**:
- Eye tracker upgrade for precise gaze measurement: 25,000 NIS
- Computer peripherals for behavioral testing: 5,000 NIS

**Miscellaneous (60,000 NIS)**:
- Conference travel for student presentations: 4,000/year
- Publication fees (open access): 3,000/year
- Software licenses: 2,000/year
- Office supplies and printing: 6,000/year

---

## References

Glimcher, P. W., & Fehr, E. (2014). Neuroeconomics: Decision making and the brain. Academic Press.

Levy, D. J., & Glimcher, P. W. (2012). The root of all value: a neural common currency for choice. Current Opinion in Neurobiology, 22(6), 1027-1038.

Marr, D. (1982). Vision: A computational investigation. MIT Press.

Tversky, A., & Kahneman, D. (1992). Advances in prospect theory: Cumulative representation of uncertainty. Journal of Risk and Uncertainty, 5(4), 297-323.

Wilson, R. C., & Niv, Y. (2015). Is model fitting necessary for model-based fMRI? PLoS Computational Biology, 11(6), e1004237.

---

*This is a synthetic example created for educational purposes. It demonstrates grant writing best practices.*

## EMBEDDED STRENGTHS (For Instructor Reference)

This proposal demonstrates the following best practices:

1. **Clear power analysis**: Specific sample sizes with justification and software used
2. **Named statistical methods**: Bayesian model comparison, WAIC, bridge sampling, FWE correction
3. **Independent aims**: Each aim produces value even if others face obstacles
4. **Strong preliminary data**: N=45, specific statistics (ICC=0.78, BF>100)
5. **Explicit contingencies**: Each aim has "potential pitfalls and alternatives"
6. **Realistic timeline**: Work distributed across years, not front-loaded
7. **Specific abstract**: Conveys gap, approach, and expected contribution
8. **Detailed budget justification**: Each item tied to specific project needs
9. **Innovation clearly articulated**: Three specific innovations named
10. **Active control addressed**: Design explicitly separates value and probability
11. **Model comparison**: Tests competing theories, not just one hypothesis
12. **Reproducibility**: Code sharing mentioned, software specified
