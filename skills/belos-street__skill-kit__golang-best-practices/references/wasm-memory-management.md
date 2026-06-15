---
name: wasm-memory-management
description: Understanding WebAssembly linear memory in Go WASM - accessing JS ArrayBuffer and typed arrays.
---

# WASM Memory Management

> Working with WebAssembly linear memory in Go.

## Problem

How to access and manipulate WebAssembly memory from Go.

## Understanding WASM Memory

Go WASM uses linear memory:
- Starts at 0, grows as needed
- Shared between Go and JS
- Can be accessed from both sides

```go
import "syscall/js"

func main() {
    // Get memory object
    global := js.Global()
    wasm := global.Get("wasm")
    memory := wasm.Get("memory")

    // Or access directly
    mem := js.Global().Get("WebAssembly").Get("memory")
}
```

## Accessing Go Memory from JS

### Getting Memory Buffer

```javascript
// In JavaScript
const wasmMemory = wasm.instance.exports.memory;
const uint8Array = new Uint8Array(wasmMemory.buffer);
```

### Reading Go Strings

```go
// Go: export a function
//export getString
func GetString(ptr int32, length int32) {
    // This is handled automatically by Go
}
```

Actually, Go handles string conversion automatically:

```go
// In JavaScript
const str = wasm.getString(ptr, length);
```

## Creating JS Arrays from Go

### Returning Array

```go
// Go function returns []byte
func getData() []byte {
    return []byte{1, 2, 3, 4}
}

// Access from JS
const data = new Uint8Array(wasm.memory.buffer, ptr, length);
```

### Using Typed Arrays

```go
func createUint8Array() js.Value {
    global := js.Global()

    // Create Uint8Array in JS
    constructor := global.Get("Uint8Array")
    length := 10
    array := constructor.New(length)

    // Fill with data
    for i := 0; i < length; i++ {
        array.SetIndex(i, i)
    }

    return array
}
```

## Passing Arrays to Go

### From JS to Go

```javascript
// JavaScript
const arr = new Uint8Array([1, 2, 3, 4]);
go.processArray(arr);
```

```go
// Go
func processArray(arr js.Value) {
    length := arr.Get("length").Int()

    for i := 0; i < length; i++ {
        value := arr.Index(i).Int()
        fmt.Println(value)
    }
}
```

## Memory Growth

### Manual Memory Management

```go
// Go's WASM runtime handles memory automatically
// No manual malloc/free needed

// Memory grows as needed
var largeSlice = make([]byte, 10*1024*1024)  // 10MB
```

## Best Practices

1. **Keep data small** - WASM memory is limited
2. **Use JS arrays** when passing to JS
3. **Minimize copies** - work in place
4. **Release callbacks** to free memory

## Key Points

- Go WASM uses linear memory
- JS can access Go memory via exports
- Use js.Value for typed arrays
- Memory grows automatically
- Keep data small for performance
