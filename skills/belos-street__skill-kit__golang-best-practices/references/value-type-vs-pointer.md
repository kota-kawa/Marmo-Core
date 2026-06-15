---
name: value-type-vs-pointer
description: Understanding when to use value types vs pointers in Go for performance and correctness.
---

# Value Types vs Pointers

> When to use value types and when to use pointers in Go.

## Problem

When to use value types (T) and when to use pointer types (*T) in Go.

## Value Types vs Pointer Types

| Type | Allocation | Copy Behavior |
|------|------------|----------------|
| `T` (value) | Stack (usually) | Full copy |
| `*T` (pointer) | Heap | Reference sharing |

## When to Use Values

### Small Types

For small types, value copies are cheap:

```go
// Good - small types, copied directly
type Point struct {
    X int
    Y int
}

func NewPoint(x, y int) Point {
    return Point{X: x, Y: y}
}

// No need for pointer
p := NewPoint(1, 2)
```

### Built-in Types

```go
// Good - use values for built-in types
count := 0
name := "Alice"
isActive := true
```

### Function Parameters

If you don't need to modify the original:

```go
func PrintUser(user User) {
    // user is a copy - safe to read
    fmt.Println(user.Name)
}
```

## When to Use Pointers

### Large Types

For large structs, pointer avoids copy overhead:

```go
type Config struct {
    Host        string
    Port        int
    Timeout     time.Duration
    MaxRetries  int
    TLSConfig   *tls.Config
    // ... many more fields
}

// Good - avoid copying large struct
func LoadConfig(path string) (*Config, error) {
    // ...
}
```

### Mutating Receiver

If the method needs to modify the receiver:

```go
func (u *User) SetName(name string) {
    u.Name = name  // modifies the original
}

// Using value would not work
func (u User) SetNameBad(name string) {
    u.Name = name  // modifies a copy, discarded
}
```

### Nil Valid State

When nil is a valid state:

```go
type Cache struct {
    data map[string]interface{}
}

func NewCache() *Cache {
    return &Cache{data: make(map[string]interface{})}
}

// nil is valid for pointer
var cache *Cache  // empty cache, no allocation
```

### Memory Allocation

When you need heap allocation for interface compliance:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

// Must return pointer for interface
func (f *File) Read(p []byte) (n int, err error)
```

## Comparison Examples

### Wrong

```go
// Bad - copying large struct
func processLargeData(data BigStruct) {
    // data is a copy
}

processLargeData(myBigStruct)  // expensive copy
```

### Correct

```go
// Good - using pointer for large struct
func processLargeData(data *BigStruct) {
    // only pointer is copied
}

processLargeData(&myBigStruct)  // cheap
```

## Benchmark Example

```go
type Small struct {
    A, B int
}

type Large struct {
    A, B, C, D, E, F, G, H int
}

func BenchmarkSmallValue(b *testing.B) {
    s := Small{}
    for i := 0; i < b.N; i++ {
        f(s)
    }
}

func BenchmarkSmallPointer(b *testing.B) {
    s := &Small{}
    for i := 0; i < b.N; i++ {
        f(s)
    }
}
```

## Best Practices

1. **Start with values** - Go defaults to values
2. **Profile first** - optimize after measuring
3. **Use pointers for mutation** - when you need to modify
4. **Use pointers for large types** - > 2-3 fields
5. **Use pointers for nil** - when nil is meaningful
6. **Be consistent** - within a codebase

## Key Points

- Small types: use values
- Large structs: use pointers
- Need mutation: use pointer receiver
- Need nil: use pointer
- Interface methods: return pointers
- Default to values, optimize after profiling
