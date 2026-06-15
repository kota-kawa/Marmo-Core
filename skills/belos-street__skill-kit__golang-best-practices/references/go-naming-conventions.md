---
name: go-naming-conventions
description: Go naming conventions for packages, variables, functions, constants, and interfaces.
---

# Go Naming Conventions

> Standard naming conventions in Go.

## Problem

How to name packages, variables, functions, and types in Go for clarity and idiomatic code.

## Solution

Follow Go's naming conventions and style guidelines.

## Package Names

### Rules

- **Short and lowercase**
- **No underscores or mixedCase**
- **Usually one word**
- **Import path suffix after final slash**

```go
package user          // good
package userService   // avoid
package UserService   // avoid
package my_package    // bad
```

### Import Path

```go
import (
    "github.com/username/project/pkg/utils"  // utils is the package name
)
```

### Package Aliases

Use aliases when needed:

```go
import (
    strconv "github.com/my/pkg/strings"  // alias to avoid conflict
)
```

## Variable Names

### Rules

- **CamelCase** (mixedCase)
- **Shorter names for shorter scope**
- **Avoid redundant type names**

```go
// Good
count := 0
user := getUser()
maxHeight := 100

// Bad - redundant
intCount := 0
userString := getUser()
maxHeightInt := 100
```

### Scope Guidelines

| Scope Length | Name Length |
|--------------|-------------|
| Short (3-4 lines) | 1-2 letters |
| Medium (screen) | Short word |
| Long (file) | Descriptive |

```go
// Short scope - short names
for i := 0; i < n; i++ {
    sum += i
}

// Medium scope
func handleRequest(req *Request) {
    ctx := context.Background()
    // ...
}

// Longer scope - more descriptive
type UserService struct {
    userRepository UserRepository
    emailSender    EmailSender
}
```

## Function Names

### Rules

- **PascalCase** for exported
- **camelCase** for unexported
- **Use verbs**: `GetUser`, `CalculateTotal`, `SendEmail`
- **Avoid redundant words**

```go
// Exported
func GetUser(id int) (*User, error)
func CalculateTotal(items []Item) float64
func SendEmail(to, subject, body string) error

// Unexported
func (u *User) validate() error
func (s *Service) processRequest() {}
```

## Constant Names

### Rules

- **PascalCase** for exported
- **camelCase** for unexported
- **Use related constants in groups**

```go
// Good
const (
    MaxConnections = 100
    DefaultTimeout = 30
    StatusActive   = "active"
)

// Related to a type
type Priority int
const (
    PriorityLow    Priority = iota
    PriorityMedium
    PriorityHigh
)
```

## Type Names

### Rules

- **PascalCase** for exported
- **camelCase** for unexported
- **Avoid redundant prefixes**

```go
// Good
type User struct{}
type Service interface{}
type Cache map[string]interface{}

// Bad - redundant
type UserStruct struct{}
type UserService struct{}
```

### Interface Naming

- **Agent nouns**: `Reader`, `Writer`, `Closer`
- **Method-oriented**: `Interface` suffix is rarely needed

```go
// Good
type Reader interface {
    Read(p []byte) (n int, err error)
}

type UserRepository interface {
    GetByID(id int) (*User, error)
    Save(user *User) error
}

// Avoid
type UserRepositoryInterface interface {}
```

## File Names

### Rules

- **Lowercase with underscores**
- **Describe functionality**
- **One word if possible**

```
user.go           // good
user_service.go   // avoid
UserService.go    // avoid
```

### Special Files

| File | Purpose |
|------|---------|
| `doc.go` | Package documentation |
| `errors.go` | Error definitions |
| `users.go` | User-related code |
| `user_test.go` | Tests for user.go |

## Acronyms

### Rules

- **Keep acronyms in original case**
- **URL, URLList** (not Url, UrlList)
- **IO, JSON, HTTP, API** - keep uppercase

```go
// Good
type URL string
type HTTPClient interface{}
type APIResponse struct{}
func JSONDecode() {}

// Bad
type Url string
type HttpClient interface{}
type ApiResponse struct{}
```

## Best Practices

1. **Clarity over brevity** - err is fine, but not e
2. **No need for Hungarian notation**
3. **Use context: names should tell you what they do**
4. **Group related constants**
5. **Be consistent** within your codebase

## Key Points

- Package: short, lowercase
- Variables/Functions: camelCase (unexported), PascalCase (exported)
- Constants: PascalCase (exported), camelCase (unexported)
- Types: PascalCase
- Files: lowercase, underscores
- Keep acronyms uppercase (HTTP, URL, JSON)
