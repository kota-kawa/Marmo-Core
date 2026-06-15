# Action Async Error Handling

Learn how to handle async operations and errors in Pinia actions.

## Basic Async Actions

Create async actions for API calls:

```ts
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
      user.value = null
    } finally {
      isLoading.value = false
    }
  }
  
  return { user, isLoading, error, fetchUser }
})
```

## Error Handling Patterns

### Try-Catch-Finally

```ts
async function login(credentials: Credentials) {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await api.login(credentials)
    user.value = response.user
    token.value = response.token
  } catch (err) {
    error.value = err instanceof Error ? err : new Error('Login failed')
    throw err
  } finally {
    isLoading.value = false
  }
}
```

### Error Types

```ts
interface APIError extends Error {
  status?: number
  code?: string
}

function isAPIError(err: unknown): err is APIError {
  return err instanceof Error && 'status' in err
}

async function fetchUser() {
  try {
    const response = await api.getCurrentUser()
    user.value = response.data
  } catch (err) {
    if (isAPIError(err)) {
      if (err.status === 401) {
        error.value = new Error('Unauthorized')
      } else if (err.status === 404) {
        error.value = new Error('User not found')
      } else {
        error.value = new Error('Failed to fetch user')
      }
    } else {
      error.value = new Error('An unexpected error occurred')
    }
  }
}
```

## Loading States

### Multiple Loading States

```ts
export const useStore = defineStore('store', () => {
  const isLoading = ref(false)
  const isFetching = ref(false)
  const isSubmitting = ref(false)
  
  async function fetchData() {
    isFetching.value = true
    try {
      const data = await api.getData()
      return data
    } finally {
      isFetching.value = false
    }
  }
  
  async function submitData(data: any) {
    isSubmitting.value = true
    try {
      const result = await api.submitData(data)
      return result
    } finally {
      isSubmitting.value = false
    }
  }
  
  return { isLoading, isFetching, isSubmitting, fetchData, submitData }
})
```

### Global Loading State

```ts
export const useStore = defineStore('store', () => {
  const loadingStates = ref<Record<string, boolean>>({})
  
  function setLoading(key: string, value: boolean) {
    loadingStates.value[key] = value
  }
  
  async function fetchData() {
    setLoading('fetch', true)
    try {
      return await api.getData()
    } finally {
      setLoading('fetch', false)
    }
  }
  
  const isLoading = computed(() => 
    Object.values(loadingStates.value).some(Boolean)
  )
  
  return { loadingStates, isLoading, fetchData }
})
```

## Retry Logic

### Simple Retry

```ts
async function fetchWithRetry(url: string, maxRetries = 3) {
  let lastError: Error | null = null
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await api.get(url)
    } catch (err) {
      lastError = err instanceof Error ? err : new Error('Request failed')
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
    }
  }
  
  throw lastError
}
```

### Exponential Backoff

```ts
async function fetchWithBackoff(url: string, maxRetries = 3) {
  let lastError: Error | null = null
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await api.get(url)
    } catch (err) {
      lastError = err instanceof Error ? err : new Error('Request failed')
      const delay = Math.min(1000 * Math.pow(2, i), 10000)
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
  
  throw lastError
}
```

## Request Cancellation

### AbortController

```ts
export const useStore = defineStore('store', () => {
  const abortController = ref<AbortController | null>(null)
  const data = ref<Data | null>(null)
  
  async function fetchData() {
    if (abortController.value) {
      abortController.value.abort()
    }
    
    abortController.value = new AbortController()
    
    try {
      const response = await api.getData(abortController.value.signal)
      data.value = response
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Request aborted')
      } else {
        throw err
      }
    } finally {
      abortController.value = null
    }
  }
  
  return { data, fetchData }
})
```

## Optimistic Updates

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  const error = ref<Error | null>(null)
  
  async function toggleTodo(id: number) {
    const todo = todos.value.find(t => t.id === id)
    if (!todo) return
    
    const originalCompleted = todo.completed
    todo.completed = !todo.completed
    
    try {
      await api.updateTodo(id, { completed: todo.completed })
    } catch (err) {
      todo.completed = originalCompleted
      error.value = err instanceof Error ? err : new Error('Failed to update todo')
      throw err
    }
  }
  
  return { todos, error, toggleTodo }
})
```

## Concurrent Requests

### Promise.all

```ts
async function fetchAll() {
  isLoading.value = true
  error.value = null
  
  try {
    const [users, products, orders] = await Promise.all([
      api.getUsers(),
      api.getProducts(),
      api.getOrders()
    ])
    
    users.value = users
    products.value = products
    orders.value = orders
  } catch (err) {
    error.value = err instanceof Error ? err : new Error('Failed to fetch data')
  } finally {
    isLoading.value = false
  }
}
```

### Promise.allSettled

```ts
async function fetchAll() {
  isLoading.value = true
  
  const results = await Promise.allSettled([
    api.getUsers(),
    api.getProducts(),
    api.getOrders()
  ])
  
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      switch (index) {
        case 0: users.value = result.value; break
        case 1: products.value = result.value; break
        case 2: orders.value = result.value; break
      }
    } else {
      console.error(`Request ${index} failed:`, result.reason)
    }
  })
  
  isLoading.value = false
}
```

## Request Queueing

### Sequential Requests

```ts
export const useStore = defineStore('store', () => {
  const requestQueue = ref<(() => Promise<any>)[]>([])
  const isProcessing = ref(false)
  
  async function processQueue() {
    if (isProcessing.value || requestQueue.value.length === 0) return
    
    isProcessing.value = true
    
    while (requestQueue.value.length > 0) {
      const request = requestQueue.value.shift()!
      try {
        await request()
      } catch (err) {
        console.error('Request failed:', err)
      }
    }
    
    isProcessing.value = false
  }
  
  function queueRequest(request: () => Promise<any>) {
    requestQueue.value.push(request)
    processQueue()
  }
  
  return { isProcessing, queueRequest }
})
```

## Error Notifications

### Global Error Handler

```ts
export const useErrorStore = defineStore('error', () => {
  const errors = ref<Error[]>([])
  
  function handleError(error: Error) {
    errors.value.push(error)
    console.error('Error:', error)
    
    if (import.meta.env.PROD) {
      analytics.trackError(error)
    }
  }
  
  function clearErrors() {
    errors.value = []
  }
  
  return { errors, handleError, clearErrors }
})
```

```ts
export const useUserStore = defineStore('user', () => {
  const errorStore = useErrorStore()
  
  async function fetchUser() {
    try {
      const response = await api.getCurrentUser()
      user.value = response.data
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch user')
      errorStore.handleError(error)
      throw error
    }
  }
  
  return { user, fetchUser }
})
```

## Best Practices

1. **Always handle errors**: Use try-catch in async actions
2. **Provide loading states**: Track loading state for UI feedback
3. **Use finally blocks**: Ensure loading state is always reset
4. **Implement retry logic**: Handle transient failures
5. **Cancel requests**: Abort ongoing requests when needed
6. **Use optimistic updates**: Improve perceived performance
7. **Log errors**: Track errors for debugging

## Common Mistakes

❌ **Not handling errors**

```ts
async function fetchData() {
  const data = await api.getData() // ❌ No error handling
  this.data = data
}
```

✅ **Handle errors properly**

```ts
async function fetchData() {
  try {
    const data = await api.getData()
    this.data = data
  } catch (err) {
    this.error = err
    this.data = null
  }
}
```

❌ **Not resetting loading state**

```ts
async function fetchData() {
  this.isLoading = true
  const data = await api.getData() // ❌ May throw
  this.data = data
  // isLoading never reset on error
}
```

✅ **Use finally block**

```ts
async function fetchData() {
  this.isLoading = true
  try {
    const data = await api.getData()
    this.data = data
  } catch (err) {
    this.error = err
  } finally {
    this.isLoading = false
  }
}
```

❌ **Not aborting requests**

```ts
async function fetchData() {
  const data = await api.getData() // ❌ Can't cancel
  this.data = data
}
```

✅ **Use AbortController**

```ts
async function fetchData() {
  if (this.abortController) {
    this.abortController.abort()
  }
  
  this.abortController = new AbortController()
  
  try {
    const data = await api.getData(this.abortController.signal)
    this.data = data
  } catch (err) {
    if (err.name !== 'AbortError') {
      throw err
    }
  }
}
```
