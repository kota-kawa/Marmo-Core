# Pinia vs Provide/Inject

Learn when to use Pinia vs provide/inject for state management.

## Pinia Overview

Pinia is a dedicated state management library:

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => !!user.value)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
  }
  
  return { user, isAuthenticated, login }
})
```

```vue
<script setup lang="ts">
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
</script>

<template>
  <div v-if="userStore.isAuthenticated">
    Welcome, {{ userStore.user?.name }}
  </div>
</template>
```

## Provide/Inject Overview

Provide/inject is Vue's built-in state management:

```ts
// providers/user.ts
export function provideUser() {
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => !!user.value)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
  }
  
  provide('user', {
    user,
    isAuthenticated,
    login
  })
}
```

```vue
<script setup lang="ts">
import { inject } from 'vue'

const userState = inject<{
  user: Ref<User | null>
  isAuthenticated: ComputedRef<boolean>
  login: (credentials: Credentials) => Promise<void>
}>('user')
</script>

<template>
  <div v-if="userState.isAuthenticated.value">
    Welcome, {{ userState.user.value?.name }}
  </div>
</template>
```

## When to Use Pinia

Use Pinia when:

1. **Global state**: State needed across the entire application
2. **Complex state**: State with multiple related properties
3. **Persistence**: State that needs to be persisted
4. **DevTools**: Need state debugging with DevTools
5. **Type safety**: Need strong TypeScript support
6. **Composition**: Need to compose multiple stores

```ts
// Good use case for Pinia
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
  
  return { items, total, addItem }
})
```

## When to Use Provide/Inject

Use provide/inject when:

1. **Local state**: State needed only in a component tree
2. **Simple state**: State with few properties
3. **Component libraries**: Building reusable components
4. **Dependency injection**: Injecting dependencies
5. **Theme/context**: Theme or context-specific state
6. **Avoiding prop drilling**: Passing data through component tree

```ts
// Good use case for provide/inject
export function provideTheme() {
  const theme = ref<'light' | 'dark'>('light')
  
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }
  
  provide('theme', {
    theme,
    toggleTheme
  })
}
```

## Comparison

| Feature | Pinia | Provide/Inject |
|---------|--------|----------------|
| Global Access | ✅ Easy access anywhere | ❌ Limited to provider tree |
| DevTools | ✅ Full DevTools support | ❌ No DevTools integration |
| TypeScript | ✅ Excellent type inference | ⚠️ Manual typing required |
| Persistence | ✅ Built-in plugins | ❌ Manual implementation |
| Composition | ✅ Easy store composition | ⚠️ More complex |
| Learning Curve | ⚠️ Requires learning | ✅ Built into Vue |
| Bundle Size | ⚠️ Additional library | ✅ No additional code |
| Performance | ✅ Optimized for state | ✅ Minimal overhead |

## Pinia for Global State

Use Pinia for application-wide state:

```ts
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => !!user.value)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
    token.value = response.token
    localStorage.setItem('token', response.token)
  }
  
  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
  }
  
  return { user, token, isAuthenticated, login, logout }
})
```

## Provide/Inject for Local State

Use provide/inject for component tree state:

```ts
// components/ThemeProvider.vue
<script setup lang="ts">
import { provide, ref } from 'vue'

const theme = ref<'light' | 'dark'>('light')

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
}

provide('theme', {
  theme,
  toggleTheme
})
</script>

<template>
  <slot />
</template>
```

```vue
<script setup lang="ts">
import { inject } from 'vue'

const themeState = inject<{
  theme: Ref<'light' | 'dark'>
  toggleTheme: () => void
}>('theme')
</script>

<template>
  <button @click="themeState.toggleTheme">
    Toggle Theme ({{ themeState.theme.value }})
  </button>
</template>
```

## Combining Both

Use Pinia and provide/inject together:

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
  
  return { user, token, login }
})
```

```ts
// providers/auth.ts
export function provideAuth() {
  const authStore = useAuthStore()
  
  provide('auth', {
    user: authStore.user,
    login: authStore.login
  })
}
```

## Best Practices

1. **Use Pinia for global state**: Application-wide state management
2. **Use provide/inject for local state**: Component tree state
3. **Consider complexity**: Use Pinia for complex state
4. **Consider scope**: Use provide/inject for scoped state
5. **Mix both**: Use both when appropriate
6. **Prefer Pinia**: For most state management needs

## Common Mistakes

❌ **Using provide/inject for global state**

```ts
// ❌ Not ideal for global state
provide('user', { user, login })
```

✅ **Use Pinia for global state**

```ts
// ✅ Better for global state
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  return { user }
})
```

❌ **Using Pinia for local component state**

```ts
// ❌ Overkill for local state
export const useModalStore = defineStore('modal', () => {
  const isOpen = ref(false)
  return { isOpen }
})
```

✅ **Use provide/inject for local state**

```ts
// ✅ Better for local state
provide('modal', {
  isOpen: ref(false)
})
```

❌ **Not considering complexity**

```ts
// ❌ Using provide/inject for complex state
provide('cart', {
  items: ref([]),
  total: computed(() => ...),
  addItem: () => {},
  removeItem: () => {},
  // ... many more properties
})
```

✅ **Use Pinia for complex state**

```ts
// ✅ Better for complex state
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const total = computed(() => ...)
  function addItem(product: Product) {}
  function removeItem(id: number) {}
  return { items, total, addItem, removeItem }
})
```

❌ **Mixing without clear purpose**

```ts
// ❌ Unclear why using both
const store = useStore()
provide('store', store)
```

✅ **Clear separation of concerns**

```ts
// ✅ Clear purpose for each
const store = useStore() // Global state
provide('theme', { theme, toggleTheme }) // Local state
```
