# SDK Publish Runbook

How to cut a new release of `@delphimarkets/sdk` to npm. The first publish (v0.1.0) is already done; this is for future releases.

## When to publish

- Bug fix → patch bump (`0.1.0` → `0.1.1`)
- New feature, backwards compatible → minor bump (`0.1.0` → `0.2.0`)
- Breaking change → major bump (`0.1.0` → `1.0.0`)

Follow [semver](https://semver.org/). Until you hit `1.0.0`, breaking changes can technically go in minor bumps, but it's still polite to bump major.

## Prerequisites (one-time)

1. You're logged into the `mason_brownrigg` npm account locally:
   ```bash
   npm whoami
   # should print: mason_brownrigg
   ```
2. 2FA is enabled on the account (already set up — required by npm for publishing).
3. You have an authenticator app (1Password / Authy / Google Auth) handy for the OTP prompt.

## Publish workflow

```bash
cd /Users/masonbrownrigg/Documents/Delphi/Delphi-Terminal/delphi-sdk

# 1. Sync deps and run the test suite — never publish without green tests
npm install
npm test

# 2. Bump version. Pick one:
npm version patch    # 0.1.0 -> 0.1.1
npm version minor    # 0.1.0 -> 0.2.0
npm version major    # 0.1.0 -> 1.0.0

# 3. Build the dist/ folder
npm run build

# 4. (Sanity check) Confirm dist/ has files
ls dist/cjs dist/esm dist/types

# 5. Publish (will prompt for 2FA OTP)
npm publish --access public

# 6. Push the version-bump commit + tag npm just made
git push --follow-tags
```

The `npm version` command auto-creates a git commit (`v0.1.1`) and a matching tag, so step 6 just pushes them.

## Verify

```bash
# Confirm new version is live
npm view @delphimarkets/sdk version

# Install in a fresh project to smoke test
mkdir /tmp/sdk-smoke && cd /tmp/sdk-smoke
npm init -y
npm install @delphimarkets/sdk
node -e "const { DelphiClient } = require('@delphimarkets/sdk'); console.log(typeof DelphiClient);"
# should print: function
```

## What to watch for in the publish output

The `npm notice` block lists every file in the tarball. Sanity-check it includes all three `dist/` subtrees:

```
npm notice dist/cjs/index.js
npm notice dist/esm/index.js
npm notice dist/types/index.d.ts
...
npm notice total files: 144   <-- should be 100+, NOT 2
```

If you see `total files: 2` (just README + package.json), you forgot `npm run build`. Stop and don't publish — you'd ship an empty package.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `403 Forbidden ... Two-factor authentication required` | 2FA wasn't completed | Approve the browser popup or paste OTP from authenticator |
| `403 You cannot publish over the previously published version` | You forgot to bump the version | Run `npm version patch` and retry |
| `403 Forbidden` (no 2FA mention) | Missing `--access public` | Always pass `--access public` for scoped packages on free orgs |
| `ENEEDAUTH` | Not logged in | Run `npm login` first |
| `total files: 2` in notice block | Forgot `npm run build` | Build first, then re-publish (note: requires version bump if first publish already succeeded) |

## Optional: automate via GitHub Actions

If you want `git push --tags` to auto-publish, drop this in `.github/workflows/release.yml`:

```yaml
name: Publish to npm

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm test
      - run: npm run build
      - run: npm publish --access public --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

To use this:
1. Create a granular access token at [npmjs.com/settings/.../tokens](https://www.npmjs.com/settings/mason_brownrigg/tokens) — set "Bypass two-factor authentication for publishing" so CI doesn't block on OTP, scope to `@delphimarkets/sdk` only.
2. Add it as `NPM_TOKEN` repo secret in GitHub.
3. Tag a release with `npm version patch && git push --follow-tags` and the workflow takes it from there.

The `--provenance` flag publishes a signed attestation linking the tarball back to the GitHub commit — adds a "Provenance" badge to the npm page and is good security hygiene.
