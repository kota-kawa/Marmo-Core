# TypeScript State Typing

Learn how to type Pinia store state with TypeScript.

## Basic State Typing

Type your state with interfaces:

```ts
interface User {
  id: number
  name: string
  email: string
  avatar?: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  return { user, isLoading, error }
})
```

## Using Interfaces

Define interfaces for your state:

```ts
interface Todo {
  id: number
  text: string
  completed: boolean
  createdAt: Date
}

interface TodoState {
  todos: Todo[]
  filter: 'all' | 'active' | 'completed'
  searchQuery: string
}

export const useTodoStore = defineStore('todos', () => {
  const state = ref<TodoState>({
    todos: [],
    filter: 'all',
    searchQuery: ''
  })
  
  return { state }
})
```

## Using Type Aliases

Use type aliases for complex types:

```ts
type FilterType = 'all' | 'active' | 'completed'
type SortOrder = 'asc' | 'desc'

interface TodoFilters {
  filter: FilterType
  sort: SortOrder
  searchQuery: string
}

export const useTodoStore = defineStore('todos', () => {
  const filters = ref<TodoFilters>({
    filter: 'all',
    sort: 'asc',
    searchQuery: ''
  })
  
  return { filters }
})
```

## Generic State Types

Create generic types for reusable stores:

```ts
interface ListState<T> {
  items: T[]
  isLoading: boolean
  error: Error | null
}

export const useListStore = <T extends { id: number }>(
  id: string,
  fetchFn: () => Promise<T[]>
) => {
  return defineStore(id, () => {
    const state = ref<ListState<T>>({
      items: [],
      isLoading: false,
      error: null
    })
    
    async function fetch() {
      state.value.isLoading = true
      state.value.error = null
      
      try {
        state.value.items = await fetchFn()
      } catch (err) {
        state.value.error = err instanceof Error ? err : new Error('Failed to fetch')
      } finally {
        state.value.isLoading = false
      }
    }
    
    return { state, fetch }
  })
}
```

## Union Types

Use union types for flexible state:

```ts
type NotificationType = 'success' | 'error' | 'info' | 'warning'

interface Notification {
  id: number
  type: NotificationType
  message: string
  timestamp: Date
}

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref<Notification[]>([])
  
  function addNotification(type: NotificationType, message: string) {
    notifications.value.push({
      id: Date.now(),
      type,
      message,
      timestamp: new Date()
    })
  }
  
  return { notifications, addNotification }
})
```

## Discriminated Unions

Use discriminated unions for complex state:

```ts
type LoadingState = {
  status: 'loading'
}

type SuccessState<T> = {
  status: 'success'
  data: T
}

type ErrorState = {
  status: 'error'
  error: Error
}

type AsyncState<T> = LoadingState | SuccessState<T> | ErrorState

export const useStore = defineStore('store', () => {
  const state = ref<AsyncState<User>>({ status: 'loading' })
  
  async function fetchUser() {
    state.value = { status: 'loading' }
    
    try {
      const user = await api.getCurrentUser()
      state.value = { status: 'success', data: user }
    } catch (err) {
      state.value = { status: 'error', error: err instanceof Error ? err : new Error('Failed') }
    }
  }
  
  return { state, fetchUser }
})
```

## Optional Properties

Use optional properties for partial state:

```ts
interface User {
  id: number
  name: string
  email: string
  avatar?: string
  phone?: string
  address?: Address
}

export const useUserStore = defineStore('user', () => {
  const user = ref<Partial<User>>({})
  
  function updateUser(updates: Partial<User>) {
    user.value = { ...user.value, ...updates }
  }
  
  return { user, updateUser }
})
```

## Readonly State

Use readonly types for immutable state:

```ts
interface User {
  id: number
  name: string
  email: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<Readonly<User>>({
    id: 0,
    name: '',
    email: ''
  })
  
  function setUser(newUser: User) {
    user.value = newUser
  }
  
  return { user, setUser }
})
```

## Array State Typing

Type arrays properly:

```ts
interface Todo {
  id: number
  text: string
  completed: boolean
}

export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  const activeTodos = ref<Todo[]>([])
  const completedTodos = ref<Todo[]>([])
  
  function addTodo(text: string) {
    todos.value.push({
      id: Date.now(),
      text,
      completed: false
    })
  }
  
  return { todos, activeTodos, completedTodos, addTodo }
})
```

## Record Types

Use Record types for key-value state:

```ts
type Theme = 'light' | 'dark'
type Language = 'en' | 'es' | 'fr'

interface Settings {
  theme: Theme
  language: Language
  fontSize: number
}

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<Settings>({
    theme: 'light',
    language: 'en',
    fontSize: 16
  })
  
  return { settings }
})
```

## Nested State Typing

Type nested objects properly:

```ts
interface Address {
  street: string
  city: string
  country: string
  zipCode: string
}

interface User {
  id: number
  name: string
  email: string
  address: Address
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function updateAddress(updates: Partial<Address>) {
    if (!user.value) return
    
    user.value = {
      ...user.value,
      address: {
        ...user.value.address,
        ...updates
      }
    }
  }
  
  return { user, updateAddress }
})
```

## State with Utility Types

Use TypeScript utility types:

```ts
interface User {
  id: number
  name: string
  email: string
  createdAt: Date
  updatedAt: Date
}

type UserInput = Omit<User, 'id' | 'createdAt' | 'updatedAt'>
type UserUpdate = Partial<UserInput>

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function createUser(input: UserInput) {
    const newUser: User = {
      ...input,
      id: Date.now(),
      createdAt: new Date(),
      updatedAt: new Date()
    }
    user.value = newUser
  }
  
  function updateUser(updates: UserUpdate) {
    if (!user.value) return
    
    user.value = {
      ...user.value,
      ...updates,
      updatedAt: new Date()
    }
  }
  
  return { user, createUser, updateUser }
})
```

## Best Practices

1. **Use interfaces**: Define clear interfaces for your state
2. **Type everything**: Don't use `any` or `unknown`
3. **Use union types**: For flexible state values
4. **Use generics**: For reusable store patterns
5. **Use utility types**: Leverage TypeScript's built-in types
6. **Keep types DRY**: Don't duplicate type definitions

## Common Mistakes

❌ **Using any**

```ts
const user = ref<any>(null) // ❌ No type safety
```

✅ **Use proper types**

```ts
const user = ref<User | null>(null) // ✅ Type safe
```

❌ **Not typing arrays**

```ts
const items = ref([]) // ❌ Type is any[]
```

✅ **Type arrays properly**

```ts
const items = ref<Item[]>([]) // ✅ Type safe
```

❌ **Not using optional properties**

```ts
interface User {
  id: number
  name: string
  avatar: string // ❌ Required
}
```

✅ **Use optional properties**

```ts
interface User {
  id: number
  name: string
  avatar?: string // ✅ Optional
}
```

❌ **Not typing nested objects**

```ts
const user = ref({
  id: 1,
  address: {} // ❌ Type is any
})
```

✅ **Type nested objects**

```ts
const user = ref<User>({
  id: 1,
  address: {
    street: '',
    city: '',
    country: ''
  }
})
```
