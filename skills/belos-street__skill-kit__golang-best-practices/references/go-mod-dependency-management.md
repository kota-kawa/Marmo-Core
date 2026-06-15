---
name: go-mod-dependency-management
description: Best practices for Go modules, dependency management, version control, and go.mod configuration.
---

# Go Modules and Dependency Management

> Managing dependencies with Go modules.

## Problem

How to properly manage dependencies in Go, handle versions, and avoid common pitfalls.

## Solution

Use Go modules (`go.mod` and `go.sum`) for dependency management.

## Basic Commands

```bash
# Initialize a new module
go mod init github.com/username/project

# Add a dependency
go get github.com/pkg/errors

# Add a specific version
go get github.com/pkg/errors@v0.9.1

# Update all dependencies
go get -u ./...

# Tidy up (remove unused, add missing)
go mod tidy

# View dependencies
go list -m all

# Download dependencies
go mod download
```

## go.mod Structure

```go.mod
module github.com/username/project

go 1.21

require (
    github.com/pkg/errors v0.9.1
    github.com/stretchr/testify v1.8.4
)
```

## Version Management

### Semantic Versions (SemVer)

- `v1.2.3` = Major.Minor.Patch
- `v1.0.0` → `v2.0.0` = Breaking change
- `v1.1.0` → `v1.2.0` = New feature (backward compatible)
- `v1.1.0` → `v1.1.1` = Bug fix

### Pseudo-versions

For untagged commits:

```
v0.0.0-20231101123456-1234567890ab
```

### Upgrade Strategies

```bash
# Patch versions only
go get -u=patch github.com/pkg/errors

# Minor versions
go get -u github.com/pkg/errors

# Latest
go get -u github.com/pkg/errors@latest
```

## Replace Directive

For local development or forks:

```go.mod
require (
    github.com/original/package v1.0.0
)

replace github.com/original/package => ../local/path
```

## Best Practices

1. **Always run `go mod tidy`** before committing
2. **Commit both `go.mod` and `go.sum`**
3. **Use explicit versions** in require, not branch names
4. **Use `//go:build`** tags for conditional compilation
5. **Avoid `go get -u` in CI** - pin versions

## Dependency Cleanup

```bash
# Remove unused dependencies
go mod tidy

# Verify checksums
go mod verify

# Show why a dependency is used
go mod why github.com/pkg/errors
```

## Common Issues

### Duplicate Dependencies

```bash
# Use go mod tidy to resolve
go mod tidy
```

### Incompatible Versions

```go.mod
require (
    github.com/A v1.0.0
    github.com/B v2.0.0
)
```

Use `go mod graph` to find conflicts.

## Key Points

- Use `go mod init` to start
- Run `go mod tidy` regularly
- Commit `go.mod` and `go.sum`
- Pin versions in production
- Use `replace` for local development
