# State Hydration

Learn how to hydrate Pinia store state from APIs, localStorage, or other sources.

## Basic Hydration Pattern

Hydrate state from an API:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function $hydrate() {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await api.getCurrentUser()
      user.value = response.data
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to load user')
    } finally {
      isLoading.value = false
    }
  }
  
  return { user, isLoading, error, $hydrate }
})
```

## Hydration on App Start

Hydrate stores when the app starts:

```ts
// main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { useUserStore } from './stores/user'
import { usePreferencesStore } from './stores/preferences'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

const userStore = useUserStore()
const preferencesStore = usePreferencesStore()

Promise.all([
  userStore.$hydrate(),
  preferencesStore.$hydrate()
]).then(() => {
  app.mount('#app')
})
```

## Hydration with localStorage

Hydrate from localStorage first, then update from API:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  function hydrateFromStorage() {
    const saved = localStorage.getItem('user')
    if (saved) {
      try {
        user.value = JSON.parse(saved)
      } catch {
        user.value = null
      }
    }
  }
  
  async function $hydrate() {
    hydrateFromStorage()
    
    isLoading.value = true
    error.value = null
    
    try {
      const response = await api.getCurrentUser()
      user.value = response.data
      localStorage.setItem('user', JSON.stringify(response.data))
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to load user')
    } finally {
      isLoading.value = false
    }
  }
  
  return { user, isLoading, error, $hydrate }
})
```

## Selective Hydration

Hydrate only specific parts of the state:

```ts
export const useDashboardStore = defineStore('dashboard', () => {
  const stats = ref<Stats | null>(null)
  const recentActivity = ref<Activity[]>([])
  const notifications = ref<Notification[]>([])
  
  async function $hydrate(options: HydrationOptions = {}) {
    const {
      loadStats = true,
      loadActivity = true,
      loadNotifications = true
    } = options
    
    if (loadStats) {
      stats.value = await api.getStats()
    }
    
    if (loadActivity) {
      recentActivity.value = await api.getRecentActivity()
    }
    
    if (loadNotifications) {
      notifications.value = await api.getNotifications()
    }
  }
  
  return { stats, recentActivity, notifications, $hydrate }
})
```

## Lazy Hydration

Hydrate stores only when needed:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const isHydrated = ref(false)
  const isLoading = ref(false)
  
  async function $hydrate() {
    if (isHydrated.value) return
    
    isLoading.value = true
    try {
      products.value = await api.getProducts()
      isHydrated.value = true
    } finally {
      isLoading.value = false
    }
  }
  
  return { products, isHydrated, isLoading, $hydrate }
})
```

## Hydration with Caching

Cache hydrated data with TTL:

```ts
export const useCacheStore = defineStore('cache', () => {
  const cache = ref<Map<string, CacheEntry>>(new Map())
  
  function setCache(key: string, data: any, ttl: number = 300000) {
    cache.value.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    })
  }
  
  function getCache(key: string): any | null {
    const entry = cache.value.get(key)
    if (!entry) return null
    
    const isExpired = Date.now() - entry.timestamp > entry.ttl
    if (isExpired) {
      cache.value.delete(key)
      return null
    }
    
    return entry.data
  }
  
  async function hydrateWithCache<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl: number = 300000
  ): Promise<T> {
    const cached = getCache(key)
    if (cached) return cached
    
    const data = await fetcher()
    setCache(key, data, ttl)
    return data
  }
  
  return { cache, setCache, getCache, hydrateWithCache }
})
```

## Hydration with Fallback

Provide fallback data when hydration fails:

```ts
export const useConfigStore = defineStore('config', () => {
  const config = ref<Config>(defaultConfig)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function $hydrate() {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await api.getConfig()
      config.value = response.data
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to load config')
      config.value = defaultConfig
    } finally {
      isLoading.value = false
    }
  }
  
  return { config, isLoading, error, $hydrate }
})
```

## Hydration with Validation

Validate hydrated data:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function isValidUser(data: any): data is User {
    return (
      data &&
      typeof data.id === 'number' &&
      typeof data.name === 'string' &&
      typeof data.email === 'string'
    )
  }
  
  function $hydrate(data: any) {
    if (isValidUser(data)) {
      user.value = data
    } else {
      user.value = null
    }
  }
  
  return { user, $hydrate }
})
```

## Hydration with Transformation

Transform data during hydration:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  function transformAPIProduct(apiProduct: APIProduct): Product {
    return {
      id: apiProduct.id,
      name: apiProduct.product_name,
      price: apiProduct.price_cents / 100,
      image: apiProduct.image_url,
      inStock: apiProduct.stock_quantity > 0
    }
  }
  
  async function $hydrate() {
    const apiProducts = await api.getProducts()
    products.value = apiProducts.map(transformAPIProduct)
  }
  
  return { products, $hydrate }
})
```

## Hydration with Partial Data

Handle partial data updates:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function $hydrate(data: Partial<User>) {
    if (!user.value) {
      user.value = data as User
    } else {
      user.value = {
        ...user.value,
        ...data
      }
    }
  }
  
  return { user, $hydrate }
})
```

## SSR Hydration

Hydrate state on the server:

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  async function $hydrate() {
    if (import.meta.env.SSR) {
      const cookie = useCookie('token')
      if (cookie) {
        user.value = await api.getCurrentUser(cookie)
      }
    } else {
      const token = localStorage.getItem('token')
      if (token) {
        user.value = await api.getCurrentUser(token)
      }
    }
  }
  
  return { user, $hydrate }
})
```

```ts
// app.vue
<script setup lang="ts">
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onServerPrefetch(async () => {
  await userStore.$hydrate()
})
</script>
```

## Hydration Status Tracking

Track hydration status:

```ts
export const useStore = defineStore('store', () => {
  const data = ref<Data | null>(null)
  const hydrationStatus = ref<'idle' | 'hydrating' | 'success' | 'error'>('idle')
  const lastHydratedAt = ref<Date | null>(null)
  
  async function $hydrate() {
    hydrationStatus.value = 'hydrating'
    
    try {
      data.value = await api.getData()
      hydrationStatus.value = 'success'
      lastHydratedAt.value = new Date()
    } catch (err) {
      hydrationStatus.value = 'error'
      throw err
    }
  }
  
  const isHydrated = computed(() => hydrationStatus.value === 'success')
  const isHydrating = computed(() => hydrationStatus.value === 'hydrating')
  const hasError = computed(() => hydrationStatus.value === 'error')
  
  return {
    data,
    hydrationStatus,
    lastHydratedAt,
    isHydrated,
    isHydrating,
    hasError,
    $hydrate
  }
})
```

## Best Practices

1. **Always provide $hydrate**: Give a consistent way to hydrate state
2. **Handle errors gracefully**: Provide fallback data when hydration fails
3. **Validate data**: Ensure hydrated data matches expected types
4. **Use caching**: Cache hydrated data to avoid unnecessary requests
5. **Track status**: Provide hydration status for UI feedback
6. **Transform data**: Convert API data to your internal format
7. **Lazy hydrate**: Only hydrate when data is needed

## Common Mistakes

❌ **Not handling hydration errors**

```ts
async function $hydrate() {
  const data = await api.getData() // ❌ No error handling
  this.data = data
}
```

✅ **Handle errors gracefully**

```ts
async function $hydrate() {
  try {
    const data = await api.getData()
    this.data = data
  } catch (err) {
    this.data = defaultData
    this.error = err
  }
}
```

❌ **Not validating data**

```ts
function $hydrate(data: any) {
  this.user = data // ❌ No validation
}
```

✅ **Validate data**

```ts
function $hydrate(data: any) {
  if (isValidUser(data)) {
    this.user = data
  } else {
    this.user = null
  }
}
```

❌ **Hydrating everything at once**

```ts
async function $hydrate() {
  this.users = await api.getUsers()
  this.products = await api.getProducts()
  this.orders = await api.getOrders()
  // ❌ Slow, blocks app start
}
```

✅ **Lazy hydrate as needed**

```ts
async function $hydrate() {
  this.users = await api.getUsers()
}

async function loadProducts() {
  if (!this.products.length) {
    this.products = await api.getProducts()
  }
}
```
