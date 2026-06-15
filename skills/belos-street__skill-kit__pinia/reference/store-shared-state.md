# Store Shared State

Learn how to share state between multiple Pinia stores.

## Basic Shared State

Create a shared store for common state:

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

## Using Shared State

Use shared state in multiple stores:

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

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const uiStore = useUIStore()
  
  const users = ref<User[]>([])
  
  async function fetchUsers() {
    uiStore.setLoading(true)
    try {
      users.value = await api.getUsers()
    } catch (err) {
      uiStore.showNotification('Failed to fetch users', 'error')
      throw err
    } finally {
      uiStore.setLoading(false)
    }
  }
  
  return { users, fetchUsers }
})
```

## Shared State with Computed

Create computed values from shared state:

```ts
// stores/shared/app.ts
export const useAppStore = defineStore('app', () => {
  const theme = ref<'light' | 'dark'>('light')
  const language = ref('en')
  const isOnline = ref(true)
  
  const isDark = computed(() => theme.value === 'dark')
  const isLight = computed(() => theme.value === 'light')
  
  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
    document.documentElement.setAttribute('data-theme', newTheme)
  }
  
  function setLanguage(newLanguage: string) {
    language.value = newLanguage
  }
  
  function setOnline(online: boolean) {
    isOnline.value = online
  }
  
  return {
    theme,
    language,
    isOnline,
    isDark,
    isLight,
    setTheme,
    setLanguage,
    setOnline
  }
})
```

## Shared State with Actions

Create shared actions for common operations:

```ts
// stores/shared/api.ts
export const useAPIStore = defineStore('api', () => {
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function execute<T>(action: () => Promise<T>): Promise<T> {
    isLoading.value = true
    error.value = null
    
    try {
      return await action()
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('API request failed')
      throw error.value
    } finally {
      isLoading.value = false
    }
  }
  
  return { isLoading, error, execute }
})
```

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const apiStore = useAPIStore()
  
  const user = ref<User | null>(null)
  
  async function fetchUser() {
    await apiStore.execute(async () => {
      const response = await api.getCurrentUser()
      user.value = response.data
    })
  }
  
  return { user, fetchUser }
})
```

## Shared State with Persistence

Persist shared state to localStorage:

```ts
// stores/shared/preferences.ts
export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<'light' | 'dark'>('light')
  const language = ref('en')
  
  function loadPreferences() {
    const saved = localStorage.getItem('preferences')
    if (saved) {
      const prefs = JSON.parse(saved)
      theme.value = prefs.theme
      language.value = prefs.language
    }
  }
  
  function savePreferences() {
    localStorage.setItem('preferences', JSON.stringify({
      theme: theme.value,
      language: language.value
    }))
  }
  
  watch([theme, language], savePreferences)
  
  return { theme, language, loadPreferences }
})
```

## Shared State with Events

Use events to communicate between stores:

```ts
// stores/shared/eventBus.ts
export const useEventBus = defineStore('eventBus', () => {
  const listeners = ref<Map<string, Set<Function>>>(new Map())
  
  function on(event: string, handler: Function) {
    if (!listeners.value.has(event)) {
      listeners.value.set(event, new Set())
    }
    listeners.value.get(event)!.add(handler)
  }
  
  function off(event: string, handler: Function) {
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
  
  const user = ref<User | null>(null)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
    eventBus.emit('user:login', response.user)
  }
  
  function logout() {
    const user = this.user
    this.user = null
    eventBus.emit('user:logout', user)
  }
  
  return { user, login, logout }
})
```

```ts
// stores/cart.ts
export const useCartStore = defineStore('cart', () => {
  const eventBus = useEventBus()
  
  const items = ref<CartItem[]>([])
  
  function init() {
    eventBus.on('user:logout', () => {
      items.value = []
    })
  }
  
  return { items, init }
})
```

## Shared State with Composables

Create composables for shared state:

```ts
// composables/useLoading.ts
export function useLoading() {
  const isLoading = ref(false)
  const loadingStates = ref<Set<string>>(new Set())
  
  function setLoading(loading: boolean, key?: string) {
    if (key) {
      if (loading) {
        loadingStates.value.add(key)
      } else {
        loadingStates.value.delete(key)
      }
    }
    isLoading.value = loadingStates.value.size > 0
  }
  
  return { isLoading, loadingStates, setLoading }
}
```

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const { isLoading, setLoading } = useLoading()
  
  const user = ref<User | null>(null)
  
  async function fetchUser() {
    setLoading(true, 'fetchUser')
    try {
      const response = await api.getCurrentUser()
      user.value = response.data
    } finally {
      setLoading(false, 'fetchUser')
    }
  }
  
  return { user, isLoading, fetchUser }
})
```

## Shared State with TypeScript

Type shared state properly:

```ts
// stores/shared/types.ts
export interface SharedUIState {
  isLoading: boolean
  notification: Notification | null
}

export interface SharedAPIState {
  isLoading: boolean
  error: Error | null
}

export interface SharedPreferencesState {
  theme: 'light' | 'dark'
  language: string
}
```

```ts
// stores/shared/ui.ts
import type { SharedUIState } from './types'

export const useUIStore = defineStore('ui', () => {
  const state = ref<SharedUIState>({
    isLoading: false,
    notification: null
  })
  
  return { state }
})
```

## Best Practices

1. **Create shared stores**: For common state and actions
2. **Use composables**: For reusable logic
3. **Use events**: For loose coupling between stores
4. **Persist shared state**: Save to localStorage when needed
5. **Type shared state**: Use TypeScript for type safety
6. **Keep shared state minimal**: Only share what's necessary

## Common Mistakes

❌ **Duplicating shared logic**

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

✅ **Use shared store**

```ts
// stores/shared/api.ts
export const useAPIStore = defineStore('api', () => {
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
})

// stores/a.ts
const apiStore = useAPIStore()
async function fetchData() {
  await apiStore.execute(() => api.getData())
}

// stores/b.ts
const apiStore = useAPIStore()
async function fetchData() {
  await apiStore.execute(() => api.getData())
}
```

❌ **Not typing shared state**

```ts
export const useSharedStore = defineStore('shared', () => {
  const state = ref({}) // ❌ No type
  return { state }
})
```

✅ **Type shared state**

```ts
interface SharedState {
  isLoading: boolean
  error: Error | null
}

export const useSharedStore = defineStore('shared', () => {
  const state = ref<SharedState>({ // ✅ Typed
    isLoading: false,
    error: null
  })
  return { state }
})
```

❌ **Sharing too much state**

```ts
export const useSharedStore = defineStore('shared', () => {
  const everything = ref({}) // ❌ Too much
  return { everything }
})
```

✅ **Share only what's needed**

```ts
export const useUIStore = defineStore('ui', () => {
  const isLoading = ref(false)
  const notification = ref(null)
  return { isLoading, notification } // ✅ Minimal
})
```
