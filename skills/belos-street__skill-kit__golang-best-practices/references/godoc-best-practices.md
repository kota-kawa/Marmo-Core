---
name: godoc-best-practices
description: Writing documentation with godoc in Go - comments, examples, and documentation conventions.
---

# Godoc Best Practices

> Writing clear and useful documentation for Go packages.

## Problem

How to write documentation that is clear and helpful.

## Documentation Rules

### 1. Start with Name

```go
// Add returns the sum of a and b.
func Add(a, b int) int {
    return a + b
}
```

### 2. Use Full Sentences

```go
// Bad
// Add a + b

// Good
// Add returns the sum of a and b.
```

### 3. Explain What, Not How

```go
// Good
// User represents a user in the system.
type User struct {
    ID   int
    Name string
}
```

## Documentation Types

### Package Documentation

```go
// Package math provides basic mathematical functions.
//
// The functions generally take types float64
// and return float64 values.
package math
```

### Function Documentation

```go
// NewUser creates a new user with the given name.
// Returns nil if name is empty.
func NewUser(name string) *User {
    if name == "" {
        return nil
    }
    return &User{Name: name}
}
```

### Type Documentation

```go
// User represents a user in the system.
type User struct {
    // ID is the unique identifier.
    ID int

    // Name is the user's display name.
    Name string

    // Email is optional.
    Email string
}
```

## Examples

### Function Examples

```go
func Add(a, b int) int {
    return a + b
}

// ExampleAdd demonstrates usage.
func ExampleAdd() {
    fmt.Println(Add(1, 2))
    // Output: 3
}
```

### Multiple Examples

```go
// Example demonstrates different cases.
func ExampleAdd_multiple() {
    fmt.Println(Add(1, 2))
    fmt.Println(Add(-1, 1))
    // Output:
    // 3
    // 0
}
```

### Complete Example

```go
// Package main provides an example of using the user package.
//
// To run this example:
//
//	go run example/main.go
package main
```

## Comment Styles

### Single Line

```go
// GetUser returns a user by ID.
func GetUser(id int) (*User, error)
```

### Multiple Lines

```go
// ProcessItem processes the given item.
// It returns the processed result or an error if processing fails.
// This function is safe to call concurrently.
func ProcessItem(item *Item) (*Result, error)
```

### Block Comments

```go
/*
Package cache provides in-memory caching.

The cache is thread-safe and supports
expiration of entries.
*/
package cache
```

## Best Practices

### 1. Document Public APIs

```go
// Only document what's exported
// user.id doesn't need docs - it's private
type User struct {
    ID   int    // exported - needs doc
    name string // private - no doc needed
}
```

### 2. Be Concise

```go
// Good
// Find returns the first matching user.
func Find(fn func(User) bool) *User

// Bad
// This function will find the first user that matches
// the given predicate function and return it.
func Find(fn func(User) bool) *User
```

### 3. Document Edge Cases

```go
// Find returns the user or nil if not found.
// Returns an error if the query is invalid.
func Find(id int) (*User, error)
```

### 4. Update Docs with Code

```go
// TODO: Update doc when implementing v2
func OldFunction()
```

## Viewing Documentation

### Terminal

```bash
# Local docs
godoc -http=:6060

# View package docs
go doc package

# View function docs
go doc package.Function
```

### Online

```bash
# View docs for standard library
go doc fmt

# View specific function
go doc fmt.Printf
```

## Key Points

- Start docs with the identifier name
- Use full sentences
- Explain what, not how
- Add examples for important functions
- Document edge cases and errors
- Keep public API docs updated
- Document only exported identifiers
