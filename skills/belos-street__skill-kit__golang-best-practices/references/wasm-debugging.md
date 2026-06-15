---
name: wasm-debugging
description: Debugging Go WebAssembly - using browser devtools, console.log, and debugging strategies.
---

# Debugging WASM

> Techniques for debugging Go WASM in browsers.

## Problem

How to debug Go WASM applications.

## Basic Debugging

### console.log

```go
import (
    "fmt"
    "syscall/js"
)

func main() {
    // Use fmt.Println (prints to console)
    fmt.Println("Hello from Go!")

    // Or use JS console
    global := js.Global()
    console := global.Get("console")
    console.Call("log", "Hello via console!")
}
```

### Debug Values

```go
func debugValue(value interface{}) {
    global := js.Global()
    console := global.Get("console")

    // Log with formatting
    console.Call("log", "Value:", value)
}
```

## Browser DevTools

### Using Chrome

1. Open Chrome DevTools (F12)
2. Go to Sources tab
3. Find WASM file
4. Set breakpoints

### Setting Breakpoints

```go
// Add this to pause in debugger
// debugger // Won't work in Go

// Instead, use:
func debug() {
    // Can't directly break in Go WASM
    // Use JS debugger in callback
}
```

### Console Output

```go
// All fmt.Println works
func main() {
    fmt.Println("Debug output")
    fmt.Printf("Value: %v\n", myValue)
}
```

## Source Maps

### Enabling

```bash
# Build with debug info
GOOS=js GOARCH=wasm go build -o main.wasm main.go

# Chrome should auto-detect
```

### Viewing Go Code

Chrome DevTools shows Go source if:
1. WASM built with debug info
2. Source map generated

## Common Issues

### 1. Panic Not Caught

```go
// This will crash the WASM
func main() {
    panic("oh no!")
}
```

Solution: Recover in main:

```go
func main() {
    defer func() {
        if r := recover(); r != nil {
            fmt.Println("Recovered:", r)
        }
    }()
    // code
}
```

### 2. Infinite Loop

```go
// This will freeze the browser!
func main() {
    for {
        // infinite loop
    }
}
```

### 3. Memory Issues

```javascript
// Check memory in console
console.log(wasm.instance.exports.memory.buffer.byteLength);
```

## Error Handling

### Graceful Errors

```go
func safeCall(fn func()) {
    defer func() {
        if r := recover(); r != nil {
            global := js.Global()
            console := global.Get("console")
            console.Call("error", "Error:", r)
        }
    }()
    fn()
}
```

## Best Practices

1. **Use fmt.Println** for debugging
2. **Recover from panics** gracefully
3. **Check browser console** for errors
4. **Use minimal code** for testing

## Key Points

- fmt.Println works in WASM
- Check browser console
- Recover from panics
- Avoid infinite loops
- Test incrementally
