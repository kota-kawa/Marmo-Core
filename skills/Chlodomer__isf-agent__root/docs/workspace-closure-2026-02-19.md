# Workspace Closure - Curitiba (2026-02-19)

## Status
- Workspace `curitiba` is complete and stable.
- Production login flow is working at `https://isf-agent.vercel.app`.
- Vercel project/settings are aligned for Next.js deployment from `web`.

## What Was Shipped
- Auth foundation with credentials login via Auth.js + Prisma.
- Production auth loop fix by aligning middleware session parsing with Auth.js.
- Deployment runbook for Vercel and env hygiene.
- Server-side owner check for persisted proposal thread access.

## Key Commits On `main`
- `f4eae31` - auth foundation and admin credentials login
- `d63efb4` - sign-in hardening and env/seed guidance
- `78dbcf2` - add `vercel-build` for deployment compatibility
- `bd79a70` - middleware auth parsing fix (resolved sign-in redirect loop)
- `9233a9f` - deployment checklist + handoff link docs
- `08e7705` - enforce owner checks for persisted proposal threads

## Baseline Tag
- `prod-auth-known-good-2026-02-19` (points to `bd79a70`)

## Current Vercel Shape
- Project: `isf-agent`
- Framework Preset: `Next.js`
- Root Directory: `web`
- `AUTH_TRUST_HOST=true` kept in production
- `ADMIN_SEED_*` removed from production scope

## Notes For Next Workspace
- Main chat/proposal history is still stored in browser local storage (device-local), not fully persisted in DB yet.
- Next priority is account recovery/password reset and then server-backed workspace persistence.
- Deployment reference: `docs/DEPLOYMENT.md`
