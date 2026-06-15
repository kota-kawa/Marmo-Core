# State Mutation Best Practices

Learn the best practices for mutating state in Pinia stores.

## Use Actions for State Mutations

Always use actions to mutate state instead of mutating directly from components.

### ❌ Bad: Direct Mutation

```vue
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()

function increment() {
  counter.count++ // Direct mutation
}
</script>
```

### ✅ Good: Use Actions

```ts
// store
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  
  function increment() {
    count.value++
  }
  
  return { count, increment }
})
```

```vue
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()

function increment() {
  counter.increment() // Use action
}
</script>
```

## Why Use Actions?

1. **Encapsulation**: Control how state is modified
2. **Validation**: Validate changes before applying them
3. **Logging**: Track state changes for debugging
4. **Testing**: Easier to test business logic
5. **Consistency**: Single source of truth for mutations

## Validation in Actions

Add validation logic to actions:

```ts
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  const min = ref(0)
  const max = ref(100)
  
  function increment() {
    if (count.value < max.value) {
      count.value++
    }
  }
  
  function decrement() {
    if (count.value > min.value) {
      count.value--
    }
  }
  
  function setCount(value: number) {
    if (value < min.value || value > max.value) {
      throw new Error(`Count must be between ${min.value} and ${max.value}`)
    }
    count.value = value
  }
  
  return { count, min, max, increment, decrement, setCount }
})
```

## Immutable Updates

For complex objects, use immutable update patterns:

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
  
  function updateAddress(address: Address) {
    if (!user.value) return
    
    user.value = {
      ...user.value,
      address: {
        ...user.value.address,
        ...address
      }
    }
  }
  
  return { user, updateUser, updateAddress }
})
```

## Batch Updates

Group related state updates together:

```ts
export const useFormStore = defineStore('form', () => {
  const formData = ref<FormData>({
    name: '',
    email: '',
    age: 0
  })
  
  const errors = ref<Record<string, string>>({})
  const isSubmitting = ref(false)
  
  async function submitForm() {
    isSubmitting.value = true
    errors.value = {}
    
    try {
      // Validate
      if (!formData.value.email.includes('@')) {
        errors.value.email = 'Invalid email'
        return
      }
      
      // Submit
      await api.submitForm(formData.value)
      
      // Reset on success
      formData.value = { name: '', email: '', age: 0 }
    } catch (err) {
      errors.value.general = 'Submission failed'
    } finally {
      isSubmitting.value = false
    }
  }
  
  return { formData, errors, isSubmitting, submitForm }
})
```

## Array Mutations

Use proper array mutation methods:

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  function addTodo(text: string) {
    todos.value.push({
      id: Date.now(),
      text,
      completed: false
    })
  }
  
  function removeTodo(id: number) {
    const index = todos.value.findIndex(t => t.id === id)
    if (index > -1) {
      todos.value.splice(index, 1)
    }
  }
  
  function updateTodo(id: number, updates: Partial<Todo>) {
    const index = todos.value.findIndex(t => t.id === id)
    if (index > -1) {
      todos.value[index] = {
        ...todos.value[index],
        ...updates
      }
    }
  }
  
  function clearCompleted() {
    todos.value = todos.value.filter(t => !t.completed)
  }
  
  function reorderTodos(sourceIndex: number, targetIndex: number) {
    const [removed] = todos.value.splice(sourceIndex, 1)
    todos.value.splice(targetIndex, 0, removed)
  }
  
  return { todos, addTodo, removeTodo, updateTodo, clearCompleted, reorderTodos }
})
```

## State Reset

Provide a way to reset state to initial values:

```ts
export const useFilterStore = defineStore('filter', () => {
  const initialState = {
    category: 'all',
    priceRange: [0, 1000],
    rating: 0,
    sortBy: 'popular'
  }
  
  const filters = ref<Filters>({ ...initialState })
  
  function setFilter<K extends keyof Filters>(key: K, value: Filters[K]) {
    filters.value[key] = value
  }
  
  function setFilters(newFilters: Partial<Filters>) {
    filters.value = {
      ...filters.value,
      ...newFilters
    }
  }
  
  function $reset() {
    filters.value = { ...initialState }
  }
  
  return { filters, setFilter, setFilters, $reset }
})
```

## Async State Updates

Handle async operations properly:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function fetchProducts() {
    isLoading.value = true
    error.value = null
    
    try {
      products.value = await api.getProducts()
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to fetch')
      products.value = []
    } finally {
      isLoading.value = false
    }
  }
  
  async function createProduct(product: Omit<Product, 'id'>) {
    isLoading.value = true
    error.value = null
    
    try {
      const newProduct = await api.createProduct(product)
      products.value.push(newProduct)
      return newProduct
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to create')
      throw err
    } finally {
      isLoading.value = false
    }
  }
  
  return { products, isLoading, error, fetchProducts, createProduct }
})
```

## Optimistic Updates

Update state immediately, then handle errors:

```ts
export const useLikeStore = defineStore('likes', () => {
  const likedItems = ref<Set<number>>(new Set())
  const pendingLikes = ref<Set<number>>(new Set())
  
  async function toggleLike(itemId: number) {
    const isLiked = likedItems.value.has(itemId)
    
    // Optimistic update
    if (isLiked) {
      likedItems.value.delete(itemId)
    } else {
      likedItems.value.add(itemId)
    }
    
    pendingLikes.value.add(itemId)
    
    try {
      await api.toggleLike(itemId)
    } catch (err) {
      // Revert on error
      if (isLiked) {
        likedItems.value.add(itemId)
      } else {
        likedItems.value.delete(itemId)
      }
      throw err
    } finally {
      pendingLikes.value.delete(itemId)
    }
  }
  
  return { likedItems, pendingLikes, toggleLike }
})
```

## State Persistence

Persist state to localStorage:

```ts
export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<'light' | 'dark'>('light')
  const language = ref('en')
  
  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
  }
  
  function setLanguage(newLanguage: string) {
    language.value = newLanguage
    localStorage.setItem('language', newLanguage)
  }
  
  function $hydrate() {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null
    const savedLanguage = localStorage.getItem('language')
    
    if (savedTheme) theme.value = savedTheme
    if (savedLanguage) language.value = savedLanguage
  }
  
  return { theme, language, setTheme, setLanguage, $hydrate }
})
```

## Best Practices

1. **Always use actions**: Never mutate state directly from components
2. **Validate inputs**: Check data before updating state
3. **Use immutable updates**: For complex objects, create new references
4. **Batch related updates**: Group related state changes
5. **Handle errors**: Always handle errors in async actions
6. **Provide reset**: Allow resetting state to initial values
7. **Keep actions focused**: Each action should do one thing well

## Common Mistakes

❌ **Mutating state directly from components**

```vue
<script setup lang="ts">
const store = useStore()
store.items.push(newItem) // ❌ Direct mutation
</script>
```

✅ **Use actions**

```ts
// store
function addItem(item: Item) {
  this.items.push(item) // ✅ Encapsulated mutation
}
```

```vue
<script setup lang="ts">
const store = useStore()
store.addItem(newItem) // ✅ Use action
</script>
```

❌ **Mutating arrays incorrectly**

```ts
function updateItems() {
  this.items = this.items.filter(item => item.active) // ❌ Loses reactivity in some cases
}
```

✅ **Use proper array methods**

```ts
function updateItems() {
  this.items = [...this.items.filter(item => item.active)] // ✅ Creates new array
}
```

❌ **Not handling errors in async actions**

```ts
async function fetchData() {
  this.isLoading = true
  this.data = await api.getData() // ❌ No error handling
  this.isLoading = false
}
```

✅ **Handle errors properly**

```ts
async function fetchData() {
  this.isLoading = true
  try {
    this.data = await api.getData()
  } catch (err) {
    this.error = err
    this.data = []
  } finally {
    this.isLoading = false
  }
}
```
