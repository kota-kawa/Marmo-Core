---
name: concurrency-pitfalls
description: Common concurrency pitfalls in Go - race conditions, deadlocks, goroutine leaks, and how to avoid them.
---

# Concurrency Pitfalls

> Common mistakes and how to avoid them.

## Problem

Common concurrency bugs that cause race conditions, deadlocks, and goroutine leaks.

## Race Condition

### What is a Race?

```go
// BAD - race condition
func main() {
    count := 0
    var wg sync.WaitGroup
    
    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            count++  // race on count
        }()
    }
    
    wg.Wait()
    fmt.Println(count)  // likely not 1000
}
```

### Fix with Mutex

```go
// GOOD - using mutex
func main() {
    var mu sync.Mutex
    count := 0
    var wg sync.WaitGroup
    
    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            mu.Lock()
            count++
            mu.Unlock()
        }()
    }
    
    wg.Wait()
    fmt.Println(count)  // 1000
}
```

### Fix with Atomic

```go
// GOOD - using atomic
func main() {
    var count int64
    var wg sync.WaitGroup
    
    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            atomic.AddInt64(&count, 1)
        }()
    }
    
    wg.Wait()
    fmt.Println(count)  // 1000
}
```

### Detect Race

```bash
go run -race main.go
go test -race ./...
```

## Deadlock

### 1. Unordered Mutex

```go
// BAD - potential deadlock
func (a *A) Method1() {
    a.mu.Lock()
    b.Method2()  // might lock b
    a.mu.Unlock()
}

func (b *B) Method2() {
    b.mu.Lock()
    a.Method1()  // might lock a - deadlock!
    b.mu.Unlock()
}
```

### Fix: Always Lock in Same Order

```go
// GOOD - consistent lock order
func (a *A) Method1() {
    a.mu.Lock()
    defer a.mu.Unlock()
    b.Method2Safe()  // doesn't acquire a's lock
}
```

### 2. Channel in Lock

```go
// BAD - deadlock
func (s *Service) Process() {
    s.mu.Lock()
    ch := make(chan int)
    go func() { ch <- 1 }()
    <-ch  // deadlock - holding lock, waiting for goroutine
    s.mu.Unlock()
}
```

### Fix: Don't Block in Lock

```go
// GOOD - release lock before blocking
func (s *Service) Process() {
    s.mu.Lock()
    data := s.data
    s.mu.Unlock()
    
    ch := make(chan int)
    go func() { ch <- 1 }()
    <-ch
}
```

### 3. No Default in Select

```go
// BAD - deadlock if no case ready
func main() {
    ch := make(chan int)
    select {
    case <-ch:
        fmt.Println("received")
    // no default, blocks forever if nothing sent
    }
}
```

### Fix: Add Default

```go
// GOOD - non-blocking
func main() {
    ch := make(chan int)
    select {
    case n := <-ch:
        fmt.Println("received:", n)
    default:
        fmt.Println("no data")
    }
}
```

## Goroutine Leaks

### 1. Forgetting to Close Channel

```go
// BAD - goroutine leaks
func produce() <-chan int {
    ch := make(chan int)
    go func() {
        for i := 0; i < 10; i++ {
            ch <- i
        }
        // never closes or signals
    }()
    return ch
}
```

### Fix: Always Close or Signal

```go
// GOOD
func produce() <-chan int {
    ch := make(chan int)
    go func() {
        for i := 0; i < 10; i++ {
            ch <- i
        }
        close(ch)  // signal completion
    }()
    return ch
}
```

### 2. No Receiver

```go
// BAD - goroutine leaks
func main() {
    ch := make(chan int)
    go func() {
        for {
            ch <- 1  // blocks forever
        }
    }()
    time.Sleep(time.Second)
    // main exits, goroutine never terminates
}
```

### Fix: Use Context or Done Channel

```go
// GOOD
func main() {
    done := make(chan struct{})
    ch := make(chan int)
    
    go func() {
        for {
            select {
            case <-done:
                close(ch)
                return
            case ch <- 1:
            }
        }
    }()
    
    time.Sleep(time.Second)
    close(done)
    time.Sleep(time.Second)
}
```

### 3. time.After in Loop

```go
// BAD - creates new timer each iteration
func processLoop() {
    for {
        select {
        case <-time.After(time.Second):  // new timer each loop!
            fmt.Println("tick")
        // handle other cases
        }
    }
}
```

### Fix: Use Ticker

```go
// GOOD
func processLoop() {
    ticker := time.NewTicker(time.Second)
    defer ticker.Stop()
    
    for {
        select {
        case <-ticker.C:
            fmt.Println("tick")
        // handle other cases
        }
    }
}
```

## Mutex Pitfalls

### Copying Mutex

```go
// BAD - copying mutex
type Counter struct {
    mu sync.Mutex
    n  int
}

func main() {
    c := Counter{}
    c2 := c  // copies mutex!
    c2.mu.Lock()  // may panic or behave incorrectly
}
```

### Fix: Use Pointer

```go
// GOOD
type Counter struct {
    mu sync.Mutex
    n  int
}

func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.n++
}
```

## WaitGroup Pitfalls

### Not Adding Before Go

```go
// BAD - race
var wg sync.WaitGroup

for i := 0; i < 10; i++ {
    go func() {
        defer wg.Done()
        // work
    }()
}
wg.Wait()  // might not wait at all
```

### Fix: Add Before Go

```go
// GOOD
var wg sync.WaitGroup

for i := 0; i < 10; i++ {
    wg.Add(1)
    go func() {
        defer wg.Done()
        // work
    }()
}
wg.Wait()
```

## Best Practices

1. **Use -race flag** to detect races
2. **Keep lock order consistent** to avoid deadlocks
3. **Don't block while holding locks**
4. **Always close or signal channels**
5. **Use context** for cancellation
6. **Use ticker, not time.After** in loops
7. **Don't copy mutexes**
8. **Add to WaitGroup before goroutine**

## Key Points

- Race: use mutex, atomic, or channels
- Deadlock: consistent lock order, no blocking in locks
- Leaks: close channels, use context, use ticker
- Copy mutex: use pointer receiver
- WaitGroup: add before goroutine
- Test with -race flag
