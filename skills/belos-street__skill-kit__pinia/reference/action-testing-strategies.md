# Action Testing Strategies

Learn how to test Pinia actions effectively.

## Basic Action Testing

Test simple actions:

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
  
  it('increments count', () => {
    const store = useCounterStore()
    
    expect(store.count).toBe(0)
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

## Testing Async Actions

Test async actions with mocked API:

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

## Testing Cross-Store Actions

Test actions that call other stores:

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
    expect(api.createOrder).toHaveBeenCalledWith({
      userId: 1,
      items: cartStore.items
    })
  })
  
  it('throws error when not authenticated', async () => {
    const authStore = useAuthStore()
    const checkoutStore = useCheckoutStore()
    
    authStore.user = null
    
    await expect(checkoutStore.processCheckout()).rejects.toThrow('User not authenticated')
  })
  
  it('throws error when cart is empty', async () => {
    const authStore = useAuthStore()
    const cartStore = useCartStore()
    const checkoutStore = useCheckoutStore()
    
    authStore.user = { id: 1, name: 'John' }
    cartStore.items = []
    
    await expect(checkoutStore.processCheckout()).rejects.toThrow('Cart is empty')
  })
})
```

## Testing Actions with Side Effects

Test actions that have side effects:

```ts
// stores/notification.ts
export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([])
  
  function addNotification(message: string, type: NotificationType) {
    const notification = {
      id: Date.now(),
      message,
      type
    }
    
    notifications.value.push(notification)
    
    setTimeout(() => {
      removeNotification(notification.id)
    }, 3000)
  }
  
  function removeNotification(id: number) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }
  
  return { notifications, addNotification, removeNotification }
})
```

```ts
// stores/__tests__/notification.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationStore } from '../notification'
import { vi } from 'vitest'

describe('Notification Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })
  
  afterEach(() => {
    vi.useRealTimers()
  })
  
  it('adds notification', () => {
    const store = useNotificationStore()
    
    store.addNotification('Test message', 'success')
    
    expect(store.notifications).toHaveLength(1)
    expect(store.notifications[0]).toMatchObject({
      message: 'Test message',
      type: 'success'
    })
  })
  
  it('removes notification after timeout', () => {
    const store = useNotificationStore()
    
    store.addNotification('Test message', 'success')
    expect(store.notifications).toHaveLength(1)
    
    vi.advanceTimersByTime(3000)
    
    expect(store.notifications).toHaveLength(0)
  })
})
```

## Testing Actions with Mocked Dependencies

Mock external dependencies:

```ts
// stores/analytics.ts
export const useAnalyticsStore = defineStore('analytics', () => {
  function trackEvent(event: string, data: any) {
    analytics.track(event, data)
  }
  
  return { trackEvent }
})
```

```ts
// stores/__tests__/analytics.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useAnalyticsStore } from '../analytics'
import * as analytics from '@/analytics'

vi.mock('@/analytics')

describe('Analytics Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })
  
  it('tracks event', () => {
    const store = useAnalyticsStore()
    
    store.trackEvent('button_click', { button: 'submit' })
    
    expect(analytics.track).toHaveBeenCalledWith('button_click', { button: 'submit' })
  })
})
```

## Testing Optimistic Updates

Test actions with optimistic updates:

```ts
// stores/todo.ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  async function toggleTodo(id: number) {
    const todo = todos.value.find(t => t.id === id)
    if (!todo) return
    
    const originalCompleted = todo.completed
    todo.completed = !todo.completed
    
    try {
      await api.updateTodo(id, { completed: todo.completed })
    } catch (err) {
      todo.completed = originalCompleted
      throw err
    }
  }
  
  return { todos, toggleTodo }
})
```

```ts
// stores/__tests__/todo.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useTodoStore } from '../todo'
import * as api from '@/api'

vi.mock('@/api')

describe('Todo Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })
  
  it('toggles todo optimistically', async () => {
    const store = useTodoStore()
    store.todos = [{ id: 1, text: 'Test', completed: false }]
    
    vi.mocked(api.updateTodo).mockResolvedValue({ id: 1, completed: true })
    
    await store.toggleTodo(1)
    
    expect(store.todos[0].completed).toBe(true)
    expect(api.updateTodo).toHaveBeenCalledWith(1, { completed: true })
  })
  
  it('rolls back on error', async () => {
    const store = useTodoStore()
    store.todos = [{ id: 1, text: 'Test', completed: false }]
    
    vi.mocked(api.updateTodo).mockRejectedValue(new Error('Network error'))
    
    await expect(store.toggleTodo(1)).rejects.toThrow('Network error')
    
    expect(store.todos[0].completed).toBe(false)
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

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Mock external dependencies**: Don't make real API calls
3. **Test success and error cases**: Cover all scenarios
4. **Test async behavior**: Use async/await properly
5. **Clean up after tests**: Reset state between tests
6. **Use test utilities**: Reduce test code duplication

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
