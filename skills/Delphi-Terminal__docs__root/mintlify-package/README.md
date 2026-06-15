# Mintlify Drop-In Package

Documentation content for the Delphi Trading SDK, ready to paste into your Mintlify project. This folder is a delivery artifact, not part of the published npm package.

## Files

| File | Purpose |
| --- | --- |
| [`openapi-additions.json`](./openapi-additions.json) | 3 new tags, 9 path entries, ~16 component schemas. Merge into your existing Mintlify `openapi.json`. |
| [`mintlify-nav.json`](./mintlify-nav.json) | Navigation snippets for both `docs.json` (Mintlify v3) and `mint.json` (v2). |
| [`sdk-publish-steps.md`](./sdk-publish-steps.md) | Reference runbook for cutting future `@delphimarkets/sdk` releases to npm. Internal use, not for the docs site. |
| [`trading/index.mdx`](./trading/index.mdx) | Trading SDK hub page — install, configure, concepts, error handling. |
| [`trading/polymarket.mdx`](./trading/polymarket.mdx) | Per-exchange guide. |
| [`trading/kalshi.mdx`](./trading/kalshi.mdx) | Per-exchange guide. |
| [`trading/opinion-labs.mdx`](./trading/opinion-labs.mdx) | Per-exchange guide. |
| [`trading/gemini.mdx`](./trading/gemini.mdx) | Per-exchange guide. |
| [`trading/limitless.mdx`](./trading/limitless.mdx) | Per-exchange guide. |
| [`trading/predict-fun.mdx`](./trading/predict-fun.mdx) | Per-exchange guide. |

## How to install into your Mintlify project

### 1. Merge `openapi-additions.json` into your existing OpenAPI spec

Your Mintlify project should have an `openapi.json` (or `openapi.yaml`) somewhere in its tree — typically at `api-reference/openapi.json` or referenced from `docs.json`'s `"openapi"` field.

Open both files and merge by top-level key:

- Append the 3 entries in `tags` to your existing `tags` array.
- Add the 9 entries in `paths` to your existing `paths` object (the keys are unique paths; no collisions expected).
- Add all entries in `components.schemas` to your existing `components.schemas`. Same for `components.responses`.
- The `_comment` field at the top is documentation, not OpenAPI — strip it before validation.

After merging, validate with the Mintlify CLI:

```bash
mintlify openapi-check ./path/to/openapi.json
```

Or use any OpenAPI validator (e.g. `npx @redocly/cli lint openapi.json`).

### 2. Drop the MDX pages into your docs tree

Copy the entire `trading/` folder into the root of your Mintlify project:

```bash
cp -r docs/mintlify-package/trading/ /path/to/your-mintlify-project/trading/
```

The page URLs will become `your-docs-domain.com/trading/`, `/trading/polymarket`, etc.

### 3. Wire up navigation in `docs.json` (or `mint.json`)

See [`mintlify-nav.json`](./mintlify-nav.json) for two example nav structures (Mintlify v3 and v2). Pick the one that matches your version, copy the relevant block, and merge into your existing `navigation` array.

The auto-generated API Reference page slugs (e.g. `api-reference/trading/place-order`) depend on how Mintlify generates them from your OpenAPI spec. Run `mintlify dev` locally and check what slugs it produces for the new endpoints, then update the nav to match if needed. Mintlify typically uses the operationId (kebab-cased) under a folder named after the tag.

### 4. Cross-link verification

Each per-exchange MDX page ends with an "API reference" section that links to the auto-generated endpoint pages. The link targets are written assuming Mintlify slugs of the form `/api-reference/<tag-slug>/<operation-id-slug>`. Adjust the path prefixes if your Mintlify config puts the API Reference somewhere else (e.g. `/reference/...`).

The hub page ([`trading/index.mdx`](./trading/index.mdx)) uses Mintlify card components (`<CardGroup>`, `<Card>`) that link to the per-exchange pages via `href="/trading/polymarket"`, etc. These work as-is once you copy `trading/` into your project root.

### 5. Local preview

```bash
cd /path/to/your-mintlify-project
mintlify dev
```

Click through:
- Sidebar should show the new "Trading SDK" group with 7 pages
- API Reference section should show 3 new groups (Trading, Credentials, Polymarket Onboarding) with 9 endpoints
- "Try It" panel on `POST /api/v1/orders` should let you switch between 6 per-exchange examples

## Source of truth

The schemas in `openapi-additions.json` and the code samples in the MDX pages were derived from the published SDK source. If the SDK adds new exchanges or changes a request shape:

- Update the corresponding type file (e.g. `src/polymarket/types.ts`)
- Update the matching schema in `openapi-additions.json`
- Update the matching MDX page

Cross-reference between SDK source and OpenAPI:

| SDK file | OpenAPI schema |
| --- | --- |
| [`src/types.ts`](../../src/types.ts) | `Exchange`, `OrderType`, `OrderSide`, `KalshiLimitOrder`, `GeminiPredictionOrder`, `PlaceOrderRequest`, `PlaceOrderResponse`, `OrderStatusResponse`, `ListOrdersResponse`, `CancelOrderResponse`, `ExchangeCredentials`, `RegisterCredentialsRequest`, `RegisterCredentialsResponse`, `ListCredentialsResponse`, `DeriveCredentialsRequest`, `DeriveCredentialsResponse`, `VerifyCredentialsRequest`, `VerifyCredentialsResponse`, `SafeAddressRequest`, `SafeAddressResponse` |
| [`src/polymarket/types.ts`](../../src/polymarket/types.ts) | `SignedPolymarketOrder` |
| [`src/opinionlabs/types.ts`](../../src/opinionlabs/types.ts) | `SignedOpinionLabsOrder` |
| [`src/limitless/types.ts`](../../src/limitless/types.ts) | `SignedLimitlessOrder` |
| [`src/predictfun/types.ts`](../../src/predictfun/types.ts) | `SignedPredictFunOrder`, `PredictFunOrderPayload` |
