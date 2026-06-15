---
name: interface-design
description: Principles for designing interfaces in Go - small interfaces, interface composition, and avoiding bloat.
---

# Interface Design

> Best practices for designing interfaces in Go.

## Problem

How to design effective interfaces that are clear, composable, and maintainable.

## Principle: Small Interfaces

### Go Philosophy

> "The bigger the interface, the weaker the abstraction."

### Small is Beautiful

```go
// GOOD - small, focused
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type Closer interface {
    Close() error
}
```

### Large Interface is Bad

```go
// BAD - too large
type FileHandler interface {
    Read(p []byte) (n int, err error)
    Write(p []byte) (n int, err error)
    Close() error
    Seek(offset int64, whence int) (int64, error)
    Stat() (os.FileInfo, error)
    // 20 more methods...
}
```

## Interface Size Guidelines

### Recommended Sizes

| Size | Methods | Use Case |
|------|---------|----------|
| Small | 1 | Reader, Writer, Closer |
| Medium | 2-3 | ReadWriter, ReadCloser |
| Large | 4+ | Usually too big |

### Example:io Package

```go
// io.Reader - single method
// io.Writer - single method
// io.Closer - single method

// io.ReadWriter - composition
type ReadWriter interface {
    Reader
    Writer
}

// io.ReadCloser
type ReadCloser interface {
    Reader
    Closer
}
```

## Interface Composition

### Embed Interfaces

```go
type ReadWriter interface {
    Reader
    Writer
}

type ReadWriteCloser interface {
    Reader
    Writer
    Closer
}
```

### Compose from Small

```go
// GOOD - compose from smaller interfaces
type Repository interface {
    Reader
    Writer
}

type Reader interface {
    GetByID(id int) (*User, error)
    List() ([]User, error)
}

type Writer interface {
    Create(user *User) error
    Update(user *User) error
    Delete(id int) error
}
```

## Naming Conventions

### Agent Nouns

Use nouns that describe action:

```go
// Good
type Reader interface { Read(p []byte) (n int, err error) }
type Writer interface { Write(p []byte) (n int, err error) }
type Closer interface { Close() error }
```

### Avoid "Interface" Suffix

```go
// Good
type UserRepository interface { ... }

// Avoid
type UserRepositoryInterface interface { ... }
```

### Method Naming

```go
// Good - descriptive
type Cache interface {
    Get(key string) (interface{}, error)
    Set(key string, value interface{}) error
    Delete(key string) error
}

// Avoid - redundant
type CacheInterface interface {
    CacheGet(key string) (interface{}, error)
    CacheSet(key string, value interface{}) error
}
```

## Empty Interface

### Use for Unknown Types

```go
// Empty interface - any type
func printAll(items ...interface{}) {
    for _, item := range items {
        fmt.Println(item)
    }
}
```

### Use Generics Instead (Go 1.18+)

```go
// Better - type safe
func printAll[T any](items ...T) {
    for _, item := range items {
        fmt.Println(item)
    }
}
```

## Interface vs Concrete

### When to Use Interface

1. **Multiple implementations** - different DBs, caches
2. **Testing** - mock/stub
3. **Decoupling** - dependency injection

### When to Use Concrete

1. **Single implementation**
2. **Performance critical** - interface has overhead
3. **Internal code** - no need for abstraction

### Example

```go
// GOOD - interface for testing
type UserRepository interface {
    GetByID(id int) (*User, error)
}

func NewService(repo UserRepository) *Service {
    return &Service{repo: repo}
}

// In production
service := NewService(&SQLUserRepository{})

// In test
service := NewService(&MockUserRepository{})
```

### Example: Concrete Type

```go
// GOOD - concrete for internal use
type service struct {
    cache *redis.Client
    db    *sql.DB
}

// No need for interface here
```

## Defining Interfaces

### Define Where You Use Them

```go
// In package that uses the interface
type Finder interface {
    Find(id int) (*User, error)
}

func process(f Finder) {
    user, err := f.Find(1)
    // ...
}
```

### Not in Implementing Package

```go
// userrepo package
type userRepository struct {
    db *sql.DB
}

// DON'T: define interface here
// type UserRepository interface { ... }
```

## Best Practices

1. **Keep interfaces small** - 1-3 methods
2. **Name by behavior** - Reader, Writer, etc.
3. **Compose interfaces** - embed smaller ones
4. **Define near usage** - not in implementing package
5. **Use generics** - for type safety (Go 1.18+)
6. **Don't export interfaces** - unless needed

## Anti-Patterns

### 1. Large Interfaces

```go
// BAD
type DatabaseHandler interface {
    Connect() error
    Disconnect() error
    Query(query string) (*Rows, error)
    Execute(query string) (Result, error)
    Begin() (*Transaction, error)
    // ... 10 more methods
}

// GOOD
type QueryExecutor interface {
    Query(query string) (*Rows, error)
    Execute(query string) (Result, error)
}
```

### 2. Unnecessary Interfaces

```go
// BAD - only one implementation
type UserStorer interface {
    Save(u *User) error
}

type userStore struct{}

func NewUserStore() UserStorer {
    return &userStore{}
}

// GOOD - just use concrete
type userStore struct{}

func NewUserStore() *userStore {
    return &userStore{}
}
```

### 3. Interface Pollution

```go
// BAD - too many interfaces
type UserService interface {
    GetUserFinder
    UserCreator
    UserUpdater
    UserDeleter
    UserValidator
    UserFormatter
}
```

## Key Points

- Small interfaces (1-3 methods)
- Name with agent nouns
- Compose from smaller interfaces
- Define interfaces where used
- Prefer concrete types when possible
- Use generics instead of empty interface
