# State Persistence

Learn how to persist Pinia store state to localStorage, sessionStorage, or other storage mechanisms.

## Basic localStorage Persistence

Persist state to localStorage:

```ts
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<'light' | 'dark'>('light')
  const language = ref('en')
  
  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
  }
  
  function setLanguage(newLanguage: string) {
    language.value = newLanguage
  }
  
  watch(
    () => ({ theme: theme.value, language: language.value }),
    (state) => {
      localStorage.setItem('preferences', JSON.stringify(state))
    },
    { deep: true }
  )
  
  function $hydrate() {
    const saved = localStorage.getItem('preferences')
    if (saved) {
      const state = JSON.parse(saved)
      theme.value = state.theme
      language.value = state.language
    }
  }
  
  return { theme, language, setTheme, setLanguage, $hydrate }
})
```

## Using @vueuse/core useLocalStorage

Simplify with VueUse:

```ts
import { defineStore } from 'pinia'
import { useLocalStorage } from '@vueuse/core'

export const usePreferencesStore = defineStore('preferences', () => {
  const theme = useLocalStorage('theme', 'light' as 'light' | 'dark')
  const language = useLocalStorage('language', 'en')
  
  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
  }
  
  function setLanguage(newLanguage: string) {
    language.value = newLanguage
  }
  
  return { theme, language, setTheme, setLanguage }
})
```

## Selective Persistence

Persist only specific properties:

```ts
export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const coupon = ref<string | null>(null)
  const isProcessing = ref(false)
  
  watch(
    () => ({ items: items.value, coupon: coupon.value }),
    (state) => {
      localStorage.setItem('cart', JSON.stringify(state))
    },
    { deep: true }
  )
  
  function $hydrate() {
    const saved = localStorage.getItem('cart')
    if (saved) {
      const state = JSON.parse(saved)
      items.value = state.items || []
      coupon.value = state.coupon || null
    }
  }
  
  function clear() {
    items.value = []
    coupon.value = null
    localStorage.removeItem('cart')
  }
  
  return { items, coupon, isProcessing, $hydrate, clear }
})
```

## sessionStorage Persistence

Use sessionStorage for temporary storage:

```ts
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useFormStore = defineStore('form', () => {
  const formData = ref<FormData>({
    name: '',
    email: '',
    message: ''
  })
  
  watch(
    formData,
    (data) => {
      sessionStorage.setItem('formData', JSON.stringify(data))
    },
    { deep: true }
  )
  
  function $hydrate() {
    const saved = sessionStorage.getItem('formData')
    if (saved) {
      formData.value = JSON.parse(saved)
    }
  }
  
  function clear() {
    formData.value = { name: '', email: '', message: '' }
    sessionStorage.removeItem('formData')
  }
  
  return { formData, $hydrate, clear }
})
```

## Custom Storage Adapter

Create a custom storage adapter:

```ts
// utils/storage.ts
export interface StorageAdapter {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export const cookieStorage: StorageAdapter = {
  getItem(key: string) {
    const match = document.cookie.match(new RegExp(`(^| )${key}=([^;]*)`))
    return match ? decodeURIComponent(match[2]) : null
  },
  setItem(key: string, value: string) {
    document.cookie = `${key}=${encodeURIComponent(value)}; path=/; max-age=31536000`
  },
  removeItem(key: string) {
    document.cookie = `${key}=; path=/; max-age=0`
  }
}

export const indexedDBStorage: StorageAdapter = {
  async getItem(key: string) {
    const db = await openDB('pinia-store', 1)
    const result = await db.get('state', key)
    return result ? JSON.stringify(result) : null
  },
  async setItem(key: string, value: string) {
    const db = await openDB('pinia-store', 1)
    await db.put('state', JSON.parse(value), key)
  },
  async removeItem(key: string) {
    const db = await openDB('pinia-store', 1)
    await db.delete('state', key)
  }
}
```

```ts
// stores/auth.ts
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { cookieStorage } from '@/utils/storage'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  
  watch(
    token,
    (value) => {
      if (value) {
        cookieStorage.setItem('token', value)
      } else {
        cookieStorage.removeItem('token')
      }
    }
  )
  
  function $hydrate() {
    token.value = cookieStorage.getItem('token')
  }
  
  return { token, $hydrate }
})
```

## Debounced Persistence

Debounce writes to improve performance:

```ts
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { debounce } from 'lodash-es'

export const useEditorStore = defineStore('editor', () => {
  const content = ref('')
  
  const saveToStorage = debounce((value: string) => {
    localStorage.setItem('editor-content', value)
  }, 1000)
  
  watch(content, saveToStorage)
  
  function $hydrate() {
    const saved = localStorage.getItem('editor-content')
    if (saved) {
      content.value = saved
    }
  }
  
  return { content, $hydrate }
})
```

## Encryption for Sensitive Data

Encrypt sensitive data before storing:

```ts
// utils/crypto.ts
export function encrypt(data: string, key: string): string {
  return btoa(data + key)
}

export function decrypt(data: string, key: string): string {
  const decoded = atob(data)
  return decoded.slice(0, -key.length)
}
```

```ts
// stores/auth.ts
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { encrypt, decrypt } from '@/utils/crypto'

const ENCRYPTION_KEY = 'my-secret-key'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  
  watch(
    token,
    (value) => {
      if (value) {
        localStorage.setItem('auth-token', encrypt(value, ENCRYPTION_KEY))
      } else {
        localStorage.removeItem('auth-token')
      }
    }
  )
  
  function $hydrate() {
    const saved = localStorage.getItem('auth-token')
    if (saved) {
      try {
        token.value = decrypt(saved, ENCRYPTION_KEY)
      } catch {
        token.value = null
      }
    }
  }
  
  return { token, $hydrate }
})
```

## Compression for Large Data

Compress large datasets:

```ts
// utils/compression.ts
import { compressToUTF16, decompressFromUTF16 } from 'lz-string'

export function compress(data: string): string {
  return compressToUTF16(data)
}

export function decompress(data: string): string {
  return decompressFromUTF16(data)
}
```

```ts
// stores/data.ts
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { compress, decompress } from '@/utils/compression'

export const useDataStore = defineStore('data', () => {
  const largeDataset = ref<LargeData[]>([])
  
  watch(
    largeDataset,
    (value) => {
      const compressed = compress(JSON.stringify(value))
      localStorage.setItem('large-dataset', compressed)
    },
    { deep: true }
  )
  
  function $hydrate() {
    const saved = localStorage.getItem('large-dataset')
    if (saved) {
      try {
        largeDataset.value = JSON.parse(decompress(saved))
      } catch {
        largeDataset.value = []
      }
    }
  }
  
  return { largeDataset, $hydrate }
})
```

## Versioning for Schema Changes

Handle schema changes over time:

```ts
// stores/preferences.ts
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

interface PreferencesV1 {
  theme: 'light' | 'dark'
}

interface PreferencesV2 {
  theme: 'light' | 'dark'
  language: string
}

const CURRENT_VERSION = 2

export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<'light' | 'dark'>('light')
  const language = ref('en')
  
  function migrate(data: any, version: number) {
    if (version === 1) {
      const v1Data = data as PreferencesV1
      return {
        theme: v1Data.theme,
        language: 'en'
      }
    }
    return data
  }
  
  watch(
    () => ({ theme: theme.value, language: language.value }),
    (state) => {
      const data = {
        version: CURRENT_VERSION,
        ...state
      }
      localStorage.setItem('preferences', JSON.stringify(data))
    },
    { deep: true }
  )
  
  function $hydrate() {
    const saved = localStorage.getItem('preferences')
    if (saved) {
      try {
        const data = JSON.parse(saved)
        const version = data.version || 1
        
        if (version < CURRENT_VERSION) {
          const migrated = migrate(data, version)
          theme.value = migrated.theme
          language.value = migrated.language
        } else {
          theme.value = data.theme
          language.value = data.language
        }
      } catch {
        theme.value = 'light'
        language.value = 'en'
      }
    }
  }
  
  return { theme, language, $hydrate }
})
```

## Hydration on App Start

Hydrate stores when app starts:

```ts
// main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { usePreferencesStore } from './stores/preferences'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

const preferencesStore = usePreferencesStore()
preferencesStore.$hydrate()

app.mount('#app')
```

## Best Practices

1. **Use selective persistence**: Only persist what's needed
2. **Handle errors**: Always try-catch when reading from storage
3. **Version your data**: Handle schema changes gracefully
4. **Encrypt sensitive data**: Don't store plain text passwords/tokens
5. **Compress large data**: Use compression for large datasets
6. **Debounce writes**: Improve performance with debouncing
7. **Clear on logout**: Remove sensitive data on logout

## Common Mistakes

❌ **Persisting everything**

```ts
watch(
  state,
  (value) => {
    localStorage.setItem('store', JSON.stringify(value))
  },
  { deep: true }
)
```

✅ **Persist only what's needed**

```ts
watch(
  () => ({ items: state.items, coupon: state.coupon }),
  (value) => {
    localStorage.setItem('cart', JSON.stringify(value))
  },
  { deep: true }
)
```

❌ **Not handling errors**

```ts
function $hydrate() {
  const saved = localStorage.getItem('data')
  const data = JSON.parse(saved) // ❌ Can throw
}
```

✅ **Handle errors gracefully**

```ts
function $hydrate() {
  const saved = localStorage.getItem('data')
  if (saved) {
    try {
      const data = JSON.parse(saved)
      state.value = data
    } catch {
      state.value = initialState
    }
  }
}
```

❌ **Storing sensitive data plain**

```ts
localStorage.setItem('token', token.value) // ❌ Security risk
```

✅ **Encrypt sensitive data**

```ts
localStorage.setItem('token', encrypt(token.value, key)) // ✅ Secure
```
