---
name: build-tags
description: Using build tags and conditional compilation in Go for platform-specific code and build variations.
---

# Build Tags

> Using build tags for conditional compilation in Go.

## Problem

How to compile different code for different platforms or build configurations.

## Build Tags Syntax

### Basic Usage

```go
//go:build linux
// +build linux

package mypackage
```

### Multiple Tags

```go
// AND: both must be true
//go:build linux && amd64
// +build linux,amd64

// OR: at least one must be true
//go:build linux || darwin
// +build linux,darwin

// NOT: must not be true
//go:build !windows
// +build !windows
```

## Common Build Tags

### OS-Specific

```go
//go:build linux
// +build linux

// Linux-specific code
package linux

//go:build darwin
// +build darwin

// macOS-specific code
package darwin

//go:build windows
// +build windows

// Windows-specific code
package windows
```

### Architecture-Specific

```go
//go:build amd64
// +build amd64

// 64-bit x86

//go:build arm64
// +build arm64

// ARM 64-bit
```

### Build Mode

```go
//go:build ignore
// +build ignore

// Not compiled normally, only with go build

//go:build wire
// +build wire

// Only with go generate -tags wire
```

## File-Based Tags

### Without Tags (Default)

```go
// utils.go - always included
package utils

func Helper() {}
```

### With Tags

```go
// utils_linux.go
//go:build linux
// +build linux

package utils

func Helper() string {
    return "linux"
}
```

```go
// utils_windows.go
//go:build windows
// +build windows

package utils

func Helper() string {
    return "windows"
}
```

## Examples

### Platform-Specific Files

```
myapp/
├── main.go
├── processor.go
├── processor_linux.go     // Linux
├── processor_darwin.go    // macOS
├── processor_windows.go   // Windows
└── processor_test.go      // test
```

### Debug vs Release

```go
// debug.go
//go:build debug
// +build debug

package main

const Debug = true
```

```go
// release.go
//go:build !debug
// +build !debug

package main

const Debug = false
```

Build:
```bash
go build -tags debug .   # debug build
go build .               # release build
```

### Build Modes

```go
// service.go
//go:build !app
// +build !app

package myapp

func RunService() {}

// main.go
//go:build app
// +build app

package main

func main() {
    myapp.RunService()
}
```

Build:
```bash
go build -tags app .     # builds executable
go build .               # builds library
```

## Using in Code

### Current Build Info

```go
import "runtime"

func init() {
    if runtime.GOOS == "linux" {
        // Linux-specific setup
    }
}
```

### Build Tag Detection in Tests

```go
//go:build integration
// +build integration

package myapp

func TestIntegration(t *testing.T) {
    // Run with: go test -tags integration
}
```

## Go Generate Tags

```go
//go:generate go run gen.go

//go:generate mytool -tags generation

//go:generate mockgen -destination=mocks/repo.go . Repository
```

## Best Practices

1. **Use new syntax** - `//go:build` over `// +build`
2. **Keep tags simple** - avoid complex conditions
3. **Name files consistently** - `file_OS.go` or `file_tag.go`
4. **Document tags** - explain what each tag does
5. **Test tagged code** - ensure tagged files compile

## Common Tags

| Tag | Description |
|-----|-------------|
| `linux` | Linux OS |
| `darwin` | macOS |
| `windows` | Windows |
| `amd64` | 64-bit x86 |
| `arm64` | ARM 64-bit |
| `race` | Race detector |
| `netgo` | Pure Go network |
| `appengine` | App Engine |

## Key Points

- Use `//go:build` for build tags
- File naming: `file_tag.go`
- Multiple tags: AND/OR/NOT
- Test tagged code
- Document custom tags
