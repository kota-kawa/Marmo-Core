---
name: escape-analysis
description: Understanding Go's escape analysis, how Go decides stack vs heap allocation, and how to write allocation-efficient code.
---

# Escape Analysis

> How Go decides where to allocate memory.

## Problem

Understanding when variables escape to the heap and how to control allocation.

## What is Escape Analysis?

Go compiler analyzes code to decide:
- **Stack allocation** - fast, no GC needed
- **Heap allocation** - slower, needs GC

The compiler does this automatically.

## How to See Escapes

```bash
# Show escape analysis
go build -gcflags '-m' main.go

# More detail
go build -gcflags '-m -m' main.go
```

### Example Output

```go
package main

func main() {
    s := "hello"
    print(s)
}
```

```
./main.go:5:10: s does not escape
```

### Another Example

```go
func newUser() *User {
    return &User{Name: "John"}
}
```

```
./main.go:3:9: &User escapes to heap
```

## Rules of Escape

### 1. Returning a Pointer

```go
// Escapes - returned
func newUser() *User {
    return &User{}
}

// Doesn't escape - not returned
func createUser(u *User) {
    u.Name = "John"
}
```

### 2. Passing to Interface

```go
func printSomething(v interface{}) {
    fmt.Println(v)
}

func main() {
    s := "hello"
    printSomething(s)  // s escapes to heap
}
```

### 3. Slicing Beyond Capacity

```go
func sliceEscape() {
    s := make([]int, 10)
    // s[20:] creates new slice, escapes
    _ = s[20:]
}
```

### 4. Adding to Map

```go
func mapEscape() {
    m := make(map[string]int)
    m["key"] = 1  // map escapes
}
```

### 5. Closure Captures Variables

```go
func closureEscape() {
    x := 10
    f := func() int {
        return x  // x escapes to heap
    }
    _ = f()
}
```

## Common Escape Scenarios

### Returning Pointer

```go
// BAD - escapes
func getUser() *User {
    u := User{ID: 1}
    return &u  // u escapes
}

// BETTER - return value
func getUser() User {
    u := User{ID: 1}
    return u  // u can be optimized to stack
}
```

### Interface Methods

```go
// BAD - allocates interface
func printAll(items ...interface{}) {
    for _, item := range items {
        fmt.Println(item)
    }
}

// BETTER - use generics (Go 1.18+)
func printAll[T any](items ...T) {
    for _, item := range items {
        fmt.Println(item)
    }
}
```

### Closures

```go
// BAD - variable escapes
func main() {
    result := 0
    go func() {
        result++  // result escapes
    }()
    time.Sleep(time.Millisecond)
}

// BETTER - pass as argument
func main() {
    result := 0
    go func(r *int) {
        *r++
    }(&result)
    time.Sleep(time.Millisecond)
}
```

## Performance Tips

### 1. Return Values When Possible

```go
// Instead of
func getConfig() *Config {
    return &Config{Host: "localhost"}
}

// Consider
func getConfig() Config {
    return Config{Host: "localhost"}
}
```

### 2. Use Values for Small Types

```go
// Small structs - use values
type Point struct{ X, Y int }

func newPoint() Point {
    return Point{X: 1, Y: 2}
}
```

### 3. Avoid Interface When Possible

```go
// Instead of
func process(v io.Reader) {}

// Use concrete type when possible
func process(r *bytes.Buffer) {}
```

### 4. Pre-allocate in Loop

```go
// Before - escapes each iteration
func collect() []int {
    var result []int
    for i := 0; i < 10; i++ {
        result = append(result, i)
    }
    return result
}

// After - stack allocated
func collect() []int {
    result := make([]int, 10)
    for i := 0; i < 10; i++ {
        result[i] = i
    }
    return result
}
```

## Measuring Allocations

```go
import "testing"

func BenchmarkEscape(b *testing.B) {
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        _ = newUser()
    }
}
```

## Best Practices

1. **Don't optimize prematurely** - profile first
2. **Use -gcflags '-m'** to see escapes
3. **Return values** when possible
4. **Avoid interfaces** when not needed
5. **Pass pointers to closures** when safe
6. **Pre-allocate slices** in loops

## Key Points

- Compiler decides stack vs heap
- Use `go build -gcflags '-m'` to see escapes
- Returning pointers causes escape
- Interface causes escape
- Closures can cause escape
- Don't optimize without profiling
