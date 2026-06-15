---
name: pprof-usage
description: Using pprof for CPU and memory profiling in Go to identify performance bottlenecks.
---

# Using pprof

> Profiling Go applications with pprof.

## Problem

How to find performance bottlenecks in Go code.

## Enabling pprof

### In Code

```go
import (
    "runtime/pprof"
    "os"
)

func main() {
    // CPU profile
    f, _ := os.Create("cpu.prof")
    pprof.StartCPUProfile(f)
    defer pprof.StopCPUProfile()
    
    // do work
    
    // Memory profile
    f2, _ := os.Create("mem.prof")
    pprof.WriteHeapProfile(f2)
    f2.Close()
}
```

### With Flags

```bash
# CPU profile
go run -cpuprofile=cpu.prof main.go

# Memory profile
go run -memprofile=mem.prof main.go

# Both
go run -cpuprofile=cpu.prof -memprofile=mem.prof main.go
```

## Viewing Profiles

### Interactive Mode

```bash
go tool pprof cpu.prof
```

Commands:
```
top          # show top functions
top10        # top 10
list funcName # show function source
web          # open SVG in browser
```

### Web Interface

```bash
# Start HTTP server with pprof
go tool pprof -http=:8080 cpu.prof
```

Then open http://localhost:8080

## Types of Profiles

| Profile | Flag | Description |
|---------|------|-------------|
| CPU | -cpuprofile | CPU usage |
| Memory | -memprofile | Memory allocation |
| Block | -blockprofile | Blocked goroutines |
| Mutex | -mutexprofile | Mutex contention |
| Goroutine | N/A | Goroutine stacks |

## Analyzing CPU Profile

```bash
go tool pprof cpu.prof

# Top functions
(pprof) top

# Show with line numbers
(pprof) top -lines

# List specific function
(pprof) list processItem

# Flame graph
(pprof) web
```

### Typical Output

```
Showing top 10 nodes out of 123
      flat  flat%   sum%        cum   cum%
     0.80s  40.00% 40.00%     1.20s  60.00%  main.processItem
     0.30s  15.00% 55.00%     0.30s  15.00%  runtime.makeslice
     0.20s  10.00% 65.00%     0.40s  20.00%  bytes.makeSlice
```

## Analyzing Memory Profile

```bash
go tool pprof mem.prof

# Top allocations
(pprof) top

# Show allocation sites
(pprof) list processItem
```

### Memory Types

```go
// Alloc space - all allocations (including freed)
// Inuse space - current memory use
// Alloc objects - number of allocations

// View inuse space
go tool pprof -inuse_space mem.prof

// View allocation
go tool pprof -alloc_space mem.prof
```

## Benchmark Profiling

```go
import "testing"

func BenchmarkProcess(b *testing.B) {
    b.ReportAllocs()
    
    for i := 0; i < b.N; i++ {
        process(data)
    }
}
```

```bash
# Run with profile
go test -bench=. -cpuprofile=cpu.prof -benchmem .

# View
go tool pprof cpu.prof
```

## Common Patterns

### 1. Find Hot Path

```bash
# CPU profile shows where time is spent
go tool pprof cpu.prof
(pprof) top
(pprof) top -lines
```

### 2. Find Memory Allocations

```bash
# What allocates most memory
go tool pprof -alloc_space mem.prof
(pprof) top
(pprof) list functionName
```

### 3. Find Goroutine Leaks

```bash
# Get goroutine profile
curl http://localhost:8080/debug/pprof/goroutine?debug=1

# Or use pprof
go tool pprof http://localhost:8080/debug/pprof/goroutine
```

### 4. Find Blocked Goroutines

```bash
# Enable block profile
go run -blockprofile=block.prof main.go

# View
go tool pprof block.prof
```

## HTTP pprof

```go
import (
    "net/http"
    _ "net/http/pprof"
)

func main() {
    go func() {
        http.ListenAndServe("localhost:8080", nil)
    }()
    
    // Your code
}
```

Then access:
- http://localhost:8080/debug/pprof/
- http://localhost:8080/debug/pprof/heap
- http://localhost:8080/debug/pprof/goroutine

## Reading pprof Output

### Flat vs Cumulative

- **flat**: Time in this function only
- **cumulative**: Time in this + functions it calls

```
     0.50s  25.00%  25.00%     1.00s  50.00%  main.processItem
       ^         ^        ^        ^         ^
     flat%    sum%    flat%   cum%       cum%
```

## Best Practices

1. **Profile in production-like environment**
2. **Get baseline before optimizing**
3. **Measure after each change**
4. **Focus on hot path first**
5. **Don't optimize based on guess**
6. **Use benchmarks for verification**

## Key Points

- Use `-cpuprofile` and `-memprofile` flags
- Use `go tool pprof` to analyze
- `top` shows hottest functions
- `list` shows source with hot lines
- `web` opens visual graph
- Benchmark with `-benchmem`
- Focus on cumulative time first
