---
name: time-after-leak
description: Memory leak with time.After in Go loops - how it creates goroutine leaks and proper alternatives.
---

# time.After Leak

> Understanding the goroutine leak with time.After in loops.

## Problem

Using `time.After` in loops creates goroutine leaks.

## The Problem

```go
func processWithTimeout(item string) {
    select {
    case <-time.After(time.Second):
        fmt.Println("timeout:", item)
    case <-doWork(item):
        fmt.Println("done:", item)
    }
}

func main() {
    items := []string{"a", "b", "c", "d", "e"}

    for _, item := range items {
        processWithTimeout(item)
    }

    // After this function:
    // 5 goroutines are leaked!
    // Each time.After creates a timer that never fires
}
```

### Why?

Each `time.After` creates a new timer with its own goroutine. These timers are never cleaned up because the channel is never read after the function returns.

## Memory Leak Visualization

```
Loop iteration 1: time.After() → timer goroutine 1 (leaked!)
Loop iteration 2: time.After() → timer goroutine 2 (leaked!)
Loop iteration 3: time.After() → timer goroutine 3 (leaked!)
...
Loop iteration N: time.After() → timer goroutine N (leaked!)
```

## Fix 1: Use Timeout Context

```go
import "context"

func processWithTimeout(item string) {
    ctx, cancel := context.WithTimeout(context.Background(), time.Second)
    defer cancel()

    select {
    case <-ctx.Done():
        fmt.Println("timeout:", item)
    case <-doWork(item):
        fmt.Println("done:", item)
    }
}
```

## Fix 2: Manual Timer

```go
func processWithTimeout(item string) {
    timer := time.NewTimer(time.Second)
    defer timer.Stop()

    select {
    case <-timer.C:
        fmt.Println("timeout:", item)
    case <-doWork(item):
        fmt.Println("done:", item)
    }
}
```

## Fix 3: Reuse Timer

```go
func processWithTimeout(item string, timer *time.Timer) {
    if !timer.Stop() {
        <-timer.C
    }
    timer.Reset(time.Second)

    select {
    case <-timer.C:
        fmt.Println("timeout:", item)
    case <-doWork(item):
        fmt.Println("done:", item)
    }
}

func main() {
    timer := time.NewTimer(time.Second)
    defer timer.Stop()

    items := []string{"a", "b", "c"}
    for _, item := range items {
        processWithTimeout(item, timer)
    }
}
```

## Real World Example

### Bad: HTTP Handler with Timeout

```go
func handler(w http.ResponseWriter, r *http.Request) {
    select {
    case <-time.After(5 * time.Second):
        http.Error(w, "timeout", http.StatusGatewayTimeout)
    case <-r.Context().Done():
        return
    }
}
```

Better:

```go
func handler(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
    defer cancel()

    select {
    case <-ctx.Done():
        http.Error(w, "timeout", http.StatusGatewayTimeout)
    }
}
```

## Comparison

| Method | Goroutines | Memory | Safe |
|--------|------------|--------|------|
| time.After | Leaked | Growing | ❌ |
| context.WithTimeout | Cleaned | Fixed | ✅ |
| time.NewTimer + Stop | Cleaned | Fixed | ✅ |
| Reused timer | Cleaned | Minimal | ✅ |

## Best Practices

1. **Never use time.After in loops** - creates leaks
2. **Use context.WithTimeout** - preferred
3. **Use time.NewTimer** - for single use
4. **Reuse timers** - for high frequency

## Key Points

- time.After creates goroutine leak
- Use context.WithTimeout instead
- Or use time.NewTimer with Stop
- Timer resources need cleanup
