---
name: go-mocking
description: Mocking techniques in Go - interfaces, manual mocks, mockgen, and counterfeiter.
---

# Mocking in Go

> Techniques for mocking dependencies in Go tests.

## Problem

How to mock dependencies for testing in Go.

## Why Mock?

1. **Test isolation** - don't depend on external services
2. **Speed** - no network/database calls
3. **Reliability** - tests don't fail due to external issues
4. **Coverage** - test error paths

## Interface-Based Mocking

### Define Interface

```go
// Define interface in consumer package
type UserRepository interface {
    GetByID(id int) (*User, error)
    Save(user *User) error
}
```

### Implement Mock

```go
// Manual mock
type MockUserRepository struct {
    Users  map[int]*User
    GetByIDFunc func(id int) (*User, error)
    SaveFunc   func(user *User) error
    Err       error
}

func (m *MockUserRepository) GetByID(id int) (*User, error) {
    if m.GetByIDFunc != nil {
        return m.GetByIDFunc(id)
    }
    if m.Err != nil {
        return nil, m.Err
    }
    return m.Users[id], nil
}

func (m *MockUserRepository) Save(user *User) error {
    if m.SaveFunc != nil {
        return m.SaveFunc(user)
    }
    if m.Err != nil {
        return m.Err
    }
    m.Users[user.ID] = user
    return nil
}
```

### Use Mock in Test

```go
func TestGetUser(t *testing.T) {
    mock := &MockUserRepository{
        Users: map[int]*User{
            1: {ID: 1, Name: "John"},
        },
    }

    service := NewUserService(mock)

    user, err := service.GetUser(1)
    assert.NoError(t, err)
    assert.Equal(t, "John", user.Name)
}
```

## Mockgen

### Installation

```bash
go install github.com/golang/mock/mockgen@v1.6.0
```

### Generate Mock

```go
//go:generate mockgen -destination=mocks/user_repo.go . UserRepository

type UserRepository interface {
    GetByID(id int) (*User, error)
    Save(user *User) error
}
```

Run:
```bash
go generate ./...
```

### Use Generated Mock

```go
import "mocks"

func TestWithMockgen(t *testing.T) {
    ctrl := gomock.NewController(t)
    defer ctrl.Finish()

    mock := mocks.NewMockUserRepository(ctrl)

    mock.EXPECT().GetID(1).Return(&User{ID: 1}, nil)

    service := NewUserService(mock)
    // test
}
```

## Counterfeiter

### Installation

```bash
go install github.com/maxbrunsfeld/counterfeiter/v6@latest
```

### Generate Fake

```go
//go:generate counterfeiter . UserRepository

type UserRepository interface {
    GetByID(id int) (*User, error)
    Save(user *User) error
}
```

Run:
```bash
go generate ./...
```

### Use Fake

```go
import "fakes"

func TestWithFake(t *testing.T) {
    fake := &fakes.FakeUserRepository{}

    // Stub
    fake.GetByIDReturns(&User{ID: 1}, nil)

    service := NewUserService(fake)

    user, err := service.GetUser(1)
    assert.NoError(t, err)
    assert.Equal(t, 1, fake.GetByIDCallCount())
}
```

## HTTP Mocking

### httptest

```go
import "net/http/httptest"

func TestHTTP(t *testing.T) {
    handler := func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte(`{"id": 1}`))
    }

    server := httptest.NewServer(http.HandlerFunc(handler))
    defer server.Close()

    resp, err := http.Get(server.URL)
    assert.NoError(t, err)
    assert.Equal(t, http.StatusOK, resp.StatusCode)
}
```

### httpmock

```go
import "github.com/jarcoal/httpmock"

func TestWithHttpmock(t *testing.T) {
    httpmock.Activate()
    defer httpmock.DeactivateAndReset()

    httpmock.RegisterResponder(
        "GET",
        "http://api.example.com/user/1",
        httpmock.NewJsonResponderOrPanic(200, User{ID: 1}),
    )

    // test
}
```

## Database Mocking

### SQL Mock

```go
import "github.com/DATA-DOG/go-sqlmock"

func TestDB(t *testing.T) {
    db, mock, err := sqlmock.New()
    assert.NoError(t, err)
    defer db.Close()

    mock.ExpectQuery("SELECT.*").
        WithArgs(1).
        WillReturnError(sql.ErrNoRows)

    // test
}
```

## Best Practices

1. **Define interfaces** where you use them
2. **Keep interfaces small** - easier to mock
3. **Use mockgen or counterfeiter** for generated mocks
4. **Test both success and error** paths
5. **Verify calls** - check mock was called
6. **Don't mock everything** - sometimes real is better

## Key Points

- Define interfaces in consumer package
- Use mockgen for generated mocks
- Use httptest for HTTP testing
- Use sqlmock for database testing
- Verify mock calls were made
- Test error paths
