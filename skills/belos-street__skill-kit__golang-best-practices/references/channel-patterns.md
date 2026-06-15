---
name: channel-patterns
description: Common channel patterns in Go - unbuffered, buffered, select, and channel direction.
---

# Channel Patterns

> Common and idiomatic channel patterns in Go.

## Problem

How to use channels effectively for goroutine communication.

## Channel Basics

### Unbuffered Channel

```go
ch := make(chan int)
// Send blocks until receive
// Receive blocks until send
```

### Buffered Channel

```go
ch := make(chan int, 10)
// Send blocks only when buffer is full
// Receive blocks only when buffer is empty
```

## Common Patterns

### 1. Signal with Channel

```go
// Done signal
done := make(chan struct{})

go func() {
    defer close(done)
    // work
}()

<-done  // wait for completion
```

### 2. Fan-Out (Multiple Workers)

```go
func fanOut(jobs <-chan int, numWorkers int) <-chan int {
    var wg sync.WaitGroup
    results := make(chan int, numWorkers)
    
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs {
                results <- job * 2
            }
        }()
    }
    
    go func() {
        wg.Wait()
        close(results)
    }()
    
    return results
}
```

### 3. Fan-In (Merge Channels)

```go
func fanIn(channels ...<-chan int) <-chan int {
    var wg sync.WaitGroup
    out := make(chan int)
    
    output := func(ch <-chan int) {
        defer wg.Done()
        for n := range ch {
            out <- n
        }
    }
    
    wg.Add(len(channels))
    for _, ch := range channels {
        go output(ch)
    }
    
    go func() {
        wg.Wait()
        close(out)
    }()
    
    return out
}
```

### 4. Timeout

```go
func withTimeout(ch <-chan int, timeout time.Duration) (int, error) {
    select {
    case n := <-ch:
        return n, nil
    case <-time.After(timeout):
        return 0, errors.New("timeout")
    }
}
```

### 5. Ticker (Periodic Work)

```go
func periodicWork() {
    ticker := time.NewTicker(1 * time.Second)
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

### 6. Quit Channel

```go
func worker(id int, jobs <-chan int, quit <-chan struct{}) {
    for {
        select {
        case job := <-jobs:
            fmt.Println("worker", id, "processed", job)
        case <-quit:
            fmt.Println("worker", id, "stopping")
            return
        }
    }
}
```

## Channel Directions

### Send-Only

```go
func producer(ch chan<- int) {
    for i := 0; i < 10; i++ {
        ch <- i
    }
    close(ch)
}
```

### Receive-Only

```go
func consumer(ch <-chan int) {
    for n := range ch {
        fmt.Println(n)
    }
}
```

### Bidirectional

```go
func process(ch chan int) {
    for n := range ch {
        ch <- n * 2
    }
}
```

## Select Statement

### Multiple Cases

```go
select {
case n := <-ch1:
    fmt.Println("from ch1:", n)
case n := <-ch2:
    fmt.Println("from ch2:", n)
case ch3 <- data:
    fmt.Println("sent to ch3")
case <-time.After(time.Second):
    fmt.Println("timeout")
}
```

### Default Case (Non-Blocking)

```go
select {
case n := <-ch:
    fmt.Println("received:", n)
default:
    fmt.Println("no data available")
}
```

### Nil Channel

```go
var ch chan int  // ch is nil

select {
case <-ch:  // this case is never selected
    fmt.Println("never happens")
default:
    fmt.Println("default case")
}
```

## Closing Channels

### Rules

1. Only sender should close
2. Never close closed channel
3. Use `range` to receive until closed

### Example

```go
func producer(ch chan<- int) {
    defer close(ch)  // close when done
    for i := 0; i < 10; i++ {
        ch <- i
    }
}

func consumer(ch <-chan int) {
    for n := range ch {
        fmt.Println(n)
    }
}
```

## Context with Channels

```go
func withContext(ctx context.Context, ch <-chan int) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case n, ok := <-ch:
            if !ok {
                return nil  // channel closed
            }
            fmt.Println(n)
        }
    }
}
```

## Best Practices

1. **Close from sender** - only sender closes
2. **Use buffered channels** - to prevent blocking
3. **Use select for timeout** - prevent forever blocking
4. **Use context** - for cancellation
5. **Use direction** - specify send-only or receive-only
6. **Use range** - for simple iteration
7. **nil channel blocks** - useful for control flow

## Anti-Patterns

### Don't Close from Receiver

```go
// BAD
ch := make(chan int)
go func() {
    for n := range ch {
        fmt.Println(n)
    }
    close(ch)  // receiver shouldn't close
}()
```

### Don't Send to Closed Channel

```go
// BAD
ch := make(chan int)
close(ch)
ch <- 1  // panic!
```

## Key Points

- Unbuffered: synchronous, blocks on send/receive
- Buffered: asynchronous, blocks when full/empty
- Use direction for type safety
- Close from sender only
- Use select for multiple channels
- Use range to receive until closed
- Use context for cancellation
