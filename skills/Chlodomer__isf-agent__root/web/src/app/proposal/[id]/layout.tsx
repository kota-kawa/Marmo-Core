import Link from "next/link";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { auth, signOut } from "@/auth";
import { findOwnedThread } from "@/lib/user-data";

const LOCAL_THREAD_ID_PREFIX = "thread-";

export const dynamic = "force-dynamic";

function isLocalThreadId(threadId: string) {
  return threadId.startsWith(LOCAL_THREAD_ID_PREFIX);
}

export default async function ProposalLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }> | { id: string };
}) {
  const session = await auth();
  if (!session?.user) {
    redirect("/sign-in");
  }

  const userId = session.user.id;
  if (!userId) {
    redirect("/sign-in");
  }

  const { id } = await params;
  const isWorkspaceRoot = id === "new";
  if (!isWorkspaceRoot && !isLocalThreadId(id)) {
    const allowedThread = await findOwnedThread(userId, id);

    if (!allowedThread) {
      redirect("/proposal/new");
    }
  }

  const isAdmin = session.user.role === "ADMIN";
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host");
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host?.includes("localhost") ? "http" : "https");
  const adminHref = host ? `${protocol}://${host}/admin` : "/admin";

  async function handleSignOut() {
    "use server";
    await signOut({ redirectTo: "/sign-in" });
  }

  return (
    <div className="min-h-screen lg:h-screen overflow-y-auto lg:overflow-hidden">
      <div className="fixed right-3 top-3 z-[90] flex items-center gap-2 rounded-full border border-slate-300 bg-white/95 px-3 py-1.5 text-xs shadow-sm backdrop-blur-sm">
        <span className="max-w-[220px] truncate text-slate-600">{session.user.email}</span>
        {isAdmin && (
          <Link
            href={adminHref}
            className="rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 font-medium text-slate-700 hover:bg-slate-200"
          >
            Admin
          </Link>
        )}
        <form action={handleSignOut}>
          <button
            type="submit"
            className="rounded-full border border-slate-300 bg-white px-2 py-0.5 font-medium text-slate-700 hover:bg-slate-100"
          >
            Sign out
          </button>
        </form>
      </div>
      {children}
    </div>
  );
}
