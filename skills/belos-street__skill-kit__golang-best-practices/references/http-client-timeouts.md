---
name: http-client-timeouts
description: HTTP client timeout issues in Go - missing timeouts, resource exhaustion, and best practices.
---

# HTTP Client Timeouts

> Setting proper timeouts for Go HTTP clients to prevent leaks.

## Problem

Default HTTP client has no timeouts, leading to resource exhaustion.

## The Problem

```go
// DANGER: No timeouts!
client := &http.Client{}

// This can hang forever if server doesn't respond
resp, err := client.Get("http://slow-server:8080/slow")
```

### What Happens

- Connection hangs indefinitely
- Goroutines accumulate
- Memory grows
- Process eventually runs out of resources

## Required Timeouts

### Basic Timeouts

```go
client := &http.Client{
    Timeout: 30 * time.Second,
}
```

### Detailed Timeouts

```go
client := &http.Client{
    Timeout: time.Duration(0), // Disable overall timeout

    Transport: &http.Transport{
        // Connection-level timeouts
        DialContext: (&net.Dialer{
            Timeout:   30 * time.Second,
            KeepAlive: 30 * time.Second,
        }).DialContext,

        // TLS handshake timeout
        TLSHandshakeTimeout:   10 * time.Second,

        // Response header timeout
        ResponseHeaderTimeout: 10 * time.Second,

        // Expect continue timeout
        ExpectContinueTimeout:  1 * time.Second,

        // Idle connection timeout
        IdleConnTimeout:       90 * time.Second,
    },
}
```

### Per-Request Timeout

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
resp, err := client.Do(req)
```

## Connection Pool

### Limit Connections

```go
transport := &http.Transport{
    MaxIdleConns:        100,        // Max idle connections
    MaxIdleConnsPerHost: 100,        // Per-host limit
    IdleConnTimeout:     90 * time.Second,
}

client := &http.Client{
    Transport: transport,
}
```

### Limit Total Connections

```go
transport := &http.Transport{
    MaxConnsPerHost: 100,  // Limit per host
}
```

## Common Mistakes

### 1. Reusing Client

```go
// GOOD: Reuse client
var client = &http.Client{
    Timeout: 30 * time.Second,
}

func handler(w http.ResponseWriter, r *http.Request) {
    resp, err := client.Get(url)  // Reuses connections
}
```

### 2. Creating New Client

```go
// BAD: New client per request
func handler(w http.ResponseWriter, r *http.Request) {
    client := &http.Client{}  // Leaks resources!
    resp, err := client.Get(url)
}
```

### 3. Not Closing Response

```go
// BAD: Response body not closed
func get(url string) error {
    resp, err := http.Get(url)
    if err != nil {
        return err
    }
    // Missing: defer resp.Body.Close()
    return nil
}

// GOOD
func get(url string) error {
    resp, err := http.Get(url)
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    return nil
}
```

### 4. Not Reading Entire Body

```go
// BAD: Not reading body
resp, _ := client.Get(url)
defer resp.Body.Close()
// Connection may be reused improperly

// GOOD: Read or discard body
resp, _ := client.Get(url)
defer resp.Body.Close()
io.Copy(ioutil.Discard, resp.Body)
```

## Best Practices

1. **Always set timeouts** - never use default
2. **Reuse HTTP client** - share transport
3. **Close response body** - always defer close
4. **Read full body** - or discard
5. **Use context** - for request-level timeout
6. **Limit connections** - prevent exhaustion

## Timeout Checklist

```go
client := &http.Client{
    Timeout: 30 * time.Second,

    Transport: &http.Transport{
        DialContext: (&net.Dialer{
            Timeout:   10 * time.Second,
        }).DialContext,

        TLSHandshakeTimeout:   10 * time.Second,
        ResponseHeaderTimeout: 10 * time.Second,
        IdleConnTimeout:       90 * time.Second,

        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 100,
    },
}
```

## Key Points

- Default client has no timeout
- Always set client timeout
- Reuse client instance
- Close response bodies
- Limit connection pools
- Use context for per-request
