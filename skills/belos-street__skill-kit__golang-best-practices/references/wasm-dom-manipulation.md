---
name: wasm-dom-manipulation
description: DOM manipulation in Go WebAssembly - creating elements, handling events, and updating the page.
---

# DOM Manipulation

> Manipulating the DOM from Go WASM.

## Problem

How to create and manipulate HTML elements from Go WASM.

## Basic DOM Access

```go
import (
    "syscall/js"
)

func main() {
    global := js.Global()
    document := global.Get("document")

    // Get element by ID
    element := document.Call("getElementById", "myDiv")

    // Create element
    newDiv := document.Call("createElement", "div")

    // Query selector
    button := document.Call("querySelector", ".myButton")
}
```

## Creating Elements

```go
func createUI() {
    global := js.Global()
    document := global.Get("document")

    // Create div
    div := document.Call("createElement", "div")
    div.Set("textContent", "Hello World")
    div.Get("style").Set("color", "red")

    // Append to body
    body := document.Get("body")
    body.Call("appendChild", div)
}
```

## Setting Attributes

```go
func main() {
    global := js.Global()
    document := global.Get("document")

    // Create button
    button := document.Call("createElement", "button")
    button.Set("textContent", "Click Me")
    button.Set("id", "myButton")

    // Set attribute
    button.Get("setAttribute").Invoke("data-id", "123")

    // Get attribute
    id := button.Get("getAttribute").Invoke("data-id").String()

    // Set class
    button.Set("className", "btn primary")
}
```

## Event Handling

```go
func main() {
    global := js.Global()
    document := global.Get("document")

    button := document.Call("getElementById", "myButton")

    // Add event listener
    clickHandler := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        event := args[0]
        fmt.Println("Clicked!")
        return nil
    })
    defer clickHandler.Release()

    button.Call("addEventListener", "click", clickHandler)
}
```

## Form Handling

```go
func handleForm() {
    global := js.Global()
    document := global.Get("document")

    form := document.Call("getElementById", "myForm")

    submitHandler := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        event := args[0]
        event.Call("preventDefault")

        // Get input value
        input := document.Call("getElementById", "username")
        username := input.Get("value").String()

        fmt.Println("Submitted:", username)
        return nil
    })
    defer submitHandler.Release()

    form.Call("addEventListener", "submit", submitHandler)
}
```

## Updating DOM

```go
func updateElement(id, text string) {
    global := js.Global()
    document := global.Get("document")

    element := document.Call("getElementById", id)
    if element.Truthy() {
        element.Set("textContent", text)
    }
}

func addClass(id, className string) {
    global := js.Global()
    document := global.Get("document")

    element := document.Call("getElementById", id)
    if element.Truthy() {
        current := element.Get("className").String()
        element.Set("className", current+" "+className)
    }
}
```

## Creating List

```go
func renderList(items []string) {
    global := js.Global()
    document := global.Get("document")

    // Get container
    list := document.Call("getElementById", "myList")

    // Clear existing
    list.Set("innerHTML", "")

    // Add items
    for _, item := range items {
        li := document.Call("createElement", "li")
        li.Set("textContent", item)
        list.Call("appendChild", li)
    }
}
```

## Best Practices

1. **Check Truthy** before using elements
2. **Release callbacks** when done
3. **Use setAttribute** for custom attributes
4. **Prevent default** for form submissions

## Key Points

- Use `document.Call("createElement", tag)`
- Use `element.Set("property", value)`
- Use `addEventListener` for events
- Remember to release callbacks
- Check element exists with `.Truthy()`
