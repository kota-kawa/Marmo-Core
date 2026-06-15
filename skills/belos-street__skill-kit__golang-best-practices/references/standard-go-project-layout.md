---
name: standard-go-project-layout
description: Standard Go project structure, directory organization, and best practices for organizing Go codebases.
---

# Standard Go Project Layout

> Guidelines for organizing Go projects with standard directory structures.

## Problem

How to organize files and directories in a Go project for maintainability and scalability.

## Solution

Use the standard Go project layout conventions that the community has adopted.

## Directory Structure

```
myproject/
├── cmd/                    # Application entry points
│   └── myapp/
│       └── main.go
├── internal/               # Private application code (not importable)
│   ├── handlers/
│   ├── services/
│   └── models/
├── pkg/                    # Importable library code (optional)
│   └── utils/
├── api/                    # API definitions (OpenAPI, Protobuf, etc.)
├── configs/                # Configuration files
├── init/                   # System init scripts
├── scripts/                # Build and installation scripts
├── docs/                   # Documentation
├── test/                   # Additional test data
├── go.mod                  # Module definition
├── go.sum                  # Checksums
├── Makefile                # Build automation
└── README.md
```

## Key Directories Explained

### cmd/

Application entry points. Each subdirectory is a single executable.

```go
// cmd/myapp/main.go
package main

import (
    "myproject/internal/handlers"
    "myproject/internal/services"
)

func main() {
    // Application logic
}
```

### internal/

Private code that cannot be imported by other packages. This is enforced by the Go compiler.

```
internal/
├── handlers/    # HTTP handlers
├── services/    # Business logic
├── models/      # Data models
├── middleware/  # HTTP middleware
└── config/      # Configuration
```

### pkg/

External packages that can be imported by other projects. Use this for reusable libraries.

```
pkg/
├── utils/
├── errors/
└── cache/
```

## When to Use Each

| Directory | Use Case |
|-----------|----------|
| cmd/ | Entry points for executables |
| internal/ | Application-specific code |
| pkg/ | Reusable libraries |
| api/ | API definitions |
| configs/ | Configuration files |
| scripts/ | Build/utility scripts |

## Best Practices

1. **Use `internal/` by default** for application code
2. **Keep `main.go` in `cmd/`** - never in the root
3. **Group by feature, not by type** in larger projects
4. **Avoid deep nesting** - 3 levels maximum
5. **Use `go mod init`** in the project root

## Key Points

- Go enforces `internal/` as non-importable
- `cmd/` should contain only entry points
- Prefer flat structure for small projects
- Group by feature for large codebases
