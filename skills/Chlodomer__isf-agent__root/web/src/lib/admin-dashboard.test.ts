import {
  buildSecurityAlerts,
  describeAccountAudit,
  describeRoleChange,
  normalizeParam,
  normalizeRoleFilter,
} from "./admin-dashboard";

describe("admin-dashboard helpers", () => {
  it("normalizes search params safely", () => {
    expect(normalizeParam(undefined)).toBeNull();
    expect(normalizeParam(["ADMIN", "RESEARCHER"])).toBe("ADMIN");
    expect(normalizeParam("q")).toBe("q");
  });

  it("normalizes role filter to known values", () => {
    expect(normalizeRoleFilter("ADMIN")).toBe("ADMIN");
    expect(normalizeRoleFilter("researcher")).toBe("RESEARCHER");
    expect(normalizeRoleFilter("super-admin")).toBe("ALL");
    expect(normalizeRoleFilter(null)).toBe("ALL");
  });

  it("renders role change description only for valid metadata", () => {
    expect(
      describeRoleChange({
        targetEmail: "a@example.com",
        fromRole: "RESEARCHER",
        toRole: "ADMIN",
      })
    ).toBe("a@example.com: RESEARCHER -> ADMIN");
    expect(describeRoleChange({ targetEmail: "a@example.com" })).toBe("Role updated");
    expect(describeRoleChange(null)).toBe("Role updated");
  });

  it("renders account audit summaries for password reset and deletion", () => {
    expect(
      describeAccountAudit("USER_PASSWORD_RESET", { targetEmail: "u@example.com" })
    ).toBe("Password reset for u@example.com");
    expect(
      describeAccountAudit("USER_DELETED", {
        targetEmail: "u@example.com",
        targetRole: "RESEARCHER",
      })
    ).toBe("Deleted u@example.com (RESEARCHER)");
  });

  it("returns critical and warning alerts for risky posture", () => {
    const alerts = buildSecurityAlerts({
      adminCount: 1,
      usersWithoutLogin: 5,
      staleAdmins: 2,
      recentRoleChanges: 12,
      orphanedRoleAuditLogs: 1,
    });

    expect(alerts.some((a) => a.id === "single-admin" && a.tone === "critical")).toBe(true);
    expect(alerts.some((a) => a.id === "never-logged-in" && a.tone === "warning")).toBe(true);
    expect(alerts.some((a) => a.id === "high-role-change-volume" && a.tone === "info")).toBe(true);
  });
});
