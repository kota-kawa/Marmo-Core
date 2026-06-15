import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { PrismaAdapter } from "@auth/prisma-adapter";
import { compare } from "bcryptjs";
import { z } from "zod";
import type { Role } from "@prisma/client";
import { prisma } from "@/lib/prisma";

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

const authSecret =
  process.env.AUTH_SECRET ??
  (process.env.NODE_ENV === "development" ? "local-dev-insecure-secret" : undefined);
const normalizedAuthUrl =
  process.env.NODE_ENV === "development" &&
  process.env.AUTH_URL &&
  process.env.AUTH_URL.includes("vercel.app")
    ? "http://localhost:3000"
    : process.env.AUTH_URL;

if (normalizedAuthUrl) {
  process.env.AUTH_URL = normalizedAuthUrl;
  process.env.NEXTAUTH_URL = normalizedAuthUrl;
}

const hasDatabaseConfig = Boolean(process.env.DATABASE_URL && process.env.DIRECT_URL);
const devFallbackEmail = process.env.ADMIN_SEED_EMAIL?.trim().toLowerCase() ?? "admin@example.com";
const devFallbackPassword = process.env.ADMIN_SEED_PASSWORD ?? "dev-password-1234";

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: hasDatabaseConfig ? PrismaAdapter(prisma) : undefined,
  secret: authSecret,
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/sign-in",
  },
  providers: [
    Credentials({
      name: "Email and Password",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      authorize: async (credentials) => {
        const parsed = credentialsSchema.safeParse(credentials);
        if (!parsed.success) return null;

        if (!hasDatabaseConfig && process.env.NODE_ENV === "development") {
          const matchesEmail = parsed.data.email.toLowerCase().trim() === devFallbackEmail;
          const matchesPassword = parsed.data.password === devFallbackPassword;
          if (!matchesEmail || !matchesPassword) return null;
          return {
            id: "local-dev-admin",
            name: process.env.ADMIN_SEED_NAME?.trim() || "Local Admin",
            email: devFallbackEmail,
            role: "ADMIN",
          };
        }

        const email = parsed.data.email.toLowerCase().trim();
        const user = await prisma.user.findUnique({
          where: { email },
        });
        if (!user?.passwordHash) return null;

        const validPassword = await compare(parsed.data.password, user.passwordHash);
        if (!validPassword) return null;

        await prisma.user.update({
          where: { id: user.id },
          data: { lastLoginAt: new Date() },
        });

        return {
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
        };
      },
    }),
  ],
  callbacks: {
    jwt: async ({ token, user }) => {
      if (user) {
        token.role = user.role as Role;
      }
      return token;
    },
    session: async ({ session, token }) => {
      if (session.user) {
        session.user.id = token.sub ?? session.user.id;
        session.user.role = (token.role as Role | undefined) ?? "RESEARCHER";
      }
      return session;
    },
  },
});
