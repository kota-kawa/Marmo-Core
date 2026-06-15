# Migrating from Vuex to Pinia

Learn how to migrate your Vuex store to Pinia.

## Key Differences

| Feature | Vuex | Pinia |
|---------|-------|--------|
| State | `state` object | `ref()` or `reactive()` |
| Getters | `getters` object | `computed()` |
| Mutations | `mutations` object | Direct mutations in actions |
| Actions | `actions` object | Regular functions |
| Modules | `modules` object | Separate store files |
| TypeScript | Manual typing required | Automatic type inference |

## Vuex Store Example

```ts
// store/index.ts
import { createStore } from 'vuex'

interface State {
  user: User | null
  token: string | null
}

export default createStore<State>({
  state: {
    user: null,
    token: null
  },
  getters: {
    isAuthenticated: (state) => !!state.user,
    userName: (state) => state.user?.name || 'Guest'
  },
  mutations: {
    SET_USER(state, user: User) {
      state.user = user
    },
    SET_TOKEN(state, token: string) {
      state.token = token
    },
    CLEAR_AUTH(state) {
      state.user = null
      state.token = null
    }
  },
  actions: {
    async login({ commit }, credentials: Credentials) {
      const response = await api.login(credentials)
      commit('SET_USER', response.user)
      commit('SET_TOKEN', response.token)
    },
    logout({ commit }) {
      commit('CLEAR_AUTH')
    }
  }
})
```

## Pinia Store Equivalent

```ts
// stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  
  const isAuthenticated = computed(() => !!user.value)
  const userName = computed(() => user.value?.name || 'Guest')
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
    token.value = response.token
  }
  
  function logout() {
    user.value = null
    token.value = null
  }
  
  return { user, token, isAuthenticated, userName, login, logout }
})
```

## Migration Steps

### Step 1: Install Pinia

```bash
npm install pinia
# or
yarn add pinia
# or
pnpm add pinia
```

### Step 2: Setup Pinia

```ts
// main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.mount('#app')
```

### Step 3: Convert State

```ts
// Vuex
state: {
  count: 0,
  name: 'Eduardo'
}

// Pinia
const count = ref(0)
const name = ref('Eduardo')
```

### Step 4: Convert Getters

```ts
// Vuex
getters: {
  doubleCount: (state) => state.count * 2,
  greeting: (state) => `Hello, ${state.name}!`
}

// Pinia
const doubleCount = computed(() => count.value * 2)
const greeting = computed(() => `Hello, ${name.value}!`)
```

### Step 5: Convert Mutations to Direct Assignments

```ts
// Vuex
mutations: {
  SET_COUNT(state, value) {
    state.count = value
  },
  SET_NAME(state, value) {
    state.name = value
  }
}

// Pinia (no mutations needed)
function setCount(value: number) {
  count.value = value
}

function setName(value: string) {
  name.value = value
}
```

### Step 6: Convert Actions

```ts
// Vuex
actions: {
  async increment({ commit }) {
    const response = await api.increment()
    commit('SET_COUNT', response.count)
  }
}

// Pinia
async function increment() {
  const response = await api.increment()
  count.value = response.count
}
```

## Migrating Modules

### Vuex Module

```ts
// store/modules/cart.ts
export default {
  namespaced: true,
  state: () => ({
    items: [] as CartItem[]
  }),
  getters: {
    total: (state) => 
      state.items.reduce((sum, item) => sum + item.price * item.quantity, 0)
  },
  mutations: {
    ADD_ITEM(state, item: CartItem) {
      state.items.push(item)
    },
    REMOVE_ITEM(state, id: number) {
      const index = state.items.findIndex(i => i.id === id)
      if (index > -1) {
        state.items.splice(index, 1)
      }
    }
  },
  actions: {
    async addItem({ commit }, product: Product) {
      const response = await api.addToCart(product)
      commit('ADD_ITEM', response.item)
    }
  }
}
```

### Pinia Store

```ts
// stores/cart.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  
  const total = computed(() => 
    items.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
  )
  
  function addItem(item: CartItem) {
    items.value.push(item)
  }
  
  function removeItem(id: number) {
    const index = items.value.findIndex(i => i.id === id)
    if (index > -1) {
      items.value.splice(index, 1)
    }
  }
  
  async function addToCart(product: Product) {
    const response = await api.addToCart(product)
    addItem(response.item)
  }
  
  return { items, total, addItem, removeItem, addToCart }
})
```

## Migrating Component Usage

### Vuex Usage

```vue
<script setup lang="ts">
import { useStore } from 'vuex'

const store = useStore()

const count = computed(() => store.state.count)
const doubleCount = computed(() => store.getters.doubleCount)

function increment() {
  store.dispatch('increment')
}
</script>

<template>
  <div>
    <p>Count: {{ count }}</p>
    <p>Double: {{ doubleCount }}</p>
    <button @click="increment">Increment</button>
  </div>
</template>
```

### Pinia Usage

```vue
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()
</script>

<template>
  <div>
    <p>Count: {{ counter.count }}</p>
    <p>Double: {{ counter.doubleCount }}</p>
    <button @click="counter.increment">Increment</button>
  </div>
</template>
```

## Migrating TypeScript

### Vuex TypeScript

```ts
interface State {
  user: User | null
  token: string | null
}

export default createStore<State>({
  state: {
    user: null,
    token: null
  },
  getters: {
    isAuthenticated: (state): boolean => !!state.user
  },
  mutations: {
    SET_USER(state, user: User) {
      state.user = user
    }
  },
  actions: {
    async login({ commit }, credentials: Credentials) {
      const response = await api.login(credentials)
      commit('SET_USER', response.user)
    }
  }
})
```

### Pinia TypeScript

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  
  const isAuthenticated = computed(() => !!user.value)
  
  async function login(credentials: Credentials) {
    const response = await api.login(credentials)
    user.value = response.user
    token.value = response.token
  }
  
  return { user, token, isAuthenticated, login }
})
```

## Migration Checklist

- [ ] Install Pinia
- [ ] Setup Pinia in main.ts
- [ ] Convert state to refs
- [ ] Convert getters to computed
- [ ] Remove mutations
- [ ] Update actions to use direct mutations
- [ ] Convert modules to separate stores
- [ ] Update component usage
- [ ] Update TypeScript types
- [ ] Remove Vuex from dependencies
- [ ] Test all functionality

## Best Practices

1. **Migrate gradually**: Migrate one module at a time
2. **Keep both during migration**: Run Vuex and Pinia side by side
3. **Use composition API**: Leverage Vue 3 composition API
4. **Remove mutations**: Direct mutations are simpler
5. **Type everything**: Use TypeScript for better type safety
6. **Test thoroughly**: Ensure all functionality works after migration

## Common Mistakes

❌ **Trying to use mutations in Pinia**

```ts
// ❌ Pinia doesn't have mutations
mutations: {
  SET_COUNT(state, value) {
    state.count = value
  }
}
```

✅ **Direct mutations in actions**

```ts
// ✅ Direct mutations in Pinia
function setCount(value: number) {
  count.value = value
}
```

❌ **Using namespaced modules**

```ts
// ❌ Pinia doesn't use namespacing
export default {
  namespaced: true,
  state: () => ({})
}
```

✅ **Separate stores**

```ts
// ✅ Separate stores in Pinia
export const useStore = defineStore('store', () => {
  return {}
})
```

❌ **Not using computed for getters**

```ts
// ❌ Not using computed
const doubleCount = () => count.value * 2
```

✅ **Use computed for getters**

```ts
// ✅ Using computed
const doubleCount = computed(() => count.value * 2)
```
