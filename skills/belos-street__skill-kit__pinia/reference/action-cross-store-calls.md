# Action Cross Store Calls

Learn how to call actions from other Pinia stores.

## Basic Cross Store Actions

Call actions from other stores:

```ts
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
    token.value = response.token
  }
  
  function logout() {
    user.value = null
    token.value = null
  }
  
  return { user, token, login, logout }
})
```

```ts
// stores/cart.ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const authStore = useAuthStore()
  
  async function checkout() {
    if (!authStore.user) {
      throw new Error('User not authenticated')
    }
    
    await api.createOrder({
      userId: authStore.user.id,
      items: items.value
    })
    
    items.value = []
  }
  
  return { items, checkout }
})
```

## Chaining Actions

Chain actions across multiple stores:

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  const orderStore = useOrderStore()
  
  async function processCheckout(paymentDetails: PaymentDetails) {
    if (!authStore.isAuthenticated) {
      throw new Error('User not authenticated')
    }
    
    if (cartStore.items.length === 0) {
      throw new Error('Cart is empty')
    }
    
    const order = await orderStore.createOrder({
      userId: authStore.user!.id,
      items: cartStore.items,
      ...paymentDetails
    })
    
    cartStore.clear()
    
    return order
  }
  
  return { processCheckout }
})
```

## Shared Actions

Extract shared actions to composables:

```ts
// composables/useAsyncAction.ts
import { ref } from 'vue'

export function useAsyncAction() {
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function execute<T>(action: () => Promise<T>): Promise<T | null> {
    isLoading.value = true
    error.value = null
    
    try {
      return await action()
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Action failed')
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  return { isLoading, error, execute }
}
```

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const { isLoading, error, execute } = useAsyncAction()
  
  async function fetchUser() {
    await execute(async () => {
      const response = await api.getCurrentUser()
      user.value = response.data
    })
  }
  
  return { user, isLoading, error, fetchUser }
})
```

## Event-Based Communication

Use events for store communication:

```ts
// stores/eventBus.ts
import { ref } from 'vue'

type EventHandler = (data: any) => void

export const useEventBus = defineStore('eventBus', () => {
  const listeners = ref<Map<string, Set<EventHandler>>>(new Map())
  
  function on(event: string, handler: EventHandler) {
    if (!listeners.value.has(event)) {
      listeners.value.set(event, new Set())
    }
    listeners.value.get(event)!.add(handler)
  }
  
  function off(event: string, handler: EventHandler) {
    const handlers = listeners.value.get(event)
    if (handlers) {
      handlers.delete(handler)
    }
  }
  
  function emit(event: string, data: any) {
    const handlers = listeners.value.get(event)
    if (handlers) {
      handlers.forEach(handler => handler(data))
    }
  }
  
  return { on, off, emit }
})
```

```ts
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const eventBus = useEventBus()
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
    token.value = response.token
    
    eventBus.emit('user:login', response.user)
  }
  
  function logout() {
    const user = this.user
    this.user = null
    this.token = null
    
    eventBus.emit('user:logout', user)
  }
  
  return { login, logout }
})
```

```ts
// stores/cart.ts
export const useCartStore = defineStore('cart', () => {
  const eventBus = useEventBus()
  
  function init() {
    eventBus.on('user:logout', () => {
      this.clear()
    })
  }
  
  function clear() {
    this.items = []
  }
  
  return { init, clear }
})
```

## Dependency Injection

Inject dependencies into actions:

```ts
// stores/factory.ts
export function createStoreWithDeps<T>(
  id: string,
  setup: (deps: T) => SetupStore
) {
  return defineStore(id, () => {
    const deps = inject<T>('store-deps')
    return setup(deps)
  })
}
```

## Lazy Store Access

Access other stores lazily to avoid circular dependencies:

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const isProcessing = ref(false)
  
  async function processCheckout() {
    const authStore = useAuthStore()
    const cartStore = useCartStore()
    
    if (!authStore.isAuthenticated) {
      throw new Error('User not authenticated')
    }
    
    if (cartStore.items.length === 0) {
      throw new Error('Cart is empty')
    }
    
    isProcessing.value = true
    
    try {
      const order = await api.createOrder({
        userId: authStore.user!.id,
        items: cartStore.items
      })
      
      cartStore.clear()
      return order
    } finally {
      isProcessing.value = false
    }
  }
  
  return { isProcessing, processCheckout }
})
```

## Action Composition

Compose actions from multiple stores:

```ts
// stores/dashboard.ts
export const useDashboardStore = defineStore('dashboard', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  const orderStore = useOrderStore()
  
  async function loadDashboard() {
    await Promise.all([
      authStore.fetchUser(),
      cartStore.fetchCart(),
      orderStore.fetchOrders()
    ])
  }
  
  return { loadDashboard }
})
```

## Error Handling Across Stores

Handle errors from cross-store actions:

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  const error = ref<Error | null>(null)
  
  async function processCheckout() {
    error.value = null
    
    try {
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
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Checkout failed')
      throw error.value
    }
  }
  
  return { error, processCheckout }
})
```

## Best Practices

1. **Avoid circular dependencies**: Be careful with store composition
2. **Use lazy access**: Access other stores inside actions
3. **Extract shared logic**: Use composables for common actions
4. **Handle errors properly**: Propagate errors from cross-store calls
5. **Use events for loose coupling**: Event-based communication
6. **Keep actions focused**: Each action should do one thing well

## Common Mistakes

❌ **Circular dependencies**

```ts
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const storeB = useStoreB() // ❌ Circular
  return { value: computed(() => storeB.value * 2) }
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const storeA = useStoreA() // ❌ Circular
  return { value: computed(() => storeA.value / 2) }
})
```

✅ **Use shared store**

```ts
// stores/shared.ts
export const useSharedStore = defineStore('shared', () => {
  const value = ref(0)
  return { value }
})

// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const shared = useSharedStore()
  return { value: computed(() => shared.value * 2) }
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const shared = useSharedStore()
  return { value: computed(() => shared.value / 2) }
})
```

❌ **Not handling errors from other stores**

```ts
async function processCheckout() {
  await authStore.login() // ❌ No error handling
  await cartStore.clear()
}
```

✅ **Handle errors properly**

```ts
async function processCheckout() {
  try {
    await authStore.login()
    await cartStore.clear()
  } catch (err) {
    this.error = err
    throw err
  }
}
```

❌ **Accessing stores at top level**

```ts
export const useStoreA = defineStore('a', () => {
  const storeB = useStoreB() // ❌ Accessed at top level
  return {}
})
```

✅ **Access lazily**

```ts
export const useStoreA = defineStore('a', () => {
  async function doSomething() {
    const storeB = useStoreB() // ✅ Accessed lazily
    await storeB.doSomething()
  }
  return { doSomething }
})
```
