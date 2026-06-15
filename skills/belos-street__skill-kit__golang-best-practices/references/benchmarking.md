---
name: benchmarking
description: Writing and analyzing benchmarks in Go to measure performance.
---

# Benchmarking in Go

> Writing and running benchmarks in Go.

## Problem

How to measure and verify performance of Go code.

## Writing Benchmarks

### Basic Structure

```go
func BenchmarkName(b *testing.B) {
    for i := 0; i < b.N; i++ {
        // Code to benchmark
    }
}
```

### Complete Example

```go
func BenchmarkAdd(b *testing.B) {
    var result int
    for i := 0; i < b.N; i++ {
        result = Add(i, i+1)
    }
    // Prevent optimization
    if result == 0 {
        b.Fatal("result is 0")
    }
}
```

## Running Benchmarks

### Basic

```bash
# Run all benchmarks
go test -bench=.

# Run specific benchmark
go test -bench=BenchmarkAdd

# Run with memory allocation
go test -bench=. -benchmem
```

### Common Flags

| Flag | Description |
|------|-------------|
| `-bench=.` | Run all benchmarks |
| `-benchmem` | Show memory allocations |
| `-benchtime=10s` | Run each benchmark for 10s |
| `-cpu=1,4,8` | Run with different CPUs |
| `-count=3` | Run each benchmark 3 times |
| `-run=^$` | Skip tests, run only benchmarks |

### Output Example

```
goos: darwin
goarch: arm64
pkg: example
BenchmarkAdd-8           1000000000               0.298 ns/op          0 B/op          0 allocs/op
BenchmarkMultiply-8     100000000                2.31 ns/op           0 B/op          0 allocs/op
```

## Benchmarking Tips

### 1. Prevent Optimization

```go
// BAD - may be optimized away
func BenchmarkBad(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Add(1, 2)
    }
}

// GOOD - use result
func BenchmarkGood(b *testing.B) {
    var r int
    for i := 0; i < b.N; i++ {
        r = Add(1, 2)
    }
    if r == 0 {
        b.Fatal("optimized away")
    }
}
```

### 2. Report Allocations

```go
func BenchmarkWithAlloc(b *testing.B) {
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        // This will show allocations
    }
}
```

### 3. Vary Input Size

```go
func BenchmarkSlice(b *testing.B) {
    sizes := []int{10, 100, 1000, 10000}

    for _, size := range sizes {
        b.Run(fmt.Sprintf("size-%d", size), func(b *testing.B) {
            data := make([]int, size)
            for i := 0; i < b.N; i++ {
                process(data)
            }
        })
    }
}
```

## Comparing Benchmarks

### Using benchstat

```bash
# Install
go install golang.org/x/tools/cmd/benchstat@latest

# Run old benchmark
go test -bench=. -count=5 -o old.test

# Run new benchmark
go test -bench=. -count=5 -o new.test

# Compare
benchstat old.test new.test
```

### Output

```
name         old time/op    new time/op    delta
Add-8          0.30ns ± 1%    0.28ns ± 2%   -6.67%  (p=0.029)

name         old alloc/op   new alloc/op   delta
Add-8            0B             0B          ~     (all equal)

name         old allocs/op  new allocs/op  delta
Add-8            0              0          ~     (all equal)
```

## Common Patterns

### Testing Multiple Implementations

```go
func Benchmark(b *testing.B) {
    implementations := map[string]func(){
        "slice": func() { useSlice() },
        "array": func() { useArray() },
    }

    for name, fn := range implementations {
        b.Run(name, func(b *testing.B) {
            for i := 0; i < b.N; i++ {
                fn()
            }
        })
    }
}
```

### Timing Operations

```go
func BenchmarkWithSetup(b *testing.B) {
    // Setup once
    data := prepareData()

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        process(data)
    }
}
```

### Parallel Benchmarks

```go
func BenchmarkParallel(b *testing.B) {
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            // This runs in parallel
        }
    })
}
```

## Profiling Benchmarks

### CPU Profile

```bash
go test -bench=. -cpuprofile=cpu.prof
go tool pprof cpu.prof
```

### Memory Profile

```bash
go test -bench=. -memprofile=mem.prof -memprofilerate=1
go tool pprof mem.prof
```

## Benchmarking Checklist

1. [ ] Use realistic input data
2. [ ] Prevent compiler optimization
3. [ ] Report allocations
4. [ ] Run multiple times
5. [ ] Compare with baseline
6. [ ] Profile to find hot spots

## Key Points

- Write benchmarks in `*_test.go` files
- Use `b.N` for iteration count
- Report allocations with `-benchmem`
- Prevent compiler optimization
- Use benchstat to compare
- Profile with `-cpuprofile`
