---
name: memory-management-gc
description: Understanding Go's garbage collector, memory allocation, and techniques for memory-efficient code.
---

# Memory Management and GC

> How Go manages memory and the garbage collector.

## Problem

Understanding Go's memory management and how to write memory-efficient code.

## Go's Garbage Collector

Go has a concurrent mark-and-sweep garbage collector.

### GC Phases

1. **Mark Start** - STW (stop-the-world) brief pause
2. **Mark Phase** - Concurrent marking with goroutines
3. **Mark Termination** - STW brief pause
4. **Sweep Phase** - Concurrent sweeping

### GC Goals

- Low latency (sub-millisecond)
- High throughput
- Consistent performance

## Memory Allocation

### Stack vs Heap

| Location | Allocation | Deallocation |
|----------|------------|--------------|
| Stack | Fast (single instruction) | Automatic (function return) |
| Heap | Slower (malloc) | GC (garbage collector) |

### Stack Allocation

Stack allocation is automatic and fast:

```go
func sum(a, b int) int {
    // a, b allocated on stack
    return a + b
}
```

### Heap Allocation

Heap allocation happens when:

```go
func newUser(name string) *User {
    // User escapes to heap
    return &User{Name: name}
}
```

## GOGC Environment Variable

Controls GC frequency:

```bash
# Default: 100 (GC triggers at 100% heap growth)
GOGC=200 go run main.go   # Less frequent GC
GOGC=50 go run main.go    # More frequent GC
```

### Trade-offs

| GOGC Value | GC Frequency | Memory Usage | CPU Usage |
|------------|--------------|--------------|-----------|
| 50 | High | Low | Higher |
| 100 | Normal | Normal | Normal |
| 200 | Low | Higher | Lower |

## sync.Pool

Object pooling to reduce allocations:

```go
var bufferPool = sync.Pool{
    New: func() interface{} {
        return new(bytes.Buffer)
    },
}

func process() {
    buf := bufferPool.Get().(*bytes.Buffer)
    buf.Reset()
    defer bufferPool.Put(buf)
    
    // use buffer
}
```

### Best Practices for Pool

1. Don't pool objects with invariants
2. Reset objects before returning
3. Don't pool large objects
4. Consider benchmarks before pooling

## Reducing Allocations

### 1. Use Pool

```go
// Before
func process(data []byte) string {
    var buf bytes.Buffer
    for _, b := range data {
        buf.WriteByte(b)
    }
    return buf.String()
}

// After - using Pool
var bufPool = sync.Pool{
    New: func() interface{} { return new(bytes.Buffer) },
}

func process(data []byte) string {
    buf := bufPool.Get().(*bytes.Buffer)
    buf.Reset()
    defer bufPool.Put(buf)
    
    for _, b := range data {
        buf.WriteByte(b)
    }
    return buf.String()
}
```

### 2. Pre-allocate Slices

```go
// Before - multiple allocations
func collectIDs(users []User) []int {
    var ids []int
    for _, u := range users {
        ids = append(ids, u.ID)
    }
    return ids
}

// After - pre-allocate
func collectIDs(users []User) []int {
    ids := make([]int, 0, len(users))
    for _, u := range users {
        ids = append(ids, u.ID)
    }
    return ids
}
```

### 3. Use strings.Builder

```go
// Before
var s string
for _, p := range parts {
    s += p
}

// After
var b strings.Builder
for _, p := range parts {
    b.WriteString(p)
}
return b.String()
```

### 4. Avoid Empty Interfaces

```go
// Bad - allocations
func printAll(items ...interface{}) {
    for _, item := range items {
        fmt.Println(item)
    }
}

// Good - type-specific
func printAll[T any](items ...T) {
    for _, item := range items {
        fmt.Println(item)
    }
}
```

## Memory Profiling

```bash
# Enable memory profiling
go run -memprofile=mem.prof main.go

# Or in code
f, _ := os.Create("mem.prof")
pprof.WriteHeapProfile(f)
f.Close()
```

## GC Tuning

### runtime/debug

```go
import "runtime/debug"

// Set GOGC programmatically
debug.SetGCPercent(200)

// Force GC
runtime.GC()

// Read GC stats
var stats runtime.MemStats
runtime.ReadMemStats(&stats)
fmt.Println("GC cycles:", stats.NumGC)
```

## Best Practices

1. **Profile first** - don't optimize prematurely
2. **Use sync.Pool** for temporary objects
3. **Pre-allocate slices** when size is known
4. **Use strings.Builder** for string concatenation
5. **Avoid empty interface** when possible
6. **Tune GOGC** for your workload

## Key Points

- Go has a concurrent mark-and-sweep GC
- Stack allocation is fast and automatic
- Heap allocation needs GC (slower)
- Use sync.Pool for temporary objects
- Pre-allocate when size is known
- Profile before optimizing
