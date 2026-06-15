# Getter Cross Store Access

Learn how to access getters from other Pinia stores.

## Basic Cross Store Access

Access getters from other stores within a getter:

```ts
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => !!user.value)
  
  return { user, isAuthenticated }
})
```

```ts
// stores/cart.ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const authStore = useAuthStore()
  
  const canCheckout = computed(() => 
    authStore.isAuthenticated && items.value.length > 0
  )
  
  return { items, canCheckout }
})
```

## Using Other Store's Getters

Combine getters from multiple stores:

```ts
// stores/products.ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const searchQuery = ref('')
  
  const filteredProducts = computed(() => {
    if (!searchQuery.value) return products.value
    
    const query = searchQuery.value.toLowerCase()
    return products.value.filter(p => 
      p.name.toLowerCase().includes(query)
    )
  })
  
  return { products, searchQuery, filteredProducts }
})
```

```ts
// stores/cart.ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const productStore = useProductStore()
  
  const cartProducts = computed(() => {
    return items.value.map(item => {
      const product = productStore.products.find(p => p.id === item.productId)
      return {
        ...item,
        product: product || null
      }
    })
  })
  
  const total = computed(() => {
    return cartProducts.value.reduce((sum, item) => {
      const price = item.product?.price || 0
      return sum + price * item.quantity
    }, 0)
  })
  
  return { items, cartProducts, total }
})
```

## Avoiding Circular Dependencies

Be careful with circular dependencies between stores:

```ts
// ❌ Bad: Circular dependency
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const storeB = useStoreB()
  const value = computed(() => storeB.value * 2)
  return { value }
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const storeA = useStoreA()
  const value = computed(() => storeA.value / 2)
  return { value }
})
```

```ts
// ✅ Good: Use shared store
// stores/shared/common.ts
export const useCommonStore = defineStore('common', () => {
  const baseValue = ref(0)
  return { baseValue }
})

// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const common = useCommonStore()
  const value = computed(() => common.baseValue * 2)
  return { value }
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const common = useCommonStore()
  const value = computed(() => common.baseValue / 2)
  return { value }
})
```

## Lazy Store Access

Access other stores lazily to avoid circular dependencies:

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const isProcessing = ref(false)
  
  const canCheckout = computed(() => {
    const authStore = useAuthStore()
    const cartStore = useCartStore()
    
    return authStore.isAuthenticated && cartStore.items.length > 0
  })
  
  return { isProcessing, canCheckout }
})
```

## Computed Cross Store Values

Create computed values that depend on multiple stores:

```ts
// stores/dashboard.ts
export const useDashboardStore = defineStore('dashboard', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  const orderStore = useOrderStore()
  
  const welcomeMessage = computed(() => {
    if (!authStore.user) return 'Welcome, Guest!'
    return `Welcome, ${authStore.user.name}!`
  })
  
  const cartSummary = computed(() => {
    return {
      itemCount: cartStore.items.length,
      total: cartStore.total
    }
  })
  
  const recentOrders = computed(() => {
    return orderStore.orders.slice(0, 5)
  })
  
  return { welcomeMessage, cartSummary, recentOrders }
})
```

## Watching Cross Store Changes

React to changes in other stores:

```ts
// stores/notifications.ts
export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref<Notification[]>([])
  
  watch(
    () => {
      const authStore = useAuthStore()
      return authStore.user
    },
    (user, oldUser) => {
      if (!oldUser && user) {
        addNotification('Welcome back!', 'success')
      } else if (oldUser && !user) {
        addNotification('You have been logged out', 'info')
      }
    }
  )
  
  function addNotification(message: string, type: NotificationType) {
    notifications.value.push({ message, type, id: Date.now() })
  }
  
  return { notifications, addNotification }
})
```

## Type-Safe Cross Store Access

Use TypeScript for type-safe cross store access:

```ts
// stores/types.ts
export interface AuthStore {
  user: Ref<User | null>
  isAuthenticated: ComputedRef<boolean>
}

export interface CartStore {
  items: Ref<CartItem[]>
  total: ComputedRef<number>
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
  
  return { canCheckout }
})
```

## Cross Store Actions with Getters

Use cross store getters in actions:

```ts
// stores/checkout.ts
export const useCheckoutStore = defineStore('checkout', () => {
  const authStore = useAuthStore()
  const cartStore = useCartStore()
  
  const canCheckout = computed(() => 
    authStore.isAuthenticated && cartStore.items.length > 0
  )
  
  async function processCheckout() {
    if (!canCheckout.value) {
      throw new Error('Cannot checkout')
    }
    
    await api.createOrder({
      userId: authStore.user!.id,
      items: cartStore.items,
      total: cartStore.total
    })
    
    cartStore.clear()
  }
  
  return { canCheckout, processCheckout }
})
```

## Best Practices

1. **Avoid circular dependencies**: Be careful with store composition
2. **Use lazy access**: Access other stores inside computed/watch
3. **Extract shared state**: Use shared stores for common data
4. **Type your stores**: Use TypeScript for better type safety
5. **Keep dependencies minimal**: Only access what you need

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
  const value = computed(() => {
    const storeB = useStoreB() // ✅ Accessed lazily
    return storeB.value
  })
  return { value }
})
```

❌ **Not handling null values**

```ts
const userName = computed(() => {
  const authStore = useAuthStore()
  return authStore.user.name // ❌ Can be null
})
```

✅ **Handle null values**

```ts
const userName = computed(() => {
  const authStore = useAuthStore()
  return authStore.user?.name || 'Guest' // ✅ Safe access
})
```
