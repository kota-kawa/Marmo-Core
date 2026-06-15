import {
  SECTION_ORDER,
  type ComplianceIssue,
  type ProjectInfo,
  type ProposalSections,
  type ReferenceSource,
  type Requirements,
  type Resources,
  type ValidationState,
} from "./types";

interface ComplianceInput {
  requirements: Requirements;
  proposalSections: ProposalSections;
  resources: Resources;
  projectInfo: ProjectInfo;
  referenceSources: ReferenceSource[];
}

function hasDraft(value: string | null): boolean {
  return typeof value === "string" && value.trim().length > 0;
}

function wordCount(value: string): number {
  const tokens = value.trim().split(/\s+/).filter(Boolean);
  return tokens.length;
}

function pushIssue(
  list: ComplianceIssue[],
  issue: Omit<ComplianceIssue, "severity">,
  severity: ComplianceIssue["severity"]
) {
  list.push({ ...issue, severity });
}

export function runComplianceValidation(input: ComplianceInput): ValidationState {
  const { requirements, proposalSections, resources, projectInfo, referenceSources } = input;
  const passed: string[] = [];
  const failed: ComplianceIssue[] = [];
  const warnings: ComplianceIssue[] = [];
  const manualReview: string[] = [];

  const draftedSections = SECTION_ORDER.filter((sectionName) =>
    hasDraft(proposalSections[sectionName].draft)
  );
  const missingSections = SECTION_ORDER.filter(
    (sectionName) => !draftedSections.includes(sectionName)
  );

  if (missingSections.length === 0) {
    passed.push("All core proposal sections contain draft content.");
  } else {
    pushIssue(
      failed,
      {
        id: "STRUCT-01",
        category: "Structure",
        name: "Missing Draft Sections",
        description: `Missing draft content in: ${missingSections.join(", ")}.`,
        fix: "Draft all core sections before final submission.",
      },
      "failed"
    );
  }

  if (requirements.requiredSections.length > 0) {
    const requiredSet = new Set(requirements.requiredSections.map((name) => name.toLowerCase()));
    const presentSet = new Set(
      draftedSections.map((sectionName) => sectionName.toLowerCase())
    );
    const missingRequired = [...requiredSet].filter((required) => !presentSet.has(required));

    if (missingRequired.length === 0) {
      passed.push("Configured required sections are covered.");
    } else {
      pushIssue(
        failed,
        {
          id: "STRUCT-02",
          category: "Structure",
          name: "Required Sections Coverage",
          description: `Required sections not yet covered: ${missingRequired.join(", ")}.`,
          fix: "Add missing required sections or update requirement mapping.",
        },
        "failed"
      );
    }
  }

  if (hasDraft(proposalSections.abstract.draft)) {
    const draft = proposalSections.abstract.draft ?? "";
    const count = proposalSections.abstract.wordCount ?? wordCount(draft);
    if (count <= 300) {
      passed.push("Abstract length is within 300 words.");
    } else {
      pushIssue(
        failed,
        {
          id: "LENGTH-01",
          category: "Length",
          name: "Abstract Length",
          description: `Abstract has ${count} words. Maximum is 300 words.`,
          fix: "Reduce abstract length while preserving aims and impact.",
        },
        "failed"
      );
    }
  }

  if (requirements.pageLimits.background && proposalSections.background.pageCount) {
    if (proposalSections.background.pageCount <= requirements.pageLimits.background) {
      passed.push("Background section is within page limit.");
    } else {
      pushIssue(
        failed,
        {
          id: "LENGTH-02",
          category: "Length",
          name: "Background Page Limit",
          description: `Background section uses ${proposalSections.background.pageCount} pages. Limit is ${requirements.pageLimits.background}.`,
          fix: "Compress background rationale and move detailed material to methods.",
        },
        "failed"
      );
    }
  }

  if (requirements.pageLimits.methods && proposalSections.methods.pageCount) {
    if (proposalSections.methods.pageCount <= requirements.pageLimits.methods) {
      passed.push("Methods section is within page limit.");
    } else {
      pushIssue(
        failed,
        {
          id: "LENGTH-03",
          category: "Length",
          name: "Methods Page Limit",
          description: `Methods section uses ${proposalSections.methods.pageCount} pages. Limit is ${requirements.pageLimits.methods}.`,
          fix: "Move less critical protocol details to appendices and keep main flow concise.",
        },
        "failed"
      );
    }
  }

  if (proposalSections.bibliography.entries.length > 0) {
    passed.push("Bibliography contains references.");
  } else {
    pushIssue(
      failed,
      {
        id: "CITE-01",
        category: "Citations",
        name: "Bibliography Missing",
        description: "No bibliography entries detected.",
        fix: "Add at least core citations for each aim and method.",
      },
      "failed"
    );
  }

  const annualMaximum = requirements.budget.annualMaximum;
  const totalMaximum = requirements.budget.totalMaximum;
  const yearTotals = [
    resources.budgetTotals.year1,
    resources.budgetTotals.year2,
    resources.budgetTotals.year3,
    resources.budgetTotals.year4,
  ];

  if (annualMaximum) {
    const violatedYear = yearTotals.findIndex(
      (value) => typeof value === "number" && value > annualMaximum
    );
    if (violatedYear === -1) {
      passed.push("Annual budget totals are within limit.");
    } else {
      const value = yearTotals[violatedYear] as number;
      pushIssue(
        failed,
        {
          id: "BUDGET-01",
          category: "Budget",
          name: "Annual Maximum",
          description: `Year ${violatedYear + 1} budget is ${value}. Maximum is ${annualMaximum}.`,
          fix: "Rebalance staffing, equipment, and consumables for that year.",
        },
        "failed"
      );
    }
  } else {
    manualReview.push("Annual budget maximum is not configured.");
  }

  if (totalMaximum && resources.budgetTotals.total) {
    if (resources.budgetTotals.total <= totalMaximum) {
      passed.push("Total budget is within configured cap.");
    } else {
      pushIssue(
        failed,
        {
          id: "BUDGET-02",
          category: "Budget",
          name: "Total Budget Cap",
          description: `Total budget is ${resources.budgetTotals.total}. Maximum is ${totalMaximum}.`,
          fix: "Reduce total requested amount or adjust project scope.",
        },
        "failed"
      );
    }
  }

  const completeAims = projectInfo.aims.filter(
    (aim) => hasDraft(aim.title) && (hasDraft(aim.hypothesis) || hasDraft(aim.approach))
  );

  if (completeAims.length >= 2) {
    passed.push("At least two complete aims are documented.");
  } else {
    pushIssue(
      warnings,
      {
        id: "AIMS-01",
        category: "Scientific Plan",
        name: "Aim Completeness",
        description:
          "Fewer than two aims have both a title and a hypothesis/approach.",
        fix: "Define at least two standalone aims with measurable outcomes.",
      },
      "warning"
    );
  }

  if (referenceSources.length > 0) {
    passed.push("Source library includes uploaded research references.");
  } else {
    pushIssue(
      warnings,
      {
        id: "EVID-01",
        category: "Evidence",
        name: "No Source Pack",
        description:
          "No source files are attached. Responses may rely on general knowledge only.",
        fix: "Upload papers, prior grants, or reviewer notes to ground claims.",
      },
      "warning"
    );
  }

  if (!requirements.formatting.font || !requirements.formatting.margins || !requirements.formatting.fileFormat) {
    manualReview.push("Formatting requirements are partially missing. Verify font, margins, and file format manually.");
  }

  return {
    lastRun: new Date().toISOString(),
    passed,
    failed,
    warnings,
    manualReview,
    readyForSubmission: failed.length === 0 && missingSections.length === 0,
  };
}
