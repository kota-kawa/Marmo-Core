# TypeScript Getters Actions Typing

Learn how to type Pinia getters and actions with TypeScript.

## Typing Getters

Getters are automatically typed with TypeScript:

```ts
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  
  const doubleCount = computed(() => count.value * 2)
  const tripleCount = computed(() => count.value * 3)
  
  return { count, doubleCount, tripleCount }
})

// Types are automatically inferred:
// count: Ref<number>
// doubleCount: ComputedRef<number>
// tripleCount: ComputedRef<number>
```

## Explicit Getter Types

Explicitly type getters when needed:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  const isAuthenticated: ComputedRef<boolean> = computed(() => 
    user.value !== null
  )
  
  const userName: ComputedRef<string> = computed(() => 
    user.value?.name || 'Guest'
  )
  
  return { user, isAuthenticated, userName }
})
```

## Typing Actions with Parameters

Type action parameters:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function setUser(newUser: User) {
    user.value = newUser
  }
  
  function updateUser(updates: Partial<User>) {
    if (!user.value) return
    
    user.value = {
      ...user.value,
      ...updates
    }
  }
  
  function updateName(name: string) {
    if (!user.value) return
    
    user.value = {
      ...user.value,
      name
    }
  }
  
  return { user, setUser, updateUser, updateName }
})
```

## Typing Async Actions

Type async actions with Promise return types:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function fetchUser(): Promise<void> {
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
  
  async function updateUser(updates: Partial<User>): Promise<User> {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await api.updateUser(user.value!.id, updates)
      user.value = response.data
      return response.data
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to update user')
      throw error.value
    } finally {
      isLoading.value = false
    }
  }
  
  return { user, isLoading, error, fetchUser, updateUser }
})
```

## Typing Actions with Return Values

Type action return values:

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  function addTodo(text: string): Todo {
    const todo: Todo = {
      id: Date.now(),
      text,
      completed: false,
      createdAt: new Date()
    }
    
    todos.value.push(todo)
    return todo
  }
  
  function findTodo(id: number): Todo | undefined {
    return todos.value.find(t => t.id === id)
  }
  
  function removeTodo(id: number): boolean {
    const index = todos.value.findIndex(t => t.id === id)
    if (index > -1) {
      todos.value.splice(index, 1)
      return true
    }
    return false
  }
  
  return { todos, addTodo, findTodo, removeTodo }
})
```

## Typing Getters with Arguments

Type getters that return functions:

```ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const getProductById: ComputedRef<(id: number) => Product | undefined> = computed(() => {
    return (id: number) => products.value.find(p => p.id === id)
  })
  
  const getProductsByCategory: ComputedRef<(category: string) => Product[]> = computed(() => {
    return (category: string) => products.value.filter(p => p.category === category)
  })
  
  return { products, getProductById, getProductsByCategory }
})
```

## Typing Complex Actions

Type complex actions with multiple parameters:

```ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  
  function addItem(
    product: Product,
    quantity: number = 1,
    options?: CartItemOptions
  ): CartItem {
    const existing = items.value.find(i => i.productId === product.id)
    
    if (existing) {
      existing.quantity += quantity
      return existing
    }
    
    const item: CartItem = {
      id: Date.now(),
      productId: product.id,
      product,
      quantity,
      options: options || {}
    }
    
    items.value.push(item)
    return item
  }
  
  function updateItem(
    itemId: number,
    updates: Partial<CartItem>
  ): CartItem | undefined {
    const index = items.value.findIndex(i => i.id === itemId)
    if (index > -1) {
      items.value[index] = {
        ...items.value[index],
        ...updates
      }
      return items.value[index]
    }
    return undefined
  }
  
  return { items, addItem, updateItem }
})
```

## Typing Actions with Overloads

Use function overloads for flexible actions:

```ts
export const useStore = defineStore('store', () => {
  const items = ref<Item[]>([])
  
  function filterItems(predicate: (item: Item) => boolean): Item[]
  function filterItems(category: string): Item[]
  function filterItems(category: string, predicate: (item: Item) => boolean): Item[]
  function filterItems(
    arg1: string | ((item: Item) => boolean),
    arg2?: (item: Item) => boolean
  ): Item[] {
    if (typeof arg1 === 'string') {
      const category = arg1
      const predicate = arg2 || (() => true)
      return items.value.filter(item => item.category === category && predicate(item))
    } else {
      return items.value.filter(arg1)
    }
  }
  
  return { items, filterItems }
})
```

## Typing Actions with Generic Parameters

Use generics for flexible action parameters:

```ts
export const useListStore = <T extends { id: number }>(
  id: string
) => {
  return defineStore(id, () => {
    const items = ref<T[]>([])
    
    function addItem(item: T): T {
      items.value.push(item)
      return item
    }
    
    function updateItem(id: number, updates: Partial<T>): T | undefined {
      const index = items.value.findIndex(i => i.id === id)
      if (index > -1) {
        items.value[index] = {
          ...items.value[index],
          ...updates
        }
        return items.value[index]
      }
      return undefined
    }
    
    function removeItem(id: number): boolean {
      const index = items.value.findIndex(i => i.id === id)
      if (index > -1) {
        items.value.splice(index, 1)
        return true
      }
      return false
    }
    
    return { items, addItem, updateItem, removeItem }
  })
}
```

## Typing Store Definition

Type the entire store definition:

```ts
interface UserState {
  user: User | null
  isLoading: boolean
  error: Error | null
}

interface UserGetters {
  isAuthenticated: ComputedRef<boolean>
  userName: ComputedRef<string>
}

interface UserActions {
  fetchUser: () => Promise<void>
  setUser: (user: User) => void
  updateUser: (updates: Partial<User>) => Promise<User>
  logout: () => void
}

export const useUserStore = defineStore<
  'user',
  UserState,
  UserGetters,
  UserActions
>('user', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  const isAuthenticated = computed(() => user.value !== null)
  const userName = computed(() => user.value?.name || 'Guest')
  
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
  
  function setUser(newUser: User) {
    user.value = newUser
  }
  
  async function updateUser(updates: Partial<User>) {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await api.updateUser(user.value!.id, updates)
      user.value = response.data
      return response.data
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to update user')
      throw error.value
    } finally {
      isLoading.value = false
    }
  }
  
  function logout() {
    user.value = null
  }
  
  return {
    user,
    isLoading,
    error,
    isAuthenticated,
    userName,
    fetchUser,
    setUser,
    updateUser,
    logout
  }
})
```

## Best Practices

1. **Let TypeScript infer**: Most types are inferred automatically
2. **Type complex actions**: Explicitly type complex action signatures
3. **Use generics**: For reusable store patterns
4. **Type return values**: Be explicit about what actions return
5. **Use utility types**: Leverage TypeScript's built-in types
6. **Avoid any**: Never use `any` for action parameters

## Common Mistakes

❌ **Not typing action parameters**

```ts
function setUser(user) { // ❌ Type is any
  this.user = user
}
```

✅ **Type action parameters**

```ts
function setUser(user: User) { // ✅ Type safe
  this.user = user
}
```

❌ **Not typing return values**

```ts
function findTodo(id) { // ❌ Return type is any
  return this.todos.find(t => t.id === id)
}
```

✅ **Type return values**

```ts
function findTodo(id: number): Todo | undefined { // ✅ Type safe
  return this.todos.find(t => t.id === id)
}
```

❌ **Using any for complex types**

```ts
function updateData(data: any) { // ❌ No type safety
  this.data = data
}
```

✅ **Use proper types**

```ts
function updateData(data: Partial<Data>) { // ✅ Type safe
  this.data = { ...this.data, ...data }
}
```

❌ **Not typing async actions**

```ts
async function fetchUser() { // ❌ Return type is Promise<any>
  const response = await api.getCurrentUser()
  this.user = response.data
}
```

✅ **Type async actions**

```ts
async function fetchUser(): Promise<void> { // ✅ Type safe
  const response = await api.getCurrentUser()
  this.user = response.data
}
```
