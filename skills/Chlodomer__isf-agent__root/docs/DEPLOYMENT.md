# Deployment Guide (Vercel + Auth)

This is the canonical checklist for deploying `web` to Vercel without auth redirect loops.

## Project Settings

In Vercel project settings:

- Framework Preset: `Next.js`
- Root Directory: `web`
- Build Command: `npm run build`
- Install Command: `npm install`

Do not use legacy Vite settings (for example `frontend/dist`).

## Required Production Env Vars

Set these on the Vercel project for `Production` (or `All Environments` if preferred):

- `DATABASE_URL`
- `AUTH_SECRET`
- `AUTH_URL`
- `AUTH_TRUST_HOST`
- `ANTHROPIC_API_KEY`

Recommended values:

- `AUTH_URL=https://isf-agent.vercel.app`
- `AUTH_TRUST_HOST=true`

Format rules:

- Values only (do not paste `KEY=value` as a value).
- No wrapping quotes.
- No angle brackets.
- `DATABASE_URL` must start with `postgresql://` or `postgres://`.
- If DB password has special characters, URL-encode the password segment.

## Optional / Dev-Only Vars

These are not required for production login flow:

- `ENABLE_LOCAL_ADMIN_SHORTCUT` (keep unset or `false` in production)
- `ADMIN_SEED_EMAIL`
- `ADMIN_SEED_PASSWORD`
- `ADMIN_SEED_NAME`

Use seed vars only when running `npm run db:seed` locally or in controlled environments.

## Redeploy Rule

After changing env vars or project settings, trigger a new deployment.  
Existing deployments do not auto-adopt new settings.

## Validation Checklist

After deployment:

1. Open `https://isf-agent.vercel.app/sign-in` in an incognito window.
2. Sign in with known-good credentials.
3. Confirm redirect lands in proposal workspace (not back on sign-in).
4. If login loops, inspect Vercel runtime logs for `[auth][error]` and Prisma datasource errors.

## Known-Good Baseline

Session loop fix is in commit `bd79a70`:

- middleware switched from manual token parsing to Auth.js `auth(...)` wrapper in `web/src/proxy.ts`.
