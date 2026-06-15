## Local Safety Rules

- Never use full-file overwrite commands for `web/.env.local` (for example: `cp`, `cat > file <<EOF`, `mv` over it).
- Only use line-specific edits for `web/.env.local`, and only after explicit user confirmation.
- Before any edit to `web/.env.local`, create a timestamped backup in `.context/`.
