# Store Composition Patterns

Learn how to compose and reuse Pinia stores for scalable state management.

## Basic Store Composition

Combine multiple stores to create higher-level stores:

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'
import { useCartStore } from './cart'

export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  
  const isProcessing = ref(false)
  const error = ref<string | null>(null)
  
  const canCheckout = computed(() => 
    authStore.isAuthenticated && cartStore.items.length > 0
  )
  
  const total = computed(() => cartStore.total)
  
  async function processCheckout(paymentDetails: PaymentDetails) {
    if (!canCheckout.value) {
      throw new Error('Cannot checkout')
    }
    
    isProcessing.value = true
    error.value = null
    
    try {
      await api.createOrder({
        userId: authStore.user!.id,
        items: cartStore.items,
        total: total.value,
        ...paymentDetails
      })
      
      cartStore.clear()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Checkout failed'
      throw err
    } finally {
      isProcessing.value = false
    }
  }
  
  return { isProcessing, error, canCheckout, total, processCheckout }
})
```

## Shared State Pattern

Share state between multiple stores:

```ts
// stores/shared/ui.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

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
// stores/modules/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useUIStore } from '../shared/ui'

export const useAuthStore = defineStore('auth', () => {
  const uiStore = useUIStore()
  
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => !!user.value)
  
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
  
  return { user, token, isAuthenticated, login }
})
```

## Extracting Common Logic

Extract common patterns into reusable composables:

```ts
// composables/useAsyncAction.ts
import { ref } from 'vue'
import { useUIStore } from '@/stores/shared/ui'

export function useAsyncAction<T = any>() {
  const uiStore = useUIStore()
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function execute(action: () => Promise<T>): Promise<T | null> {
    isLoading.value = true
    error.value = null
    
    try {
      const result = await action()
      return result
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Unknown error')
      uiStore.showNotification(error.value.message, 'error')
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  return { isLoading, error, execute }
}
```

```ts
// stores/modules/products.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAsyncAction } from '@/composables/useAsyncAction'

export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const { isLoading, error, execute } = useAsyncAction()
  
  async function fetchProducts() {
    await execute(async () => {
      products.value = await api.getProducts()
    })
  }
  
  async function createProduct(product: Omit<Product, 'id'>) {
    const result = await execute(async () => {
      return await api.createProduct(product)
    })
    
    if (result) {
      products.value.push(result)
    }
  }
  
  return { products, isLoading, error, fetchProducts, createProduct }
})
```

## Store Factory Pattern

Create stores with similar structure using a factory function:

```ts
// stores/factories/createListStore.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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
        items.value[index] = { ...items.value[index], ...updates }
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
// stores/modules/users.ts
import { createListStore } from '../factories/createListStore'

export const useUserStore = createListStore('users', () => api.getUsers())
```

```ts
// stores/modules/comments.ts
import { createListStore } from '../factories/createListStore'

export const useCommentStore = createListStore('comments', () => api.getComments())
```

## Store Mixin Pattern

Add common functionality to multiple stores:

```ts
// stores/mixins/withTimestamps.ts
import { ref } from 'vue'

export function withTimestamps<T extends Record<string, any>>(
  store: T
): T & { createdAt: Ref<Date>, updatedAt: Ref<Date> } {
  const createdAt = ref(new Date())
  const updatedAt = ref(new Date())
  
  return {
    ...store,
    createdAt,
    updatedAt,
    touch() {
      updatedAt.value = new Date()
    }
  }
}
```

```ts
// stores/modules/document.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { withTimestamps } from '../mixins/withTimestamps'

const baseStore = defineStore('document', () => {
  const title = ref('')
  const content = ref('')
  
  function setTitle(newTitle: string) {
    title.value = newTitle
  }
  
  function setContent(newContent: string) {
    content.value = newContent
  }
  
  return { title, content, setTitle, setContent }
})

export const useDocumentStore = withTimestamps(baseStore)
```

## Store Extension Pattern

Extend existing stores with additional functionality:

```ts
// stores/modules/base-cart.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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
// stores/modules/cart-with-discounts.ts
import { defineStore } from 'pinia'
import { computed } from 'vue'
import { useBaseCartStore } from './base-cart'

export const useCartWithDiscountsStore = defineStore('cart-with-discounts', () => {
  const baseCart = useBaseCartStore()
  
  const coupon = ref<string | null>(null)
  const discount = computed(() => {
    if (!coupon.value) return 0
    return baseCart.total * 0.1 // 10% discount
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
// stores/modules/todos.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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
import { useTodoStore } from '../modules/todos'

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

## Best Practices

1. **Keep stores focused**: Each store should have a single responsibility
2. **Compose, don't duplicate**: Reuse logic through composition
3. **Extract common patterns**: Use composables for shared functionality
4. **Avoid circular dependencies**: Be careful with store composition
5. **Type everything**: Use TypeScript for better type safety
6. **Test composition**: Test how stores work together

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

✅ **Use shared state or composables**

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
// Bad: Too many layers
export const useCheckoutStore = defineStore('checkout', () => {
  const auth = useAuthStore()
  const cart = useCartStore()
  const payment = usePaymentStore()
  const shipping = useShippingStore()
  const validation = useValidationStore()
  const analytics = useAnalyticsStore()
  // ... complex logic mixing all stores
})
```

✅ **Keep composition focused**

```ts
// Good: Clear separation of concerns
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
