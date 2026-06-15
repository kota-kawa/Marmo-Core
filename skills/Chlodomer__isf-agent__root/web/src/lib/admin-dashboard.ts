import type { Role } from "@prisma/client";

export const ROLE_OPTIONS: Role[] = ["RESEARCHER", "ADMIN"];
export type UserRoleFilter = Role | "ALL";

export const STATUS_MESSAGES: Record<string, string> = {
  "db-not-configured": "Admin data tools require DATABASE_URL and DIRECT_URL to be configured.",
  "role-updated": "Role updated.",
  "password-reset": "Password reset.",
  "user-deleted": "User account deleted.",
  "no-change": "No role change needed.",
  "user-not-found": "User not found.",
  "invalid-request": "Invalid role update request.",
  "invalid-password": "Password must be at least 8 characters.",
  "delete-confirm-mismatch": "Delete confirmation must match the account email.",
  "delete-self-blocked": "You cannot delete your own account.",
  "delete-last-admin-blocked": "Cannot delete the last admin user.",
  "self-demote-blocked": "You cannot remove your own admin role.",
  "last-admin-blocked": "Cannot remove admin role from the last admin user.",
};

export function normalizeParam(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

export function normalizeRoleFilter(input: string | null): UserRoleFilter {
  const value = (input ?? "").trim().toUpperCase();
  if (value === "ADMIN" || value === "RESEARCHER") {
    return value;
  }
  return "ALL";
}

export function describeRoleChange(meta: unknown): string {
  if (!meta || typeof meta !== "object") return "Role updated";

  const data = meta as Record<string, unknown>;
  const fromRole = typeof data.fromRole === "string" ? data.fromRole : null;
  const toRole = typeof data.toRole === "string" ? data.toRole : null;
  const targetEmail = typeof data.targetEmail === "string" ? data.targetEmail : null;

  if (fromRole && toRole && targetEmail) {
    return `${targetEmail}: ${fromRole} -> ${toRole}`;
  }

  return "Role updated";
}

export function describeAccountAudit(action: string, meta: unknown): string {
  if (action === "USER_ROLE_UPDATED") {
    return describeRoleChange(meta);
  }

  if (!meta || typeof meta !== "object") {
    return action;
  }

  const data = meta as Record<string, unknown>;
  const targetEmail = typeof data.targetEmail === "string" ? data.targetEmail : null;
  if (!targetEmail) return action;

  if (action === "USER_PASSWORD_RESET") {
    return `Password reset for ${targetEmail}`;
  }

  if (action === "USER_DELETED") {
    const targetRole = typeof data.targetRole === "string" ? data.targetRole : null;
    return targetRole
      ? `Deleted ${targetEmail} (${targetRole})`
      : `Deleted ${targetEmail}`;
  }

  return action;
}

export type SecurityAlertTone = "critical" | "warning" | "info";

export interface SecurityAlert {
  id: string;
  tone: SecurityAlertTone;
  message: string;
}

interface BuildSecurityAlertsInput {
  adminCount: number;
  usersWithoutLogin: number;
  staleAdmins: number;
  recentRoleChanges: number;
  orphanedRoleAuditLogs: number;
}

export function buildSecurityAlerts(input: BuildSecurityAlertsInput): SecurityAlert[] {
  const alerts: SecurityAlert[] = [];

  if (input.adminCount <= 1) {
    alerts.push({
      id: "single-admin",
      tone: "critical",
      message: "Only one admin account exists. Add a second admin to reduce lockout risk.",
    });
  }

  if (input.staleAdmins > 0) {
    alerts.push({
      id: "stale-admins",
      tone: "warning",
      message: `${input.staleAdmins} admin account(s) have no login in the last 30 days.`,
    });
  }

  if (input.usersWithoutLogin > 0) {
    alerts.push({
      id: "never-logged-in",
      tone: "warning",
      message: `${input.usersWithoutLogin} user account(s) were created but never logged in.`,
    });
  }

  if (input.orphanedRoleAuditLogs > 0) {
    alerts.push({
      id: "orphaned-audit",
      tone: "warning",
      message: `${input.orphanedRoleAuditLogs} role-change audit log(s) are missing actor metadata.`,
    });
  }

  if (input.recentRoleChanges >= 10) {
    alerts.push({
      id: "high-role-change-volume",
      tone: "info",
      message: `${input.recentRoleChanges} role changes occurred in the last 7 days.`,
    });
  }

  if (alerts.length === 0) {
    alerts.push({
      id: "no-security-alerts",
      tone: "info",
      message: "No immediate admin security alerts were detected.",
    });
  }

  return alerts;
}
