import Image from "next/image";
import Link from "next/link";
import { signUpWithCredentials } from "@/app/sign-in/actions";

interface SignUpPageProps {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}

function normalizeParam(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

export default async function SignUpPage({ searchParams }: SignUpPageProps) {
  const params = (await searchParams) ?? {};
  const error = normalizeParam(params.error);
  const callbackUrl = normalizeParam(params.callbackUrl) ?? "/proposal/new";
  const signInUrl = `/sign-in?${new URLSearchParams({ callbackUrl }).toString()}`;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_8%_8%,rgba(186,136,86,0.22),transparent_38%),radial-gradient(circle_at_88%_10%,rgba(95,104,111,0.16),transparent_42%),linear-gradient(180deg,#f8f3eb_0%,#ece3d6_100%)] px-4 py-10">
      <div className="mx-auto w-full max-w-md rounded-2xl border border-[#d8c8b2] bg-white/95 p-7 shadow-[0_30px_60px_-38px_rgba(47,41,36,0.5)]">
        <div className="mb-4 flex items-center gap-3">
          <Image
            src="/granite-logo.png"
            alt="Granite logo"
            width={36}
            height={36}
            className="h-9 w-9 rounded-lg object-cover"
          />
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#6a5642]">Granite</p>
        </div>
        <h1 className="font-display text-2xl font-semibold text-[#2f2924]">Create account</h1>
        <p className="mt-2 text-sm text-[#675646]">
          Sign up with your researcher email to start drafting and reviewing proposals.
        </p>

        {error && (
          <div className="mt-4 rounded-lg border border-[#d7b48b] bg-[#fff4e8] px-3 py-2 text-sm text-[#7f5228]">
            {error}
          </div>
        )}

        <form action={signUpWithCredentials} className="mt-6 space-y-4">
          <input type="hidden" name="callbackUrl" value={callbackUrl} />
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-[#524338]">Full name (optional)</span>
            <input
              type="text"
              name="name"
              autoComplete="name"
              placeholder="Dr. Ada Lovelace"
              className="w-full rounded-lg border border-[#d6c7b5] bg-white px-3 py-2.5 text-base text-[#2f2924] outline-none focus:border-[#ad8459] focus:ring-2 focus:ring-[#d8bb9a]/50"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-[#524338]">Email</span>
            <input
              required
              type="email"
              name="email"
              autoComplete="email"
              placeholder="name@university.edu"
              className="w-full rounded-lg border border-[#d6c7b5] bg-white px-3 py-2.5 text-base text-[#2f2924] outline-none focus:border-[#ad8459] focus:ring-2 focus:ring-[#d8bb9a]/50"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-[#524338]">Password</span>
            <input
              required
              type="password"
              name="password"
              autoComplete="new-password"
              minLength={8}
              className="w-full rounded-lg border border-[#d6c7b5] bg-white px-3 py-2.5 text-base text-[#2f2924] outline-none focus:border-[#ad8459] focus:ring-2 focus:ring-[#d8bb9a]/50"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-[#524338]">Confirm password</span>
            <input
              required
              type="password"
              name="confirmPassword"
              autoComplete="new-password"
              minLength={8}
              className="w-full rounded-lg border border-[#d6c7b5] bg-white px-3 py-2.5 text-base text-[#2f2924] outline-none focus:border-[#ad8459] focus:ring-2 focus:ring-[#d8bb9a]/50"
            />
          </label>
          <button
            type="submit"
            className="w-full rounded-lg bg-[#312a24] px-4 py-2.5 text-base font-semibold text-white transition-colors hover:bg-[#241f1b]"
          >
            Create account
          </button>
        </form>

        <p className="mt-4 text-sm text-[#675646]">
          Already have an account?{" "}
          <Link href={signInUrl} className="font-semibold text-[#4d3d2f] underline underline-offset-2">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
