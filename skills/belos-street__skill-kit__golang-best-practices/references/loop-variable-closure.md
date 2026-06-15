---
name: loop-variable-closure
description: Common closure pitfalls in Go loops - how loop variables are captured and how to fix them.
---

# Loop Variable Closure

> Understanding the closure trap with loop variables in Go.

## Problem

Loop variables are captured by reference, not by value, leading to surprising behavior.

## The Problem

```go
func main() {
    var funcs []func()

    for i := 0; i < 3; i++ {
        funcs = append(funcs, func() {
            fmt.Println(i)  // Captures i by reference!
        })
    }

    // Call all functions
    for _, f := range funcs {
        f()
    }

    // Output:
    // 3
    // 3
    // 3
    // NOT 0, 1, 2!
}
```

### Why?

The loop variable `i` is reused each iteration. All closures capture the same variable.

## Fix 1: Create New Variable

```go
func main() {
    var funcs []func()

    for i := 0; i < 3; i++ {
        i := i  // Create new variable
        funcs = append(funcs, func() {
            fmt.Println(i)  // Captures new i
        })
    }

    // Now outputs: 0, 1, 2
    for _, f := range funcs {
        f()
    }
}
```

## Fix 2: Pass as Argument

```go
func main() {
    var funcs []func()

    for i := 0; i < 3; i++ {
        i := i
        funcs = append(funcs, func(j int) func() {
            return func() {
                fmt.Println(j)
            }
        }(i))  // Pass as argument
    }

    for _, f := range funcs {
        f()
    }
}
```

## Fix 3: Use goroutine with argument

```go
func main() {
    var funcs []func()
    var mu sync.Mutex

    for i := 0; i < 3; i++ {
        go func(i int) {
            mu.Lock()
            funcs = append(funcs, func() {
                fmt.Println(i)
            })
            mu.Unlock()
        }(i)
    }

    time.Sleep(time.Second)
    for _, f := range funcs {
        f()
    }
}
```

## With Pointers

```go
type Config struct {
    Value int
}

func main() {
    configs := []*Config{
        {Value: 1},
        {Value: 2},
        {Value: 3},
    }

    var funcs []func()

    for _, c := range configs {
        funcs = append(funcs, func() {
            fmt.Println(c.Value)  // c is reused!
        })
    }

    // All print 3!
    // Because c ends at last iteration value
}
```

### Fix: Copy pointer value

```go
for _, c := range configs {
    c := c  // Create new variable
    funcs = append(funcs, func() {
        fmt.Println(c.Value)  // Now captures correct value
    })
}
```

## In Go 1.22+ (Fixed!)

```go
// Go 1.22+ - loop variables are now per-iteration
// This now works correctly:
for i := 0; i < 3; i++ {
    funcs = append(funcs, func() {
        fmt.Println(i)  // Captures correctly!
    })
}
```

Check version:
```bash
go version
```

## Best Practices

1. **Always copy loop variable** in pre-1.22 Go
2. **Use `i := i`** pattern
3. **Pass as argument** to closures
4. **Upgrade to Go 1.22+** if possible

## Key Points

- Loop variables captured by reference
- Use `i := i` to copy
- Pass as argument
- Upgrade to Go 1.22+
