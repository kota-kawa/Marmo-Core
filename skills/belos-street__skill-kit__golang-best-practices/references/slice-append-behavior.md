---
name: slice-append-behavior
description: Understanding slice append behavior in Go - when slices share backing arrays and unexpected mutations.
---

# Slice Append Behavior

> Understanding how slice append works and memory sharing.

## Problem

Appending to a slice can affect another slice if they share backing arrays.

## The Problem

```go
func main() {
    // Original slice
    original := []int{1, 2, 3, 4, 5}

    // Slice with capacity
    slice := original[:3]  // [1, 2, 3]

    // Append beyond capacity
    slice = append(slice, 99)

    fmt.Println("original:", original)
    fmt.Println("slice:", slice)

    // Output:
    // original: [1, 2, 3, 99, 5]
    // slice: [1, 2, 3, 99]
    // original was modified!
}
```

### Why?

Both slices share the same backing array. When append exceeds capacity, a new array is allocated - but only sometimes!

## When Arrays are Shared

### Same Backing Array

```go
func main() {
    original := []int{1, 2, 3, 4, 5}

    // Both share same backing array
    a := original[:3]   // [1, 2, 3]
    b := original[2:]  // [3, 4, 5]

    // a modifies index 2, b sees it
    a[2] = 99
    fmt.Println(b[0])  // 99!
}
```

### After Append

```go
func main() {
    original := []int{1, 2, 3, 4, 5}
    slice := original[:3]  // capacity 5

    // No new allocation - shares backing array
    slice = append(slice, 6)
    fmt.Println(original)  // [1, 2, 3, 6, 5] - modified!

    // New allocation after capacity exceeded
    slice = append(slice, 7, 8, 9)
    fmt.Println(original)  // [1, 2, 3, 6, 5] - unchanged!
    fmt.Println(slice)     // [1, 2, 3, 6, 7, 8, 9]
}
```

## Safe Patterns

### 1. Use Full Slice Expression

```go
func main() {
    original := []int{1, 2, 3, 4, 5}

    // Full slice expression - creates copy
    slice := original[:3:3]  // capacity = length = 3

    // Now append won't affect original
    slice = append(slice, 99)
    fmt.Println("original:", original)  // [1, 2, 3, 4, 5]
    fmt.Println("slice:", slice)        // [1, 2, 3, 99]
}
```

### 2. Explicit Copy

```go
func main() {
    original := []int{1, 2, 3, 4, 5}
    slice := make([]int, 3)
    copy(slice, original[:3])

    slice = append(slice, 99)
    fmt.Println(original)  // [1, 2, 3, 4, 5] - safe
}
```

### 3. Pre-allocate with Make

```go
func main() {
    // Pre-allocate with enough capacity
    slice := make([]int, 0, 10)

    // Append won't affect anything
    slice = append(slice, 1, 2, 3)
    fmt.Println(slice)
}
```

## Function Parameters

```go
func process(s []int) {
    // May modify caller's slice if capacity > len
    s = append(s, 99)
}

func main() {
    original := []int{1, 2, 3, 4, 5}
    process(original[:3])
    fmt.Println(original)  // May be modified!
}
```

### Fix with Copy

```go
func process(s []int) {
    // Make a copy first
    s = append([]int(nil), s...)
    s = append(s, 99)
}

func main() {
    original := []int{1, 2, 3, 4, 5}
    process(original[:3])
    fmt.Println(original)  // [1, 2, 3, 4, 5] - safe
}
```

## Visual Explanation

```
original: [1, 2, 3, 4, 5]
           ↑
           backing array

slice := original[:3]
slice:   [1, 2, 3]
         ↑  ↑  ↑
         └──┼──┘
            same backing array

append(slice, 99)
slice:   [1, 2, 3, 99]
original:[1, 2, 3, 99, 5]  ← modified!
```

## Best Practices

1. **Use full slice expression** `[:3:3]` when splitting
2. **Be careful** with slice parameters
3. **Copy when needed** for safety
4. **Pre-allocate** with make when possible

## Key Points

- Slices share backing arrays
- Append can modify original
- Use `[:3:3]` for safe slicing
- Copy to be safe
