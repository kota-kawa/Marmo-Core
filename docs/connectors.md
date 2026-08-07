# Built-in Connectors

Marmo-Core includes standard-library-backed HTTP, filesystem, shell, and SQLite
Connectors. Each operation is installed as a normal Tool resource, so it
cannot bypass resource selection, activation and execution Policy gates,
ToolRuntime schema/SecretRef handling, State Store, Recovery, or Audit Log.

## Python API

```python
from marmo_core import (
    FileSystemConnector,
    HTTPConnector,
    Kernel,
    MockLLMProvider,
    PolicyContext,
    ResourceRegistry,
    SQLiteConnector,
    ShellConnector,
)

connectors = (
    FileSystemConnector("./workspace"),
    HTTPConnector(allowed_hosts=("api.example.com",)),
    SQLiteConnector("./workspace/app.sqlite3"),
    ShellConnector("./workspace", allowed_commands=("echo",)),
)

kernel = Kernel(
    ResourceRegistry(),
    MockLLMProvider(),
    connectors=connectors,
    policy_context=PolicyContext(
        granted_permissions=(
            "connector.file.read",
            "connector.http.request",
            "connector.sqlite.read",
            "shell.exec",
        ),
        allowed_external_hosts=("api.example.com",),
        minimum_isolation_level="L1",
    ),
)
```

`write`, `external`, and `irreversible` operations require scoped human
approval by default. `dry_run=True` still checks permissions, trust, cost,
isolation, safety rules, and input schemas, but never invokes a Connector.

## CLI examples

Read a file beneath a fixed root:

```bash
python3 -m marmo_core.cli run \
  --task "read the note text file" \
  --no-default-resources \
  --strict \
  --connector-file-root ./workspace \
  --granted-permission connector.file.read \
  --minimum-isolation-level L2 \
  --tool-args '{"connector.file.read_text":{"path":"note.txt"}}'
```

Validate an HTTP request without sending it:

```bash
python3 -m marmo_core.cli run \
  --task "request the example API" \
  --no-default-resources \
  --strict \
  --connector-http \
  --granted-permission connector.http.request \
  --allow-external-host api.example.com \
  --minimum-isolation-level L2 \
  --dry-run \
  --tool-args '{"connector.http.request":{"url":"https://api.example.com/status"}}'
```

Run one allowlisted executable with shell expansion disabled:

```bash
python3 -m marmo_core.cli run \
  --task "run the echo command" \
  --no-default-resources \
  --strict \
  --connector-shell-root ./workspace \
  --connector-shell-command echo \
  --granted-permission shell.exec \
  --minimum-isolation-level L1 \
  --dry-run \
  --tool-args '{"connector.shell.run":{"command":"echo hello"}}'
```

Query one fixed SQLite database:

```bash
python3 -m marmo_core.cli run \
  --task "query notes from sqlite" \
  --no-default-resources \
  --strict \
  --connector-sqlite ./workspace/app.sqlite3 \
  --granted-permission connector.sqlite.read \
  --minimum-isolation-level L2 \
  --tool-args '{"connector.sqlite.query":{"sql":"SELECT id, body FROM notes LIMIT 10"}}'
```

`--no-default-resources` prevents unrelated definitions in the current
directory from changing Connector selection. The `--strict` flag makes the
CLI return a non-zero status if a resource is skipped or an explicitly
configured tool is not evaluated. When resuming a task in another process,
repeat these flags as well. The State Store persists the task and reviewed
operation, while paths, executable
allowlists, network access, and credentials remain runtime configuration.

## Security boundaries

- HTTP permits only HTTP/HTTPS, rejects URL credentials, does not follow
  redirects, bounds response size, and blocks private/loopback/link-local
  destinations unless explicitly enabled. Policy host allow/block lists are
  still applied before the request. It declares L2 when the Connector itself
  has an `allowed_hosts` list, and L1 when public destinations are unrestricted.
- File operations resolve every path beneath one root, reject absolute and
  escaping/symlink paths, bound reads/listings, and use atomic replacement for
  writes. Parent directories must already exist.
- Shell uses `subprocess` with `shell=False`, a resolved executable allowlist,
  a root-confined working directory, an environment-key allowlist, no stdin,
  timeout, and bounded persisted output. This is L1 process isolation, not a
  container or filesystem sandbox.
- SQLite is fixed to one database. Queries use a read-only connection and
  bounded rows; writes accept one parameterized statement from an explicit
  verb allowlist. `ATTACH` and transaction-control statements are rejected.
- Connector-local retries are only applied to declared retry-safe reads.
  Writes, shell commands, and HTTP requests execute once per Kernel attempt.
  Rate limits and circuit breakers are tracked per Connector operation.

L3 container/VM isolation, browser automation, and messaging Connectors remain
optional v3 work.
