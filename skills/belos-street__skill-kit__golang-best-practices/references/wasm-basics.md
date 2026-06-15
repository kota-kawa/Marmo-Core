---
name: wasm-basics
description: Getting started with Go WebAssembly - compilation, setup, and basic concepts.
---

# WASM Basics

> Introduction to Go WebAssembly (GOOS=js, GOARCH=wasm).

## Problem

How to compile Go code to WebAssembly and run it in browsers.

## Compilation

### Build Command

```bash
# Build WASM
GOOS=js GOARCH=wasm go build -o main.wasm main.go

# With optimization
GOOS=js GOARCH=wasm go build -ldflags="-s -w" -o main.wasm main.go
```

### HTML Setup

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Go WASM</title>
    <script src="wasm_exec.js"></script>
</head>
<body>
    <h1>Go WASM Demo</h1>
    <pre id="output"></pre>

    <script>
        const go = new Go();

        WebAssembly.instantiateStreaming(
            fetch("main.wasm"),
            go.importObject
        ).then(result => {
            go.run(result.instance);
        });
    </script>
</body>
</html>
```

### Getting wasm_exec.js

```bash
# From Go installation
cp $(go env GOROOT)/misc/wasm/wasm_exec.js .

# Or from npm
npm install @assemblyscript/loader  # alternative
```

## Go Entry Point

```go
package main

import (
    "fmt"
    "syscall/js"
)

func main() {
    fmt.Println("Hello from Go WASM!")
    
    // Keep running
    <-make(chan struct{})
}
```

## Important Differences

### 1. No os.Exit

```go
// This will crash the WASM
func main() {
    // Use blocking channel instead
    <-make(chan struct{})
}
```

### 2. No TCP/UDP

```go
// Won't work in WASM
// net/http uses os.Stdin/Stdout which don't exist
```

### 3. Limited syscalls

Only some syscalls work:
- js package
- time
- math
- strings

## Running Locally

### Using Go's Server

```bash
# Simple server
python3 -m http.server 8080

# Or Go
go run -tags=foo .
```

### With Node (Testing)

```bash
# Install wasm-opt (optional)
npm i -g wasm-opt

# Run with Node
node --experimental-wasm-simd WasmFileName.js
```

## Key Points

- Use `GOOS=js GOARCH=wasm` to build
- Need wasm_exec.js from Go installation
- No os.Exit - use blocking channel
- Limited standard library
- Run with local server for testing
