# Store Logic Extraction

Learn how to extract and reuse logic from Pinia stores.

## Extracting to Composables

Extract reusable logic to composables:

```ts
// composables/useAsyncAction.ts
export function useAsyncAction() {
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function execute<T>(action: () => Promise<T>): Promise<T | null> {
    isLoading.value = true
    error.value = null
    
    try {
      return await action()
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Action failed')
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  return { isLoading, error, execute }
}
```

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const { isLoading, error, execute } = useAsyncAction()
  
  async function fetchUser() {
    await execute(async () => {
      const response = await api.getCurrentUser()
      user.value = response.data
    })
  }
  
  return { user, isLoading, error, fetchUser }
})
```

## Extracting CRUD Operations

Extract common CRUD operations:

```ts
// composables/useCRUD.ts
export function useCRUD<T extends { id: number }>(
  items: Ref<T[]>,
  api: {
    getAll: () => Promise<T[]>
    create: (data: Omit<T, 'id'>) => Promise<T>
    update: (id: number, data: Partial<T>) => Promise<T>
    delete: (id: number) => Promise<void>
  }
) {
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  
  async function fetchAll() {
    isLoading.value = true
    error.value = null
    
    try {
      items.value = await api.getAll()
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to fetch')
    } finally {
      isLoading.value = false
    }
  }
  
  async function create(data: Omit<T, 'id'>) {
    isLoading.value = true
    error.value = null
    
    try {
      const item = await api.create(data)
      items.value.push(item)
      return item
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to create')
      throw error.value
    } finally {
      isLoading.value = false
    }
  }
  
  async function update(id: number, data: Partial<T>) {
    isLoading.value = true
    error.value = null
    
    try {
      const item = await api.update(id, data)
      const index = items.value.findIndex(i => i.id === id)
      if (index > -1) {
        items.value[index] = item
      }
      return item
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to update')
      throw error.value
    } finally {
      isLoading.value = false
    }
  }
  
  async function remove(id: number) {
    isLoading.value = true
    error.value = null
    
    try {
      await api.delete(id)
      const index = items.value.findIndex(i => i.id === id)
      if (index > -1) {
        items.value.splice(index, 1)
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to delete')
      throw error.value
    } finally {
      isLoading.value = false
    }
  }
  
  return {
    isLoading,
    error,
    fetchAll,
    create,
    update,
    remove
  }
}
```

```ts
// stores/products.ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const {
    isLoading,
    error,
    fetchAll,
    create,
    update,
    remove
  } = useCRUD(products, {
    getAll: api.getProducts,
    create: api.createProduct,
    update: api.updateProduct,
    delete: api.deleteProduct
  })
  
  return {
    products,
    isLoading,
    error,
    fetchAll,
    create,
    update,
    remove
  }
})
```

## Extracting Pagination Logic

Extract pagination logic:

```ts
// composables/usePagination.ts
export function usePagination<T>(
  fetchFn: (page: number, pageSize: number) => Promise<T[]>
) {
  const items = ref<T[]>([])
  const currentPage = ref(1)
  const pageSize = ref(20)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  const hasMore = ref(true)
  
  async function fetchPage(page: number) {
    isLoading.value = true
    error.value = null
    
    try {
      const newItems = await fetchFn(page, pageSize.value)
      
      if (page === 1) {
        items.value = newItems
      } else {
        items.value.push(...newItems)
      }
      
      hasMore.value = newItems.length === pageSize.value
      currentPage.value = page
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to fetch')
    } finally {
      isLoading.value = false
    }
  }
  
  async function loadMore() {
    if (!isLoading.value && hasMore.value) {
      await fetchPage(currentPage.value + 1)
    }
  }
  
  async function refresh() {
    await fetchPage(1)
  }
  
  return {
    items,
    currentPage,
    pageSize,
    isLoading,
    error,
    hasMore,
    fetchPage,
    loadMore,
    refresh
  }
}
```

```ts
// stores/products.ts
export const useProductStore = defineStore('products', () => {
  const {
    items: products,
    currentPage,
    pageSize,
    isLoading,
    error,
    hasMore,
    loadMore,
    refresh
  } = usePagination((page, pageSize) => api.getProducts(page, pageSize))
  
  return {
    products,
    currentPage,
    pageSize,
    isLoading,
    error,
    hasMore,
    loadMore,
    refresh
  }
})
```

## Extracting Search Logic

Extract search logic:

```ts
// composables/useSearch.ts
export function useSearch<T>(
  items: Ref<T[]>,
  searchFn: (item: T, query: string) => boolean
) {
  const query = ref('')
  const results = ref<T[]>([])
  
  watch(
    [items, query],
    ([newItems, newQuery]) => {
      if (!newQuery) {
        results.value = newItems
        return
      }
      
      results.value = newItems.filter(item => searchFn(item, newQuery))
    },
    { immediate: true }
  )
  
  return { query, results }
}
```

```ts
// stores/products.ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const { query, results: filteredProducts } = useSearch(
    products,
    (product, query) => {
      const q = query.toLowerCase()
      return (
        product.name.toLowerCase().includes(q) ||
        product.description.toLowerCase().includes(q)
      )
    }
  )
  
  return { products, query, filteredProducts }
})
```

## Extracting Filter Logic

Extract filter logic:

```ts
// composables/useFilter.ts
export function useFilter<T>(
  items: Ref<T[]>,
  filterFn: (item: T) => boolean
) {
  const isActive = ref(false)
  const filteredItems = ref<T[]>([])
  
  watch(
    [items, isActive],
    ([newItems, newIsActive]) => {
      if (!newIsActive) {
        filteredItems.value = newItems
      } else {
        filteredItems.value = newItems.filter(filterFn)
      }
    },
    { immediate: true }
  )
  
  function toggle() {
    isActive.value = !isActive.value
  }
  
  return { isActive, filteredItems, toggle }
}
```

```ts
// stores/todos.ts
export const useTodoStore = defineStore('todos', () => {
  const todos = ref<Todo[]>([])
  
  const { isActive: showActive, filteredItems: activeTodos, toggle: toggleActive } = useFilter(
    todos,
    todo => !todo.completed
  )
  
  const { isActive: showCompleted, filteredItems: completedTodos, toggle: toggleCompleted } = useFilter(
    todos,
    todo => todo.completed
  )
  
  return {
    todos,
    showActive,
    activeTodos,
    toggleActive,
    showCompleted,
    completedTodos,
    toggleCompleted
  }
})
```

## Extracting Sort Logic

Extract sort logic:

```ts
// composables/useSort.ts
export function useSort<T>(
  items: Ref<T[]>,
  compareFn: (a: T, b: T) => number
) {
  const sortBy = ref<'asc' | 'desc'>('asc')
  const sortedItems = ref<T[]>([])
  
  watch(
    [items, sortBy],
    ([newItems, newSortBy]) => {
      const sorted = [...newItems].sort(compareFn)
      if (newSortBy === 'desc') {
        sorted.reverse()
      }
      sortedItems.value = sorted
    },
    { immediate: true }
  )
  
  function toggle() {
    sortBy.value = sortBy.value === 'asc' ? 'desc' : 'asc'
  }
  
  return { sortBy, sortedItems, toggle }
}
```

```ts
// stores/products.ts
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  
  const { sortBy, sortedItems, toggle } = useSort(
    products,
    (a, b) => a.price - b.price
  )
  
  return { products, sortBy, sortedItems, toggle }
})
```

## Extracting Validation Logic

Extract validation logic:

```ts
// composables/useValidation.ts
export function useValidation<T>(
  data: Ref<T>,
  rules: Record<keyof T, (value: any) => string | null>
) {
  const errors = ref<Partial<Record<keyof T, string>>>({})
  const isValid = computed(() => Object.values(errors.value).every(v => !v))
  
  function validate() {
    errors.value = {}
    
    for (const [key, rule] of Object.entries(rules)) {
      const error = rule(data.value[key as keyof T])
      if (error) {
        errors.value[key as keyof T] = error
      }
    }
    
    return isValid.value
  }
  
  function clearErrors() {
    errors.value = {}
  }
  
  return { errors, isValid, validate, clearErrors }
}
```

```ts
// stores/form.ts
export const useFormStore = defineStore('form', () => {
  const formData = ref<FormData>({
    name: '',
    email: '',
    password: ''
  })
  
  const { errors, isValid, validate, clearErrors } = useValidation(formData, {
    name: (value) => value ? null : 'Name is required',
    email: (value) => value.includes('@') ? null : 'Invalid email',
    password: (value) => value.length >= 8 ? null : 'Password must be at least 8 characters'
  })
  
  async function submit() {
    if (!validate()) return
    
    await api.submitForm(formData.value)
  }
  
  return { formData, errors, isValid, submit }
})
```

## Best Practices

1. **Extract common patterns**: Reusable logic in composables
2. **Keep composables focused**: Each composable should do one thing
3. **Type your composables**: Use TypeScript for type safety
4. **Test composables**: Test extracted logic independently
5. **Document composables**: Explain what each composable does
6. **Keep stores simple**: Use composables to reduce store complexity

## Common Mistakes

❌ **Not extracting common logic**

```ts
// stores/a.ts
async function fetchData() {
  this.isLoading = true
  try {
    this.data = await api.getData()
  } finally {
    this.isLoading = false
  }
}

// stores/b.ts
async function fetchData() {
  this.isLoading = true // ❌ Duplicated
  try {
    this.data = await api.getData()
  } finally {
    this.isLoading = false
  }
}
```

✅ **Extract to composable**

```ts
// composables/useAsyncAction.ts
export function useAsyncAction() {
  const isLoading = ref(false)
  
  async function execute<T>(action: () => Promise<T>) {
    isLoading.value = true
    try {
      return await action()
    } finally {
      isLoading.value = false
    }
  }
  
  return { isLoading, execute }
}

// stores/a.ts
const { isLoading, execute } = useAsyncAction()
async function fetchData() {
  await execute(() => api.getData())
}

// stores/b.ts
const { isLoading, execute } = useAsyncAction()
async function fetchData() {
  await execute(() => api.getData())
}
```

❌ **Extracting too much**

```ts
// composables/useEverything.ts
export function useEverything() {
  // ❌ Too much logic in one composable
  const isLoading = ref(false)
  const data = ref([])
  const error = ref(null)
  // ... hundreds of lines
}
```

✅ **Extract focused composables**

```ts
// composables/useAsyncAction.ts
export function useAsyncAction() {
  const isLoading = ref(false)
  async function execute<T>(action: () => Promise<T>) {
    isLoading.value = true
    try {
      return await action()
    } finally {
      isLoading.value = false
    }
  }
  return { isLoading, execute }
}

// composables/usePagination.ts
export function usePagination<T>(fetchFn: FetchFn<T>) {
  // Focused on pagination
}

// composables/useSearch.ts
export function useSearch<T>(items: Ref<T[]>, searchFn: SearchFn<T>) {
  // Focused on search
}
```

❌ **Not typing composables**

```ts
export function useComposable() {
  const data = ref(null) // ❌ No type
  return { data }
}
```

✅ **Type composables**

```ts
export function useComposable<T>() {
  const data = ref<T | null>(null) // ✅ Typed
  return { data }
}
```
