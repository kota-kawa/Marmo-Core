# TypeScript Generic Stores

Learn how to create generic Pinia stores with TypeScript.

## Basic Generic Store

Create a generic store for reusable patterns:

```ts
export const useListStore = <T extends { id: number }>(
  id: string,
  fetchFn: () => Promise<T[]>
) => {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    const isLoading = ref(false)
    const error = ref<Error | null>(null)
    
    async function fetch() {
      isLoading.value = true
      error.value = null
      
      try {
        items.value = await fetchFn()
      } catch (err) {
        error.value = err instanceof Error ? err : new Error('Failed to fetch')
      } finally {
        isLoading.value = false
      }
    }
    
    function add(item: T) {
      items.value.push(item)
    }
    
    function update(id: number, updates: Partial<T>) {
      const index = items.value.findIndex(i => i.id === id)
      if (index > -1) {
        items.value[index] = {
          ...items.value[index],
          ...updates
        }
      }
    }
    
    function remove(id: number) {
      const index = items.value.findIndex(i => i.id === id)
      if (index > -1) {
        items.value.splice(index, 1)
      }
    }
    
    return {
      items,
      isLoading,
      error,
      fetch,
      add,
      update,
      remove
    }
  })
}
```

## Using Generic Stores

Use generic stores with specific types:

```ts
interface Product {
  id: number
  name: string
  price: number
  category: string
}

export const useProductStore = useListStore<Product>('products', () => 
  api.getProducts()
)

interface User {
  id: number
  name: string
  email: string
}

export const useUserStore = useListStore<User>('users', () => 
  api.getUsers()
)
```

## Generic Store with Constraints

Add constraints to generic types:

```ts
export const useEntityStore = <T extends { id: number; createdAt: Date }>(
  id: string,
  fetchFn: () => Promise<T[]>
) => {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    
    function add(item: Omit<T, 'id' | 'createdAt'>): T {
      const newItem: T = {
        ...item,
        id: Date.now(),
        createdAt: new Date()
      } as T
      
      items.value.push(newItem)
      return newItem
    }
    
    return { items, add }
  })
}
```

## Generic Store with Multiple Type Parameters

Use multiple type parameters for complex stores:

```ts
export const useMapStore = <
  K extends string | number,
  V extends { id: K }
>(
  id: string
) => {
  return defineStore(id, () => {
    const items = ref<Map<K, V>>(new Map())
    
    function set(key: K, value: V) {
      items.value.set(key, value)
    }
    
    function get(key: K): V | undefined {
      return items.value.get(key)
    }
    
    function has(key: K): boolean {
      return items.value.has(key)
    }
    
    function deleteItem(key: K) {
      items.value.delete(key)
    }
    
    return {
      items,
      set,
      get,
      has,
      deleteItem
    }
  })
}
```

## Generic Store with Default Types

Provide default types for generic parameters:

```ts
export const useStore = <
  T = any,
  E = Error
>(
  id: string
) => {
  return defineStore(id, () => {
    const data = ref<T | null>(null)
    const error = ref<E | null>(null)
    
    return { data, error }
  })
}
```

## Generic CRUD Store

Create a generic CRUD store:

```ts
export const createCRUDStore = <T extends { id: number }>(
  id: string,
  api: {
    getAll: () => Promise<T[]>
    getById: (id: number) => Promise<T>
    create: (data: Omit<T, 'id'>) => Promise<T>
    update: (id: number, data: Partial<T>) => Promise<T>
    delete: (id: number) => Promise<void>
  }
) => {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    const isLoading = ref(false)
    const error = ref<Error | null>(null)
    
    async function fetchAll() {
      isLoading.value = true
      error.value = null
      
      try {
        items.value = await api.getAll()
      } catch (err) {
        error.value = err instanceof Error ? err : new Error('Failed to fetch')
      } finally {
        isLoading.value = false
      }
    }
    
    async function fetchById(id: number) {
      isLoading.value = true
      error.value = null
      
      try {
        const item = await api.getById(id)
        const index = items.value.findIndex(i => i.id === id)
        if (index > -1) {
          items.value[index] = item
        } else {
          items.value.push(item)
        }
        return item
      } catch (err) {
        error.value = err instanceof Error ? err : new Error('Failed to fetch')
        throw error.value
      } finally {
        isLoading.value = false
      }
    }
    
    async function create(data: Omit<T, 'id'>) {
      isLoading.value = true
      error.value = null
      
      try {
        const item = await api.create(data)
        items.value.push(item)
        return item
      } catch (err) {
        error.value = err instanceof Error ? err : new Error('Failed to create')
        throw error.value
      } finally {
        isLoading.value = false
      }
    }
    
    async function update(id: number, data: Partial<T>) {
      isLoading.value = true
      error.value = null
      
      try {
        const item = await api.update(id, data)
        const index = items.value.findIndex(i => i.id === id)
        if (index > -1) {
          items.value[index] = item
        }
        return item
      } catch (err) {
        error.value = err instanceof Error ? err : new Error('Failed to update')
        throw error.value
      } finally {
        isLoading.value = false
      }
    }
    
    async function remove(id: number) {
      isLoading.value = true
      error.value = null
      
      try {
        await api.delete(id)
        const index = items.value.findIndex(i => i.id === id)
        if (index > -1) {
          items.value.splice(index, 1)
        }
      } catch (err) {
        error.value = err instanceof Error ? err : new Error('Failed to delete')
        throw error.value
      } finally {
        isLoading.value = false
      }
    }
    
    return {
      items,
      isLoading,
      error,
      fetchAll,
      fetchById,
      create,
      update,
      remove
    }
  })
}
```

## Using Generic CRUD Store

Use the generic CRUD store with specific types:

```ts
interface Product {
  id: number
  name: string
  price: number
  category: string
}

export const useProductStore = createCRUDStore<Product>('products', {
  getAll: () => api.getProducts(),
  getById: (id) => api.getProduct(id),
  create: (data) => api.createProduct(data),
  update: (id, data) => api.updateProduct(id, data),
  delete: (id) => api.deleteProduct(id)
})
```

## Generic Store with Type Guards

Use type guards in generic stores:

```ts
export const useStore = <T extends { type: string }>(
  id: string,
  typeGuard: (item: any) => item is T
) => {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    
    function addItem(item: any): item is T {
      if (!typeGuard(item)) {
        throw new Error('Invalid item type')
      }
      
      items.value.push(item)
      return true
    }
    
    return { items, addItem }
  })
}
```

## Generic Store with Utility Types

Use utility types in generic stores:

```ts
export const useStore = <T extends { id: number }>(
  id: string
) => {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    
    function create(data: Omit<T, 'id'>): T {
      const item: T = {
        ...data,
        id: Date.now()
      } as T
      
      items.value.push(item)
      return item
    }
    
    function update(id: number, data: Partial<T>): T | undefined {
      const index = items.value.findIndex(i => i.id === id)
      if (index > -1) {
        items.value[index] = {
          ...items.value[index],
          ...data
        }
        return items.value[index]
      }
      return undefined
    }
    
    function patch(id: number, data: Pick<T, keyof T>): T | undefined {
      const index = items.value.findIndex(i => i.id === id)
      if (index > -1) {
        items.value[index] = {
          ...items.value[index],
          ...data
        }
        return items.value[index]
      }
      return undefined
    }
    
    return { items, create, update, patch }
  })
}
```

## Generic Store with Computed Types

Use computed types in generic stores:

```ts
export const useStore = <T extends { id: number }>(
  id: string
) => {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    
    type ItemId = T['id']
    type ItemType = T
    
    function findById(id: ItemId): ItemType | undefined {
      return items.value.find(i => i.id === id)
    }
    
    function filterBy<K extends keyof T>(
      key: K,
      value: T[K]
    ): ItemType[] {
      return items.value.filter(item => item[key] === value)
    }
    
    return { items, findById, filterBy }
  })
}
```

## Best Practices

1. **Use constraints**: Add constraints to generic types
2. **Provide defaults**: Use default types when appropriate
3. **Type guards**: Use type guards for runtime validation
4. **Utility types**: Leverage TypeScript's utility types
5. **Document types**: Document what types are expected
6. **Test generics**: Test with multiple type combinations

## Common Mistakes

❌ **Not using constraints**

```ts
export const useStore = <T>(id: string) => { // ❌ No constraints
  return defineStore(id, () => {
    const items = ref<T[]>([])
    return { items }
  })
}
```

✅ **Use constraints**

```ts
export const useStore = <T extends { id: number }>(id: string) => { // ✅ Has constraints
  return defineStore(id, () => {
    const items = ref<T[]>([])
    return { items }
  })
}
```

❌ **Not typing generic parameters**

```ts
function add(item) { // ❌ Type is any
  this.items.push(item)
}
```

✅ **Type generic parameters**

```ts
function add(item: T) { // ✅ Type safe
  this.items.push(item)
}
```

❌ **Not using utility types**

```ts
function create(data) { // ❌ No type safety
  const item = { ...data, id: Date.now() }
  this.items.push(item)
}
```

✅ **Use utility types**

```ts
function create(data: Omit<T, 'id'>) { // ✅ Type safe
  const item: T = { ...data, id: Date.now() } as T
  this.items.push(item)
}
```

❌ **Not documenting types**

```ts
export const useStore = <T>(id: string) => { // ❌ No documentation
  return defineStore(id, () => {})
}
```

✅ **Document types**

```ts
/**
 * Generic store for items with id
 * @template T - Type extending { id: number }
 */
export const useStore = <T extends { id: number }>(id: string) => { // ✅ Documented
  return defineStore(id, () => {})
}
```
