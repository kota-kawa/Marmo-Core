# Store Organization

Organize your Pinia stores in a way that scales well with your application.

## Recommended Directory Structure

```
src/
├── stores/
│   ├── index.ts          # Export all stores
│   ├── modules/          # Feature-based stores
│   │   ├── auth.ts
│   │   ├── cart.ts
│   │   └── products.ts
│   ├── shared/           # Shared/common stores
│   │   ├── ui.ts
│   │   └── preferences.ts
│   └── types.ts          # Shared types
```

## Feature-Based Organization

Organize stores by feature or domain:

```ts
// stores/modules/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => !!user.value)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
    token.value = response.token
  }
  
  function logout() {
    user.value = null
    token.value = null
  }
  
  return { user, token, isAuthenticated, login, logout }
})
```

```ts
// stores/modules/cart.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCartStore = defineStore('cart', () => {
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

## Centralized Export

Create an index file to export all stores:

```ts
// stores/index.ts
export { useAuthStore } from './modules/auth'
export { useCartStore } from './modules/cart'
export { useProductStore } from './modules/products'
export { useUIStore } from './shared/ui'
export { usePreferencesStore } from './shared/preferences'

export * from './types'
```

Now you can import stores from a single location:

```ts
import { useAuthStore, useCartStore } from '@/stores'
```

## Shared Types

Define shared types in a separate file:

```ts
// stores/types.ts
export interface User {
  id: number
  name: string
  email: string
  avatar?: string
}

export interface Credentials {
  email: string
  password: string
}

export interface Product {
  id: number
  name: string
  price: number
  image: string
}

export interface CartItem extends Product {
  quantity: number
}

export interface ApiResponse<T> {
  data: T
  message: string
}
```

## Store Composition Pattern

For complex features, compose multiple stores:

```ts
// stores/modules/checkout.ts
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
  
  return { isProcessing, error, canCheckout, processCheckout }
})
```

## Naming Conventions

### Store Files

- Use lowercase with hyphens: `auth-store.ts`, `user-preferences.ts`
- Or camelCase: `authStore.ts`, `userPreferences.ts`
- Be consistent across your project

### Store Functions

- Use `use` prefix: `useAuthStore`, `useCartStore`
- Use descriptive names: `useUserPreferencesStore`, not `useStore`

### Store IDs

- Use lowercase with hyphens: `'auth'`, `'user-preferences'`
- Keep them short but descriptive

```ts
// Good
export const useAuthStore = defineStore('auth', () => {})
export const useUserPreferencesStore = defineStore('user-preferences', () => {})

// Avoid
export const useStore = defineStore('store', () => {})
export const useAStore = defineStore('a', () => {})
```

## Auto-Import Configuration

Configure auto-imports for stores (with unplugin-auto-import):

```ts
// vite.config.ts
import AutoImport from 'unplugin-auto-import/vite'

export default defineConfig({
  plugins: [
    AutoImport({
      imports: [
        'vue',
        'vue-router',
        {
          'pinia': ['defineStore', 'storeToRefs']
        }
      ],
      dts: 'src/auto-imports.d.ts',
      dirs: [
        './src/stores'
      ],
      vueTemplate: true
    })
  ]
})
```

Now you can use stores without importing:

```vue
<script setup lang="ts">
const authStore = useAuthStore()
const cartStore = useCartStore()
</script>
```

## Store Initialization

Initialize stores in your main entry point:

```ts
// main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.mount('#app')
```

## Testing Store Organization

Test stores in isolation:

```ts
// stores/__tests__/auth.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../modules/auth'

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  
  it('initializes with no user', () => {
    const store = useAuthStore()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })
  
  it('logs in user', async () => {
    const store = useAuthStore()
    await store.login({ email: 'test@example.com', password: 'password' })
    expect(store.user).toBeTruthy()
    expect(store.isAuthenticated).toBe(true)
  })
  
  it('logs out user', () => {
    const store = useAuthStore()
    store.logout()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })
})
```

## Best Practices

1. **One store per domain**: Don't create a single giant store
2. **Keep stores focused**: Each store should have a single responsibility
3. **Use composition**: Combine stores when needed, don't duplicate logic
4. **Export from index**: Centralize exports for easier imports
5. **Type everything**: Use TypeScript interfaces for all store types
6. **Test in isolation**: Each store should be testable independently
7. **Document complex logic**: Add comments for non-obvious code

## Anti-Patterns

❌ **Don't create a single store for everything**

```ts
// Bad
export const useAppStore = defineStore('app', () => {
  const user = ref(null)
  const cart = ref([])
  const products = ref([])
  const ui = ref({ theme: 'light' })
  // ... hundreds of lines
})
```

✅ **Split into focused stores**

```ts
// Good
export const useAuthStore = defineStore('auth', () => {})
export const useCartStore = defineStore('cart', () => {})
export const useProductStore = defineStore('products', () => {})
export const useUIStore = defineStore('ui', () => {})
```

❌ **Don't duplicate logic across stores**

```ts
// Bad
export const useStoreA = defineStore('a', () => {
  function formatDate(date: Date) {
    return date.toLocaleDateString()
  }
})

export const useStoreB = defineStore('b', () => {
  function formatDate(date: Date) {
    return date.toLocaleDateString()
  }
})
```

✅ **Extract shared logic to composables**

```ts
// utils/date.ts
export function useDateFormat() {
  function formatDate(date: Date) {
    return date.toLocaleDateString()
  }
  return { formatDate }
}

// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const { formatDate } = useDateFormat()
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const { formatDate } = useDateFormat()
})
```
