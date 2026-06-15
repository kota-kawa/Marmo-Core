# State Deep Reactivity

Learn how to handle deep reactivity with nested objects in Pinia stores.

## Understanding Deep Reactivity

Pinia stores are deeply reactive by default when using `ref()` or `reactive()`:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function setUser(newUser: User) {
    user.value = newUser
  }
  
  function updateEmail(newEmail: string) {
    if (user.value) {
      user.value.email = newEmail // ✅ Deeply reactive
    }
  }
  
  return { user, setUser, updateEmail }
})
```

## Nested Object Updates

### Direct Property Updates

```ts
export const useFormStore = defineStore('form', () => {
  const formData = ref<FormData>({
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
  })
  
  function updateUserName(name: string) {
    formData.value.user.name = name // ✅ Triggers reactivity
  }
  
  function updateCity(city: string) {
    formData.value.user.address.city = city // ✅ Triggers reactivity
  }
  
  return { formData, updateUserName, updateCity }
})
```

### Immutable Updates for Complex Objects

For complex updates, use immutable patterns:

```ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  
  function updateUser(updates: Partial<User>) {
    if (!user.value) return
    
    user.value = {
      ...user.value,
      ...updates
    }
  }
  
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
  
  return { user, updateUser, updateAddress }
})
```

## Array Mutations

### Adding Items

```ts
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

### Updating Items

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  function updateTodo(id: number, updates: Partial<Todo>) {
    const index = todos.value.findIndex(t => t.id === id)
    if (index > -1) {
      todos.value[index] = {
        ...todos.value[index],
        ...updates
      }
    }
  }
  
  function toggleTodo(id: number) {
    const todo = todos.value.find(t => t.id === id)
    if (todo) {
      todo.completed = !todo.completed // ✅ Direct mutation works
    }
  }
  
  return { todos, updateTodo, toggleTodo }
})
```

### Removing Items

```ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  function removeTodo(id: number) {
    const index = todos.value.findIndex(t => t.id === id)
    if (index > -1) {
      todos.value.splice(index, 1)
    }
  }
  
  function clearCompleted() {
    todos.value = todos.value.filter(t => !t.completed)
  }
  
  return { todos, removeTodo, clearCompleted }
})
```

## Using reactive() for Deep Objects

```ts
export const useComplexStore = defineStore('complex', () => {
  const state = reactive({
    user: {
      profile: {
        name: '',
        email: '',
        avatar: ''
      },
      settings: {
        theme: 'light',
        language: 'en'
      }
    },
    notifications: [] as Notification[]
  })
  
  function updateProfile(updates: Partial<Profile>) {
    Object.assign(state.user.profile, updates)
  }
  
  function addNotification(notification: Notification) {
    state.notifications.push(notification)
  }
  
  return { state, updateProfile, addNotification }
})
```

## Watching Deep Changes

### Watch Deep Changes

```ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  
  watch(
    items,
    (newItems) => {
      console.log('Cart changed:', newItems)
      localStorage.setItem('cart', JSON.stringify(newItems))
    },
    { deep: true }
  )
  
  return { items }
})
```

### Watch Specific Properties

```ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  
  watch(
    () => items.value.map(item => item.quantity),
    (quantities) => {
      console.log('Quantities changed:', quantities)
    }
  )
  
  return { items }
})
```

## Performance Considerations

### Avoid Unnecessary Deep Watches

```ts
// ❌ Bad: Watching entire large object
watch(
  largeObject,
  () => {
    // Expensive operation
  },
  { deep: true }
)
```

```ts
// ✅ Good: Watching specific properties
watch(
  () => largeObject.value.importantProperty,
  (newValue) => {
    // Expensive operation
  }
)
```

### Use shallowRef for Large Objects

```ts
export const useDataStore = defineStore('data', () => {
  const largeDataset = shallowRef<LargeData[]>([])
  
  function updateDataset(newData: LargeData[]) {
    largeDataset.value = newData // Only triggers when ref changes
  }
  
  function updateItem(index: number, updates: Partial<LargeData>) {
    const newData = [...largeDataset.value]
    newData[index] = { ...newData[index], ...updates }
    largeDataset.value = newData
  }
  
  return { largeDataset, updateDataset, updateItem }
})
```

## Handling Non-Reactive Properties

### Using markRaw for Non-Reactive Objects

```ts
import { markRaw } from 'vue'

export const useEditorStore = defineStore('editor', () => {
  const editor = ref<EditorInstance | null>(null)
  
  function initEditor(element: HTMLElement) {
    editor.value = markRaw(new Editor(element))
  }
  
  return { editor, initEditor }
})
```

### Using shallowRef for External Libraries

```ts
export const useMapStore = defineStore('map', () => {
  const map = shallowRef<MapInstance | null>(null)
  
  function initMap(container: HTMLElement) {
    map.value = new Map(container)
  }
  
  function addMarker(marker: Marker) {
    map.value?.addMarker(marker) // Won't trigger reactivity
  }
  
  return { map, initMap, addMarker }
})
```

## Common Patterns

### Updating Nested State with Path

```ts
export const useStore = defineStore('store', () => {
  const state = ref<ComplexState>(initialState)
  
  function updateByPath(path: string, value: any) {
    const keys = path.split('.')
    let current: any = state.value
    
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]]
    }
    
    current[keys[keys.length - 1]] = value
  }
  
  return { state, updateByPath }
})

// Usage
store.updateByPath('user.profile.name', 'John')
store.updateByPath('settings.theme', 'dark')
```

### Batch Updates

```ts
export const useStore = defineStore('store', () => {
  const state = ref<State>(initialState)
  
  function batchUpdate(updates: Partial<State>) {
    state.value = {
      ...state.value,
      ...updates
    }
  }
  
  return { state, batchUpdate }
})
```

## Best Practices

1. **Use ref() by default**: Better TypeScript inference and destructuring
2. **Be careful with deep watches**: Can impact performance with large objects
3. **Use immutable updates**: For complex nested objects
4. **Use markRaw/shallowRef**: For non-reactive objects and external libraries
5. **Watch specific properties**: Instead of entire objects
6. **Test reactivity**: Ensure changes trigger updates as expected

## Common Mistakes

❌ **Not triggering reactivity with array methods**

```ts
function updateItems() {
  this.items[0].name = 'New Name' // ❌ May not trigger in some cases
}
```

✅ **Use proper array methods**

```ts
function updateItems() {
  this.items = [...this.items] // ✅ Triggers reactivity
}
```

❌ **Replacing reactive object breaks reactivity**

```ts
const state = reactive({ count: 0 })
state = { count: 1 } // ❌ Breaks reactivity
```

✅ **Update properties instead**

```ts
const state = reactive({ count: 0 })
state.count = 1 // ✅ Works
```

❌ **Deep watching large objects**

```ts
watch(
  largeObject,
  () => {
    // Expensive operation
  },
  { deep: true }
)
```

✅ **Watch specific properties**

```ts
watch(
  () => largeObject.value.importantProperty,
  () => {
    // Expensive operation
  }
)
```

❌ **Not using markRaw for external libraries**

```ts
const editor = ref(new Editor())
editor.value.method() // ❌ May cause issues
```

✅ **Use markRaw for external instances**

```ts
const editor = ref(markRaw(new Editor()))
editor.value.method() // ✅ Works correctly
```
