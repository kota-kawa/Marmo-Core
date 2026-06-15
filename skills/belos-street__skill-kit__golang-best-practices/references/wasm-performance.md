---
name: wasm-performance
description: Performance considerations for Go WebAssembly - bundle size, startup time, and optimization techniques.
---

# WASM Performance

> Optimizing performance for Go WASM applications.

## Problem

How to optimize Go WASM for smaller size and faster startup.

## Bundle Size

### Typical Sizes

| Type | Size |
|------|------|
| Go WASM (tiny) | ~2MB |
| Go WASM (normal) | ~5-10MB |
| TinyGo WASM | ~100KB-500KB |

### Reducing Size

```bash
# Strip symbols
GOOS=js GOARCH=wasm go build -ldflags="-s -w" -o main.wasm main.go

# Use TinyGo for smaller binaries
tinygo build -target=wasm -o main.wasm main.go
```

## Startup Time

### Lazy Loading

```go
// Don't load everything at startup
// Import packages only when needed
func init() {
    // Minimal init
}
```

### Use WASM Features

```bash
# Enable SIMD (if supported)
GOOS=js GOARCH=wasm go build -tags=wasm_alpha -o main.wasm main.go
```

## Optimization Tips

### 1. Minimize Imports

```go
// Bad - imports lots of packages
import (
    "encoding/json"
    "fmt"
    "os"
)

// Good - use minimal imports
import (
    "syscall/js"
)
```

### 2. Use TinyGo

```bash
# Install TinyGo
brew install tinygo

# Build tiny binary
tinygo build -target=wasm -o main.wasm main.go
```

### 3. Code Splitting

```go
// Lazy load heavy functions
var heavyModule js.Value

func loadHeavyModule() {
    if !heavyModule.Truthy() {
        // Load only when needed
    }
}
```

## Memory Considerations

### Heap Size

```bash
# Set initial heap size
GOOS=js GOARCH=wasm go build -ldflags="-s -w -X main.MaxMem=134217728" main.go
```

### Memory Limits

- Browser limits: 2GB (most browsers)
- Start small, grow as needed

## Profiling

### Chrome DevTools

1. Open Chrome DevTools
2. Go to Memory tab
3. Take heap snapshot
4. Check WASM memory

### WASM Internals

```javascript
// Check WASM memory
console.log(wasm.instance.exports.memory.buffer.byteLength);
```

## Best Practices

1. **Use TinyGo** for smaller binaries
2. **Minimize imports** - strip unused
3. **Lazy load** heavy features
4. **Compress** with brotli/gzip
5. **Cache** the WASM file

## Key Points

- Use TinyGo for smaller size
- Strip symbols with ldflags
- Minimize package imports
- Lazy load heavy features
- Compress for transfer
- Profile to find bottlenecks
