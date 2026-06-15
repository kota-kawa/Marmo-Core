# TypeScript Auto Import Types

Learn how to type auto-imported Pinia stores.

## Auto-Import Configuration

Configure auto-imports for Pinia stores:

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

## Type Declaration File

Create a type declaration file for auto-imported stores:

```ts
// src/auto-imports.d.ts
export {}
declare global {
  const useAuthStore: typeof import('./stores/auth').useAuthStore
  const useCartStore: typeof import('./stores/cart').useCartStore
  const useProductStore: typeof import('./stores/product').useProductStore
}
```

## Using Auto-Imported Stores

Use auto-imported stores with proper typing:

```vue
<script setup lang="ts">
const authStore = useAuthStore()
const cartStore = useCartStore()

const { user, isAuthenticated } = storeToRefs(authStore)
const { items, total } = storeToRefs(cartStore)
</script>

<template>
  <div>
    <p v-if="isAuthenticated">Welcome, {{ user?.name }}</p>
    <p>Cart: {{ items.length }} items ({{ total }})</p>
  </div>
</template>
```

## Typing Auto-Imported Stores

Define types for auto-imported stores:

```ts
// src/stores/types.ts
export interface AuthStore {
  user: Ref<User | null>
  token: Ref<string | null>
  isAuthenticated: ComputedRef<boolean>
  login: (credentials: Credentials) => Promise<void>
  logout: () => void
}

export interface CartStore {
  items: Ref<CartItem[]>
  total: ComputedRef<number>
  addItem: (product: Product) => void
  removeItem: (id: number) => void
  clear: () => void
}
```

```ts
// src/auto-imports.d.ts
import type { AuthStore, CartStore } from './stores/types'

export {}
declare global {
  const useAuthStore: () => AuthStore
  const useCartStore: () => CartStore
}
```

## Type-Safe Auto-Imports

Use type-safe auto-imports:

```ts
// src/stores/auth.ts
export interface AuthStoreState {
  user: User | null
  token: string | null
}

export interface AuthStoreGetters {
  isAuthenticated: ComputedRef<boolean>
  userName: ComputedRef<string>
}

export interface AuthStoreActions {
  login: (credentials: Credentials) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export type AuthStore = AuthStoreState & AuthStoreGetters & AuthStoreActions

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => !!user.value)
  const userName = computed(() => user.value?.name || 'Guest')
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
    token.value = response.token
  }
  
  function logout() {
    user.value = null
    token.value = null
  }
  
  async function fetchUser() {
    const response = await api.getCurrentUser()
    user.value = response.user
  }
  
  return {
    user,
    token,
    isAuthenticated,
    userName,
    login,
    logout,
    fetchUser
  }
})
```

```ts
// src/auto-imports.d.ts
import type { AuthStore } from './stores/auth'

export {}
declare global {
  const useAuthStore: () => AuthStore
}
```

## Generic Store Auto-Imports

Auto-import generic stores:

```ts
// src/stores/factory.ts
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
// src/stores/products.ts
export const useProductStore = createListStore<Product>('products')
```

```ts
// src/auto-imports.d.ts
import type { Product } from './types/product'

export {}
declare global {
  const useProductStore: ReturnType<typeof import('./stores/products').useProductStore>
}
```

## Type Inference with Auto-Imports

Let TypeScript infer types from auto-imported stores:

```ts
// src/stores/user.ts
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

export type UserStore = ReturnType<typeof useUserStore>
```

```ts
// src/auto-imports.d.ts
import type { UserStore } from './stores/user'

export {}
declare global {
  const useUserStore: () => UserStore
}
```

## Composable Auto-Imports

Auto-import store composables:

```ts
// src/composables/useStore.ts
export function useStore<T extends { id: number }>(
  id: string
) {
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
}
```

```ts
// src/auto-imports.d.ts
export {}
declare global {
  const useStore: typeof import('./composables/useStore').useStore
}
```

## Best Practices

1. **Generate types**: Use dts option to generate type declarations
2. **Define interfaces**: Create interfaces for store types
3. **Use ReturnType**: Infer types from store functions
4. **Document types**: Document what types are available
5. **Keep types updated**: Regenerate types when stores change
6. **Use type assertions**: Cast stores when needed

## Common Mistakes

❌ **Not generating type declarations**

```ts
AutoImport({
  imports: ['vue', 'pinia']
  // ❌ No dts option
})
```

✅ **Generate type declarations**

```ts
AutoImport({
  imports: ['vue', 'pinia'],
  dts: 'src/auto-imports.d.ts' // ✅ Generates types
})
```

❌ **Not typing auto-imported stores**

```ts
declare global {
  const useAuthStore: any // ❌ No type safety
}
```

✅ **Type auto-imported stores**

```ts
import type { AuthStore } from './stores/auth'

declare global {
  const useAuthStore: () => AuthStore // ✅ Type safe
}
```

❌ **Not using ReturnType for inference**

```ts
declare global {
  const useUserStore: () => {
    user: Ref<User | null>
    // ❌ Manual typing
  }
}
```

✅ **Use ReturnType for inference**

```ts
import type { UserStore } from './stores/user'

declare global {
  const useUserStore: () => UserStore // ✅ Inferred from store
}
```

❌ **Not updating types when stores change**

```ts
// Store changed but types not updated
declare global {
  const useAuthStore: () => OldAuthStore // ❌ Outdated types
}
```

✅ **Regenerate types when stores change**

```ts
// Auto-generated types stay in sync
// src/auto-imports.d.ts is regenerated automatically
```
