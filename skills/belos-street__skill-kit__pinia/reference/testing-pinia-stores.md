# Testing Pinia Stores

Learn how to test Pinia stores effectively.

## Basic Store Testing

Test simple stores:

```ts
// stores/counter.ts
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  
  function increment() {
    count.value++
  }
  
  function decrement() {
    count.value--
  }
  
  return { count, increment, decrement }
})
```

```ts
// stores/__tests__/counter.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useCounterStore } from '../counter'

describe('Counter Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  
  it('initializes with count 0', () => {
    const store = useCounterStore()
    expect(store.count).toBe(0)
  })
  
  it('increments count', () => {
    const store = useCounterStore()
    store.increment()
    expect(store.count).toBe(1)
  })
  
  it('decrements count', () => {
    const store = useCounterStore()
    store.count = 5
    store.decrement()
    expect(store.count).toBe(4)
  })
})
```

## Testing Async Stores

Test stores with async operations:

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function fetchUser() {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await api.getCurrentUser()
      user.value = response.data
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to fetch user')
    } finally {
      isLoading.value = false
    }
  }
  
  return { user, isLoading, error, fetchUser }
})
```

```ts
// stores/__tests__/user.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '../user'
import * as api from '@/api'

vi.mock('@/api')

describe('User Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })
  
  it('fetches user successfully', async () => {
    const mockUser = { id: 1, name: 'John' }
    vi.mocked(api.getCurrentUser).mockResolvedValue({ data: mockUser })
    
    const store = useUserStore()
    
    expect(store.isLoading).toBe(false)
    expect(store.user).toBe(null)
    
    await store.fetchUser()
    
    expect(store.isLoading).toBe(false)
    expect(store.user).toEqual(mockUser)
    expect(api.getCurrentUser).toHaveBeenCalledOnce()
  })
  
  it('handles fetch errors', async () => {
    const mockError = new Error('Network error')
    vi.mocked(api.getCurrentUser).mockRejectedValue(mockError)
    
    const store = useUserStore()
    
    await store.fetchUser()
    
    expect(store.isLoading).toBe(false)
    expect(store.user).toBe(null)
    expect(store.error).toEqual(mockError)
  })
})
```

## Testing Getters

Test computed getters:

```ts
// stores/cart.ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  
  const total = computed(() => 
    items.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
  )
  
  const itemCount = computed(() => 
    items.value.reduce((sum, item) => sum + item.quantity, 0)
  )
  
  return { items, total, itemCount }
})
```

```ts
// stores/__tests__/cart.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useCartStore } from '../cart'

describe('Cart Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  
  it('calculates total correctly', () => {
    const store = useCartStore()
    store.items = [
      { id: 1, name: 'Item 1', price: 10, quantity: 2 },
      { id: 2, name: 'Item 2', price: 20, quantity: 1 }
    ]
    
    expect(store.total).toBe(40)
  })
  
  it('calculates item count correctly', () => {
    const store = useCartStore()
    store.items = [
      { id: 1, name: 'Item 1', price: 10, quantity: 2 },
      { id: 2, name: 'Item 2', price: 20, quantity: 3 }
    ]
    
    expect(store.itemCount).toBe(5)
  })
})
```

## Testing Actions

Test store actions:

```ts
// stores/todo.ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  function addTodo(text: string) {
    todos.value.push({
      id: Date.now(),
      text,
      completed: false
    })
  }
  
  function toggleTodo(id: number) {
    const todo = todos.value.find(t => t.id === id)
    if (todo) {
      todo.completed = !todo.completed
    }
  }
  
  function removeTodo(id: number) {
    const index = todos.value.findIndex(t => t.id === id)
    if (index > -1) {
      todos.value.splice(index, 1)
    }
  }
  
  return { todos, addTodo, toggleTodo, removeTodo }
})
```

```ts
// stores/__tests__/todo.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useTodoStore } from '../todo'

describe('Todo Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  
  it('adds todo', () => {
    const store = useTodoStore()
    store.addTodo('Test todo')
    
    expect(store.todos).toHaveLength(1)
    expect(store.todos[0]).toMatchObject({
      text: 'Test todo',
      completed: false
    })
  })
  
  it('toggles todo', () => {
    const store = useTodoStore()
    store.addTodo('Test todo')
    const todoId = store.todos[0].id
    
    store.toggleTodo(todoId)
    expect(store.todos[0].completed).toBe(true)
    
    store.toggleTodo(todoId)
    expect(store.todos[0].completed).toBe(false)
  })
  
  it('removes todo', () => {
    const store = useTodoStore()
    store.addTodo('Test todo')
    const todoId = store.todos[0].id
    
    store.removeTodo(todoId)
    expect(store.todos).toHaveLength(0)
  })
})
```

## Testing Cross-Store Actions

Test actions that use other stores:

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  
  async function processCheckout() {
    if (!authStore.isAuthenticated) {
      throw new Error('User not authenticated')
    }
    
    if (cartStore.items.length === 0) {
      throw new Error('Cart is empty')
    }
    
    const order = await api.createOrder({
      userId: authStore.user!.id,
      items: cartStore.items
    })
    
    cartStore.clear()
    return order
  }
  
  return { processCheckout }
})
```

```ts
// stores/__tests__/checkout.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useCheckoutStore } from '../checkout'
import { useAuthStore } from '../auth'
import { useCartStore } from '../cart'
import * as api from '@/api'

vi.mock('@/api')

describe('Checkout Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })
  
  it('processes checkout successfully', async () => {
    const authStore = useAuthStore()
    const cartStore = useCartStore()
    const checkoutStore = useCheckoutStore()
    
    authStore.user = { id: 1, name: 'John' }
    cartStore.items = [{ id: 1, name: 'Product', price: 10 }]
    
    const mockOrder = { id: 1, userId: 1, items: cartStore.items }
    vi.mocked(api.createOrder).mockResolvedValue(mockOrder)
    
    const result = await checkoutStore.processCheckout()
    
    expect(result).toEqual(mockOrder)
    expect(cartStore.items).toEqual([])
  })
  
  it('throws error when not authenticated', async () => {
    const authStore = useAuthStore()
    const checkoutStore = useCheckoutStore()
    
    authStore.user = null
    
    await expect(checkoutStore.processCheckout()).rejects.toThrow('User not authenticated')
  })
})
```

## Testing with Test Utilities

Create test utilities for common patterns:

```ts
// utils/test/store.ts
export function createStoreTest<T extends (...args: any[]) => any>(
  setup: T
) {
  const pinia = createPinia()
  setActivePinia(pinia)
  
  const store = setup()
  
  return {
    store,
    pinia
  }
}

export function mockApiResponse<T>(data: T) {
  return Promise.resolve({ data })
}

export function mockApiError(message: string) {
  return Promise.reject(new Error(message))
}
```

```ts
// stores/__tests__/user.test.ts
import { createStoreTest, mockApiResponse } from '@/utils/test/store'
import { useUserStore } from '../user'
import * as api from '@/api'

vi.mock('@/api')

describe('User Store', () => {
  it('fetches user', async () => {
    const mockUser = { id: 1, name: 'John' }
    vi.mocked(api.getCurrentUser).mockReturnValue(mockApiResponse(mockUser))
    
    const { store } = createStoreTest(() => useUserStore())
    
    await store.fetchUser()
    
    expect(store.user).toEqual(mockUser)
  })
})
```

## Testing Store Persistence

Test stores with persistence:

```ts
// stores/preferences.ts
export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<'light' | 'dark'>('light')
  const language = ref('en')
  
  watch(
    () => ({ theme: theme.value, language: language.value }),
    (state) => {
      localStorage.setItem('preferences', JSON.stringify(state))
    },
    { deep: true }
  )
  
  function $hydrate() {
    const saved = localStorage.getItem('preferences')
    if (saved) {
      const state = JSON.parse(saved)
      theme.value = state.theme
      language.value = state.language
    }
  }
  
  return { theme, language, $hydrate }
})
```

```ts
// stores/__tests__/preferences.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { usePreferencesStore } from '../preferences'

describe('Preferences Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })
  
  it('hydrates from localStorage', () => {
    const savedState = { theme: 'dark', language: 'es' }
    localStorage.setItem('preferences', JSON.stringify(savedState))
    
    const store = usePreferencesStore()
    store.$hydrate()
    
    expect(store.theme).toBe('dark')
    expect(store.language).toBe('es')
  })
  
  it('persists to localStorage', () => {
    const store = usePreferencesStore()
    store.theme = 'dark'
    store.language = 'es'
    
    const saved = localStorage.getItem('preferences')
    expect(saved).toBeTruthy()
    
    const state = JSON.parse(saved!)
    expect(state.theme).toBe('dark')
    expect(state.language).toBe('es')
  })
})
```

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Reset state**: Reset pinia between tests
3. **Mock external dependencies**: Don't make real API calls
4. **Test async behavior**: Use async/await properly
5. **Test getters**: Verify computed values
6. **Test actions**: Verify state changes
7. **Test error cases**: Cover error scenarios

## Common Mistakes

❌ **Not resetting state between tests**

```ts
describe('Store', () => {
  it('test 1', () => {
    const store = useStore()
    store.count = 5
  })
  
  it('test 2', () => {
    const store = useStore()
    expect(store.count).toBe(0) // ❌ Fails, count is 5
  })
})
```

✅ **Reset state between tests**

```ts
describe('Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  
  it('test 1', () => {
    const store = useStore()
    store.count = 5
  })
  
  it('test 2', () => {
    const store = useStore()
    expect(store.count).toBe(0) // ✅ Passes
  })
})
```

❌ **Not awaiting async actions**

```ts
it('fetches user', () => {
  const store = useStore()
  store.fetchUser() // ❌ Not awaited
  expect(store.user).toBeTruthy() // Fails
})
```

✅ **Await async actions**

```ts
it('fetches user', async () => {
  const store = useStore()
  await store.fetchUser() // ✅ Awaited
  expect(store.user).toBeTruthy()
})
```

❌ **Not mocking API calls**

```ts
it('fetches user', async () => {
  const store = useStore()
  await store.fetchUser() // ❌ Makes real API call
})
```

✅ **Mock API calls**

```ts
it('fetches user', async () => {
  vi.mocked(api.getCurrentUser).mockResolvedValue({ data: mockUser })
  const store = useStore()
  await store.fetchUser() // ✅ Uses mock
})
```
