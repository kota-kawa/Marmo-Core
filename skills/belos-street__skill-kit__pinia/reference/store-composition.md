# Store Composition

Learn how to compose and combine Pinia stores.

## Basic Store Composition

Combine multiple stores:

```ts
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => !!user.value)
  
  return { user, token, isAuthenticated }
})
```

```ts
// stores/cart.ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const total = computed(() => 
    items.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
  )
  
  return { items, total }
})
```

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  
  const canCheckout = computed(() => 
    authStore.isAuthenticated && cartStore.items.length > 0
  )
  
  async function processCheckout(paymentDetails: PaymentDetails) {
    if (!canCheckout.value) {
      throw new Error('Cannot checkout')
    }
    
    const order = await api.createOrder({
      userId: authStore.user!.id,
      items: cartStore.items,
      total: cartStore.total,
      ...paymentDetails
    })
    
    cartStore.items = []
    return order
  }
  
  return { canCheckout, processCheckout }
})
```

## Shared State Pattern

Share state between multiple stores:

```ts
// stores/shared/ui.ts
export const useUIStore = defineStore('ui', () => {
  const isLoading = ref(false)
  const notification = ref<Notification | null>(null)
  
  function setLoading(loading: boolean) {
    isLoading.value = loading
  }
  
  function showNotification(message: string, type: 'success' | 'error' | 'info') {
    notification.value = { message, type }
    setTimeout(() => {
      notification.value = null
    }, 3000)
  }
  
  return { isLoading, notification, setLoading, showNotification }
})
```

```ts
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const uiStore = useUIStore()
  
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  
  async function login(credentials: Credentials) {
    uiStore.setLoading(true)
    try {
      const response = await api.login(credentials)
      user.value = response.user
      token.value = response.token
      uiStore.showNotification('Login successful', 'success')
    } catch (err) {
      uiStore.showNotification('Login failed', 'error')
      throw err
    } finally {
      uiStore.setLoading(false)
    }
  }
  
  return { user, token, login }
})
```

## Store Factory Pattern

Create stores with similar structure:

```ts
// stores/factories/createListStore.ts
export function createListStore<T extends { id: number }>(
  id: string,
  fetchFn: () => Promise<T[]>
) {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    const isLoading = ref(false)
    const error = ref<Error | null>(null)
    
    const isEmpty = computed(() => items.value.length === 0)
    const count = computed(() => items.value.length)
    
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
    
    function clear() {
      items.value = []
    }
    
    return {
      items,
      isLoading,
      error,
      isEmpty,
      count,
      fetch,
      add,
      update,
      remove,
      clear
    }
  })
}
```

```ts
// stores/users.ts
export const useUserStore = createListStore<User>('users', () => api.getUsers())
```

```ts
// stores/comments.ts
export const useCommentStore = createListStore<Comment>('comments', () => api.getComments())
```

## Store Extension Pattern

Extend existing stores:

```ts
// stores/base-cart.ts
export const useBaseCartStore = defineStore('base-cart', () => {
  const items = ref<CartItem[]>([])
  
  const total = computed(() => 
    items.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
  )
  
  function addItem(product: Product) {
    const existing = items.value.find(i => i.id === product.id)
    if (existing) {
      existing.quantity++
    } else {
      items.value.push({ ...product, quantity: 1 })
    }
  }
  
  function removeItem(id: number) {
    const index = items.value.findIndex(i => i.id === id)
    if (index > -1) {
      items.value.splice(index, 1)
    }
  }
  
  function clear() {
    items.value = []
  }
  
  return { items, total, addItem, removeItem, clear }
})
```

```ts
// stores/cart-with-discounts.ts
export const useCartWithDiscountsStore = defineStore('cart-with-discounts', () => {
  const baseCart = useBaseCartStore()
  
  const coupon = ref<string | null>(null)
  
  const discount = computed(() => {
    if (!coupon.value) return 0
    return baseCart.total * 0.1
  })
  
  const totalWithDiscount = computed(() => baseCart.total - discount.value)
  
  function applyCoupon(code: string) {
    coupon.value = code
  }
  
  function removeCoupon() {
    coupon.value = null
  }
  
  return {
    ...baseCart,
    coupon,
    discount,
    totalWithDiscount,
    applyCoupon,
    removeCoupon
  }
})
```

## Store Selector Pattern

Create specialized views of store data:

```ts
// stores/todos.ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  const filter = ref<FilterType>('all')
  
  const filteredTodos = computed(() => {
    if (filter.value === 'active') {
      return todos.value.filter(t => !t.completed)
    }
    if (filter.value === 'completed') {
      return todos.value.filter(t => t.completed)
    }
    return todos.value
  })
  
  const activeCount = computed(() => 
    todos.value.filter(t => !t.completed).length
  )
  
  const completedCount = computed(() => 
    todos.value.filter(t => t.completed).length
  )
  
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
  
  return {
    todos,
    filter,
    filteredTodos,
    activeCount,
    completedCount,
    addTodo,
    toggleTodo,
    removeTodo
  }
})
```

```ts
// stores/selectors/todoSelectors.ts
export function useActiveTodos() {
  const todoStore = useTodoStore()
  
  return computed(() => 
    todoStore.todos.filter(t => !t.completed)
  )
}

export function useCompletedTodos() {
  const todoStore = useTodoStore()
  
  return computed(() => 
    todoStore.todos.filter(t => t.completed)
  )
}

export function useTodoStats() {
  const todoStore = useTodoStore()
  
  return computed(() => ({
    total: todoStore.todos.length,
    active: todoStore.activeCount,
    completed: todoStore.completedCount,
    completionRate: todoStore.todos.length > 0
      ? (todoStore.completedCount / todoStore.todos.length) * 100
      : 0
  }))
}
```

## Store Composition with Composables

Use composables for shared logic:

```ts
// composables/useAsyncAction.ts
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

## Best Practices

1. **Keep stores focused**: Each store should have a single responsibility
2. **Compose, don't duplicate**: Reuse logic through composition
3. **Use factories**: Create reusable store patterns
4. **Share state**: Use shared stores for common data
5. **Extend stores**: Build on existing stores when needed
6. **Create selectors**: Provide specialized views of data

## Common Mistakes

❌ **Creating circular dependencies**

```ts
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const storeB = useStoreB() // ❌ Circular dependency
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const storeA = useStoreA() // ❌ Circular dependency
})
```

✅ **Use shared state**

```ts
// stores/shared/common.ts
export const useCommonStore = defineStore('common', () => {
  const sharedState = ref(null)
  return { sharedState }
})

// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const common = useCommonStore()
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const common = useCommonStore()
})
```

❌ **Over-composing stores**

```ts
export const useCheckoutStore = defineStore('checkout', () => {
  const auth = useAuthStore()
  const cart = useCartStore()
  const payment = usePaymentStore()
  const shipping = useShippingStore()
  const validation = useValidationStore()
  const analytics = useAnalyticsStore()
  // ❌ Too many dependencies
})
```

✅ **Keep composition focused**

```ts
export const useCheckoutStore = defineStore('checkout', () => {
  const auth = useAuthStore()
  const cart = useCartStore()
  
  async function checkout() {
    if (!auth.isAuthenticated) throw new Error('Not authenticated')
    if (cart.items.length === 0) throw new Error('Cart is empty')
    
    return await api.createOrder({
      userId: auth.user.id,
      items: cart.items
    })
  }
  
  return { checkout }
})
```
