---
name: slice-optimization
description: Optimizing slice usage in Go - pre-allocation, capacity, append behavior, and memory efficiency.
---

# Slice Optimization

> Optimizing slice operations for better performance.

## Problem

Understanding slice internals and optimizing for performance.

## Slice Internals

```go
type sliceHeader struct {
    Data uintptr  // pointer to underlying array
    Len  int      // current length
    Cap  int      // capacity (allocated length)
}
```

## Pre-allocation

### Without Pre-allocation

```go
// BAD - multiple allocations
func collectBad(items []Item) []int {
    var result []int  // nil slice
    for _, item := range items {
        result = append(result, item.ID)  // may reallocate
    }
    return result
}
```

### With Pre-allocation

```go
// GOOD - single allocation
func collectGood(items []Item) []int {
    result := make([]int, 0, len(items))  // pre-allocate
    for _, item := range items {
        result = append(result, item.ID)
    }
    return result
}
```

### With Known Size

```go
// If you know exact size
func collectFixed(items []Item) []int {
    result := make([]int, len(items))
    for i, item := range items {
        result[i] = item.ID
    }
    return result
}
```

## Capacity

### Initial Capacity

```go
// Start with capacity
ch := make(chan int, 100)  // buffered

// For slices
buf := make([]byte, 0, 4096)  // capacity 4096
```

### Growth Strategy

Go doubles capacity until 1024, then grows by 25%:

```go
s := make([]int, 0)
// append: 0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 1280, ...
```

## Common Mistakes

### 1. Not Using Cap

```go
// BAD
func bad() []int {
    var s []int
    for i := 0; i < 1000; i++ {
        s = append(s, i)  // multiple reallocations
    }
    return s
}

// GOOD
func good() []int {
    s := make([]int, 0, 1000)  // pre-allocate
    for i := 0; i < 1000; i++ {
        s = append(s, i)
    }
    return s
}
```

### 2. Modifying in Loop

```go
// BAD - modifies original slice
func badModify(s []int) {
    for i := range s {
        s[i] *= 2  // modifies original
    }
}

// GOOD - copy if needed
func goodModify(s []int) {
    copy := make([]int, len(s))
    copy(copy, s)
    for i := range copy {
        copy[i] *= 2
    }
}
```

### 3. Slicing Pitfall

```go
// BAD - shares underlying array
func bad() {
    original := make([]int, 100)
    subset := original[:10]
    
    // modifying subset modifies original!
    subset[0] = 999
    fmt.Println(original[0])  // 999!
}

// GOOD - use copy or new slice
func good() {
    original := make([]int, 100)
    subset := make([]int, 10)
    copy(subset, original[:10])
    
    subset[0] = 999
    fmt.Println(original[0])  // 0 - original unchanged
}
```

## Clearing a Slice

### Option 1: Reset Length

```go
// Simple - just reset length
s := make([]int, 10)
s = s[:0]  // length 0, same capacity
```

### Option 2: Nil it Out

```go
// Release memory
s := make([]int, 10)
s = nil  // releases memory
```

### Option 3: For Large Slices

```go
// Clear to release for GC faster
s := make([]int, 10000)
for i := range s {
    s[i] = 0
}
s = s[:0]
```

## Append Tips

### Multiple Appends

```go
// Instead of
a = append(a, 1)
a = append(a, 2)
a = append(a, 3)

// Use variadic
a = append(a, 1, 2, 3)

// Or spread
b := []int{1, 2, 3}
a = append(a, b...)
```

### Append Slice to Itself

```go
// Duplicate slice
s := []int{1, 2, 3}
s = append(s, s...)  // [1,2,3,1,2,3]

// Or copy
s = append(s[:len(s):len(s)], s...)
```

### Efficient Filtering

```go
// Filter in-place
func filter(s []int, fn func(int) bool) []int {
    n := 0
    for _, v := range s {
        if fn(v) {
            s[n] = v
            n++
        }
    }
    return s[:n]
}
```

## Memory Optimization

### Stack vs Heap

```go
// Small - stack allocated
s := [3]int{1, 2, 3}

// Large - heap allocated
s := make([]int, 1000000)
```

### Reduce Allocations

```go
// BAD - allocates new slice each time
func process(items []Item) []Result {
    results := make([]Result, len(items))
    for i, item := range items {
        results[i] = transform(item)  // new slice inside?
    }
    return results
}

// GOOD - reuse if possible
func processInto(items []Item, results []Result) {
    for i, item := range items {
        results[i] = transform(item)
    }
}
```

## Iterating Efficiently

```go
// Range over index and value
for i, v := range s {
    // i: index, v: value (copy)
}

// Range over value only
for _, v := range s {
    // v: value (copy)
}

// Range over index only (fastest)
for i := range s {
    // i: index
}
```

## Key Points

- Pre-allocate with `make([]T, 0, n)`
- Use capacity to avoid reallocation
- Be careful with slicing (shares array)
- Clear with `s = nil` or `s = s[:0]`
- Use append efficiently
- Prefer index-only range when value not needed
- Benchmark to verify improvements
