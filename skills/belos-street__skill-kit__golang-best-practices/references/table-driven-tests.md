---
name: table-driven-tests
description: Writing table-driven tests in Go for cleaner, more maintainable test code.
---

# Table-Driven Tests

> Writing efficient and maintainable tests in Go.

## Problem

How to write tests that are easy to maintain and extend.

## Table-Driven Tests

### Basic Structure

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
        {"mixed", -1, 2, 1},
        {"zero", 0, 0, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Add(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```

### With Error Cases

```go
func TestDivide(t *testing.T) {
    tests := []struct {
        name        string
        dividend    float64
        divisor     float64
        expected    float64
        expectError bool
    }{
        {"normal", 10, 2, 5, false},
        {"zero divisor", 10, 0, 0, true},
        {"negative", -10, 2, -5, false},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result, err := Divide(tt.dividend, tt.divisor)

            if tt.expectError {
                assert.Error(t, err)
            } else {
                assert.NoError(t, err)
                assert.Equal(t, tt.expected, result)
            }
        })
    }
}
```

## Benefits

1. **DRY** - Don't Repeat Yourself
2. **Easy to add** - just add to table
3. **Clear** - each case has a name
4. **Parallel** - can run tests in parallel
5. **Readable** - easy to see what's tested

## Testify

### Installation

```bash
go get github.com/stretchr/testify
```

### Assertions

```go
import "github.com/stretchr/testify/assert"

func TestWithAssert(t *testing.T) {
    assert.Equal(t, 4, 2+2, "math should work")
    assert.NotNil(t, object)
    assert.True(t, condition)
    assert.NoError(t, err)
    assert.Contains(t, string, substring)
}
```

### Require

```go
import "github.com/stretchr/testify/require"

func TestWithRequire(t *testing.T) {
    // Fail immediately on error
    require.NoError(t, err)
    require.NotNil(t, obj)
}
```

## Sub-tests

### Run Sub-tests

```go
func TestMath(t *testing.T) {
    t.Run("Add", func(t *testing.T) {
        if Add(1, 2) != 3 {
            t.Error("fail")
        }
    })

    t.Run("Multiply", func(t *testing.T) {
        if Multiply(2, 3) != 6 {
            t.Error("fail")
        }
    })
}
```

### Run Specific Test

```bash
go test -run TestMath/Add
go test -v -run TestMath/Multiply
```

## Table-Driven with Helpers

```go
func TestProcess(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        setup   func(*testing.T) func()
        verify  func(*testing.T, string)
    }{
        {
            name:  "valid input",
            input: "hello",
            setup: func(t *testing.T) func() {
                // setup
                return func() {
                    // teardown
                }
            },
            verify: func(t *testing.T, result string) {
                assert.Equal(t, "hello", result)
            },
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            if tt.setup != nil {
                defer tt.setup(t)()
            }
            result := Process(tt.input)
            tt.verify(t, result)
        })
    }
}
```

## Benchmark Tests

```go
func BenchmarkAdd(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Add(1, 2)
    }
}

func BenchmarkTable(b *testing.B) {
    tests := []struct {
        name string
        a, b int
    }{
        {"small", 1, 2},
        {"large", 1000, 2000},
    }

    for _, tt := range tests {
        b.Run(tt.name, func(b *testing.B) {
            for i := 0; i < b.N; i++ {
                Add(tt.a, tt.b)
            }
        })
    }
}
```

## Best Practices

1. **Use descriptive names** for test cases
2. **Group related tests** in tables
3. **Test edge cases** - empty, nil, zero
4. **Test errors** - not just happy path
5. **Use testify** for cleaner assertions
6. **Use sub-tests** for organization
7. **Keep tables small** - split if too large

## Key Points

- Table-driven tests reduce duplication
- Use `t.Run` for named sub-tests
- Test both success and error cases
- Use testify for readable assertions
- Run specific tests with `-run`
- Benchmark with table structure
