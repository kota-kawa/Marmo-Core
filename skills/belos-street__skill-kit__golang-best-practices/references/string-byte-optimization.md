---
name: string-byte-optimization
description: Optimizing string and []byte conversions in Go to reduce allocations and improve performance.
---

# String and []byte Optimization

> Avoiding unnecessary string/[]byte conversions for better performance.

## Problem

Frequent string/[]byte conversions cause allocations and hurt performance.

## String vs []byte

| Type | Immutable | Allocation | Conversion Cost |
|------|-----------|------------|-----------------|
| string | Yes | New each time | O(n) |
| []byte | No | Can reuse | O(n) |

## Conversion Costs

```go
// Each conversion allocates
s := "hello"
b := []byte(s)  // allocates new []byte

// And back
s2 := string(b)  // allocates new string
```

## Common Mistakes

### 1. Repeated Conversions

```go
// BAD - converts every iteration
func process(data string) []byte {
    var result []byte
    for i := 0; i < len(data); i++ {
        result = append(result, byte(data[i]))  // converts each time
    }
    return result
}

// GOOD - convert once
func process(data string) []byte {
    b := []byte(data)  // convert once
    var result = make([]byte, len(b))
    for i := 0; i < len(b); i++ {
        result[i] = b[i]
    }
    return result
}
```

### 2. String Concatenation in Loop

```go
// BAD - allocates each iteration
func badConcat(items []string) string {
    var result string
    for _, item := range items {
        result += item  // allocates each time
    }
    return result
}

// GOOD - use strings.Builder
func goodConcat(items []string) string {
    var b strings.Builder
    for _, item := range items {
        b.WriteString(item)
    }
    return b.String()
}
```

### 3. JSON with []byte

```go
// BAD - double conversion
func encodeJSON(data MyStruct) []byte {
    jsonStr, _ := json.Marshal(data)
    return []byte(jsonStr)  // converts string to []byte
}

// GOOD - use json.Marshal directly
func encodeJSON(data MyStruct) ([]byte, error) {
    return json.Marshal(data)  // returns []byte directly
}
```

## Best Practices

### 1. Work with []byte When Possible

```go
// If you need to modify, use []byte
func modify(data []byte) {
    for i := range data {
        data[i] = bytes.ToUpper(data[i])
    }
}

// Call with []byte
b := []byte("hello")
modify(b)
```

### 2. Use strings.Builder

```go
// For string building
var b strings.Builder
b.WriteString("hello")
b.WriteString(" ")
b.WriteString("world")
result := b.String()
```

### 3. Use bytes.Buffer

```go
// For []byte building
var buf bytes.Buffer
buf.Write([]byte("hello"))
buf.Write([]byte(" "))
buf.Write([]byte("world"))
result := buf.Bytes()
```

### 4. Convert Once at Boundaries

```go
// Convert at I/O boundaries
func readData() ([]byte, error) {
    data, err := os.ReadFile("file.txt")
    return data, err  // already []byte
}

func writeData(data []byte) error {
    return os.WriteFile("file.txt", data, 0644)
}

// Work with []byte internally
func process(data []byte) []byte {
    // modify in place
    return data
}
```

## Benchmarks

```go
func BenchmarkStringConcat(b *testing.B) {
    items := []string{"a", "b", "c", "d", "e"}
    
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        var result string
        for _, s := range items {
            result += s
        }
        _ = result
    }
}

func BenchmarkBuilderConcat(b *testing.B) {
    items := []string{"a", "b", "c", "d", "e"}
    
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        var b strings.Builder
        for _, s := range items {
            b.WriteString(s)
        }
        _ = b.String()
    }
}
```

## Type Switching

```go
// Efficiently handle both
func process(data interface{}) {
    switch v := data.(type) {
    case string:
        handleString(v)
    case []byte:
        handleBytes(v)
    }
}

func handleString(s string) {
    b := []byte(s)  // convert when needed
    // process
}

func handleBytes(b []byte) {
    // process directly
}
```

## strconv Optimization

```go
// BAD - uses string
func intToString(i int) string {
    return strconv.Itoa(i)
}

// GOOD - use fmt with buffer
func intToString(i int) string {
    var buf [20]byte
    n := strconv.AppendInt(buf[:0], int64(i), 10)
    return string(n)
}
```

## Key Points

- Convert string to []byte only when needed
- Use strings.Builder for string concatenation
- Use bytes.Buffer for byte concatenation
- Work with []byte internally when possible
- Convert at I/O boundaries
- Benchmark to verify improvements
