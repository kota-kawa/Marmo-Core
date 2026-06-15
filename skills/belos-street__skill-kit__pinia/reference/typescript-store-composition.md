# TypeScript Store Composition

Learn how to compose Pinia stores with TypeScript.

## Basic Store Composition

Compose stores with proper typing:

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
  
  async function processCheckout(paymentDetails: PaymentDetails): Promise<Order> {
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

## Typed Store Composition

Define types for composed stores:

```ts
// stores/types.ts
export interface AuthStore {
  user: Ref<User | null>
  token: Ref<string | null>
  isAuthenticated: ComputedRef<boolean>
}

export interface CartStore {
  items: Ref<CartItem[]>
  total: ComputedRef<number>
}

export interface CheckoutStore {
  canCheckout: ComputedRef<boolean>
  processCheckout: (paymentDetails: PaymentDetails) => Promise<Order>
}
```

```ts
// stores/checkout.ts
import type { AuthStore, CartStore } from './types'

export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore() as AuthStore
  const cartStore = useCartStore() as CartStore
  
  const canCheckout = computed(() => 
    authStore.isAuthenticated.value && cartStore.items.value.length > 0
  )
  
  async function processCheckout(paymentDetails: PaymentDetails): Promise<Order> {
    if (!canCheckout.value) {
      throw new Error('Cannot checkout')
    }
    
    const order = await api.createOrder({
      userId: authStore.user.value!.id,
      items: cartStore.items.value,
      total: cartStore.total.value,
      ...paymentDetails
    })
    
    cartStore.items.value = []
    return order
  }
  
  return { canCheckout, processCheckout }
})
```

## Generic Store Composition

Compose generic stores:

```ts
// stores/factory.ts
export function createListStore<T extends { id: number }>(
  id: string
) {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    
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
    
    return { items, add, update, remove }
  })
}
```

```ts
// stores/products.ts
export const useProductStore = createListStore<Product>('products')
```

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const productStore = useProductStore()
  const cartStore = useCartStore()
  
  const availableProducts = computed(() => 
    productStore.items.filter(p => p.inStock)
  )
  
  function addToCart(productId: number) {
    const product = productStore.items.find(p => p.id === productId)
    if (!product) return
    
    const existing = cartStore.items.find(i => i.productId === productId)
    if (existing) {
      existing.quantity++
    } else {
      cartStore.items.push({
        productId,
        product,
        quantity: 1
      })
    }
  }
  
  return { availableProducts, addToCart }
})
```

## Store Composition with Type Inference

Use type inference for composed stores:

```ts
// stores/composed.ts
export const useComposedStore = defineStore('composed', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  const productStore = useProductStore()
  
  const state = computed(() => ({
    isAuthenticated: authStore.isAuthenticated.value,
    cartTotal: cartStore.total.value,
    productCount: productStore.items.length
  }))
  
  return { state }
})
```

## Store Composition with Shared Types

Define shared types for composition:

```ts
// stores/types.ts
export interface StoreState {
  isLoading: boolean
  error: Error | null
}

export interface ListStore<T> extends StoreState {
  items: Ref<T[]>
  fetch: () => Promise<void>
  add: (item: T) => void
  update: (id: number, updates: Partial<T>) => void
  remove: (id: number) => void
}
```

```ts
// stores/products.ts
export const useProductStore = defineStore('products', () => {
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  const items = ref<Product[]>([])
  
  async function fetch() {
    isLoading.value = true
    error.value = null
    
    try {
      items.value = await api.getProducts()
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to fetch')
    } finally {
      isLoading.value = false
    }
  }
  
  function add(item: Product) {
    items.value.push(item)
  }
  
  function update(id: number, updates: Partial<Product>) {
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
    isLoading,
    error,
    items,
    fetch,
    add,
    update,
    remove
  } as ListStore<Product>
})
```

## Store Composition with Mixins

Create typed mixins for store composition:

```ts
// stores/mixins/asyncActions.ts
export interface AsyncActions<T> {
  isLoading: Ref<boolean>
  error: Ref<Error | null>
  execute: (action: () => Promise<T>) => Promise<T | null>
}

export function withAsyncActions<T>(): AsyncActions<T> {
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function execute(action: () => Promise<T>): Promise<T | null> {
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
  const { isLoading, error, execute } = withAsyncActions<User>()
  
  async function fetchUser() {
    await execute(async () => {
      const response = await api.getCurrentUser()
      user.value = response.data
    })
  }
  
  return { user, isLoading, error, fetchUser }
})
```

## Store Composition with Type Guards

Use type guards for store composition:

```ts
// stores/types.ts
export function isAuthStore(store: any): store is AuthStore {
  return store && typeof store.isAuthenticated !== 'undefined'
}

export function isCartStore(store: any): store is CartStore {
  return store && typeof store.total !== 'undefined'
}
```

```ts
// stores/composed.ts
export const useComposedStore = defineStore('composed', () => {
  const stores = [
    useAuthStore(),
    useCartStore(),
    useProductStore()
  ]
  
  const authStore = stores.find(isAuthStore)
  const cartStore = stores.find(isCartStore)
  
  const canCheckout = computed(() => 
    authStore?.isAuthenticated.value && 
    (cartStore?.items.value.length || 0) > 0
  )
  
  return { canCheckout }
})
```

## Best Practices

1. **Define interfaces**: Create interfaces for store types
2. **Use type assertions**: Cast stores to proper types
3. **Leverage inference**: Let TypeScript infer when possible
4. **Create shared types**: Define common types for composition
5. **Use type guards**: Validate store types at runtime
6. **Document composition**: Document how stores are composed

## Common Mistakes

❌ **Not typing composed stores**

```ts
const authStore = useAuthStore()
const cartStore = useCartStore()

const canCheckout = computed(() => 
  authStore.isAuthenticated && // ❌ No type safety
  cartStore.items.length > 0
)
```

✅ **Type composed stores**

```ts
const authStore = useAuthStore() as AuthStore
const cartStore = useCartStore() as CartStore

const canCheckout = computed(() => 
  authStore.isAuthenticated.value && // ✅ Type safe
  cartStore.items.value.length > 0
)
```

❌ **Not defining interfaces**

```ts
export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  // ❌ No type definitions
})
```

✅ **Define interfaces**

```ts
interface AuthStore {
  isAuthenticated: ComputedRef<boolean>
  user: Ref<User | null>
}

export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore() as AuthStore
  const cartStore = useCartStore() as CartStore
  // ✅ Type safe
})
```

❌ **Not using type guards**

```ts
function getAuthStore() {
  return useAuthStore() // ❌ No validation
}
```

✅ **Use type guards**

```ts
function isAuthStore(store: any): store is AuthStore {
  return store && typeof store.isAuthenticated !== 'undefined'
}

function getAuthStore(): AuthStore | null {
  const store = useAuthStore()
  return isAuthStore(store) ? store : null
}
```

❌ **Not documenting composition**

```ts
export const useCheckoutStore = defineStore('checkout', () => {
  // ❌ No documentation
})
```

✅ **Document composition**

```ts
/**
 * Checkout store that composes auth and cart stores
 * @requires AuthStore - User authentication
 * @requires CartStore - Shopping cart
 */
export const useCheckoutStore = defineStore('checkout', () => {
  // ✅ Documented
})
```
