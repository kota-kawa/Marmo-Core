# Action Batch Updates

Learn how to batch state updates in Pinia actions for better performance.

## Why Batch Updates?

Batching updates reduces re-renders and improves performance:

```ts
// ❌ Bad: Multiple individual updates
function updateMultipleItems() {
  this.items[0].name = 'New Name 1'
  this.items[1].name = 'New Name 2'
  this.items[2].name = 'New Name 3'
}
```

```ts
// ✅ Good: Batch update
function updateMultipleItems() {
  this.items = [
    { ...this.items[0], name: 'New Name 1' },
    { ...this.items[1], name: 'New Name 2' },
    { ...this.items[2], name: 'New Name 3' }
  ]
}
```

## Array Batch Updates

### Replace Entire Array

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  function updateMultipleTodos(updates: Array<{ id: number; updates: Partial<Todo> }>) {
    todos.value = todos.value.map(todo => {
      const update = updates.find(u => u.id === todo.id)
      return update ? { ...todo, ...update.updates } : todo
    })
  }
  
  return { todos, updateMultipleTodos }
})
```

### Batch Add Items

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  
  function addMultipleItems(newItems: Item[]) {
    items.value = [...items.value, ...newItems]
  }
  
  return { items, addMultipleItems }
})
```

### Batch Remove Items

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  
  function removeMultipleItems(ids: number[]) {
    const idSet = new Set(ids)
    items.value = items.value.filter(item => !idSet.has(item.id))
  }
  
  return { items, removeMultipleItems }
})
```

## Object Batch Updates

### Update Multiple Properties

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function updateUser(updates: Partial<User>) {
    if (!user.value) return
    
    user.value = {
      ...user.value,
      ...updates
    }
  }
  
  return { user, updateUser }
})
```

### Nested Object Updates

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function updateAddress(updates: Partial<Address>) {
    if (!user.value) return
    
    user.value = {
      ...user.value,
      address: {
        ...user.value.address,
        ...updates
      }
    }
  }
  
  return { user, updateAddress }
})
```

## Using nextTick for Batching

Use `nextTick` to batch DOM updates:

```ts
import { nextTick } from 'vue'

export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  const isUpdating = ref(false)
  
  async function batchUpdate(updates: Array<{ id: number; data: Partial<Item> }>) {
    isUpdating.value = true
    
    items.value = items.value.map(item => {
      const update = updates.find(u => u.id === item.id)
      return update ? { ...item, ...update.data } : item
    })
    
    await nextTick()
    isUpdating.value = false
  }
  
  return { items, isUpdating, batchUpdate }
})
```

## Debounced Batch Updates

Debounce updates to batch rapid changes:

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
  
  watch(query, (newQuery) => {
    performSearch(newQuery)
  })
  
  return { query, results }
})
```

## Queued Batch Updates

Queue updates and process them in batches:

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  const updateQueue = ref<Array<{ id: number; data: Partial<Item> }>>([])
  const isProcessing = ref(false)
  
  async function processQueue() {
    if (isProcessing.value || updateQueue.value.length === 0) return
    
    isProcessing.value = true
    
    try {
      const updates = [...updateQueue.value]
      updateQueue.value = []
      
      items.value = items.value.map(item => {
        const update = updates.find(u => u.id === item.id)
        return update ? { ...item, ...update.data } : item
      })
      
      await api.batchUpdate(updates)
    } finally {
      isProcessing.value = false
    }
  }
  
  function queueUpdate(id: number, data: Partial<Item>) {
    updateQueue.value.push({ id, data })
    processQueue()
  }
  
  return { items, isProcessing, queueUpdate }
})
```

## Transaction Pattern

Use transactions for atomic updates:

```ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const coupon = ref<string | null>(null)
  
  async function applyTransaction(transaction: CartTransaction) {
    const originalItems = [...items.value]
    const originalCoupon = coupon.value
    
    try {
      items.value = transaction.items
      coupon.value = transaction.coupon
      
      await api.validateCart({ items: items.value, coupon: coupon.value })
    } catch (err) {
      items.value = originalItems
      coupon.value = originalCoupon
      throw err
    }
  }
  
  return { items, coupon, applyTransaction }
})
```

## Optimistic Batch Updates

Apply updates optimistically and rollback on error:

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  async function batchToggle(ids: number[]) {
    const originalTodos = todos.value.map(todo => ({
      id: todo.id,
      completed: todo.completed
    }))
    
    try {
      todos.value = todos.value.map(todo => 
        ids.includes(todo.id) 
          ? { ...todo, completed: !todo.completed }
          : todo
      )
      
      await api.batchToggle(ids)
    } catch (err) {
      todos.value = todos.value.map(todo => {
        const original = originalTodos.find(o => o.id === todo.id)
        return original ? { ...todo, completed: original.completed } : todo
      })
      throw err
    }
  }
  
  return { todos, batchToggle }
})
```

## Batch API Calls

Combine multiple API calls into one:

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  const isLoading = ref(false)
  
  async function batchFetch(ids: number[]) {
    isLoading.value = true
    
    try {
      const fetchedItems = await api.batchGet(ids)
      
      const idSet = new Set(ids)
      items.value = items.value.map(item =>
        idSet.has(item.id)
          ? fetchedItems.find(f => f.id === item.id) || item
          : item
      )
    } finally {
      isLoading.value = false
    }
  }
  
  return { items, isLoading, batchFetch }
})
```

## Batch with Loading State

Track loading state for batch operations:

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  const batchOperations = ref<Set<string>>(new Set())
  
  async function batchUpdate(operationId: string, updates: Array<{ id: number; data: Partial<Item> }>) {
    batchOperations.value.add(operationId)
    
    try {
      items.value = items.value.map(item => {
        const update = updates.find(u => u.id === item.id)
        return update ? { ...item, ...update.data } : item
      })
      
      await api.batchUpdate(updates)
    } finally {
      batchOperations.value.delete(operationId)
    }
  }
  
  const isProcessing = computed(() => batchOperations.value.size > 0)
  
  return { items, isProcessing, batchUpdate }
})
```

## Best Practices

1. **Batch array updates**: Replace entire array instead of individual mutations
2. **Use immutable updates**: Create new objects/arrays for better reactivity
3. **Debounce rapid changes**: Batch frequent updates
4. **Queue updates**: Process updates in batches
5. **Use transactions**: Atomic updates with rollback
6. **Optimistic updates**: Apply immediately, rollback on error

## Common Mistakes

❌ **Individual array mutations**

```ts
function updateItems() {
  this.items[0].name = 'New Name' // ❌ Individual mutation
  this.items[1].name = 'New Name'
  this.items[2].name = 'New Name'
}
```

✅ **Batch array update**

```ts
function updateItems() {
  this.items = [
    { ...this.items[0], name: 'New Name' },
    { ...this.items[1], name: 'New Name' },
    { ...this.items[2], name: 'New Name' }
  ]
}
```

❌ **Multiple individual API calls**

```ts
async function updateItems() {
  await api.updateItem(this.items[0].id, this.items[0])
  await api.updateItem(this.items[1].id, this.items[1])
  await api.updateItem(this.items[2].id, this.items[2])
}
```

✅ **Batch API call**

```ts
async function updateItems() {
  await api.batchUpdate(this.items)
}
```

❌ **Not handling batch errors**

```ts
async function batchUpdate(updates: any[]) {
  this.items = this.items.map(item => {
    const update = updates.find(u => u.id === item.id)
    return update ? { ...item, ...update } : item
  })
  await api.batchUpdate(updates) // ❌ No error handling
}
```

✅ **Handle errors with rollback**

```ts
async function batchUpdate(updates: any[]) {
  const originalItems = [...this.items]
  
  try {
    this.items = this.items.map(item => {
      const update = updates.find(u => u.id === item.id)
      return update ? { ...item, ...update } : item
    })
    await api.batchUpdate(updates)
  } catch (err) {
    this.items = originalItems
    throw err
  }
}
```

❌ **Not debouncing rapid updates**

```ts
watch(query, (newQuery) => {
  this.search(newQuery) // ❌ Called on every keystroke
})
```

✅ **Debounce updates**

```ts
const debouncedSearch = debounce((q: string) => {
  this.search(q)
}, 300)

watch(query, debouncedSearch)
```
