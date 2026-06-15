import { prisma } from "@/lib/prisma";

export async function findOwnedThread(userId: string, threadId: string) {
  return prisma.thread.findFirst({
    where: {
      id: threadId,
      project: {
        ownerUserId: userId,
      },
    },
    select: { id: true },
  });
}

export async function getUserWorkspaceExport(userId: string) {
  const [user, projects, auditLogs] = await Promise.all([
    prisma.user.findUnique({
      where: { id: userId },
      select: {
        id: true,
        name: true,
        email: true,
        role: true,
        createdAt: true,
        lastLoginAt: true,
      },
    }),
    prisma.project.findMany({
      where: { ownerUserId: userId },
      orderBy: { updatedAt: "desc" },
      include: {
        threads: {
          orderBy: { updatedAt: "desc" },
          include: {
            messages: {
              orderBy: { createdAt: "asc" },
            },
          },
        },
        sourceFiles: {
          orderBy: { createdAt: "desc" },
        },
        readiness: {
          orderBy: { createdAt: "desc" },
        },
        compliance: {
          orderBy: { createdAt: "desc" },
        },
      },
    }),
    prisma.auditLog.findMany({
      where: { actorUserId: userId },
      orderBy: { createdAt: "desc" },
      take: 200,
      select: {
        id: true,
        action: true,
        entityType: true,
        entityId: true,
        meta: true,
        createdAt: true,
      },
    }),
  ]);

  return {
    user,
    projects,
    auditLogs,
  };
}
