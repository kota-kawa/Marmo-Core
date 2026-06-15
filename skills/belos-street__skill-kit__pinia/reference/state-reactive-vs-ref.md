# State: Reactive vs Ref

Learn when to use `ref()` vs `reactive()` for Pinia store state.

## Using ref()

`ref()` is the recommended approach for Pinia stores:

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
  
  return { count, name, doubleCount, increment }
})
```

### Advantages of ref()

- **Consistent with components**: Same pattern as Vue components
- **Explicit reactivity**: Clear when accessing `.value`
- **Better TypeScript inference**: Automatic type inference
- **Easier to destructure**: Works with `storeToRefs`
- **Works with primitives**: Can store strings, numbers, booleans

## Using reactive()

`reactive()` works for objects but has limitations:

```ts
import { defineStore } from 'pinia'
import { reactive, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const state = reactive({
    user: null as User | null,
    isLoading: false,
    error: null as Error | null
  })
  
  const isAuthenticated = computed(() => state.user !== null)
  
  async function login(credentials: Credentials) {
    state.isLoading = true
    try {
      const response = await api.login(credentials)
      state.user = response.user
    } catch (err) {
      state.error = err instanceof Error ? err : new Error('Login failed')
    } finally {
      state.isLoading = false
    }
  }
  
  return { state, isAuthenticated, login }
})
```

### Limitations of reactive()

- **Cannot destructure**: Loses reactivity
- **Cannot replace entire object**: Breaks reactivity
- **No primitive values**: Only works with objects
- **TypeScript issues**: Less accurate type inference

## Comparison Examples

### Primitive Values

```ts
// ✅ Good: Using ref for primitives
export const useStore = defineStore('store', () => {
  const count = ref(0)
  const name = ref('Eduardo')
  const isActive = ref(true)
  
  return { count, name, isActive }
})
```

```ts
// ❌ Bad: Cannot use reactive for primitives
export const useStore = defineStore('store', () => {
  const state = reactive({
    count: 0,
    name: 'Eduardo',
    isActive: true
  })
  
  return { state }
})
```

### Object State

```ts
// ✅ Good: Using ref for objects
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function setUser(newUser: User) {
    user.value = newUser
  }
  
  return { user, setUser }
})
```

```ts
// ✅ Also Good: Using reactive for objects
export const useUserStore = defineStore('user', () => {
  const state = reactive({
    user: null as User | null
  })
  
  function setUser(newUser: User) {
    state.user = newUser
  }
  
  return { state, setUser }
})
```

### Array State

```ts
// ✅ Good: Using ref for arrays
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  function addTodo(text: string) {
    todos.value.push({
      id: Date.now(),
      text,
      completed: false
    })
  }
  
  return { todos, addTodo }
})
```

```ts
// ✅ Also Good: Using reactive for arrays
export const useTodoStore = defineStore('todos', () => {
  const state = reactive({
    todos: [] as Todo[]
  })
  
  function addTodo(text: string) {
    state.todos.push({
      id: Date.now(),
      text,
      completed: false
    })
  }
  
  return { state, addTodo }
})
```

## Destructuring Issues

### With ref()

```ts
// ✅ Works with storeToRefs
export const useStore = defineStore('store', () => {
  const count = ref(0)
  const name = ref('Eduardo')
  
  return { count, name }
})
```

```vue
<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useStore } from '@/stores/store'

const store = useStore()
const { count, name } = storeToRefs(store) // ✅ Keeps reactivity
</script>
```

### With reactive()

```ts
// ❌ Cannot destructure reactive objects
export const useStore = defineStore('store', () => {
  const state = reactive({
    count: 0,
    name: 'Eduardo'
  })
  
  return { state }
})
```

```vue
<script setup lang="ts">
import { useStore } from '@/stores/store'

const store = useStore()
const { count, name } = store.state // ❌ Loses reactivity
</script>
```

## Replacing State

### With ref()

```ts
// ✅ Can replace entire ref
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function setUser(newUser: User) {
    user.value = newUser // ✅ Works
  }
  
  function resetUser() {
    user.value = null // ✅ Works
  }
  
  return { user, setUser, resetUser }
})
```

### With reactive()

```ts
// ❌ Cannot replace entire reactive object
export const useUserStore = defineStore('user', () => {
  const state = reactive({
    user: null as User | null
  })
  
  function setUser(newUser: User) {
    state.user = newUser // ✅ Works for properties
  }
  
  function resetUser() {
    state.user = null // ✅ Works for properties
  }
  
  function replaceState(newState: { user: User | null }) {
    state = newState // ❌ Breaks reactivity
  }
  
  return { state, setUser, resetUser }
})
```

## Mixed Approach

Use `ref()` for most state, `reactive()` for complex nested objects:

```ts
export const useFormStore = defineStore('form', () => {
  const formData = ref<FormData>({
    name: '',
    email: '',
    address: {
      street: '',
      city: '',
      country: ''
    }
  })
  
  const validation = reactive({
    errors: {} as Record<string, string>,
    isValid: false
  })
  
  function validate() {
    validation.errors = {}
    validation.isValid = true
    
    if (!formData.value.name) {
      validation.errors.name = 'Name is required'
      validation.isValid = false
    }
    
    if (!formData.value.email) {
      validation.errors.email = 'Email is required'
      validation.isValid = false
    }
  }
  
  return { formData, validation, validate }
})
```

## TypeScript Comparison

### With ref() - Better Inference

```ts
export const useStore = defineStore('store', () => {
  const count = ref(0)
  const name = ref('Eduardo')
  
  // Types are automatically inferred:
  // count: Ref<number>
  // name: Ref<string>
  
  return { count, name }
})
```

### With reactive() - Manual Typing

```ts
export const useStore = defineStore('store', () => {
  const state = reactive({
    count: 0,
    name: 'Eduardo'
  })
  
  // Type is inferred but less flexible:
  // state: { count: number; name: string }
  
  return { state }
})
```

## Performance Considerations

Both `ref()` and `reactive()` have similar performance. Choose based on:

1. **Use ref() when**:
   - You need to store primitive values
   - You want to destructure with `storeToRefs`
   - You need to replace the entire object
   - You want better TypeScript inference

2. **Use reactive() when**:
   - You have complex nested objects
   - You don't need to destructure
   - You want to access properties without `.value`
   - You're migrating from Options API

## Best Practices

1. **Prefer ref()**: Default to using `ref()` for store state
2. **Use ref() for primitives**: Always use `ref()` for strings, numbers, booleans
3. **Use ref() for arrays**: Easier to replace entire arrays
4. **Use reactive() for nested objects**: When you have deeply nested structures
5. **Be consistent**: Choose one pattern and stick with it
6. **Use storeToRefs**: When destructuring refs from stores

## Common Mistakes

❌ **Using reactive() for primitives**

```ts
const state = reactive({
  count: 0,
  name: 'Eduardo'
})

// Accessing requires state.count, state.name
```

✅ **Using ref() for primitives**

```ts
const count = ref(0)
const name = ref('Eduardo')

// Accessing requires count.value, name.value
```

❌ **Destructuring reactive() without toRefs()**

```ts
const store = useStore()
const { count, name } = store.state // ❌ Loses reactivity
```

✅ **Using storeToRefs() with ref()**

```ts
import { storeToRefs } from 'pinia'

const store = useStore()
const { count, name } = storeToRefs(store) // ✅ Keeps reactivity
```

❌ **Replacing reactive() object**

```ts
const state = reactive({ count: 0 })
state = { count: 1 } // ❌ Breaks reactivity
```

✅ **Replacing ref() value**

```ts
const count = ref(0)
count.value = 1 // ✅ Works
```

## Recommendation

**Use ref() as the default choice** for Pinia stores:

```ts
export const useStore = defineStore('store', () => {
  const count = ref(0)
  const name = ref('Eduardo')
  const items = ref<Item[]>([])
  
  return { count, name, items }
})
```

Only use `reactive()` when you have a specific reason, such as:
- Deeply nested objects where `.value` access is cumbersome
- Migrating from Options API stores
- Working with external libraries that expect reactive objects
