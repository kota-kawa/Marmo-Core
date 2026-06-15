---
name: goroutine-lifecycle
description: Managing goroutine lifecycle, proper startup, cleanup, and avoiding goroutine leaks.
---

# Goroutine Lifecycle Management

> Proper goroutine management and avoiding leaks.

## Problem

Managing goroutine lifecycle - starting, monitoring, and stopping goroutines properly.

## Starting Goroutines

### Basic Usage

```go
func main() {
    go sayHello()
    time.Sleep(time.Second)
}

func sayHello() {
    fmt.Println("Hello!")
}
```

### With Function Arguments

```go
func main() {
    for i := 0; i < 3; i++ {
        go func(i int) {
            fmt.Println("goroutine", i)
        }(i)  // pass as argument
    }
    time.Sleep(time.Second)
}
```

## Lifecycle Management

### Using WaitGroup

```go
import "sync"

func main() {
    var wg sync.WaitGroup
    
    for i := 0; i < 3; i++ {
        wg.Add(1)
        go func(i int) {
            defer wg.Done()
            fmt.Println("goroutine", i)
        }(i)
    }
    
    wg.Wait()  // wait for all
}
```

### Using Context for Cancellation

```go
func main() {
    ctx, cancel := context.WithCancel(context.Background())
    
    go worker(ctx, "worker1")
    go worker(ctx, "worker2")
    
    time.Sleep(2 * time.Second)
    cancel()  // signal cancellation
    time.Sleep(time.Second)
}

func worker(ctx context.Context, name string) {
    for {
        select {
        case <-ctx.Done():
            fmt.Println(name, "stopped")
            return
        default:
            fmt.Println(name, "working")
            time.Sleep(500 * time.Millisecond)
        }
    }
}
```

### Using Channel for Signaling

```go
func main() {
    done := make(chan struct{})
    
    go func() {
        for {
            select {
            case <-done:
                fmt.Println("worker stopped")
                return
            default:
                fmt.Println("working")
                time.Sleep(500 * time.Millisecond)
            }
        }
    }()
    
    time.Sleep(2 * time.Second)
    close(done)  // signal stop
    time.Sleep(time.Second)
}
```

## Avoiding Goroutine Leaks

### Leak 1: Forgotten Goroutine

```go
// BAD - goroutine never terminates
func leak() {
    ch := make(chan int)
    go func() {
        for n := range ch {
            fmt.Println(n)
        }
    }()
    ch <- 1
    ch <- 2
    // ch never closed, goroutine leaks
}
```

### Fix: Always Signal Completion

```go
// GOOD - use context or done channel
func noLeak() {
    ch := make(chan int, 10)
    done := make(chan struct{})
    
    go func() {
        for {
            select {
            case n := <-ch:
                fmt.Println(n)
            case <-done:
                fmt.Println("stopped")
                return
            }
        }
    }()
    
    ch <- 1
    ch <- 2
    close(done)
}
```

### Leak 2: Blocking Forever

```go
// BAD - goroutine blocks forever
func blockLeak() {
    ch := make(chan int)
    go func() {
        ch <- 1  // blocks forever
    }()
    // nothing receives
}
```

### Fix: Use Buffered Channel or Timeout

```go
// GOOD - with timeout
func noBlockLeak() {
    ch := make(chan int, 1)
    
    go func() {
        ch <- 1
    }()
    
    select {
    case n := <-ch:
        fmt.Println("received", n)
    case <-time.After(time.Second):
        fmt.Println("timeout")
    }
}
```

### Leak 3: Goroutine in select with No Case

```go
// BAD - blocks forever
func noCaseLeak() {
    done := make(chan struct{})
    
    go func() {
        select {
        case <-done:
            return
        // no default, blocks if nothing sends to done
        }
    }()
}
```

## Best Practices

### 1. Always Have Exit Strategy

```go
func worker(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            return
        // work
        }
    }
}
```

### 2. Use sync.WaitGroup for Known Count

```go
func processItems(items []Item) {
    var wg sync.WaitGroup
    
    for _, item := range items {
        wg.Add(1)
        go func(item Item) {
            defer wg.Done()
            process(item)
        }(item)
    }
    
    wg.Wait()
}
```

### 3. Limit Concurrent Goroutines

```go
func limitedWorker(jobs <-chan int, workers int) {
    var wg sync.WaitGroup
    
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs {
                process(job)
            }
        }()
    }
    
    wg.Wait()
}
```

### 4. Use errgroup for Group Operations

```go
import "golang.org/x/sync/errgroup"

func parallel() error {
    g := new(errgroup.Group)
    
    var urls = []string{
        "http://golang.org",
        "http://google.com",
    }
    
    for _, url := range urls {
        url := url
        g.Go(func() error {
            _, err := http.Get(url)
            return err
        })
    }
    
    return g.Wait()  // returns first error
}
```

## Monitoring

### Adding Logging

```go
func worker(ctx context.Context, id int) {
    fmt.Printf("worker %d started\n", id)
    defer fmt.Printf("worker %d stopped\n", id)
    
    for {
        select {
        case <-ctx.Done():
            return
        // work
        }
    }
}
```

## Key Points

- Always have exit strategy
- Use WaitGroup for known count
- Use context for cancellation
- Use buffered channels to prevent blocking
- Limit concurrent goroutines
- Add logging for debugging
- Use errgroup for group operations
