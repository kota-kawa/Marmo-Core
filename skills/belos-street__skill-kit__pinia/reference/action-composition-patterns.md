# Action Composition Patterns

Learn how to compose and reuse Pinia actions.

## Basic Action Composition

Combine multiple actions into a single action:

```ts
export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  const orderStore = useOrderStore()
  
  async function processCheckout(paymentDetails: PaymentDetails) {
    await validateCheckout()
    const order = await createOrder(paymentDetails)
    await clearCart()
    return order
  }
  
  async function validateCheckout() {
    if (!authStore.isAuthenticated) {
      throw new Error('User not authenticated')
    }
    
    if (cartStore.items.length === 0) {
      throw new Error('Cart is empty')
    }
  }
  
  async function createOrder(paymentDetails: PaymentDetails) {
    return await orderStore.createOrder({
      userId: authStore.user!.id,
      items: cartStore.items,
      ...paymentDetails
    })
  }
  
  async function clearCart() {
    cartStore.clear()
  }
  
  return { processCheckout }
})
```

## Extracting Common Actions

Extract common actions to composables:

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

## Action Factories

Create actions with factory functions:

```ts
// factories/createCRUDActions.ts
export function createCRUDActions<T extends { id: number }>(
  items: Ref<T[]>,
  api: {
    getAll: () => Promise<T[]>
    create: (data: Omit<T, 'id'>) => Promise<T>
    update: (id: number, data: Partial<T>) => Promise<T>
    delete: (id: number) => Promise<void>
  }
) {
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
    isLoading,
    error,
    fetchAll,
    create,
    update,
    remove
  }
}
```

```ts
// stores/products.ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const {
    isLoading,
    error,
    fetchAll,
    create,
    update,
    remove
  } = createCRUDActions(products, {
    getAll: api.getProducts,
    create: api.createProduct,
    update: api.updateProduct,
    delete: api.deleteProduct
  })
  
  return {
    products,
    isLoading,
    error,
    fetchAll,
    create,
    update,
    remove
  }
})
```

## Middleware Pattern

Add middleware to actions:

```ts
// middleware/withLogging.ts
export function withLogging<T extends (...args: any[]) => Promise<any>>(
  action: T,
  name: string
): T {
  return (async (...args: Parameters<T>) => {
    console.log(`[Action] ${name} started`, args)
    
    try {
      const result = await action(...args)
      console.log(`[Action] ${name} succeeded`, result)
      return result
    } catch (err) {
      console.error(`[Action] ${name} failed`, err)
      throw err
    }
  }) as T
}
```

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  async function fetchUser() {
    const response = await api.getCurrentUser()
    user.value = response.data
  }
  
  return {
    user,
    fetchUser: withLogging(fetchUser, 'fetchUser')
  }
})
```

## Action Pipeline

Create a pipeline of actions:

```ts
// pipelines/createActionPipeline.ts
export function createActionPipeline<T>(
  ...steps: Array<(data: T) => Promise<T>>
) {
  return async (initialData: T): Promise<T> => {
    let data = initialData
    
    for (const step of steps) {
      data = await step(data)
    }
    
    return data
  }
}
```

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const validateStep = async (data: CheckoutData) => {
    if (!data.userId) throw new Error('User required')
    if (!data.items.length) throw new Error('Items required')
    return data
  }
  
  const calculateTotalsStep = async (data: CheckoutData) => {
    const subtotal = data.items.reduce((sum, item) => sum + item.price, 0)
    const tax = subtotal * 0.08
    const total = subtotal + tax
    
    return { ...data, subtotal, tax, total }
  }
  
  const createOrderStep = async (data: CheckoutData) => {
    const order = await api.createOrder(data)
    return { ...data, orderId: order.id }
  }
  
  const processCheckout = createActionPipeline(
    validateStep,
    calculateTotalsStep,
    createOrderStep
  )
  
  return { processCheckout }
})
```

## Action Decorators

Add functionality to actions with decorators:

```ts
// decorators/withRetry.ts
export function withRetry<T extends (...args: any[]) => Promise<any>>(
  action: T,
  maxRetries = 3
): T {
  return (async (...args: Parameters<T>) => {
    let lastError: Error | null = null
    
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await action(...args)
      } catch (err) {
        lastError = err instanceof Error ? err : new Error('Action failed')
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
      }
    }
    
    throw lastError
  }) as T
}
```

```ts
// decorators/withLoading.ts
export function withLoading<T extends (...args: any[]) => Promise<any>>(
  action: T,
  isLoading: Ref<boolean>
): T {
  return (async (...args: Parameters<T>) => {
    isLoading.value = true
    try {
      return await action(...args)
    } finally {
      isLoading.value = false
    }
  }) as T
}
```

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  
  async function fetchUser() {
    const response = await api.getCurrentUser()
    user.value = response.data
  }
  
  return {
    user,
    isLoading,
    fetchUser: withRetry(withLoading(fetchUser, isLoading))
  }
})
```

## Action Composition with Composables

Use composables for reusable action logic:

```ts
// composables/usePagination.ts
export function usePagination<T>(fetchFn: (page: number) => Promise<T[]>) {
  const items = ref<T[]>([])
  const currentPage = ref(1)
  const isLoading = ref(false)
  const hasMore = ref(true)
  
  async function fetchPage(page: number) {
    isLoading.value = true
    
    try {
      const newItems = await fetchFn(page)
      
      if (page === 1) {
        items.value = newItems
      } else {
        items.value.push(...newItems)
      }
      
      hasMore.value = newItems.length > 0
      currentPage.value = page
    } finally {
      isLoading.value = false
    }
  }
  
  async function loadMore() {
    if (!isLoading.value && hasMore.value) {
      await fetchPage(currentPage.value + 1)
    }
  }
  
  async function refresh() {
    await fetchPage(1)
  }
  
  return {
    items,
    currentPage,
    isLoading,
    hasMore,
    loadMore,
    refresh
  }
}
```

```ts
// stores/products.ts
export const useProductStore = defineStore('products', () => {
  const {
    items: products,
    isLoading,
    hasMore,
    loadMore,
    refresh
  } = usePagination((page) => api.getProducts(page))
  
  return {
    products,
    isLoading,
    hasMore,
    loadMore,
    refresh
  }
})
```

## Best Practices

1. **Extract common logic**: Use composables for shared actions
2. **Use factories**: Create reusable action patterns
3. **Add middleware**: Enhance actions with logging, retry, etc.
4. **Compose actions**: Build complex actions from simple ones
5. **Keep actions focused**: Each action should do one thing well
6. **Handle errors properly**: Propagate errors through composed actions

## Common Mistakes

❌ **Duplicating logic across stores**

```ts
// stores/a.ts
async function fetchData() {
  this.isLoading = true
  try {
    this.data = await api.getData()
  } finally {
    this.isLoading = false
  }
}

// stores/b.ts
async function fetchData() {
  this.isLoading = true // ❌ Duplicated
  try {
    this.data = await api.getData()
  } finally {
    this.isLoading = false
  }
}
```

✅ **Extract to composable**

```ts
// composables/useAsyncAction.ts
export function useAsyncAction() {
  const isLoading = ref(false)
  
  async function execute<T>(action: () => Promise<T>) {
    isLoading.value = true
    try {
      return await action()
    } finally {
      isLoading.value = false
    }
  }
  
  return { isLoading, execute }
}

// stores/a.ts
const { isLoading, execute } = useAsyncAction()
async function fetchData() {
  await execute(() => api.getData())
}

// stores/b.ts
const { isLoading, execute } = useAsyncAction()
async function fetchData() {
  await execute(() => api.getData())
}
```

❌ **Complex actions without composition**

```ts
async function processCheckout() {
  // ❌ Too much logic in one action
  if (!this.user) throw new Error('No user')
  if (!this.cart.length) throw new Error('Empty cart')
  const totals = this.calculateTotals()
  const order = await api.createOrder({ ...totals })
  await api.sendEmail(order.id)
  this.cart = []
  analytics.track('checkout', order)
}
```

✅ **Compose smaller actions**

```ts
async function validateCheckout() {
  if (!this.user) throw new Error('No user')
  if (!this.cart.length) throw new Error('Empty cart')
}

async function calculateTotals() {
  return { subtotal: 100, tax: 8, total: 108 }
}

async function createOrder(totals: any) {
  return await api.createOrder(totals)
}

async function sendConfirmation(order: Order) {
  await api.sendEmail(order.id)
}

async function clearCart() {
  this.cart = []
}

async function trackCheckout(order: Order) {
  analytics.track('checkout', order)
}

async function processCheckout() {
  await this.validateCheckout()
  const totals = await this.calculateTotals()
  const order = await this.createOrder(totals)
  await this.sendConfirmation(order)
  await this.clearCart()
  await this.trackCheckout(order)
}
```
