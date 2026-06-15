# Using Stores in Components

Learn how to use Pinia stores in Vue components with proper reactivity and best practices.

## Basic Usage

Import and use a store in a component:

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

## Direct Access vs storeToRefs

You can access store properties directly or use `storeToRefs` to preserve reactivity when destructuring.

### Direct Access

```vue
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()
</script>

<template>
  <div>
    <p>{{ counter.count }}</p>
    <button @click="counter.increment">Increment</button>
  </div>
</template>
```

### Using storeToRefs

Use `storeToRefs` when you need to destructure while keeping reactivity:

```vue
<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()
const { count, doubleCount } = storeToRefs(counter)
const { increment } = counter // Actions don't need storeToRefs
</script>

<template>
  <div>
    <p>Count: {{ count }}</p>
    <p>Double: {{ doubleCount }}</p>
    <button @click="increment">Increment</button>
  </div>
</template>
```

**Why use storeToRefs?**

Without `storeToRefs`, destructuring loses reactivity:

```vue
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()
const { count } = counter // ❌ Loses reactivity!
</script>

<template>
  <div>
    <p>{{ count }}</p>
    <button @click="counter.increment">Increment</button>
  </div>
</template>
```

The count won't update in the template because it's no longer reactive.

## Reading State

### In Templates

```vue
<template>
  <div>
    <p>User: {{ authStore.user?.name }}</p>
    <p>Authenticated: {{ authStore.isAuthenticated }}</p>
  </div>
</template>
```

### In Script

```vue
<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

function checkAuth() {
  if (authStore.isAuthenticated) {
    console.log('User is authenticated:', authStore.user)
  }
}
</script>
```

### With Computed

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const greeting = computed(() => {
  return authStore.user 
    ? `Hello, ${authStore.user.name}!`
    : 'Please log in'
})
</script>

<template>
  <div>
    <h1>{{ greeting }}</h1>
  </div>
</template>
```

## Mutating State

### Calling Actions

```vue
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()
</script>

<template>
  <div>
    <p>Count: {{ counter.count }}</p>
    <button @click="counter.increment">Increment</button>
    <button @click="counter.decrement">Decrement</button>
    <button @click="counter.$reset()">Reset</button>
  </div>
</template>
```

### Direct Mutation (Not Recommended)

While you can directly mutate state, it's better to use actions:

```vue
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()

function setValue(value: number) {
  counter.count = value // Direct mutation
}
</script>
```

**Why use actions?**

- Encapsulation and validation
- Easier to test
- Better for debugging
- Consistent API

```ts
// store
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  
  function setCount(value: number) {
    if (value >= 0) { // Validation
      count.value = value
    }
  }
  
  return { count, setCount }
})
```

## Watching Store Changes

### Using watch

```vue
<script setup lang="ts">
import { watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) {
      console.log('User logged in')
    } else {
      console.log('User logged out')
    }
  }
)
</script>
```

### Using watchEffect

```vue
<script setup lang="ts">
import { watchEffect } from 'vue'
import { useCartStore } from '@/stores/cart'

const cartStore = useCartStore()

watchEffect(() => {
  // Automatically tracks dependencies
  if (cartStore.items.length > 0) {
    document.title = `Cart (${cartStore.items.length})`
  } else {
    document.title = 'My Store'
  }
})
</script>
```

## Multiple Stores

You can use multiple stores in a single component:

```vue
<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const authStore = useAuthStore()
const cartStore = useCartStore()

const { user, isAuthenticated } = storeToRefs(authStore)
const { items, total } = storeToRefs(cartStore)

const { login, logout } = authStore
const { addItem, removeItem } = cartStore
</script>

<template>
  <div>
    <header v-if="isAuthenticated">
      <p>Welcome, {{ user?.name }}</p>
      <button @click="logout">Logout</button>
    </header>
    
    <main>
      <div v-for="item in items" :key="item.id">
        <h3>{{ item.name }}</h3>
        <p>Price: {{ item.price }}</p>
        <button @click="removeItem(item.id)">Remove</button>
      </div>
      
      <p>Total: {{ total }}</p>
    </main>
  </div>
</template>
```

## Conditional Store Usage

Only use a store when needed:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const needsAuth = computed(() => {
  return authStore.isAuthenticated && authStore.user?.role === 'admin'
})

const adminStore = computed(() => {
  if (!needsAuth.value) return null
  return useAdminStore()
})
</script>

<template>
  <div>
    <p v-if="needsAuth && adminStore">
      Admin panel: {{ adminStore.dashboardData }}
    </p>
  </div>
</template>
```

## Store in Composables

You can use stores inside composables:

```ts
// composables/useCartBadge.ts
import { computed } from 'vue'
import { useCartStore } from '@/stores/cart'

export function useCartBadge() {
  const cartStore = useCartStore()
  
  const badgeCount = computed(() => {
    return cartStore.items.reduce((sum, item) => sum + item.quantity, 0)
  })
  
  const showBadge = computed(() => badgeCount.value > 0)
  
  return { badgeCount, showBadge }
}
```

```vue
<script setup lang="ts">
import { useCartBadge } from '@/composables/useCartBadge'

const { badgeCount, showBadge } = useCartBadge()
</script>

<template>
  <div>
    <button>Cart</button>
    <span v-if="showBadge" class="badge">{{ badgeCount }}</span>
  </div>
</template>
```

## Performance Optimization

### Lazy Store Initialization

Stores are created when first accessed. This is fine for most cases, but you can optimize:

```vue
<script setup lang="ts">
import { shallowRef } from 'vue'
import { useHeavyStore } from '@/stores/heavy'

const heavyStore = shallowRef(null)

function initializeStore() {
  if (!heavyStore.value) {
    heavyStore.value = useHeavyStore()
  }
  return heavyStore.value
}
</script>

<template>
  <div>
    <button @click="initializeStore">Load Heavy Data</button>
    <div v-if="heavyStore">
      {{ heavyStore.data }}
    </div>
  </div>
</template>
```

### Avoiding Unnecessary Re-renders

Use `storeToRefs` selectively:

```vue
<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useCartStore } from '@/stores/cart'

const cartStore = useCartStore()

// Only destructure what you need
const { total } = storeToRefs(cartStore)
// Keep items as store reference to avoid reactivity overhead
</script>

<template>
  <div>
    <p>Total: {{ total }}</p>
    <div v-for="item in cartStore.items" :key="item.id">
      {{ item.name }}
    </div>
  </div>
</template>
```

## Best Practices

1. **Use storeToRefs for destructuring**: Preserves reactivity
2. **Don't destructure actions**: Actions don't need storeToRefs
3. **Call actions, don't mutate directly**: Better encapsulation
4. **Watch store changes when needed**: For side effects
5. **Use multiple stores**: Keep stores focused and composable
6. **Lazy load heavy stores**: For performance optimization

## Common Mistakes

❌ **Destructuring without storeToRefs**

```vue
<script setup lang="ts">
const counter = useCounterStore()
const { count } = counter // ❌ Loses reactivity
</script>
```

✅ **Use storeToRefs**

```vue
<script setup lang="ts">
import { storeToRefs } from 'pinia'
const counter = useCounterStore()
const { count } = storeToRefs(counter) // ✅ Keeps reactivity
</script>
```

❌ **Mutating state directly**

```vue
<script setup lang="ts">
const counter = useCounterStore()
counter.count = 10 // ❌ Bypasses validation
</script>
```

✅ **Use actions**

```vue
<script setup lang="ts">
const counter = useCounterStore()
counter.setCount(10) // ✅ Includes validation
</script>
```

❌ **Creating store in computed**

```vue
<script setup lang="ts">
const store = computed(() => useCounterStore()) // ❌ Creates new instance
</script>
```

✅ **Create store at top level**

```vue
<script setup lang="ts">
const store = useCounterStore() // ✅ Single instance
</script>
```
