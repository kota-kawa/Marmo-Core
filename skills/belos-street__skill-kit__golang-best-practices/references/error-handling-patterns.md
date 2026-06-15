---
name: error-handling-patterns
description: Go error handling patterns, error creation, checking, and best practices for error management.
---

# Error Handling Patterns

> Best practices for handling errors in Go.

## Problem

How to handle errors properly in Go without using exceptions.

## Solution

Go uses explicit error returns. This is a design feature, not a limitation.

## Basic Error Handling

### Return Errors

```go
func Divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}

// Usage
result, err := Divide(10, 0)
if err != nil {
    log.Fatal(err)
}
```

### Error Checking

```go
// Check error type
if err != nil {
    return err
}

// Check specific error
if errors.Is(err, ErrNotFound) {
    // handle not found
}

// Check error type assertion
var pathError *os.PathError
if errors.As(err, &pathError) {
    fmt.Println("Failed at path:", pathError.Path)
}
```

## Creating Errors

### errors.New

For simple static errors:

```go
var ErrNotFound = errors.New("resource not found")
var ErrUnauthorized = errors.New("unauthorized")
```

### fmt.Errorf

For formatted error messages:

```go
func GetUser(id int) (*User, error) {
    user, err := findUser(id)
    if err != nil {
        return nil, fmt.Errorf("failed to get user %d: %w", id, err)
    }
    return user, nil
}
```

### Custom Error Types

For rich error information:

```go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

// Usage
return nil, &ValidationError{Field: "email", Message: "invalid format"}
```

## Error Wrapping

### With %w

Preserve the original error chain:

```go
func ReadFile(path string) ([]byte, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("read file %s: %w", path, err)
    }
    return data, nil
}

// Check wrapped errors
if errors.Is(err, os.ErrNotFound) {
    // works even if wrapped
}
```

### With %v

When you don't need error chain:

```go
return nil, fmt.Errorf("invalid input: %v", err)
```

## Error Handling Patterns

### Guard Clauses

```go
func ProcessUser(user *User) error {
    if user == nil {
        return errors.New("user is nil")
    }
    if user.ID == 0 {
        return errors.New("user ID is required")
    }
    // main logic
    return nil
}
```

### Handle Errors at the Boundary

```go
func main() {
    if err := run(); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
}
```

### errors.Join

For multiple errors:

```go
func Validate(req *Request) error {
    var errs []error
    
    if req.Name == "" {
        errs = append(errs, errors.New("name is required"))
    }
    if req.Email == "" {
        errs = append(errs, errors.New("email is required"))
    }
    
    if len(errs) > 0 {
        return errors.Join(errs...)
    }
    return nil
}
```

## Error Constants (Sentinel Errors)

### Define Sentinel Errors

```go
var (
    ErrNotFound     = errors.New("not found")
    ErrUnauthorized = errors.New("unauthorized")
    ErrForbidden    = errors.New("forbidden")
)
```

### Use in Code

```go
func GetUser(id int) (*User, error) {
    user, err := findUser(id)
    if err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return nil, ErrNotFound
        }
        return nil, err
    }
    return user, nil
}
```

## Best Practices

1. **Don't ignore errors** - always handle or explicitly ignore
2. **Wrap with context** - use `%w` to preserve error chain
3. **Use sentinel errors** - for known error conditions
4. **Custom error types** - for rich error information
5. **Error at boundaries** - handle errors at package edges

## Common Mistakes

### Ignoring Errors

```go
// Bad
_ = os.ReadFile("file.txt")

// Good
data, err := os.ReadFile("file.txt")
if err != nil {
    return err
}
```

### Redundant Error Wrapping

```go
// Bad - double wrapping
if err != nil {
    return fmt.Errorf("failed: %w", err)
}

// Good - wrap once with context
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}
```

### Error Strings

```go
// Bad - starting with lowercase
return errors.New("invalid email")

// Good - starting with capital (for user-facing)
return errors.New("Invalid email")
```

## Key Points

- Errors are values - treat them as such
- Use `errors.New` for static errors
- Use `fmt.Errorf` with `%w` for wrapping
- Use `errors.Is` and `errors.As` for checking
- Don't ignore errors unless intentionally
- Error messages should be descriptive
