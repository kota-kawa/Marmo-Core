# Getter Computed Caching

Learn how Pinia getters cache computed values and how to use them effectively.

## Getters as Computed Properties

Pinia getters are computed properties that cache their results:

```ts
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  
  const doubleCount = computed(() => count.value * 2)
  const tripleCount = computed(() => count.value * 3)
  
  return { count, doubleCount, tripleCount }
})
```

## How Caching Works

Getters only recompute when their dependencies change:

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  const filter = ref<FilterType>('all')
  
  const filteredTodos = computed(() => {
    console.log('Computing filtered todos')
    
    if (filter.value === 'active') {
      return todos.value.filter(t => !t.completed)
    }
    if (filter.value === 'completed') {
      return todos.value.filter(t => t.completed)
    }
    return todos.value
  })
  
  return { todos, filter, filteredTodos }
})
```

The getter only recomputes when `todos` or `filter` changes, not on every access.

## Expensive Computations

Getters are perfect for expensive computations:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const searchQuery = ref('')
  const category = ref('all')
  
  const filteredProducts = computed(() => {
    let result = products.value
    
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(p => 
        p.name.toLowerCase().includes(query) ||
        p.description.toLowerCase().includes(query)
      )
    }
    
    if (category.value !== 'all') {
      result = result.filter(p => p.category === category.value)
    }
    
    return result.sort((a, b) => a.price - b.price)
  })
  
  return { products, searchQuery, category, filteredProducts }
})
```

The expensive filtering and sorting only happens when dependencies change.

## Chained Getters

Getters can depend on other getters:

```ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const coupon = ref<string | null>(null)
  
  const subtotal = computed(() => 
    items.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
  )
  
  const discount = computed(() => {
    if (!coupon.value) return 0
    return subtotal.value * 0.1 // 10% discount
  })
  
  const tax = computed(() => (subtotal.value - discount.value) * 0.08)
  
  const total = computed(() => subtotal.value - discount.value + tax.value)
  
  return { items, coupon, subtotal, discount, tax, total }
})
```

## Caching with Multiple Access

Getters cache results across multiple accesses:

```ts
export const useStore = defineStore('store', () => {
  const data = ref<Data[]>([])
  
  const processedData = computed(() => {
    console.log('Processing data')
    return data.value.map(item => ({
      ...item,
      processed: true
    }))
  })
  
  return { data, processedData }
})
```

```vue
<script setup lang="ts">
const store = useStore()

// All three accesses use the same cached value
console.log(store.processedData) // Logs "Processing data"
console.log(store.processedData) // Uses cache
console.log(store.processedData) // Uses cache
</script>
```

## Avoiding Side Effects in Getters

Getters should be pure functions without side effects:

```ts
// ❌ Bad: Side effect in getter
const filteredTodos = computed(() => {
  console.log('Filtering todos') // Side effect
  analytics.track('filter_todos') // Side effect
  return todos.value.filter(t => !t.completed)
})
```

```ts
// ✅ Good: Pure getter
const filteredTodos = computed(() => {
  return todos.value.filter(t => !t.completed)
})

// Track side effects separately
watch(filteredTodos, () => {
  analytics.track('filter_todos')
})
```

## Getters vs Methods

Use getters for derived state, methods for computations with arguments:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const cheapProducts = computed(() => 
    products.value.filter(p => p.price < 50)
  )
  
  const expensiveProducts = computed(() => 
    products.value.filter(p => p.price >= 50)
  )
  
  function filterByPrice(min: number, max: number) {
    return products.value.filter(p => p.price >= min && p.price <= max)
  }
  
  return { products, cheapProducts, expensiveProducts, filterByPrice }
})
```

## Performance Considerations

### Avoid Expensive Getters

```ts
// ❌ Bad: Expensive getter called frequently
const expensiveResult = computed(() => {
  return heavyComputation(data.value)
})
```

```ts
// ✅ Good: Cache with watchEffect or use a method
const expensiveResult = ref<Result | null>(null)

watchEffect(async () => {
  expensiveResult.value = await heavyComputation(data.value)
})
```

### Memoize Complex Computations

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  
  const groupedItems = computed(() => {
    const groups = new Map<string, Item[]>()
    
    for (const item of items.value) {
      const key = item.category
      if (!groups.has(key)) {
        groups.set(key, [])
      }
      groups.get(key)!.push(item)
    }
    
    return groups
  })
  
  return { items, groupedItems }
})
```

## Debugging Getters

Track getter recomputations:

```ts
export const useStore = defineStore('store', () => {
  const data = ref<Data[]>([])
  
  const processedData = computed(() => {
    if (import.meta.env.DEV) {
      console.log('Recomputing processedData')
    }
    return data.value.map(item => ({ ...item, processed: true }))
  })
  
  return { data, processedData }
})
```

## Best Practices

1. **Use getters for derived state**: Computed values from state
2. **Keep getters pure**: No side effects
3. **Leverage caching**: Getters automatically cache results
4. **Chain getters**: Build complex derived state
5. **Avoid expensive operations**: Use methods for heavy computations
6. **Use methods for arguments**: Getters can't accept parameters

## Common Mistakes

❌ **Side effects in getters**

```ts
const filtered = computed(() => {
  api.track('filter') // ❌ Side effect
  return items.value.filter(i => i.active)
})
```

✅ **Track separately**

```ts
const filtered = computed(() => {
  return items.value.filter(i => i.active)
})

watch(filtered, () => {
  api.track('filter') // ✅ Side effect separate
})
```

❌ **Expensive operations in getters**

```ts
const result = computed(() => {
  return heavyComputation(data.value) // ❌ Expensive
})
```

✅ **Use watchEffect for expensive operations**

```ts
const result = ref(null)

watchEffect(() => {
  result.value = heavyComputation(data.value) // ✅ Controlled
})
```

❌ **Not using caching**

```ts
function getFilteredItems() {
  return items.value.filter(i => i.active) // ❌ Recomputes every call
}
```

✅ **Use getter for caching**

```ts
const filteredItems = computed(() => {
  return items.value.filter(i => i.active) // ✅ Cached
})
```
