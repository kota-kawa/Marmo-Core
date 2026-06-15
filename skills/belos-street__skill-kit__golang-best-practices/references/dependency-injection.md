---
name: dependency-injection
description: Dependency injection in Go - constructor injection, interface injection, and testing with mocks.
---

# Dependency Injection

> Managing dependencies in Go for testability and flexibility.

## Problem

How to manage dependencies to make code testable and flexible.

## Why Dependency Injection?

1. **Testability** - swap real implementations with mocks
2. **Flexibility** - swap implementations at runtime
3. **Decoupling** - depend on abstractions, not concretions

## Injection Methods

### 1. Constructor Injection

```go
type UserService struct {
    repo   UserRepository
    email  EmailSender
}

func NewUserService(repo UserRepository, email EmailSender) *UserService {
    return &UserService{
        repo:  repo,
        email: email,
    }
}
```

### 2. Interface Injection

```go
type Finder interface {
    Find(id int) (*User, error)
}

func ProcessUser(f Finder) error {
    user, err := f.Find(1)
    if err != nil {
        return err
    }
    return process(user)
}
```

### 3. Functional Options

```go
type Server struct {
    host string
    port int
    tls  bool
}

type Option func(*Server)

func WithHost(host string) Option {
    return func(s *Server) {
        s.host = host
    }
}

func WithPort(port int) Option {
    return func(s *Server) {
        s.port = port
    }
}

func NewServer(opts ...Option) *Server {
    s := &Server{
        host: "localhost",
        port: 8080,
    }
    for _, opt := range opts {
        opt(s)
    }
    return s
}

// Usage
server := NewServer(
    WithHost("0.0.0.0"),
    WithPort(3000),
)
```

### 4. Package-Level (Simple)

```go
// Use package-level variable (for simple cases)
var (
    repo   UserRepository
    logger Logger
)

func Init(r UserRepository, l Logger) {
    repo = r
    logger = l
}

func GetUser(id int) (*User, error) {
    return repo.Find(id)
}
```

## Testing with Mocks

### Manual Mock

```go
// Interface
type UserRepository interface {
    Find(id int) (*User, error)
    Save(user *User) error
}

// Mock
type mockUserRepository struct {
    users map[int]*User
    err   error
}

func (m *mockUserRepository) Find(id int) (*User, error) {
    if m.err != nil {
        return nil, m.err
    }
    return m.users[id], nil
}

// Test
func TestGetUser(t *testing.T) {
    mock := &mockUserRepository{
        users: map[int]*User{1: {ID: 1, Name: "John"}},
    }
    
    service := NewUserService(mock, nil)
    
    user, err := service.GetUser(1)
    assert.NoError(t, err)
    assert.Equal(t, "John", user.Name)
}
```

### Using Mockery

```go
//go:generate mockgen -destination=mocks/user_repo.go . UserRepository

import "project/mocks"

func TestWithMock(t *testing.T) {
    mock := mocks.NewUserRepository(t)
    mock.On("Find", 1).Return(&User{ID: 1}, nil)
    
    service := NewUserService(mock, nil)
    // ...
}
```

### Using counterfeiter

```go
//go:generate counterfeiter . UserRepository

// Use in test
func TestWithCounterfeiter(t *testing.T) {
    fixture := &FakeUserRepository{}
    
    service := NewUserService(fixture, nil)
    // ...
}
```

## Best Practices

### 1. Accept Interfaces, Return Concretes

```go
// GOOD - accept interface
func NewService(repo UserRepository) *Service {
    return &Service{repo: repo}
}

// GOOD - return concrete
func NewService() *Service {
    return &Service{repo: &sqlRepo{}}
}
```

### 2. Define Interfaces Where Needed

```go
// In the package that uses the interface
type UserFinder interface {
    Find(id int) (*User, error)
}

func GetUser(f UserFinder, id int) (*User, error) {
    return f.Find(id)
}
```

### 3. Use Interfaces for External Dependencies

```go
// GOOD - interface for DB, HTTP, etc.
type HTTPClient interface {
    Do(req *http.Request) (*http.Response, error)
}

// Easy to mock
type mockHTTPClient struct {
    resp *http.Response
    err  error
}
```

### 4. Don't Over-Abstract

```go
// BAD - unnecessary interface
type Adder interface {
    Add(a, b int) int
}

type adder int

func (a adder) Add(b, c int) int {
    return b + c
}

// GOOD - just use function
func Add(a, b int) int {
    return a + b
}
```

## Example: Full Service

```go
package service

type UserService struct {
    repo    UserRepository
    cache   Cache
    email   EmailSender
    logger  Logger
}

type UserRepository interface {
    Find(id int) (*User, error)
    Save(user *User) error
}

type Cache interface {
    Get(key string) (interface{}, error)
    Set(key string, value interface{}) error
}

type EmailSender interface {
    Send(to, subject, body string) error
}

type Logger interface {
    Print(v ...interface{})
}

func NewUserService(
    repo UserRepository,
    cache Cache,
    email EmailSender,
    logger Logger,
) *UserService {
    return &UserService{
        repo:  repo,
        cache: cache,
        email: email,
        logger: logger,
    }
}

func (s *UserService) GetUser(id int) (*User, error) {
    // Try cache first
    if cached, err := s.cache.Get(fmt.Sprintf("user:%d", id)); err == nil {
        return cached.(*User), nil
    }
    
    // Fetch from DB
    user, err := s.repo.Find(id)
    if err != nil {
        return nil, err
    }
    
    // Cache it
    s.cache.Set(fmt.Sprintf("user:%d", id), user)
    
    return user, nil
}
```

## DI Container (For Large Projects)

### Simple Container

```go
type Container struct {
    services map[string]interface{}
}

func NewContainer() *Container {
    return &Container{services: make(map[string]interface{})}
}

func (c *Container) Register(name string, service interface{}) {
    c.services[name] = service
}

func (c *Container) Get(name string) interface{} {
    return c.services[name]
}

// Usage
c := NewContainer()
c.Register("repo", &SQLRepository{})
c.Register("cache", &RedisCache{})

repo := c.Get("repo").(UserRepository)
```

## Key Points

- Use constructor injection for required deps
- Use functional options for optional deps
- Define interfaces where used (consumer)
- Accept interfaces, return concretes
- Don't over-abstract
- Use mocks for testing
- Use interfaces for external dependencies
