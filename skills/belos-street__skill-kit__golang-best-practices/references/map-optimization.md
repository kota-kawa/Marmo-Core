---
name: map-optimization
description: Optimizing map usage in Go - initialization, iteration order, and performance considerations.
---

# Map Optimization

> Optimizing map operations in Go.

## Problem

Understanding map performance and optimizing for speed.

## Map Basics

```go
// Create
m := make(map[string]int)

// Add
m["key"] = 1

// Get
v := m["key"]

// Delete
delete(m, "key")
```

## Initialization

### Pre-allocation

```go
// Without pre-allocation
m := make(map[string]int)
for i := 0; i < 1000; i++ {
    m[fmt.Sprintf("key%d", i)] = i
}

// With pre-allocation - fewer rehashes
m := make(map[string]int, 1000)
for i := 0; i < 1000; i++ {
    m[fmt.Sprintf("key%d", i)] = i
}
```

## Iteration

### Unordered

**Go map iteration is random!**

```go
m := map[string]int{"a": 1, "b": 2, "c": 3}
for k, v := range m {
    fmt.Println(k, v)  // order is random each time
}
```

### Deterministic Iteration

```go
// Sort keys first
m := map[string]int{"a": 1, "b": 2, "c": 3}

keys := make([]string, 0, len(m))
for k := range m {
    keys = append(keys, k)
}
sort.Strings(keys)

for _, k := range keys {
    fmt.Println(k, m[k])  // deterministic
}
```

## Common Mistakes

### 1. Map in Loop

```go
// BAD - creates new map each iteration
func bad() []int {
    var results []int
    for i := 0; i < 10; i++ {
        m := map[string]int{"a": 1}  // new map each time!
        results = append(results, m["a"])
    }
    return results
}

// GOOD - reuse map
func good() []int {
    results := make([]int, 10)
    m := map[string]int{"a": 1}
    for i := range results {
        results[i] = m["a"]
    }
    return results
}
```

### 2. Check Before Delete

```go
// Safe - delete handles missing keys
m := map[string]int{"a": 1}
delete(m, "nonexistent")  // safe, no panic

// No need to check
if _, ok := m["key"]; ok {
    delete(m, "key")
}
```

### 3. Nil Map

```go
// Nil map - safe to read, unsafe to write
var m map[string]int
_ = m["key"]  // safe, returns zero value

m["key"] = 1  // PANIC!

// Initialize before writing
m = make(map[string]int)
m["key"] = 1  // OK
```

## Performance Tips

### 1. Use Right Size

```go
// Pre-allocate if you know size
m := make(map[K]V, expectedSize)
```

### 2. Avoid Frequent Map Creation

```go
// BAD - creates map each request
func handler() {
    m := map[string]interface{}{}
    // process
}

// GOOD - reuse or use sync.Map
var pool = sync.Pool{
    New: func() interface{} {
        return make(map[string]interface{})
    },
}

func handler() {
    m := pool.Get().(map[string]interface{})
    defer pool.Put(m)
    
    for k := range m {
        delete(m, k)
    }
    // use m
}
```

### 3. sync.Map for Concurrent

```go
// For concurrent access
var m sync.Map

// Store
m.Store("key", value)

// Load
if v, ok := m.Load("key"); ok {
    // use v
}

// Delete
m.Delete("key")

// Range
m.Range(func(key, value interface{}) bool {
    // return false to stop
    return true
})
```

## Map vs Slice

| Operation | Map | Slice |
|-----------|-----|-------|
| Lookup | O(1) avg | O(n) |
| Insert | O(1) avg | O(1) amortized |
| Iteration | Random order | Order |
| Memory | Higher | Lower |

Use map for key-value lookup.
Use slice for ordered data.

## Struct as Key

```go
type Point struct{ X, Y int }

// Can use struct as map key
m := map[Point]string{}
m[Point{1, 2}] = "origin"
```

## Key Points

- Pre-allocate with capacity hint
- Iteration order is random
- Nil map safe to read, not write
- delete is safe on missing keys
- Use sync.Map for concurrent access
- Don't create maps in loops
- Choose map for lookup, slice for order
