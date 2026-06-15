# defineStore with Composition API

Use `defineStore()` with the Composition API style (setup stores) for the most flexible and type-safe Pinia stores.

## Setup Store Pattern

The setup store uses Vue's Composition API functions like `ref`, `computed`, and functions to define state, getters, and actions.

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  const name = ref('Eduardo')
  
  const doubleCount = computed(() => count.value * 2)
  
  function increment() {
    count.value++
  }
  
  function $reset() {
    count.value = 0
    name.value = 'Eduardo'
  }
  
  return { count, name, doubleCount, increment, $reset }
})
```

## Why Setup Stores?

Setup stores provide several advantages over options stores:

- **Better TypeScript inference**: Full type inference without manual typing
- **More flexible**: Can use any Composition API function
- **More intuitive**: Follows the same patterns as Vue components
- **Composable**: Easier to extract and reuse logic

## Store ID

The first argument to `defineStore()` is a unique store ID:

```ts
export const useUserStore = defineStore('user', () => {
  // store implementation
})

export const useCartStore = defineStore('cart', () => {
  // store implementation
})
```

Store IDs must be unique across your application. They are used for:
- DevTools identification
- SSR state hydration
- Store instance caching

## Return Object

The return object defines the public API of your store:

```ts
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
  
  function addTodo(text: string) {
    todos.value.push({
      id: Date.now(),
      text,
      completed: false
    })
  }
  
  function removeTodo(id: number) {
    const index = todos.value.findIndex(t => t.id === id)
    if (index > -1) {
      todos.value.splice(index, 1)
    }
  }
  
  function toggleTodo(id: number) {
    const todo = todos.value.find(t => t.id === id)
    if (todo) {
      todo.completed = !todo.completed
    }
  }
  
  return {
    todos,
    filter,
    filteredTodos,
    addTodo,
    removeTodo,
    toggleTodo
  }
})
```

Only properties and functions returned from the setup function are accessible from outside the store.

## Private State

You can keep state private by not returning it:

```ts
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  
  const isAuthenticated = computed(() => token.value !== null)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    token.value = response.access_token
    refreshToken.value = response.refresh_token
  }
  
  async function logout() {
    token.value = null
    refreshToken.value = null
  }
  
  async function refreshAccessToken() {
    if (!refreshToken.value) return
    
    const response = await api.refreshToken(refreshToken.value)
    token.value = response.access_token
  }
  
  return {
    isAuthenticated,
    login,
    logout
  }
  // token and refreshToken are private
})
```

## Using External Composables

Setup stores can use external composables:

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'

export const usePreferencesStore = defineStore('preferences', () => {
  const theme = useLocalStorage('theme', 'light')
  const language = useLocalStorage('language', 'en')
  
  function setTheme(newTheme: string) {
    theme.value = newTheme
  }
  
  function setLanguage(newLanguage: string) {
    language.value = newLanguage
  }
  
  return { theme, language, setTheme, setLanguage }
})
```

## Store with Watchers

You can use `watch` to react to state changes:

```ts
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const results = ref<SearchResult[]>([])
  const isLoading = ref(false)
  
  watch(query, async (newQuery) => {
    if (newQuery.length < 2) {
      results.value = []
      return
    }
    
    isLoading.value = true
    try {
      results.value = await searchAPI(newQuery)
    } finally {
      isLoading.value = false
    }
  }, { debounce: 300 })
  
  return { query, results, isLoading }
})
```

## Best Practices

1. **Use descriptive store names**: `useUserStore`, `useCartStore`, not `useStore`
2. **Keep stores focused**: One store per domain (user, cart, products, etc.)
3. **Return only what's needed**: Keep internal state private
4. **Use TypeScript interfaces**: Define clear types for your state
5. **Use computed for derived state**: Don't duplicate logic in components

## Common Mistakes

❌ **Don't mutate state outside the store**

```ts
const store = useCounterStore()
store.count = 10 // This bypasses any validation
```

✅ **Use actions to mutate state**

```ts
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  
  function setCount(value: number) {
    if (value >= 0) {
      count.value = value
    }
  }
  
  return { count, setCount }
})
```

❌ **Don't return non-reactive values**

```ts
export const useStore = defineStore('store', () => {
  const data = ref({ foo: 'bar' })
  
  return {
    data: data.value // Returns non-reactive object
  }
})
```

✅ **Return refs directly**

```ts
export const useStore = defineStore('store', () => {
  const data = ref({ foo: 'bar' })
  
  return {
    data // Returns reactive ref
  }
})
```
