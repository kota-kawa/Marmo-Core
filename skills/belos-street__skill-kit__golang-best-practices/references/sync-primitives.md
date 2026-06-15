---
name: sync-primitives
description: Using sync package primitives - Mutex, RWMutex, WaitGroup, Once, Cond, and atomic operations.
---

# Sync Primitives

> Using synchronization primitives in Go's sync package.

## Problem

How to synchronize access to shared resources without channels.

## Mutex

### Basic Mutex

```go
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

func (c *Counter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.count
}
```

### TryLock (Go 1.18+)

```go
func (c *Counter) TryIncrement() bool {
    if c.mu.TryLock() {
        defer c.mu.Unlock()
        c.count++
        return true
    }
    return false
}
```

## RWMutex

Multiple readers, single writer:

```go
type Cache struct {
    mu    sync.RWMutex
    data  map[string]string
}

func (c *Cache) Get(key string) string {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.data[key]
}

func (c *Cache) Set(key, value string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.data[key] = value
}
```

## WaitGroup

Wait for multiple goroutines:

```go
func main() {
    var wg sync.WaitGroup
    
    for i := 0; i < 5; i++ {
        wg.Add(1)
        go func(i int) {
            defer wg.Done()
            fmt.Println("goroutine", i)
        }(i)
    }
    
    wg.Wait()
    fmt.Println("all done")
}
```

## Once

Execute exactly once:

```go
var (
    once     sync.Once
    instance *Singleton
)

func GetInstance() *Singleton {
    once.Do(func() {
        instance = &Singleton{}
    })
    return instance
}
```

### Once with Error

```go
var (
    once  sync.Once
    err   error
    value interface{}
)

func LoadConfig() (interface{}, error) {
    once.Do(func() {
        value, err = loadFromFile()
    })
    return value, err
}
```

## Cond

Condition variable - waiting for conditions:

```go
func main() {
    cond := sync.NewCond(&sync.Mutex{})
    queue := make([]int, 0, 10)
    
    // Consumer
    go func() {
        cond.L.Lock()
        for len(queue) == 0 {
            cond.Wait()
        }
        val := queue[0]
        queue = queue[1:]
        cond.L.Unlock()
        fmt.Println("Got:", val)
    }()
    
    // Producer
    for i := 0; i < 3; i++ {
        time.Sleep(100 * time.Millisecond)
        cond.L.Lock()
        queue = append(queue, i)
        cond.Signal()
        cond.L.Unlock()
    }
    
    time.Sleep(time.Second)
}
```

### Broadcast vs Signal

- `Signal()` - wakes one waiter
- `Broadcast()` - wakes all waiters

## Atomic

Lock-free atomic operations:

```go
import "sync/atomic"

type Counter struct {
    count int64
}

func (c *Counter) Increment() {
    atomic.AddInt64(&c.count, 1)
}

func (c *Counter) Value() int64 {
    return atomic.LoadInt64(&c.count)
}

func (c *Counter) CompareAndSwap(old, new int64) bool {
    return atomic.CompareAndSwapInt64(&c.count, old, new)
}
```

### Atomic Operations

| Operation | Example |
|-----------|---------|
| Add | `atomic.AddInt64(&n, 1)` |
| Load | `atomic.LoadInt64(&n)` |
| Store | `atomic.StoreInt64(&n, 10)` |
| Swap | `atomic.SwapInt64(&n, 10)` |
| CAS | `atomic.CompareAndSwapInt64(&n, old, new)` |

### Atomic Pointer

```go
type Config struct {
    Host string
}

var config atomic.Value

func LoadConfig(c *Config) {
    config.Store(c)
}

func GetConfig() *Config {
    return config.Load().(*Config)
}
```

## Map

Thread-safe map (for specific use cases):

```go
var m sync.Map

// Store
m.Store("key", "value")

// Load
if val, ok := m.Load("key"); ok {
    fmt.Println(val)
}

// Delete
m.Delete("key")

// Range
m.Range(func(key, value interface{}) bool {
    fmt.Println(key, value)
    return true
})
```

## Map vs RWMutex

| Feature | sync.Map | RWMutex + map |
|---------|----------|---------------|
| Read-heavy | Better | Good |
| Key-heavy | Good | Better |
| Large number of keys | Better | Good |
| Clear all | Better | Manual |

## Best Practices

1. **Use mutex for simple cases**
2. **Use RWMutex for read-heavy workloads**
3. **Use WaitGroup for known count**
4. **Use Once for one-time initialization**
5. **Use atomic for counters**
6. **Prefer channels** unless mutex is clearer

## Common Patterns

### Pool Pattern

```go
type Pool struct {
    pool sync.Pool
}

func (p *Pool) Get() []byte {
    return p.pool.Get().(*bytes.Buffer)
}

func (p *Pool) Put(b []byte) {
    p.pool.Put(b)
}
```

### Semaphore (Limiting Concurrency)

```go
func semaphoreAcquire(sem chan struct{}) {
    sem <- struct{}{}
}

func semaphoreRelease(sem chan struct{}) {
    <-sem
}

func main() {
    sem := make(chan struct{}, 3)  // max 3 concurrent
    
    for _, task := range tasks {
        sem <- struct{}{}
        go func(t Task) {
            defer func() { <-sem }()
            process(t)
        }(task)
    }
}
```

## Key Points

- Mutex: basic mutual exclusion
- RWMutex: multiple readers, single writer
- WaitGroup: wait for goroutine count
- Once: execute exactly once
- Cond: wait for conditions
- Atomic: lock-free operations
- Map: thread-safe map
- Prefer channels when appropriate
