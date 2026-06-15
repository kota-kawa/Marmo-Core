---
name: linting-formatting
description: Code linting and formatting tools in Go - gofmt, golangci-lint, staticcheck, and IDE integration.
---

# Linting and Formatting

> Using linting and formatting tools for Go code quality.

## Problem

How to maintain consistent code style and catch issues early.

## gofmt

### Basic Usage

```bash
# Format file
gofmt -w main.go

# Format directory
gofmt -w .

# Show diff
gofmt -d main.go
```

### Options

```bash
# Simplify code
gofmt -s -w main.go

# Tab indentation
gofmt -tab -w main.go

# Print only
gofmt main.go
```

### Integration

```bash
# Save on every file
go fmt ./...

# In Makefile
fmt:
	gofmt -l -w .
```

## go vet

### Basic Usage

```go
// Run vet
go vet ./...

// Vet with flags
go vet -shadow ./...
```

### What vet Catches

- Printf format mismatch
- Unreachable code
- Incorrect channel usage
- Invalid unmaeded struct fields

```go
// vet catches this
fmt.Printf("%s", 123)  // %s expects string
```

## golangci-lint

### Installation

```bash
# Binary
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin

# Or
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
```

### Configuration

Create `.golangci.yml`:

```yaml
linters:
  enable:
    - errcheck
    - gosimple
    - govet
    - ineffassign
    - staticcheck
    - unused

linters-settings:
  errcheck:
    check-type-assertions: true
  govet:
    enable-all: true

issues:
  exclude-use-default: false
```

### Running

```bash
# Run
golangci-lint run

# Fix issues
golangci-lint run --fix

# With config
golangci-lint run -c .golangci.yml ./...
```

## staticcheck

### Installation

```bash
go install honnef.co/go/tools/cmd/staticcheck@latest
```

### Usage

```bash
# Run
staticcheck ./...

# Check specific rules
staticcheck -checks ST1000,SA5001 ./...
```

## IDE Integration

### VS Code

```json
{
    "go.formatTool": "gofmt",
    "go.lintTool": "golangci-lint",
    "go.lintOnSave": "package",
    "go.vetOnSave": "package"
}
```

### GoLand

Settings → Go → Linting → Enable golangci-lint

### Neovim

```lua
-- nvim-lspconfig
require('lspconfig').golangci_lint_ls.setup{}
```

## CI Integration

### GitHub Actions

```yaml
name: Lint
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
      - uses: golangci/golangci-lint-action@v3
        with:
          version: latest
```

### GitLab CI

```yaml
lint:
  image: golang:1.21
  script:
    - go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
    - golangci-lint run ./...
```

## Makefile Example

```makefile
.PHONY: fmt lint test

fmt:
	gofmt -l -w .

vet:
	go vet ./...

lint:
	golangci-lint run ./...

test:
	go test -race ./...

check: fmt vet lint test
```

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/golangci/golangci-lint
    rev: v1.54.0
    hooks:
      - id: golangci-lint
```

## Best Practices

1. **Run gofmt** on save
2. **Use golangci-lint** for comprehensive linting
3. **Integrate in CI** to prevent bad code
4. **Configure IDE** for automatic formatting
5. **Use go vet** before commits

## Key Points

- `gofmt` - code formatting
- `go vet` - basic checks
- `golangci-lint` - comprehensive linting
- IDE integration - automatic formatting
- CI integration - prevent bad code
