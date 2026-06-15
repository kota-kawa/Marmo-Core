---
name: wasm-js-interop
description: JavaScript interop with Go WebAssembly using js.Global() and js.Value for calling JS functions.
---

# JS Interop

> Calling JavaScript functions from Go WASM.

## Problem

How to interact with JavaScript from Go WASM.

## Getting JavaScript Objects

### Global Object

```go
import "syscall/js"

func main() {
    // Get global object (window in browser)
    global := js.Global()

    // Access properties
    console := global.Get("console")
    console.Call("log", "Hello from Go!")

    document := global.Get("document")
    _ = document
}
```

### Type Conversion

```go
func main() {
    global := js.Global()

    // Go string to JS string
    global.Set("myVar", "hello")

    // JS string to Go string
    myVar := global.Get("myVar").String()

    // JS number to Go float64
    num := global.Get("myNum").Float()

    // Go number to JS number
    global.Set("num", 42)

    // Go bool to JS boolean
    global.Set("flag", true)
    flag := global.Get("flag").Bool()

    // Go function to JS function
    global.Set("goFunc", js.FuncOf(goFunc))
}

func goFunc(this js.Value, args []js.Value) interface{} {
    return "result"
}
```

## Calling JavaScript Functions

### Call Method

```go
func main() {
    global := js.Global()

    // Call console.log
    console := global.Get("console")
    console.Call("log", "Hello", "World")

    // Call with return value
    Math := global.Get("Math")
    random := Math.Call("random").Float()
    fmt.Println(random)

    // Call with arguments
    max := Math.Call("max", 1, 2, 3).Int()
    fmt.Println(max)
}
```

### Access Properties

```go
func main() {
    global := js.Global()

    // Get property
    location := global.Get("location")
    href := location.Get("href").String()
    fmt.Println(href)

    // Set property
    global.Set("title", "My Title")

    // Check if exists
    if global.Get("jQuery").Truthy() {
        // jQuery exists
    }
}
```

## Callback Functions

### JS Calls Go

```go
import "syscall/js"

func main() {
    global := js.Global()

    // Define a Go function callable from JS
    jsCallback := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        fmt.Println("Called from JS!")
        return "result"
    })
    defer jsCallback.Release()

    // Expose to JS
    global.Set("goFunction", jsCallback)
}
```

```javascript
// In JavaScript
let result = goFunction();
console.log(result); // "result"
```

### Callback with Arguments

```go
jsCallback := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
    // args[0], args[1], etc.
    name := args[0].String()
    age := args[1].Int()

    fmt.Printf("Name: %s, Age: %d\n", name, age)
    return "processed"
})
```

## Type Conversion Table

| Go Type | JS Type | Method |
|---------|---------|--------|
| string | String | .String() |
| int, int64 | Number | .Int() / .Int64() |
| float64 | Number | .Float() |
| bool | Boolean | .Bool() |
| []byte | Uint8Array | .Bytes() |
| js.Value | any | - |

## Error Handling

```go
func main() {
    global := js.Global()

    // Check if function exists
    if !global.Get("maybeExists").Truthy() {
        // doesn't exist
    }

    // Try/catch equivalent
    // JS try/catch not directly available
    // Handle errors in callbacks gracefully
}
```

## Best Practices

1. **Release callbacks** when done
2. **Check Truthy** before using values
3. **Use js.Value methods** for conversion
4. **Keep callbacks simple** to avoid blocking

## Key Points

- Use `js.Global()` to access global scope
- Use `Call()` to invoke JS functions
- Use `Get()`/`Set()` for properties
- Use `js.FuncOf()` for Go callbacks
- Remember to `.Release()` callbacks
- Type conversion uses .String(), .Int(), etc.
