# Store Circular Dependencies

Learn how to avoid and handle circular dependencies in Pinia stores.

## Understanding Circular Dependencies

Circular dependencies occur when two or more stores depend on each other:

```ts
// ❌ Bad: Circular dependency
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const storeB = useStoreB()
  const value = computed(() => storeB.value * 2)
  return { value }
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const storeA = useStoreA()
  const value = computed(() => storeA.value / 2)
  return { value }
})
```

## Solution 1: Shared State Store

Create a shared store for common state:

```ts
// stores/shared/common.ts
export const useCommonStore = defineStore('common', () => {
  const baseValue = ref(0)
  
  return { baseValue }
})
```

```ts
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const common = useCommonStore()
  const value = computed(() => common.baseValue * 2)
  return { value }
})
```

```ts
// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const common = useCommonStore()
  const value = computed(() => common.baseValue / 2)
  return { value }
})
```

## Solution 2: Lazy Store Access

Access stores lazily inside computed or functions:

```ts
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const value = ref(0)
  
  const doubledValue = computed(() => {
    const storeB = useStoreB()
    return value.value * 2
  })
  
  return { value, doubledValue }
})
```

```ts
// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const value = ref(0)
  
  const halvedValue = computed(() => {
    const storeA = useStoreA()
    return value.value / 2
  })
  
  return { value, halvedValue }
})
```

## Solution 3: Event-Based Communication

Use events for loose coupling:

```ts
// stores/eventBus.ts
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
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const eventBus = useEventBus()
  const value = ref(0)
  
  function updateValue(newValue: number) {
    value.value = newValue
    eventBus.emit('value:updated', newValue)
  }
  
  return { value, updateValue }
})
```

```ts
// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const eventBus = useEventBus()
  const value = ref(0)
  
  function init() {
    eventBus.on('value:updated', (newValue: number) => {
      value.value = newValue / 2
    })
  }
  
  return { value, init }
})
```

## Solution 4: Dependency Injection

Inject dependencies to break cycles:

```ts
// stores/factory.ts
export function createStoreWithDeps<T>(
  id: string,
  setup: (deps: T) => SetupStore
) {
  return defineStore(id, () => {
    const deps = inject<T>('store-deps')
    return setup(deps)
  })
}
```

## Solution 5: Composable Pattern

Extract shared logic to composables:

```ts
// composables/useSharedValue.ts
export function useSharedValue() {
  const value = ref(0)
  
  function setValue(newValue: number) {
    value.value = newValue
  }
  
  return { value, setValue }
}
```

```ts
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const { value, setValue } = useSharedValue()
  
  const doubledValue = computed(() => value.value * 2)
  
  return { value, setValue, doubledValue }
})
```

```ts
// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const { value } = useSharedValue()
  
  const halvedValue = computed(() => value.value / 2)
  
  return { halvedValue }
})
```

## Solution 6: Refactor Store Structure

Refactor stores to eliminate circular dependencies:

```ts
// ❌ Before: Circular dependency
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const userStore = useUserStore()
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    userStore.setUser(response.user)
  }
  
  return { login }
})

// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const authStore = useAuthStore()
  
  const isAuthenticated = computed(() => !!authStore.token)
  
  return { isAuthenticated }
})
```

```ts
// ✅ After: Refactored
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const user = ref<User | null>(null)
  
  const isAuthenticated = computed(() => !!token.value)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    token.value = response.token
    user.value = response.user
  }
  
  return { token, user, isAuthenticated, login }
})

// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const authStore = useAuthStore()
  
  const user = computed(() => authStore.user)
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  
  return { user, isAuthenticated }
})
```

## Detecting Circular Dependencies

Use tools to detect circular dependencies:

```ts
// utils/detectCircularDeps.ts
const dependencyGraph = new Map<string, Set<string>>()

function trackDependency(from: string, to: string) {
  if (!dependencyGraph.has(from)) {
    dependencyGraph.set(from, new Set())
  }
  dependencyGraph.get(from)!.add(to)
}

function detectCircularDeps(): string[][] {
  const cycles: string[][] = []
  const visited = new Set<string>()
  const recursionStack = new Set<string>()
  
  function dfs(node: string, path: string[]) {
    visited.add(node)
    recursionStack.add(node)
    
    const dependencies = dependencyGraph.get(node) || new Set()
    for (const dep of dependencies) {
      if (!visited.has(dep)) {
        dfs(dep, [...path, dep])
      } else if (recursionStack.has(dep)) {
        const cycleStart = path.indexOf(dep)
        cycles.push([...path.slice(cycleStart), dep])
      }
    }
    
    recursionStack.delete(node)
  }
  
  for (const node of dependencyGraph.keys()) {
    if (!visited.has(node)) {
      dfs(node, [node])
    }
  }
  
  return cycles
}

export { trackDependency, detectCircularDeps }
```

## Best Practices

1. **Avoid circular dependencies**: Design stores to avoid them
2. **Use shared state**: Create shared stores for common data
3. **Lazy access**: Access stores inside computed/functions
4. **Use events**: Event-based communication for loose coupling
5. **Extract composables**: Shared logic in composables
6. **Refactor structure**: Eliminate circular dependencies by refactoring

## Common Mistakes

❌ **Creating circular dependencies**

```ts
// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const storeB = useStoreB() // ❌ Circular
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const storeA = useStoreA() // ❌ Circular
})
```

✅ **Use shared store**

```ts
// stores/shared.ts
export const useSharedStore = defineStore('shared', () => {
  const value = ref(0)
  return { value }
})

// stores/a.ts
export const useStoreA = defineStore('a', () => {
  const shared = useSharedStore() // ✅ No circular dependency
})

// stores/b.ts
export const useStoreB = defineStore('b', () => {
  const shared = useSharedStore() // ✅ No circular dependency
})
```

❌ **Accessing stores at top level**

```ts
export const useStoreA = defineStore('a', () => {
  const storeB = useStoreB() // ❌ Accessed at top level
  return {}
})
```

✅ **Access lazily**

```ts
export const useStoreA = defineStore('a', () => {
  const value = computed(() => {
    const storeB = useStoreB() // ✅ Accessed lazily
    return storeB.value
  })
  return { value }
})
```

❌ **Not detecting circular dependencies**

```ts
// No detection, circular dependencies go unnoticed
```

✅ **Detect circular dependencies**

```ts
import { trackDependency, detectCircularDeps } from '@/utils/detectCircularDeps'

trackDependency('storeA', 'storeB')
trackDependency('storeB', 'storeA')

const cycles = detectCircularDeps()
if (cycles.length > 0) {
  console.error('Circular dependencies detected:', cycles)
}
```
