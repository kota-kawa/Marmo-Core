import type { Prisma, Role } from "@prisma/client";
import { hash } from "bcryptjs";
import Link from "next/link";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";
import {
  ROLE_OPTIONS,
  STATUS_MESSAGES,
  buildSecurityAlerts,
  describeAccountAudit,
  normalizeParam,
  normalizeRoleFilter,
  type SecurityAlertTone,
} from "@/lib/admin-dashboard";

export const dynamic = "force-dynamic";
const MIN_PASSWORD_LENGTH = 8;
const hasDatabaseConfig = Boolean(process.env.DATABASE_URL && process.env.DIRECT_URL);

interface AdminPageProps {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}

function roleToneClass(tone: SecurityAlertTone): string {
  if (tone === "critical") return "border-red-300 bg-red-50 text-red-800";
  if (tone === "warning") return "border-amber-300 bg-amber-50 text-amber-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

async function updateUserRole(formData: FormData) {
  "use server";

  const session = await auth();
  if (!session?.user) {
    redirect("/sign-in");
  }
  if (session.user.role !== "ADMIN" || !session.user.id) {
    redirect("/proposal/new");
  }
  if (!hasDatabaseConfig) {
    redirect("/admin?status=db-not-configured");
  }

  const actorUserId = session.user.id;
  const targetUserId = String(formData.get("userId") ?? "").trim();
  const requestedRole = String(formData.get("role") ?? "").trim().toUpperCase();
  const nextRole =
    requestedRole === "ADMIN" || requestedRole === "RESEARCHER"
      ? (requestedRole as Role)
      : null;

  if (!targetUserId || !nextRole) {
    redirect("/admin?status=invalid-request");
  }

  const targetUser = await prisma.user.findUnique({
    where: { id: targetUserId },
    select: {
      id: true,
      email: true,
      role: true,
    },
  });

  if (!targetUser) {
    redirect("/admin?status=user-not-found");
  }

  if (targetUser.id === actorUserId && nextRole !== "ADMIN") {
    redirect("/admin?status=self-demote-blocked");
  }

  if (targetUser.role === nextRole) {
    redirect("/admin?status=no-change");
  }

  if (targetUser.role === "ADMIN" && nextRole !== "ADMIN") {
    const adminCount = await prisma.user.count({
      where: { role: "ADMIN" },
    });
    if (adminCount <= 1) {
      redirect("/admin?status=last-admin-blocked");
    }
  }

  await prisma.$transaction([
    prisma.user.update({
      where: { id: targetUser.id },
      data: { role: nextRole },
    }),
    prisma.auditLog.create({
      data: {
        actorUserId,
        action: "USER_ROLE_UPDATED",
        entityType: "User",
        entityId: targetUser.id,
        meta: {
          targetEmail: targetUser.email,
          fromRole: targetUser.role,
          toRole: nextRole,
        },
      },
    }),
  ]);

  revalidatePath("/admin");
  redirect("/admin?status=role-updated");
}

async function resetUserPassword(formData: FormData) {
  "use server";

  const session = await auth();
  if (!session?.user) {
    redirect("/sign-in");
  }
  if (session.user.role !== "ADMIN" || !session.user.id) {
    redirect("/proposal/new");
  }
  if (!hasDatabaseConfig) {
    redirect("/admin?status=db-not-configured");
  }

  const actorUserId = session.user.id;
  const targetUserId = String(formData.get("userId") ?? "").trim();
  const nextPassword = String(formData.get("newPassword") ?? "");

  if (!targetUserId) {
    redirect("/admin?status=invalid-request");
  }
  if (nextPassword.length < MIN_PASSWORD_LENGTH) {
    redirect("/admin?status=invalid-password");
  }

  const targetUser = await prisma.user.findUnique({
    where: { id: targetUserId },
    select: { id: true, email: true },
  });
  if (!targetUser) {
    redirect("/admin?status=user-not-found");
  }

  const passwordHash = await hash(nextPassword, 10);
  await prisma.$transaction([
    prisma.user.update({
      where: { id: targetUser.id },
      data: { passwordHash },
    }),
    prisma.auditLog.create({
      data: {
        actorUserId,
        action: "USER_PASSWORD_RESET",
        entityType: "User",
        entityId: targetUser.id,
        meta: {
          targetEmail: targetUser.email,
        },
      },
    }),
  ]);

  revalidatePath("/admin");
  redirect("/admin?status=password-reset");
}

async function deleteUserAccount(formData: FormData) {
  "use server";

  const session = await auth();
  if (!session?.user) {
    redirect("/sign-in");
  }
  if (session.user.role !== "ADMIN" || !session.user.id) {
    redirect("/proposal/new");
  }
  if (!hasDatabaseConfig) {
    redirect("/admin?status=db-not-configured");
  }

  const actorUserId = session.user.id;
  const targetUserId = String(formData.get("userId") ?? "").trim();
  const confirmEmail = String(formData.get("confirmEmail") ?? "")
    .trim()
    .toLowerCase();

  if (!targetUserId) {
    redirect("/admin?status=invalid-request");
  }

  const targetUser = await prisma.user.findUnique({
    where: { id: targetUserId },
    select: { id: true, email: true, role: true },
  });
  if (!targetUser) {
    redirect("/admin?status=user-not-found");
  }

  if (targetUser.id === actorUserId) {
    redirect("/admin?status=delete-self-blocked");
  }

  if (confirmEmail !== targetUser.email.toLowerCase()) {
    redirect("/admin?status=delete-confirm-mismatch");
  }

  if (targetUser.role === "ADMIN") {
    const adminCount = await prisma.user.count({
      where: { role: "ADMIN" },
    });
    if (adminCount <= 1) {
      redirect("/admin?status=delete-last-admin-blocked");
    }
  }

  await prisma.$transaction([
    prisma.auditLog.create({
      data: {
        actorUserId,
        action: "USER_DELETED",
        entityType: "User",
        entityId: targetUser.id,
        meta: {
          targetEmail: targetUser.email,
          targetRole: targetUser.role,
        },
      },
    }),
    prisma.user.delete({
      where: { id: targetUser.id },
    }),
  ]);

  revalidatePath("/admin");
  redirect("/admin?status=user-deleted");
}

export default async function AdminPage({ searchParams }: AdminPageProps) {
  const session = await auth();
  if (!session?.user) {
    redirect("/sign-in");
  }
  if (session.user.role !== "ADMIN") {
    redirect("/proposal/new");
  }

  const params = (await searchParams) ?? {};
  const status = normalizeParam(params.status);
  const query = normalizeParam(params.q)?.trim() ?? "";
  const roleFilter = normalizeRoleFilter(normalizeParam(params.role));
  const statusMessage = status ? STATUS_MESSAGES[status] : null;

  if (!hasDatabaseConfig) {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-8">
        <div className="mx-auto max-w-4xl space-y-6">
          <header className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">Admin Console</h1>
              <p className="mt-1 text-sm text-slate-600">Operational tools and account management.</p>
            </div>
            <Link
              href="/proposal/new"
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back to workspace
            </Link>
          </header>

          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            {statusMessage ?? STATUS_MESSAGES["db-not-configured"]}
          </section>
        </div>
      </main>
    );
  }

  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const userWhere: Prisma.UserWhereInput = {};
  if (query) {
    userWhere.OR = [
      { email: { contains: query, mode: "insensitive" } },
      { name: { contains: query, mode: "insensitive" } },
    ];
  }
  if (roleFilter !== "ALL") {
    userWhere.role = roleFilter;
  }

  const [
    userCount,
    adminCount,
    activeUsers7dCount,
    inactiveUsers30dCount,
    usersWithoutLoginCount,
    recentSignupsCount,
    staleAdminsCount,
    projectCount,
    threadCount,
    messageCount,
    messagesLast7dCount,
    sourceFileCount,
    uploadsLast7dCount,
    complianceReportCount,
    readinessSnapshotCount,
    recentRoleChangeCount,
    passwordResets7dCount,
    deletedUsers30dCount,
    adminActions7dCount,
    orphanedRoleAuditCount,
    users,
    recentAccountAuditLogs,
  ] = await Promise.all([
    prisma.user.count(),
    prisma.user.count({
      where: { role: "ADMIN" },
    }),
    prisma.user.count({
      where: { lastLoginAt: { gte: sevenDaysAgo } },
    }),
    prisma.user.count({
      where: {
        OR: [{ lastLoginAt: null }, { lastLoginAt: { lt: thirtyDaysAgo } }],
      },
    }),
    prisma.user.count({
      where: { lastLoginAt: null },
    }),
    prisma.user.count({
      where: { createdAt: { gte: sevenDaysAgo } },
    }),
    prisma.user.count({
      where: {
        role: "ADMIN",
        OR: [{ lastLoginAt: null }, { lastLoginAt: { lt: thirtyDaysAgo } }],
      },
    }),
    prisma.project.count(),
    prisma.thread.count(),
    prisma.message.count(),
    prisma.message.count({
      where: { createdAt: { gte: sevenDaysAgo } },
    }),
    prisma.sourceFile.count(),
    prisma.sourceFile.count({
      where: { createdAt: { gte: sevenDaysAgo } },
    }),
    prisma.complianceReport.count(),
    prisma.readinessSnapshot.count(),
    prisma.auditLog.count({
      where: {
        action: "USER_ROLE_UPDATED",
        createdAt: { gte: sevenDaysAgo },
      },
    }),
    prisma.auditLog.count({
      where: {
        action: "USER_PASSWORD_RESET",
        createdAt: { gte: sevenDaysAgo },
      },
    }),
    prisma.auditLog.count({
      where: {
        action: "USER_DELETED",
        createdAt: { gte: thirtyDaysAgo },
      },
    }),
    prisma.auditLog.count({
      where: {
        createdAt: { gte: sevenDaysAgo },
      },
    }),
    prisma.auditLog.count({
      where: {
        action: "USER_ROLE_UPDATED",
        actorUserId: null,
      },
    }),
    prisma.user.findMany({
      where: userWhere,
      orderBy: { createdAt: "desc" },
      take: 50,
      select: {
        id: true,
        name: true,
        email: true,
        role: true,
        createdAt: true,
        lastLoginAt: true,
      },
    }),
    prisma.auditLog.findMany({
      where: {
        action: {
          in: ["USER_ROLE_UPDATED", "USER_PASSWORD_RESET", "USER_DELETED"],
        },
      },
      orderBy: { createdAt: "desc" },
      take: 20,
      select: {
        id: true,
        action: true,
        createdAt: true,
        meta: true,
        actor: {
          select: {
            email: true,
          },
        },
      },
    }),
  ]);

  const userIds = users.map((user) => user.id);
  const [projectThreadStats, uploadsByUser, adminActionsByUser] =
    userIds.length > 0
      ? await Promise.all([
          prisma.project.findMany({
            where: { ownerUserId: { in: userIds } },
            select: {
              ownerUserId: true,
              _count: {
                select: {
                  threads: true,
                },
              },
            },
          }),
          prisma.sourceFile.groupBy({
            by: ["uploaderUserId"],
            where: { uploaderUserId: { in: userIds } },
            _count: { _all: true },
          }),
          prisma.auditLog.groupBy({
            by: ["actorUserId"],
            where: { actorUserId: { in: userIds } },
            _count: { _all: true },
          }),
        ])
      : [[], [], []];

  const statsByUserId = new Map<
    string,
    { projects: number; threads: number; uploads: number; adminActions: number }
  >();
  for (const user of users) {
    statsByUserId.set(user.id, {
      projects: 0,
      threads: 0,
      uploads: 0,
      adminActions: 0,
    });
  }

  for (const item of projectThreadStats) {
    const current = statsByUserId.get(item.ownerUserId);
    if (!current) continue;
    current.projects += 1;
    current.threads += item._count.threads;
  }

  for (const item of uploadsByUser) {
    const current = statsByUserId.get(item.uploaderUserId);
    if (!current) continue;
    current.uploads = item._count._all;
  }

  for (const item of adminActionsByUser) {
    if (!item.actorUserId) continue;
    const current = statsByUserId.get(item.actorUserId);
    if (!current) continue;
    current.adminActions = item._count._all;
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Admin Console</h1>
            <p className="mt-1 text-sm text-slate-600">
              Operational overview, security signals, and user role management.
            </p>
          </div>
          <Link
            href="/proposal/new"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Back to workspace
          </Link>
        </header>

        {statusMessage && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
            {statusMessage}
          </div>
        )}

        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <form className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px_auto]">
            <label className="space-y-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Search users
              <input
                type="text"
                name="q"
                defaultValue={query}
                placeholder="email or name"
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-normal text-slate-800"
              />
            </label>

            <label className="space-y-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Role
              <select
                name="role"
                defaultValue={roleFilter}
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-normal text-slate-800"
              >
                <option value="ALL">All roles</option>
                {ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex items-end gap-2">
              <button
                type="submit"
                className="rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
              >
                Apply filters
              </button>
              <a
                href="/admin"
                className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Reset
              </a>
            </div>
          </form>
        </section>

        <section className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Users</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{userCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Projects</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{projectCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Threads</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{threadCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Admins</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{adminCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Active Users (7d)</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{activeUsers7dCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Dormant Users (30d)</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{inactiveUsers30dCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">New Users (7d)</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{recentSignupsCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">No Login Yet</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{usersWithoutLoginCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Messages</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{messageCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Messages (7d)</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{messagesLast7dCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Source Files</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{sourceFileCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Uploads (7d)</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{uploadsLast7dCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Compliance Reports</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{complianceReportCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Readiness Snapshots</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{readinessSnapshotCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Admin Actions (7d)</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{adminActions7dCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Password Resets (7d)</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{passwordResets7dCount}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Account Deletions (30d)</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{deletedUsers30dCount}</p>
          </article>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">Security Signals</h2>
          </div>
          <div className="space-y-2 p-4">
            {buildSecurityAlerts({
              adminCount,
              usersWithoutLogin: usersWithoutLoginCount,
              staleAdmins: staleAdminsCount,
              recentRoleChanges: recentRoleChangeCount,
              orphanedRoleAuditLogs: orphanedRoleAuditCount,
            }).map((alert) => (
              <div
                key={alert.id}
                className={`rounded-lg border px-3 py-2 text-sm ${roleToneClass(alert.tone)}`}
              >
                {alert.message}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">Users</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5">Name</th>
                  <th className="px-4 py-2.5">Email</th>
                  <th className="px-4 py-2.5">Role</th>
                  <th className="px-4 py-2.5">Projects / Threads</th>
                  <th className="px-4 py-2.5">Uploads</th>
                  <th className="px-4 py-2.5">Admin Actions</th>
                  <th className="px-4 py-2.5">Joined</th>
                  <th className="px-4 py-2.5">Last Login</th>
                  <th className="px-4 py-2.5">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-3 text-slate-500">
                      No users found for this filter.
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id} className="text-slate-700">
                      {(() => {
                        const userStats = statsByUserId.get(user.id) ?? {
                          projects: 0,
                          threads: 0,
                          uploads: 0,
                          adminActions: 0,
                        };

                        return (
                          <>
                            <td className="px-4 py-2.5">{user.name || "—"}</td>
                            <td className="px-4 py-2.5">{user.email}</td>
                            <td className="px-4 py-2.5">{user.role}</td>
                            <td className="px-4 py-2.5">
                              {userStats.projects} / {userStats.threads}
                            </td>
                            <td className="px-4 py-2.5">{userStats.uploads}</td>
                            <td className="px-4 py-2.5">{userStats.adminActions}</td>
                            <td className="px-4 py-2.5">{user.createdAt.toLocaleDateString()}</td>
                            <td className="px-4 py-2.5">
                              {user.lastLoginAt
                                ? user.lastLoginAt.toLocaleString()
                                : "No login recorded"}
                            </td>
                            <td className="min-w-[360px] space-y-2 px-4 py-2.5">
                              <form action={updateUserRole} className="flex items-center gap-2">
                                <input type="hidden" name="userId" value={user.id} />
                                <select
                                  name="role"
                                  defaultValue={user.role}
                                  className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
                                >
                                  {ROLE_OPTIONS.map((role) => (
                                    <option key={role} value={role}>
                                      {role}
                                    </option>
                                  ))}
                                </select>
                                <button
                                  type="submit"
                                  className="rounded-md border border-slate-300 bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                                >
                                  Update role
                                </button>
                              </form>

                              <form action={resetUserPassword} className="flex items-center gap-2">
                                <input type="hidden" name="userId" value={user.id} />
                                <input
                                  type="password"
                                  name="newPassword"
                                  minLength={MIN_PASSWORD_LENGTH}
                                  required
                                  placeholder={`New password (min ${MIN_PASSWORD_LENGTH})`}
                                  className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
                                />
                                <button
                                  type="submit"
                                  className="whitespace-nowrap rounded-md border border-blue-300 bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100"
                                >
                                  Reset password
                                </button>
                              </form>

                              <form action={deleteUserAccount} className="flex items-center gap-2">
                                <input type="hidden" name="userId" value={user.id} />
                                <input
                                  type="text"
                                  name="confirmEmail"
                                  required
                                  placeholder="Type email to delete"
                                  className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
                                />
                                <button
                                  type="submit"
                                  className="whitespace-nowrap rounded-md border border-red-300 bg-red-50 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-100"
                                >
                                  Delete account
                                </button>
                              </form>
                            </td>
                          </>
                        );
                      })()}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">Account Activity Audit Log</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5">When</th>
                  <th className="px-4 py-2.5">Action</th>
                  <th className="px-4 py-2.5">Actor</th>
                  <th className="px-4 py-2.5">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentAccountAuditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-3 text-slate-500">
                      No account actions recorded.
                    </td>
                  </tr>
                ) : (
                  recentAccountAuditLogs.map((log) => (
                    <tr key={log.id} className="text-slate-700">
                      <td className="px-4 py-2.5">{log.createdAt.toLocaleString()}</td>
                      <td className="px-4 py-2.5 font-medium">{log.action}</td>
                      <td className="px-4 py-2.5">{log.actor?.email ?? "Unknown actor"}</td>
                      <td className="px-4 py-2.5">{describeAccountAudit(log.action, log.meta)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
