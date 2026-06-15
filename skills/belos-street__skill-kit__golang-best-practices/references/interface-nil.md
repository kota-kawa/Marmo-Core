---
name: interface-nil
description: Understanding nil interfaces in Go - interface with typed nil, nil checks, and common pitfalls.
---

# Interface and nil

> Understanding nil interfaces and how to handle them correctly.

## Problem

nil interfaces can be confusing in Go. Understanding the difference between truly nil and typed nil.

## Interface Structure

An interface has two components:
- **Type** (can be nil)
- **Value** (can be nil)

```go
type Error interface {
    Error() string
}
```

### Truly Nil Interface

```go
var err error  // err is nil
// Type: nil
// Value: nil

fmt.Println(err == nil)  // true
```

### Typed Nil (Not Really nil!)

```go
var b *bytes.Buffer
var err error = b

// err is NOT nil!
// Type: *bytes.Buffer
// Value: nil

fmt.Println(err == nil)  // false!
fmt.Println(err)         // <nil>
```

## The Problem

```go
func getReader() io.Reader {
    var b *bytes.Buffer
    return b  // returns "nil" but type is *bytes.Buffer
}

r := getReader()
if r == nil {  // FALSE!
    fmt.Println("is nil")
}
// Actually r is NOT nil, but r.Read() would panic!
```

### Why This Happens

```go
// Interface representation (simplified)
type emptyInterface struct {
    typ unsafe.Pointer  // type pointer
    val unsafe.Pointer  // value pointer
}

var err error = (*bytes.Buffer)(nil)
// typ = typeOf(*bytes.Buffer)
// val = nil
// err is not nil!
```

## Correct Way to Return nil

```go
// BAD
func getReader() io.Reader {
    var b *bytes.Buffer
    return b  // typed nil, NOT nil
}

// GOOD
func getReader() io.Reader {
    return nil  // truly nil
}

// ALSO GOOD - return error separately
func getReader() (io.Reader, error) {
    var b *bytes.Buffer
    return b, nil  // this is OK - checked separately
}
```

## Checking for nil Interface

### Option 1: Return Error Separately

```go
// BEST - return error separately
func findUser(id int) (*User, error) {
    if notFound {
        return nil, ErrNotFound  // value is nil, error is not
    }
    return user, nil
}

user, err := findUser(1)
if err != nil {
    // handle error
}
if user == nil {
    // user is truly nil
}
```

### Option 2: Check Type First

```go
var r io.Reader
var b *bytes.Buffer
r = b

// Check if interface is truly nil
if r == nil {
    fmt.Println("truly nil")
} else {
    fmt.Println("typed nil")  // this prints!
}
```

### Option 3: Use Reflection

```go
import "reflect"

var r io.Reader
var b *bytes.Buffer
r = b

// Check typed nil
if reflect.ValueOf(r).IsNil() {
    fmt.Println("interface is nil (typed nil)")
}
```

## Common Mistakes

### Mistake 1: Returning Typed nil

```go
// BAD
func getError() error {
    var err *MyError
    return err  // typed nil!
}

// GOOD
func getError() error {
    return nil  // truly nil
}
```

### Mistake 2: Checking Interface Directly

```go
// BAD
func process(r io.Reader) {
    if r == nil {  // may be typed nil!
        return
    }
    r.Read(buf)  // might panic!
}

// GOOD - check with ok
func process(r io.Reader) {
    if r == nil {
        return
    }
    // safe to use
}
```

### Mistake 3: Interface as Error

```go
// BAD
func doSomething() error {
    var err error = (*CustomError)(nil)
    return err  // returns typed nil!
}

// GOOD
func doSomething() error {
    return nil  // truly nil
}
```

## Safe Patterns

### Pattern 1: Separate Error Return

```go
// Always return error separately
func findUser(id int) (*User, error) {
    return nil, ErrNotFound
}

// Usage
user, err := findUser(1)
if err != nil {
    return err
}
// user is safe to use
```

### Pattern 2: Return Truly nil

```go
// Return truly nil when no error
func getReader() io.Reader {
    return nil  // truly nil
}

// Check
r := getReader()
if r == nil {  // true!
    fmt.Println("no reader")
}
```

### Pattern 3: Use Pointers for Optional

```go
// If you need optional, use pointer
type Config struct {
    Name string
    Timeout *time.Duration  // nil = not set
}

func NewConfig() *Config {
    return nil  // truly nil - no config
}
```

## Testing for nil Interface

```go
func isNil(i interface{}) bool {
    if i == nil {
        return true
    }
    // Use reflection for typed nil
    v := reflect.ValueOf(i)
    return v.Kind() == reflect.Ptr && v.IsNil()
}

// Usage
var r io.Reader
var b *bytes.Buffer
r = b

fmt.Println(r == nil)           // false
fmt.Println(isNil(r))           // true
```

## Summary Table

| Code | Type | Value | == nil? |
|------|------|-------|---------|
| `var e error` | nil | nil | true |
| `var e error = nil` | nil | nil | true |
| `var b *bytes.Buffer` | nil | nil | N/A |
| `var e error = b` | *bytes.Buffer | nil | **false** |

## Best Practices

1. **Return nil, not typed nil** - for interfaces
2. **Return error separately** - for errors
3. **Be careful with error variables** - typed nil trap
4. **Test with reflect** - for edge cases
5. **Use pointers** - for optional values

## Key Points

- Interface nil has both type and value nil
- Typed nil: type is set, value is nil → not == nil
- Always return truly nil for interfaces
- Return errors separately
- Use reflection to check typed nil
- Be careful with error variables
