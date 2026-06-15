---
name: wasm-callbacks-async
description: Handling asynchronous operations and callbacks in Go WebAssembly - setTimeout, Promises, and async patterns.
---

# Callbacks and Async

> Handling asynchronous operations in Go WASM.

## Problem

How to handle async operations and callbacks in Go WASM.

## setTimeout

### Basic Usage

```go
import (
    "syscall/js"
    "time"
)

func main() {
    global := js.Global()

    // Create setTimeout function
    setTimeout := global.Get("setTimeout")

    // Create callback
    callback := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        fmt.Println("Timeout triggered!")
        return nil
    })
    defer callback.Release()

    // Call setTimeout - 1000ms delay
    setTimeout.Invoke(callback, 1000)

    // Keep running
    <-make(chan struct{})
}
```

### setInterval

```go
func periodicWork() {
    global := js.Global()
    setInterval := global.Get("setInterval")

    counter := 0

    callback := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        counter++
        fmt.Println("Tick:", counter)

        if counter >= 5 {
            // Stop after 5 ticks - need to store interval ID
        }
        return nil
    })
    defer callback.Release()

    intervalID := setInterval.Invoke(callback, 1000)
    _ = intervalID
}
```

## Promises

### Handling JS Promises

Go doesn't have native Promise support, but you can work with them:

```go
import "syscall/js"

func main() {
    global := js.Global()

    // Call a function that returns a Promise
    promise := global.Call("fetch", "/api/data")

    // Get .then method
    then := promise.Get("then")

    // Create callback for resolve
    resolve := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        response := args[0]
        fmt.Println("Promise resolved!")
        return nil
    })

    // Create callback for reject  
    reject := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        err := args[0]
        fmt.Println("Promise rejected:", err)
        return nil
    })

    then.Invoke(resolve, reject)
}
```

## Async/Await Pattern

### Wrapper Pattern

```go
// Create async wrapper
func awaitPromise(promise js.Value) (js.Value, error) {
    done := make(chan js.Value)

    // Success callback
    resolve := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        done <- args[0]
        return nil
    })

    // Error callback
    reject := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        done <- js.Value{}
        return nil
    })

    promise.Get("then").Invoke(resolve, reject)

    result := <-done
    resolve.Release()
    reject.Release()

    return result, nil
}
```

## Event Listeners

### One-time Event

```go
func waitForLoad() {
    global := js.Global()

    callback := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        fmt.Println("Page loaded!")
        return nil
    })
    defer callback.Release()

    document := global.Get("document")
    document.Get("addEventListener").Invoke("DOMContentLoaded", callback)
}
```

### Custom Events

```go
func dispatchEvent() {
    global := js.Global()
    document := global.Get("document")

    // Create custom event
    event := document.Call("createEvent", "Event")
    event.Call("initEvent", "myEvent", true, true)

    // Dispatch
    document.Call("dispatchEvent", event)
}
```

## Channel-Based Async

### Using Channels

```go
func main() {
    resultCh := make(chan string)

    global := js.Global()
    setTimeout := global.Get("setTimeout")

    callback := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        resultCh <- "Timeout done!"
        return nil
    })
    defer callback.Release()

    setTimeout.Invoke(callback, 1000)

    // Wait for result
    result := <-resultCh
    fmt.Println(result)
}
```

## Best Practices

1. **Always release callbacks** - memory leak prevention
2. **Use channels** for async coordination
3. **Handle errors** in Promise callbacks
4. **Keep main alive** - use blocking channel

## Key Points

- Use `setTimeout` from `js.Global()`
- Work with Promises using callbacks
- Release callbacks to prevent leaks
- Use channels for Go-side async
- Keep main function running
