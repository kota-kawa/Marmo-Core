# State Reset Pattern

Learn how to reset Pinia store state to initial values.

## Basic Reset Pattern

Provide a `$reset()` function to reset state:

```ts
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  const name = ref('Eduardo')
  
  function increment() {
    count.value++
  }
  
  function $reset() {
    count.value = 0
    name.value = 'Eduardo'
  }
  
  return { count, name, increment, $reset }
})
```

## Using Initial State Reference

Store initial state in a constant:

```ts
export const useFilterStore = defineStore('filter', () => {
  const initialState: Filters = {
    category: 'all',
    priceRange: [0, 1000],
    rating: 0,
    sortBy: 'popular'
  }
  
  const filters = ref<Filters>({ ...initialState })
  
  function setFilter<K extends keyof Filters>(key: K, value: Filters[K]) {
    filters.value[key] = value
  }
  
  function $reset() {
    filters.value = { ...initialState }
  }
  
  return { filters, setFilter, $reset }
})
```

## Deep Reset for Nested Objects

For nested objects, use deep cloning:

```ts
export const useFormStore = defineStore('form', () => {
  const initialState: FormData = {
    user: {
      name: '',
      email: '',
      address: {
        street: '',
        city: '',
        country: ''
      }
    },
    preferences: {
      notifications: true,
      newsletter: false
    }
  }
  
  const formData = ref<FormData>(JSON.parse(JSON.stringify(initialState)))
  
  function $reset() {
    formData.value = JSON.parse(JSON.stringify(initialState))
  }
  
  return { formData, $reset }
})
```

## Reset with Factory Function

Use a factory function to create initial state:

```ts
function createInitialTodoState(): TodoState {
  return {
    todos: [],
    filter: 'all',
    searchQuery: ''
  }
}

export const useTodoStore = defineStore('todos', () => {
  const state = ref<TodoState>(createInitialTodoState())
  
  function $reset() {
    state.value = createInitialTodoState()
  }
  
  return { state, $reset }
})
```

## Selective Reset

Reset only specific parts of the state:

```ts
export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const results = ref<SearchResult[]>([])
  const filters = ref<SearchFilters>({
    category: 'all',
    dateRange: null
  })
  const pagination = ref({
    page: 1,
    perPage: 20
  })
  
  function resetFilters() {
    filters.value = {
      category: 'all',
      dateRange: null
    }
  }
  
  function resetResults() {
    results.value = []
    pagination.value.page = 1
  }
  
  function $reset() {
    query.value = ''
    resetResults()
    resetFilters()
  }
  
  return {
    query,
    results,
    filters,
    pagination,
    resetFilters,
    resetResults,
    $reset
  }
})
```

## Reset with Side Effects

Perform side effects when resetting:

```ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const coupon = ref<string | null>(null)
  
  function $reset() {
    items.value = []
    coupon.value = null
    localStorage.removeItem('cart')
    localStorage.removeItem('coupon')
    analytics.track('cart_cleared')
  }
  
  return { items, coupon, $reset }
})
```

## Reset After Async Operation

Reset state after successful async operations:

```ts
export const useFormStore = defineStore('form', () => {
  const initialState: FormState = {
    name: '',
    email: '',
    message: ''
  }
  
  const formData = ref<FormState>({ ...initialState })
  const isSubmitting = ref(false)
  const error = ref<Error | null>(null)
  
  async function submitForm() {
    isSubmitting.value = true
    error.value = null
    
    try {
      await api.submitForm(formData.value)
      $reset()
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Submission failed')
    } finally {
      isSubmitting.value = false
    }
  }
  
  function $reset() {
    formData.value = { ...initialState }
    error.value = null
  }
  
  return { formData, isSubmitting, error, submitForm, $reset }
})
```

## Reset Multiple Stores

Reset multiple related stores:

```ts
// stores/modules/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  
  function $reset() {
    user.value = null
    token.value = null
  }
  
  return { user, token, $reset }
})
```

```ts
// stores/modules/preferences.ts
export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref('light')
  const language = ref('en')
  
  function $reset() {
    theme.value = 'light'
    language.value = 'en'
  }
  
  return { theme, language, $reset }
})
```

```ts
// stores/modules/session.ts
export const useSessionStore = defineStore('session', () => {
  const authStore = useAuthStore()
  const preferencesStore = usePreferencesStore()
  
  function logout() {
    authStore.$reset()
    preferencesStore.$reset()
    localStorage.clear()
    router.push('/login')
  }
  
  return { logout }
})
```

## Reset with Validation

Validate state before resetting:

```ts
export const useEditorStore = defineStore('editor', () => {
  const content = ref('')
  const isDirty = ref(false)
  const lastSaved = ref<Date | null>(null)
  
  async function $reset(force = false) {
    if (isDirty.value && !force) {
      const confirmed = await confirm('You have unsaved changes. Continue?')
      if (!confirmed) return
    }
    
    content.value = ''
    isDirty.value = false
    lastSaved.value = null
  }
  
  return { content, isDirty, lastSaved, $reset }
})
```

## Reset with Persistence

Handle persistent state when resetting:

```ts
export const useSettingsStore = defineStore('settings', () => {
  const initialState: Settings = {
    theme: 'light',
    language: 'en',
    fontSize: 16
  }
  
  const settings = ref<Settings>({ ...initialState })
  
  function loadSettings() {
    const saved = localStorage.getItem('settings')
    if (saved) {
      settings.value = JSON.parse(saved)
    }
  }
  
  function saveSettings() {
    localStorage.setItem('settings', JSON.stringify(settings.value))
  }
  
  function $reset() {
    settings.value = { ...initialState }
    saveSettings()
  }
  
  return { settings, loadSettings, saveSettings, $reset }
})
```

## Using Reset in Components

```vue
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()

function handleReset() {
  counter.$reset()
}
</script>

<template>
  <div>
    <p>Count: {{ counter.count }}</p>
    <button @click="counter.increment">Increment</button>
    <button @click="handleReset">Reset</button>
  </div>
</template>
```

## Reset on Route Change

Reset store when route changes:

```ts
// stores/modules/list.ts
export const useListStore = defineStore('list', () => {
  const items = ref<Item[]>([])
  const filter = ref('all')
  
  function $reset() {
    items.value = []
    filter.value = 'all'
  }
  
  return { items, filter, $reset }
})
```

```ts
// router/index.ts
import { useListStore } from '@/stores/modules/list'

router.beforeEach((to, from, next) => {
  const listStore = useListStore()
  
  if (to.path !== from.path) {
    listStore.$reset()
  }
  
  next()
})
```

## Best Practices

1. **Always provide $reset**: Give users a way to reset state
2. **Use initial state reference**: Store initial state for easy reset
3. **Handle nested objects**: Use deep cloning for complex objects
4. **Add validation**: Confirm before resetting if state is dirty
5. **Clean up side effects**: Remove listeners, clear storage, etc.
6. **Document reset behavior**: Explain what gets reset and why

## Common Mistakes

❌ **Not resetting all state**

```ts
function $reset() {
  this.count = 0 // ❌ Forgot to reset name
}
```

✅ **Reset all state**

```ts
function $reset() {
  this.count = 0
  this.name = 'Eduardo' // ✅ Reset all state
}
```

❌ **Mutating initial state**

```ts
const initialState = { items: [] }
const state = ref(initialState)

function $reset() {
  state.value = initialState // ❌ Reference to same object
}
```

✅ **Create new instance**

```ts
const initialState = { items: [] }
const state = ref({ ...initialState })

function $reset() {
  state.value = { ...initialState } // ✅ New instance
}
```

❌ **Not handling nested objects**

```ts
const initialState = {
  user: { name: '', email: '' }
}

function $reset() {
  this.user = initialState // ❌ Shallow copy
}
```

✅ **Deep copy nested objects**

```ts
const initialState = {
  user: { name: '', email: '' }
}

function $reset() {
  this.user = { ...initialState.user } // ✅ Deep copy
}
```
