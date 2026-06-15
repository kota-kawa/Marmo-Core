---
name: go-nil-handling
description: Understanding nil in Go - nil slices, maps, interfaces, and pointers. Common nil pitfalls.
---

# Understanding nil in Go

> How nil works in Go and common pitfalls.

## Problem

nil in Go can be confusing. Different types have different nil behaviors.

## nil for Different Types

### Pointer

```go
var p *int
fmt.Println(p == nil)  // true

p = new(int)
fmt.Println(p == nil)  // false
fmt.Println(*p)        // 0
```

### Slice

```go
var s []int
fmt.Println(s == nil)   // true
fmt.Println(len(s))     // 0
fmt.Println(s[:])       // panics? No! works fine

// Append works on nil slice
s = append(s, 1)  // works
```

### Map

```go
var m map[string]int
fmt.Println(m == nil)   // true
fmt.Println(len(m))     // 0

// Read from nil map returns zero value
fmt.Println(m["key"])   // 0

// Write to nil map PANICS
m["key"] = 1  // panic: assignment to entry in nil map
```

### Interface

```go
var err error
fmt.Println(err == nil)  // true

err = errors.New("error")
fmt.Println(err == nil)  // false

// nil interface with typed nil
var r io.Reader
var t *bytes.Buffer
r = t
fmt.Println(r == nil)  // false! interface holds typed nil
```

### Channel

```go
var c chan int
fmt.Println(c == nil)  // true

// Receive from nil channel blocks forever
// Send to nil channel blocks forever
// Close nil channel panics
```

## Common Pitfalls

### Pitfall 1: Interface with Typed nil

```go
// Bad
func getReader() io.Reader {
    var b *bytes.Buffer
    return b  // returns nil typed *bytes.Buffer
}

r := getReader()
if r == nil {  // false!
    fmt.Println("is nil")
}

// Good
func getReader() io.Reader {
    return nil  // truly nil
}
```

### Pitfall 2: Nil Check on Value Receiver

```go
type Config struct {
    Name string
}

func (c Config) IsEmpty() bool {
    return c.Name == ""
}

var cfg *Config
// cfg is nil, but calling IsEmpty works
// because value receiver creates a copy
fmt.Println(cfg.IsEmpty())  // works, but Name is ""
```

### Pitfall 3: Map Assignment

```go
// Bad
func addToMap(m map[string]int, key string, val int) {
    m[key] = val  // panic if m is nil
}

// Good
func addToMap(m map[string]int, key string, val int) {
    if m == nil {
        m = make(map[string]int)
    }
    m[key] = val
}
```

### Pitfall 4: JSON Marshal

```go
// nil slice marshals to "null" in JSON
var s []string
json.Marshal(s)  // "null"

// Empty slice marshals to "[]"
s = []string{}
json.Marshal(s)  // "[]"

// Same for map
var m map[string]int
json.Marshal(m)  // "null"
m = map[string]int{}
json.Marshal(m)  // "{}"
```

## Safe Patterns

### Return True nil for Interfaces

```go
// Good - return nil interface
func findUser(id int) (*User, error) {
    if notFound {
        return nil, nil  // both are nil
    }
    return user, nil
}

// Check both
user, err := findUser(1)
if err != nil {
    return err
}
if user == nil {
    return errors.New("not found")
}
```

### Initialize Maps and Slices

```go
// Initialize before use
users := make(map[string]*User)
// or
users := map[string]*User{}

// Initialize slices when needed
items := make([]Item, 0, 10)  // with capacity
```

### Check Interface Properly

```go
var r io.Reader
var b *bytes.Buffer

r = b
if r == nil {
    fmt.Println("truly nil")
}

// Use reflection to check typed nil
import "reflect"

if reflect.ValueOf(r).IsNil() {
    fmt.Println("typed nil")
}
```

## Best Practices

1. **Initialize maps** before writing
2. **Return nil interfaces** correctly
3. **Check both error and value**
4. **nil slices are safe** - can read and append
5. **nil maps are unsafe** - read returns zero, write panics
6. **nil channels** block forever

## Key Points

- nil slices: len=0, can append
- nil maps: len=0, read OK, write PANICS
- nil interfaces: check type too
- nil channels: block forever
- Initialize before writing to maps
- Return truly nil for interfaces
