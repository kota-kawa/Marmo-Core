# Getter Performance Optimization

Learn how to optimize Pinia getters for better performance.

## Understanding Getter Performance

Getters are computed properties that cache their results:

```ts
export const useStore = defineStore('store', () => {
  const data = ref<Data[]>([])
  
  const processedData = computed(() => {
    return data.value.map(item => ({
      ...item,
      processed: true
    }))
  })
  
  return { data, processedData }
})
```

The getter only recomputes when `data` changes.

## Expensive Computations

Avoid expensive operations in getters:

```ts
// ❌ Bad: Expensive computation in getter
const expensiveResult = computed(() => {
  return heavyComputation(data.value)
})
```

```ts
// ✅ Good: Use watchEffect for expensive operations
const expensiveResult = ref<Result | null>(null)

watchEffect(async () => {
  expensiveResult.value = await heavyComputation(data.value)
})
```

## Memoization

Memoize expensive computations:

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  const cache = ref<Map<string, Item[]>>(new Map())
  
  const getItemsByCategory = computed(() => {
    return (category: string) => {
      if (cache.value.has(category)) {
        return cache.value.get(category)!
      }
      
      const filtered = items.value.filter(item => item.category === category)
      cache.value.set(category, filtered)
      return filtered
    }
  })
  
  watch(items, () => {
    cache.value.clear()
  }, { deep: true })
  
  return { items, getItemsByCategory }
})
```

## Debouncing Getters

Debounce expensive getters:

```ts
import { debounce } from 'lodash-es'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const items = ref<Item[]>([])
  const filteredItems = ref<Item[]>([])
  
  const debouncedFilter = debounce(() => {
    filteredItems.value = items.value.filter(item =>
      item.name.toLowerCase().includes(query.value.toLowerCase())
    )
  }, 300)
  
  watch(query, debouncedFilter)
  
  return { query, items, filteredItems }
})
```

## Lazy Evaluation

Only compute getters when accessed:

```ts
export const useStore = defineStore('store', () => {
  const data = ref<Data[]>([])
  const isComputed = ref(false)
  
  const processedData = computed(() => {
    if (!isComputed.value) {
      isComputed.value = true
    }
    return data.value.map(item => ({ ...item, processed: true }))
  })
  
  return { data, processedData, isComputed }
})
```

## Shallow vs Deep Reactivity

Use shallow reactivity for large objects:

```ts
import { shallowRef } from 'vue'

export const useStore = defineStore('store', () => {
  const largeDataset = shallowRef<LargeData[]>([])
  
  const summary = computed(() => {
    return {
      count: largeDataset.value.length,
      total: largeDataset.value.reduce((sum, item) => sum + item.value, 0)
    }
  })
  
  return { largeDataset, summary }
})
```

## Selective Dependencies

Only watch necessary dependencies:

```ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const coupon = ref<string | null>(null)
  
  const subtotal = computed(() => 
    items.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
  )
  
  const discount = computed(() => {
    if (!coupon.value) return 0
    return subtotal.value * 0.1
  })
  
  const total = computed(() => subtotal.value - discount.value)
  
  return { items, coupon, subtotal, discount, total }
})
```

## Avoiding Unnecessary Recomputations

Structure getters to minimize recomputations:

```ts
// ❌ Bad: Multiple getters with overlapping dependencies
const filteredActive = computed(() => 
  items.value.filter(i => i.active)
)

const filteredActiveSorted = computed(() => 
  filteredActive.value.sort((a, b) => a.name.localeCompare(b.name))
)

const filteredActiveSortedLimited = computed(() => 
  filteredActiveSorted.value.slice(0, 10)
)
```

```ts
// ✅ Good: Single getter with all logic
const filteredItems = computed(() => {
  let result = items.value.filter(i => i.active)
  result.sort((a, b) => a.name.localeCompare(b.name))
  return result.slice(0, 10)
})
```

## Using Methods for Dynamic Arguments

Use methods instead of getters for dynamic arguments:

```ts
// ❌ Bad: Getter with function that recomputes
const getFilteredItems = computed(() => {
  return (filter: Filter) => {
    return items.value.filter(item => matchesFilter(item, filter))
  }
})
```

```ts
// ✅ Good: Method with memoization
const filterCache = ref<Map<string, Item[]>>(new Map())

function getFilteredItems(filter: Filter): Item[] {
  const key = JSON.stringify(filter)
  
  if (filterCache.value.has(key)) {
    return filterCache.value.get(key)!
  }
  
  const filtered = items.value.filter(item => matchesFilter(item, filter))
  filterCache.value.set(key, filtered)
  return filtered
}

watch(items, () => {
  filterCache.value.clear()
}, { deep: true })
```

## Virtual Scrolling for Large Lists

Use virtual scrolling for large lists:

```ts
export const useListStore = defineStore('list', () => {
  const allItems = ref<Item[]>([])
  const visibleStart = ref(0)
  const visibleEnd = ref(50)
  
  const visibleItems = computed(() => {
    return allItems.value.slice(visibleStart.value, visibleEnd.value)
  })
  
  return { allItems, visibleStart, visibleEnd, visibleItems }
})
```

## Pagination

Implement pagination for large datasets:

```ts
export const useProductStore = defineStore('products', () => {
  const allProducts = ref<Product[]>([])
  const currentPage = ref(1)
  const pageSize = ref(20)
  
  const paginatedProducts = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    return allProducts.value.slice(start, end)
  })
  
  const totalPages = computed(() => 
    Math.ceil(allProducts.value.length / pageSize.value)
  )
  
  return { allProducts, currentPage, pageSize, paginatedProducts, totalPages }
})
```

## Performance Monitoring

Monitor getter performance in development:

```ts
export const useStore = defineStore('store', () => {
  const data = ref<Data[]>([])
  
  const processedData = computed(() => {
    if (import.meta.env.DEV) {
      console.time('processedData')
    }
    
    const result = data.value.map(item => ({
      ...item,
      processed: true
    }))
    
    if (import.meta.env.DEV) {
      console.timeEnd('processedData')
    }
    
    return result
  })
  
  return { data, processedData }
})
```

## Best Practices

1. **Avoid expensive operations**: Use methods or watchEffect for heavy computations
2. **Memoize when needed**: Cache expensive getter results
3. **Minimize dependencies**: Only watch what's necessary
4. **Use shallow reactivity**: For large objects
5. **Implement pagination**: For large datasets
6. **Debounce expensive operations**: Reduce recomputation frequency
7. **Monitor performance**: Track getter performance in development

## Common Mistakes

❌ **Expensive operations in getters**

```ts
const result = computed(() => {
  return heavyComputation(data.value) // ❌ Expensive
})
```

✅ **Use watchEffect**

```ts
const result = ref(null)

watchEffect(() => {
  result.value = heavyComputation(data.value) // ✅ Controlled
})
```

❌ **Not memoizing expensive getters**

```ts
const getFiltered = computed(() => (filter: Filter) => {
  return items.value.filter(i => matchesFilter(i, filter)) // ❌ No caching
})
```

✅ **Memoize expensive operations**

```ts
const cache = ref(new Map())

function getFiltered(filter: Filter) {
  const key = JSON.stringify(filter)
  if (cache.value.has(key)) return cache.value.get(key)
  
  const result = items.value.filter(i => matchesFilter(i, filter))
  cache.value.set(key, result)
  return result
}
```

❌ **Multiple getters with overlapping dependencies**

```ts
const filtered = computed(() => items.value.filter(i => i.active))
const sorted = computed(() => filtered.value.sort(...))
const limited = computed(() => sorted.value.slice(0, 10))
```

✅ **Single getter with all logic**

```ts
const result = computed(() => {
  let result = items.value.filter(i => i.active)
  result.sort(...)
  return result.slice(0, 10)
})
```

❌ **Deep watching large objects**

```ts
watch(
  largeObject,
  () => {
    // Expensive operation
  },
  { deep: true }
)
```

✅ **Watch specific properties**

```ts
watch(
  () => largeObject.value.importantProperty,
  () => {
    // Expensive operation
  }
)
```
