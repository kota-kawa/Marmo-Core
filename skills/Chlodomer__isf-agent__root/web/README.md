This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Conversational Backend Setup

The chat UI now calls `POST /api/chat` for free-form conversation.
Set the following environment variables before running `npm run dev`:

```bash
export ANTHROPIC_API_KEY="your_claude_api_key_here"
# optional (defaults to claude-sonnet-4-20250514)
export ANTHROPIC_MODEL="claude-sonnet-4-20250514"
```

Without `ANTHROPIC_API_KEY`, the app will still load but conversation requests will return a configuration error.

## Authentication + Database Setup

The app now uses Auth.js + Prisma for multi-user login and role-based access (`RESEARCHER` / `ADMIN`).

1. Copy environment variables:

```bash
cp .env.example .env.local
```

2. Set at minimum:

```bash
DATABASE_URL=postgresql://...
AUTH_SECRET=...
AUTH_URL=http://localhost:3000
ADMIN_SEED_EMAIL=admin@example.com
ADMIN_SEED_PASSWORD=...
ENABLE_LOCAL_ADMIN_SHORTCUT=false
```

3. Generate Prisma client and run migrations:

```bash
npm run prisma:generate
npm run prisma:migrate
```

4. Seed the first admin user:

```bash
npm run db:seed
```

`db:seed` upserts the admin user from `ADMIN_SEED_*`. If you change the admin password in env, run `npm run db:seed` again.

5. Start the app and sign in at `/sign-in`.

Optional local convenience:

- Set `ENABLE_LOCAL_ADMIN_SHORTCUT=true` only in local development to show a one-click "Continue as local admin" button.
- Keep `ENABLE_LOCAL_ADMIN_SHORTCUT=false` for production deployments.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
