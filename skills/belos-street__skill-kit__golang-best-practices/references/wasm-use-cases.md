---
name: wasm-use-cases
description: Practical use cases for Go WebAssembly - image processing,计算密集型任务, and real-world examples.
---

# WASM Use Cases

> Practical applications for Go WASM.

## Problem

When and why to use Go WASM in real applications.

## Common Use Cases

### 1. Image Processing

```go
package main

import (
    "fmt"
    "image"
    "image/png"
    "syscall/js"
)

func main() {
    global := js.Global()

    processImage := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        // Get image data from JS
        data := args[0]
        width := args[1].Int()
        height := args[2].Int()

        // Process in Go
        img := image.NewNRGBA(image.Rect(0, 0, width, height))
        // Apply filters, resize, etc.

        // Return processed data
        return nil
    })
    defer processImage.Release()

    global.Set("processImage", processImage)

    <-make(chan struct{})
}
```

### 2. Data Processing

```go
package main

import (
    "syscall/js"
)

func main() {
    global := js.Global()

    // Sort large arrays
    sortArray := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        arr := args[0]
        length := arr.Get("length").Int()

        // Convert to Go slice
        slice := make([]int, length)
        for i := 0; i < length; i++ {
            slice[i] = arr.Index(i).Int()
        }

        // Sort in Go (much faster for large arrays)
        quickSort(slice)

        // Write back
        for i := 0; i < length; i++ {
            arr.SetIndex(i, slice[i])
        }

        return nil
    })
    defer sortArray.Release()

    global.Set("sortArray", sortArray)

    <-make(chan struct{})
}

func quickSort(arr []int) {
    if len(arr) <= 1 {
        return
    }
    // Quick sort implementation
    // ...
}
```

### 3. Encryption

```go
package main

import (
    "crypto/aes"
    "crypto/cipher"
    "syscall/js"
)

func main() {
    global := js.Global()

    encrypt := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        key := args[0]
        plaintext := args[1]

        // Use Go's crypto libraries
        block, _ := aes.NewCipher(keyBytes)
        // ...

        return encryptedData
    })
    defer encrypt.Release()

    global.Set("encrypt", encrypt)

    <-make(chan struct{})
}
```

### 4. Markdown Parser

```go
package main

import (
    "fmt"
    "github.com/gomarkdown/markdown"
    "syscall/js"
)

func main() {
    global := js.Global()

    parseMarkdown := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        md := args[0].String()
        html := markdown.ToHTML([]byte(md), nil, nil)
        return string(html)
    })
    defer parseMarkdown.Release()

    global.Set("parseMarkdown", parseMarkdown)

    <-make(chan struct{})
}
```

### 5. JSON Processing

```go
package main

import (
    "encoding/json"
    "syscall/js"
)

func main() {
    global := js.Global()

    parseJSON := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        jsonStr := args[0].String()
        
        var data map[string]interface{}
        json.Unmarshal([]byte(jsonStr), &data)
        
        // Process...
        
        result, _ := json.Marshal(data)
        return string(result)
    })
    defer parseJSON.Release()

    global.Set("parseJSON", parseJSON)

    <-make(chan struct{})
}
```

### 6. Game Logic

```go
package main

import (
    "syscall/js"
)

type Vector struct {
    X, Y float64
}

func main() {
    global := js.Global()

    updatePosition := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        x := args[0].Float()
        y := args[1].Float()
        vx := args[2].Float()
        vy := args[3].Float()

        // Update physics in Go
        x += vx
        y += vy

        return map[string]interface{}{
            "x": x,
            "y": y,
        }
    })
    defer updatePosition.Release()

    global.Set("updatePosition", updatePosition)

    <-make(chan struct{})
}
```

## Performance Comparison

| Task | Pure JS | Go WASM | Speedup |
|------|---------|----------|---------|
| Sort 1M items | ~200ms | ~50ms | 4x |
| AES encrypt | ~50ms | ~20ms | 2.5x |
| Image blur | ~300ms | ~80ms | 3.75x |

## When to Use WASM

### Good For

- **Computation heavy** - number crunching
- **Existing Go code** - reuse libraries
- **Performance critical** - need native speed
- **Server-client shared** - use same code

### Not Good For

- **Simple UI** - use JS
- **DOM manipulation** - use JS
- **Network I/O** - use JS fetch

## Best Practices

1. **Profile first** - verify WASM is faster
2. **Minimize data transfer** - keep data in WASM
3. **Batch operations** - reduce call overhead
4. **Use TinyGo** - for smaller binaries

## Key Points

- Image/data processing
- Encryption/compression
- Game physics
- Reuse Go libraries
- Profile before using
