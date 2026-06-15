# Getter Pass Arguments

Learn how to pass arguments to Pinia getters.

## The Problem

Getters are computed properties and cannot accept arguments:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const getProductById = computed(() => (id: number) => {
    return products.value.find(p => p.id === id)
  })
  
  return { products, getProductById }
})
```

This works but the getter returns a function, not the value directly.

## Solution: Return Functions from Getters

Return a function from the getter that accepts arguments:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const getProductById = computed(() => {
    return (id: number) => products.value.find(p => p.id === id)
  })
  
  const getProductsByCategory = computed(() => {
    return (category: string) => products.value.filter(p => p.category === category)
  })
  
  return { products, getProductById, getProductsByCategory }
})
```

## Usage in Components

```vue
<script setup lang="ts">
import { useProductStore } from '@/stores/products'

const productStore = useProductStore()

const product = productStore.getProductById(1)
const electronics = productStore.getProductsByCategory('electronics')
</script>

<template>
  <div>
    <h2>{{ product?.name }}</h2>
    <div v-for="item in electronics" :key="item.id">
      {{ item.name }}
    </div>
  </div>
</template>
```

## Multiple Arguments

Pass multiple arguments to getter functions:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const filterProducts = computed(() => {
    return (filters: ProductFilters) => {
      let result = products.value
      
      if (filters.category) {
        result = result.filter(p => p.category === filters.category)
      }
      
      if (filters.minPrice !== undefined) {
        result = result.filter(p => p.price >= filters.minPrice)
      }
      
      if (filters.maxPrice !== undefined) {
        result = result.filter(p => p.price <= filters.maxPrice)
      }
      
      if (filters.inStock) {
        result = result.filter(p => p.inStock)
      }
      
      return result
    }
  })
  
  return { products, filterProducts }
})
```

## Caching Considerations

Getters that return functions don't cache the function results:

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  
  const getItem = computed(() => {
    return (id: number) => {
      console.log('Finding item') // Logs every time
      return items.value.find(i => i.id === id)
    }
  })
  
  return { items, getItem }
})
```

```vue
<script setup lang="ts">
const store = useStore()

const item1 = store.getItem(1) // Logs "Finding item"
const item2 = store.getItem(1) // Logs "Finding item" again
</script>
```

## Memoizing Getter Functions

Memoize function results for better performance:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const cache = ref<Map<number, Product | undefined>>(new Map())
  
  const getProductById = computed(() => {
    return (id: number) => {
      if (cache.value.has(id)) {
        return cache.value.get(id)
      }
      
      const product = products.value.find(p => p.id === id)
      cache.value.set(id, product)
      return product
    }
  })
  
  watch(products, () => {
    cache.value.clear()
  }, { deep: true })
  
  return { products, getProductById }
})
```

## Using Methods Instead

For complex argument handling, consider using methods:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  function getProductById(id: number) {
    return products.value.find(p => p.id === id)
  }
  
  function getProductsByCategory(category: string) {
    return products.value.filter(p => p.category === category)
  }
  
  function filterProducts(filters: ProductFilters) {
    let result = products.value
    
    if (filters.category) {
      result = result.filter(p => p.category === filters.category)
    }
    
    if (filters.minPrice !== undefined) {
      result = result.filter(p => p.price >= filters.minPrice)
    }
    
    if (filters.maxPrice !== undefined) {
      result = result.filter(p => p.price <= filters.maxPrice)
    }
    
    return result
  }
  
  return { products, getProductById, getProductsByCategory, filterProducts }
})
```

## When to Use Getters vs Methods

### Use Getters When:
- The result is derived from state
- You want caching for simple cases
- The computation is lightweight

### Use Methods When:
- You need complex argument handling
- The computation is expensive
- You need side effects
- You need better control over caching

## Comparison Examples

### Getter with Arguments

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  
  const getItem = computed(() => (id: number) => {
    return items.value.find(i => i.id === id)
  })
  
  return { items, getItem }
})
```

### Method

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  
  function getItem(id: number) {
    return items.value.find(i => i.id === id)
  }
  
  return { items, getItem }
})
```

Both work, but methods give you more control.

## Advanced: Curried Getters

Create reusable getter functions:

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  
  const filterBy = computed(() => {
    return (key: keyof Item) => (value: any) => {
      return items.value.filter(item => item[key] === value)
    }
  })
  
  return { items, filterBy }
})
```

```vue
<script setup lang="ts">
const store = useStore()

const activeItems = store.filterBy('active')(true)
const categoryItems = store.filterBy('category')('electronics')
</script>
```

## Best Practices

1. **Use methods for complex arguments**: Better control and clarity
2. **Use getters for simple derived state**: Leverage caching
3. **Memoize when needed**: Cache expensive computations
4. **Clear cache on state changes**: Prevent stale data
5. **Consider readability**: Choose the approach that's clearer

## Common Mistakes

❌ **Expecting automatic caching**

```ts
const getProduct = computed(() => (id: number) => {
  return expensiveComputation(id) // ❌ Not cached
})
```

✅ **Use methods for expensive operations**

```ts
const cache = ref(new Map())

function getProduct(id: number) {
  if (cache.value.has(id)) {
    return cache.value.get(id)
  }
  
  const result = expensiveComputation(id)
  cache.value.set(id, result)
  return result
}
```

❌ **Complex logic in getters**

```ts
const filtered = computed(() => (filters: ComplexFilters) => {
  // ❌ Too complex for getter
  let result = items.value
  if (filters.a) result = result.filter(...)
  if (filters.b) result = result.filter(...)
  if (filters.c) result = result.filter(...)
  return result
})
```

✅ **Use method for complex logic**

```ts
function filterItems(filters: ComplexFilters) {
  let result = items.value
  if (filters.a) result = result.filter(...)
  if (filters.b) result = result.filter(...)
  if (filters.c) result = result.filter(...)
  return result
}
```

❌ **Not clearing cache**

```ts
const cache = ref(new Map())

const getItem = computed(() => (id: number) => {
  if (cache.value.has(id)) return cache.value.get(id)
  const item = items.value.find(i => i.id === id)
  cache.value.set(id, item)
  return item
})
// ❌ Cache never cleared
```

✅ **Clear cache on state changes**

```ts
const cache = ref(new Map())

const getItem = computed(() => (id: number) => {
  if (cache.value.has(id)) return cache.value.get(id)
  const item = items.value.find(i => i.id === id)
  cache.value.set(id, item)
  return item
})

watch(items, () => {
  cache.value.clear()
}, { deep: true })
```
