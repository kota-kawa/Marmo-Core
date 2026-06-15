# Setup Stores vs Options Stores

Pinia supports two store definition styles: setup stores (Composition API) and options stores. Setup stores are recommended for new projects.

## Setup Stores (Recommended)

Setup stores use Vue's Composition API functions:

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  const doubleCount = computed(() => count.value * 2)
  
  function increment() {
    count.value++
  }
  
  return { count, doubleCount, increment }
})
```

### Advantages

- **Better TypeScript inference**: Full automatic type inference
- **More flexible**: Can use any Composition API function
- **Easier to test**: Pure functions that can be tested in isolation
- **Composable**: Logic can be extracted into reusable composables
- **Consistent with Vue 3**: Same patterns as `<script setup>` components

### When to Use

- New Vue 3 projects
- Projects using TypeScript
- Complex stores with multiple concerns
- Stores that need to use external composables

## Options Stores

Options stores use an object-based API similar to Vuex:

```ts
import { defineStore } from 'pinia'

export const useCounterStore = defineStore('counter', {
  state: () => ({
    count: 0
  }),
  getters: {
    doubleCount: (state) => state.count * 2
  },
  actions: {
    increment() {
      this.count++
    }
  }
})
```

### Advantages

- **Familiar to Vuex users**: Similar structure to Vuex
- **Explicit structure**: Clear separation of state, getters, actions
- **Simpler for basic stores**: Less boilerplate for simple cases
- **Better for migration**: Easier to migrate from Vuex

### When to Use

- Migrating from Vuex
- Simple stores without complex logic
- Teams more comfortable with options API
- Projects without TypeScript

## Comparison

| Feature | Setup Stores | Options Stores |
|---------|--------------|----------------|
| TypeScript Inference | ✅ Full automatic | ⚠️ Requires manual typing |
| Flexibility | ✅ Full Composition API | ❌ Limited to state/getters/actions |
| Code Organization | ✅ Logical grouping | ✅ Explicit sections |
| Learning Curve | ⚠️ Requires Composition API | ✅ Familiar to Vuex users |
| Testing | ✅ Easy to test functions | ⚠️ Requires store instance |
| Composability | ✅ Can use composables | ❌ Limited composability |
| Migration from Vuex | ❌ Different patterns | ✅ Similar structure |

## TypeScript Comparison

### Setup Store - Automatic Inference

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => user.value !== null)
  
  async function login(email: string, password: string) {
    const response = await api.login({ email, password })
    user.value = response.data
  }
  
  return { user, isAuthenticated, login }
})

// Types are automatically inferred:
// user: Ref<User | null>
// isAuthenticated: ComputedRef<boolean>
// login: (email: string, password: string) => Promise<void>
```

### Options Store - Manual Typing Required

```ts
import { defineStore } from 'pinia'

interface UserState {
  user: User | null
}

interface UserGetters {
  isAuthenticated: boolean
}

interface UserActions {
  login: (email: string, password: string) => Promise<void>
}

export const useUserStore = defineStore<
  string,
  UserState,
  UserGetters,
  UserActions
>('user', {
  state: (): UserState => ({
    user: null
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null
  },
  actions: {
    async login(email: string, password: string) {
      const response = await api.login({ email, password })
      this.user = response.data
    }
  }
})
```

## Complex Logic Comparison

### Setup Store - Clean and Composable

```ts
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useLocalStorage } from '@vueuse/core'

export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const coupon = useLocalStorage('coupon', null as string | null)
  
  const subtotal = computed(() => 
    items.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
  )
  
  const discount = computed(() => {
    if (!coupon.value) return 0
    return subtotal.value * 0.1 // 10% discount
  })
  
  const total = computed(() => subtotal.value - discount.value)
  
  watch(items, (newItems) => {
    analytics.track('cart_updated', { itemCount: newItems.length })
  }, { deep: true })
  
  function addItem(product: Product) {
    const existing = items.value.find(i => i.id === product.id)
    if (existing) {
      existing.quantity++
    } else {
      items.value.push({ ...product, quantity: 1 })
    }
  }
  
  function removeItem(id: number) {
    const index = items.value.findIndex(i => i.id === id)
    if (index > -1) {
      items.value.splice(index, 1)
    }
  }
  
  function clear() {
    items.value = []
    coupon.value = null
  }
  
  return { items, coupon, subtotal, discount, total, addItem, removeItem, clear }
})
```

### Options Store - More Verbose

```ts
import { defineStore } from 'pinia'

interface CartState {
  items: CartItem[]
  coupon: string | null
}

interface CartGetters {
  subtotal: number
  discount: number
  total: number
}

interface CartActions {
  addItem: (product: Product) => void
  removeItem: (id: number) => void
  clear: () => void
}

export const useCartStore = defineStore<
  string,
  CartState,
  CartGetters,
  CartActions
>('cart', {
  state: (): CartState => ({
    items: [],
    coupon: localStorage.getItem('coupon')
  }),
  getters: {
    subtotal: (state) => 
      state.items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    discount: (state) => {
      if (!state.coupon) return 0
      return state.items.reduce((sum, item) => sum + item.price * item.quantity, 0) * 0.1
    },
    total: (state) => {
      const subtotal = state.items.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const discount = state.coupon ? subtotal * 0.1 : 0
      return subtotal - discount
    }
  },
  actions: {
    addItem(product: Product) {
      const existing = this.items.find(i => i.id === product.id)
      if (existing) {
        existing.quantity++
      } else {
        this.items.push({ ...product, quantity: 1 })
      }
    },
    removeItem(id: number) {
      const index = this.items.findIndex(i => i.id === id)
      if (index > -1) {
        this.items.splice(index, 1)
      }
    },
    clear() {
      this.items = []
      this.coupon = null
      localStorage.removeItem('coupon')
    }
  }
})
```

## Migration Path

If you have options stores and want to migrate to setup stores:

```ts
// Before (Options Store)
export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    isLoading: false
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null
  },
  actions: {
    async login(email: string, password: string) {
      this.isLoading = true
      try {
        const response = await api.login({ email, password })
        this.user = response.data
      } finally {
        this.isLoading = false
      }
    }
  }
})

// After (Setup Store)
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const isAuthenticated = computed(() => user.value !== null)
  
  async function login(email: string, password: string) {
    isLoading.value = true
    try {
      const response = await api.login({ email, password })
      user.value = response.data
    } finally {
      isLoading.value = false
    }
  }
  
  return { user, isLoading, isAuthenticated, login }
})
```

## Recommendation

**Use setup stores for:**
- New projects
- TypeScript projects
- Complex stores with multiple concerns
- Stores using external composables

**Use options stores for:**
- Migrating from Vuex
- Simple, straightforward stores
- Teams more comfortable with options API
- Projects without TypeScript
