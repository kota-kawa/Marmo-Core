# Agent rules — memory-dev

## This is NOT a Next.js project

This project was migrated from Next.js to a standalone CLI tool. Do not suggest:
- `app/` or `pages/` directory conventions
- `next.config.js` / `next.config.mjs`
- `useRouter`, `Link`, `Image` from `next/*`
- Vercel deployment or `next build`
- `NEXT_PUBLIC_*` environment variable prefixes

## ESM module — `.js` extensions required

All local imports in `.ts` files must use `.js` extension:
```ts
// correct
import { foo } from './foo.js';

// wrong — fails at runtime
import { foo } from './foo';
```

## Windows path compatibility

Dynamic `import()` on Windows requires `file://` URLs, not raw paths:
```ts
import { pathToFileURL } from 'url';
import { resolve } from 'path';

await import(pathToFileURL(resolve(__dirname, 'file.ts')).href);
```

## Prisma v7

Uses Prisma v7 with `@prisma/adapter-libsql`. Client initialized in `src/lib/db.ts`. Do not use v5/v6 API patterns.

## React 18 (not 19)

Ink v5 requires React 18. `react-reconciler` in Ink accesses `ReactCurrentOwner`, removed in React 19. Project pins `react@^18.3.1` — do not upgrade.

## tsx at runtime

No build step. `cli.js` registers a TypeScript loader via `tsx/esm/api`, then dynamically imports `cli.ts`. Never compile or emit JS files.
