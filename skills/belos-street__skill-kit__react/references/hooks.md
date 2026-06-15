---
name: hooks
description: React Hooks API reference - useState, useEffect, useCallback, useMemo, useRef, useContext, useReducer, useId, useTransition
---

# Hooks

React Hooks allow function components to have access to state and other React features.

## useState

Declare a state variable that persists across re-renders.

```tsx
import { useState } from 'react'

// Basic usage
const [count, setCount] = useState<number>(0)

// With initializer function (lazy initialization)
const [data, setData] = useState(() => {
  return expensiveInitialComputation()
})

// Type inference with interface
interface User {
  name: string
  age: number
}
const [user, setUser] = useState<User | null>(null)

// SetState with function (batch updates)
setCount(prev => prev + 1)
```

## useEffect

Perform side effects after render. Runs after every render by default.

```tsx
import { useEffect, useState } from 'react'

// Basic effect - runs after every render
useEffect(() => {
  console.log('Component rendered')
})

// With cleanup - runs before unmount and before re-run
useEffect(() => {
  const subscription = api.subscribe(id)
  return () => subscription.unsubscribe()
}, [id])  // Dependency array - re-run when id changes

// Empty deps - run once on mount
useEffect(() => {
  fetchData()
}, [])  // Mount only

// Async effect
useEffect(() => {
  let cancelled = false
  
  async function fetchData() {
    const res = await fetch(`/api/${id}`)
    if (!cancelled) {
      setData(await res.json())
    }
  }
  
  fetchData()
  return () => { cancelled = true }
}, [id])
```

### useLayoutEffect

Same as useEffect but fires synchronously after DOM mutations. Use for DOM measurements.

```tsx
import { useLayoutEffect, useRef } from 'react'

function Tooltip() {
  const ref = useRef<HTMLDivElement>(null)
  
  useLayoutEffect(() => {
    const rect = ref.current?.getBoundingClientRect()
    // Synchronous DOM read, then state update
  }, [])
  
  return <div ref={ref}>Tooltip</div>
}
```

### useInsertionEffect

Fire before DOM mutations. Use for CSS-in-JS libraries.

```tsx
import { useInsertionEffect } from 'react'

useInsertionEffect(() => {
  // Inject dynamic styles before DOM updates
}, [])
```

## useCallback

Memoize a callback function to prevent unnecessary re-renders of child components.

```tsx
import { useCallback } from 'react'

interface Props {
  onSubmit: (data: string) => void
}

function Form({ onSubmit }: Props) {
  // Memoized callback - only changes when onSubmit changes
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    onSubmit('submitted')
  }, [onSubmit])
  
  return <form onSubmit={handleSubmit}>...</form>
}
```

## useMemo

Memoize a computed value to avoid expensive recalculations on every render.

```tsx
import { useMemo } from 'react'

function List({ items, filter }: { items: Item[], filter: string }) {
  // Computed value - only recalculated when items or filter changes
  const filteredItems = useMemo(() => {
    return items.filter(item => 
      item.name.toLowerCase().includes(filter.toLowerCase())
    )
  }, [items, filter])
  
  // Object memoization (often unnecessary)
  const config = useMemo(() => ({
    threshold: 0.5,
    rootMargin: '10px'
  }), [])
}
```

## useRef

Create a mutable ref object that persists across renders without triggering re-renders.

```tsx
import { useRef, useEffect } from 'react'

function Timer() {
  const count = useRef(0)
  const intervalRef = useRef<number | null>(null)
  
  useEffect(() => {
    intervalRef.current = window.setInterval(() => {
      count.current += 1
      console.log(count.current)
    }, 1000)
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])
  
  return <div>Check console</div>
}
```

### useRef with DOM

```tsx
function Input() {
  const inputRef = useRef<HTMLInputElement>(null)
  
  const focus = () => inputRef.current?.focus()
  
  return <input ref={inputRef} />
}
```

## useContext

Access a Context value without nesting Consumer components.

```tsx
import { createContext, useContext } from 'react'

const ThemeContext = createContext<string>('light')

function ThemedComponent() {
  const theme = useContext(ThemeContext)
  return <div className={theme}>Themed</div>
}

// Provider
<ThemeContext.Provider value="dark">
  <ThemedComponent />
</ThemeContext.Provider>
```

## useReducer

Manage complex state logic with multiple sub-values or when next state depends on previous.

```tsx
import { useReducer, useCallback } from 'react'

interface State {
  count: number
  status: 'idle' | 'loading' | 'error'
}

type Action =
  | { type: 'increment' }
  | { type: 'decrement' }
  | { type: 'setStatus'; payload: State['status'] }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'increment':
      return { ...state, count: state.count + 1 }
    case 'decrement':
      return { ...state, count: state.count - 1 }
    case 'setStatus':
      return { ...state, status: action.payload }
    default:
      return state
  }
}

function Counter() {
  const [state, dispatch] = useReducer(reducer, { 
    count: 0, 
    status: 'idle' 
  })
  
  const increment = useCallback(() => dispatch({ type: 'increment' }), [])
  
  return (
    <div>
      Count: {state.count}
      <button onClick={increment}>+</button>
    </div>
  )
}
```

## useId

Generate unique IDs accessible for accessibility attributes.

```tsx
import { useId } from 'react'

function Checkbox() {
  const id = useId()
  return (
    <>
      <input type="checkbox" id={id} />
      <label htmlFor={id}>Accept terms</label>
    </>
  )
}

// For multiple IDs in a component
const id1 = useId()
const id2 = useId()
// Result: ['react-dom-server:id1', 'react-dom-server:id2']
```

## useTransition

Mark a state transition as non-blocking to keep the UI responsive.

```tsx
import { useState, useTransition } from 'react'

function SearchableList() {
  const [query, setQuery] = useState('')
  const [isPending, startTransition] = useTransition()
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Urgent: show input immediately
    setQuery(e.target.value)
    
    // Non-urgent: filter list can wait
    startTransition(() => {
      setFilteredList(items.filter(...))
    })
  }
  
  return (
    <>
      <input value={query} onChange={handleChange} />
      {isPending && <Spinner />}
      <List items={filteredList} />
    </>
  )
}
```

## useDeferredValue

Defer updating a non-critical part of the UI.

```tsx
import { useDeferredValue, useState, useMemo } from 'react'

function SearchResults({ query }: { query: string }) {
  const deferredQuery = useDeferredValue(query)
  
  const results = useMemo(() => 
    searchData(deferredQuery), 
    [deferredQuery]
  )
  
  return <ul>{results.map(...)}</ul>
}
```

## useSyncExternalStore

Subscribe to an external data source in a way that supports concurrent rendering.

```tsx
import { useSyncExternalStore } from 'react'

const subscribe = (callback: () => void) => {
  window.addEventListener('resize', callback)
  return () => window.removeEventListener('resize', callback)
}

const getSnapshot = () => window.innerWidth

function WindowWidth() {
  const width = useSyncExternalStore(subscribe, getSnapshot)
  return <div>Window width: {width}</div>
}
```

## useInsertionEffect

Hook for CSS-in-JS libraries to inject styles before DOM mutations.

```tsx
import { useInsertionEffect } from 'react'

function useCSS(rule: string) {
  useInsertionEffect(() => {
    const style = document.createElement('style')
    style.textContent = rule
    document.head.appendChild(style)
    return () => document.head.removeChild(style)
  }, [rule])
}
```

## Rules of Hooks

1. **Only call Hooks at the top level** - Don't call inside loops, conditions, or nested functions
2. **Only call Hooks from React functions** - Function components, custom hooks
3. **Name custom hooks with `use` prefix** - Enables React to check for rule violations
