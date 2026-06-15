import { vi } from "vitest";

const { authMock, getUserWorkspaceExportMock } = vi.hoisted(() => ({
  authMock: vi.fn(),
  getUserWorkspaceExportMock: vi.fn(),
}));

vi.mock("@/auth", () => ({
  auth: authMock,
}));

vi.mock("@/lib/user-data", () => ({
  getUserWorkspaceExport: getUserWorkspaceExportMock,
}));

import { GET } from "./route";

describe("GET /api/export", () => {
  it("rejects unauthenticated requests", async () => {
    authMock.mockResolvedValue(null);

    const response = await GET();
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ error: "Unauthorized." });
  });

  it("returns scoped user export payload", async () => {
    authMock.mockResolvedValue({ user: { id: "user-1" } });
    getUserWorkspaceExportMock.mockResolvedValue({
      user: { id: "user-1", email: "user@example.com" },
      projects: [],
      auditLogs: [],
    });

    const response = await GET();
    expect(response.status).toBe(200);

    const body = await response.json();
    expect(body.scope).toBe("user-owned-data");
    expect(body.user.id).toBe("user-1");
    expect(body.exportedAt).toEqual(expect.any(String));
  });
});
