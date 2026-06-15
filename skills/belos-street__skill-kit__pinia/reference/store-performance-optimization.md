# Store Performance Optimization

Learn how to optimize Pinia store performance.

## Understanding Performance

Pinia stores are reactive and can impact performance if not optimized:

```ts
// ❌ Bad: Large object in single ref
export const useStore = defineStore('store', () => {
  const largeObject = ref<LargeObject>({ ... })
  return { largeObject }
})
```

```ts
// ✅ Good: Split into smaller refs
export const useStore = defineStore('store', () => {
  const part1 = ref<Part1>({ ... })
  const part2 = ref<Part2>({ ... })
  return { part1, part2 }
})
```

## Using Shallow Refs

Use shallow refs for large objects:

```ts
import { shallowRef } from 'vue'

export const useStore = defineStore('store', () => {
  const largeDataset = shallowRef<LargeData[]>([])
  
  function updateDataset(newData: LargeData[]) {
    largeDataset.value = newData // Only triggers when ref changes
  }
  
  return { largeDataset, updateDataset }
})
```

## Lazy Loading Stores

Load stores only when needed:

```ts
// stores/heavy.ts
export const useHeavyStore = defineStore('heavy', () => {
  const data = ref<HeavyData[]>([])
  
  async function loadData() {
    data.value = await api.getHeavyData()
  }
  
  return { data, loadData }
})
```

```ts
// stores/app.ts
export const useAppStore = defineStore('app', () => {
  const heavyStore = ref<ReturnType<typeof useHeavyStore> | null>(null)
  
  function loadHeavyData() {
    if (!heavyStore.value) {
      heavyStore.value = useHeavyStore()
    }
    return heavyStore.value.loadData()
  }
  
  return { loadHeavyData }
})
```

## Debouncing Updates

Debounce frequent updates:

```ts
import { debounce } from 'lodash-es'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const results = ref<SearchResult[]>([])
  
  const performSearch = debounce(async (q: string) => {
    if (q.length < 2) {
      results.value = []
      return
    }
    
    results.value = await api.search(q)
  }, 300)
  
  watch(query, performSearch)
  
  return { query, results }
})
```

## Throttling Updates

Throttle rapid updates:

```ts
import { throttle } from 'lodash-es'

export const useStore = defineStore('store', () => {
  const position = ref({ x: 0, y: 0 })
  
  const updatePosition = throttle((x: number, y: number) => {
    position.value = { x, y }
  }, 100)
  
  return { position, updatePosition }
})
```

## Virtual Scrolling

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

## Memoizing Expensive Computations

Memoize expensive computed values:

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  const cache = ref<Map<string, any>>(new Map())
  
  const expensiveComputation = computed(() => {
    const key = JSON.stringify(items.value)
    
    if (cache.value.has(key)) {
      return cache.value.get(key)
    }
    
    const result = heavyComputation(items.value)
    cache.value.set(key, result)
    return result
  })
  
  watch(items, () => {
    cache.value.clear()
  }, { deep: true })
  
  return { items, expensiveComputation }
})
```

## Selective Reactivity

Only make necessary parts reactive:

```ts
// ❌ Bad: Entire large object reactive
export const useStore = defineStore('store', () => {
  const largeObject = ref<LargeObject>({ ... })
  return { largeObject }
})
```

```ts
// ✅ Good: Only reactive parts
export const useStore = defineStore('store', () => {
  const importantPart = ref<ImportantPart>({ ... })
  const staticPart = ref<StaticPart>({ ... })
  
  return { importantPart, staticPart }
})
```

## Using Computed Selectors

Create computed selectors for specific data:

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  const activeTodos = computed(() => 
    todos.value.filter(t => !t.completed)
  )
  
  const completedTodos = computed(() => 
    todos.value.filter(t => t.completed)
  )
  
  const todoCount = computed(() => todos.value.length)
  const activeCount = computed(() => activeTodos.value.length)
  const completedCount = computed(() => completedTodos.value.length)
  
  return {
    todos,
    activeTodos,
    completedTodos,
    todoCount,
    activeCount,
    completedCount
  }
})
```

## Optimizing Watchers

Optimize watchers for better performance:

```ts
// ❌ Bad: Deep watch on large object
watch(
  largeObject,
  () => {
    // Expensive operation
  },
  { deep: true }
)
```

```ts
// ✅ Good: Watch specific properties
watch(
  () => largeObject.value.importantProperty,
  () => {
    // Expensive operation
  }
)
```

## Using markRaw

Use markRaw for non-reactive objects:

```ts
import { markRaw } from 'vue'

export const useStore = defineStore('store', () => {
  const config = ref(markRaw({
    // Large configuration object
  }))
  
  return { config }
})
```

## Optimizing Getters

Optimize getters for better performance:

```ts
// ❌ Bad: Expensive getter called frequently
const expensiveResult = computed(() => {
  return heavyComputation(data.value)
})
```

```ts
// ✅ Good: Memoize expensive computations
const cache = ref(new Map())

const expensiveResult = computed(() => {
  const key = JSON.stringify(data.value)
  
  if (cache.value.has(key)) {
    return cache.value.get(key)
  }
  
  const result = heavyComputation(data.value)
  cache.value.set(key, result)
  return result
})
```

## Best Practices

1. **Use shallow refs**: For large objects
2. **Lazy load stores**: Only load when needed
3. **Debounce/throttle**: For frequent updates
4. **Use virtual scrolling**: For large lists
5. **Implement pagination**: For large datasets
6. **Memoize computations**: Cache expensive operations
7. **Optimize watchers**: Watch only what's needed

## Common Mistakes

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

❌ **Not debouncing frequent updates**

```ts
watch(query, (newQuery) => {
  this.search(newQuery) // Called on every keystroke
})
```

✅ **Debounce updates**

```ts
const debouncedSearch = debounce((q: string) => {
  this.search(q)
}, 300)

watch(query, debouncedSearch)
```

❌ **Loading all data at once**

```ts
const allItems = ref<Item[]>([])

async function loadAll() {
  allItems.value = await api.getAllItems() // ❌ Too much data
}
```

✅ **Implement pagination**

```ts
const items = ref<Item[]>([])
const currentPage = ref(1)

async function loadPage(page: number) {
  items.value = await api.getItems(page, 20)
}
```

❌ **Not memoizing expensive computations**

```ts
const expensiveResult = computed(() => {
  return heavyComputation(data.value) // ❌ Recomputes every time
})
```

✅ **Memoize computations**

```ts
const cache = ref(new Map())

const expensiveResult = computed(() => {
  const key = JSON.stringify(data.value)
  if (cache.value.has(key)) return cache.value.get(key)
  
  const result = heavyComputation(data.value)
  cache.value.set(key, result)
  return result
})
```
