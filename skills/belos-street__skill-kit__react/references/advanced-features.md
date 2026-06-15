---
name: advanced-features
description: React advanced features - Suspense, Error Boundary, Lazy loading, Context, Refs, Portals
---

# Advanced Features

## Suspense

Handle async dependencies with loading states. Allows components to suspend rendering while waiting for data.

```tsx
import { Suspense, lazy } from 'react'

const AsyncComponent = lazy(() => import('./AsyncComponent'))

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AsyncComponent />
    </Suspense>
  )
}
```

### Suspense with Multiple Components

```tsx
function App() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Dashboard />
      <Comments />
    </Suspense>
  )
}
```

### use hook

React 19's `use` hook can be used to read Suspense promises directly.

```tsx
import { use, Suspense } from 'react'

function UserProfile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise)
  return <div>{user.name}</div>
}

function App() {
  const userPromise = fetchUser()
  
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <UserProfile userPromise={userPromise} />
    </Suspense>
  )
}
```

### Error Boundaries

Handle errors in component tree with class-based Error Boundary.

```tsx
import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught:', error, errorInfo)
  }
  
  render() {
    if (this.state.hasError) {
      return this.props.fallback
    }
    
    return this.props.children
  }
}

// Usage
<ErrorBoundary fallback={<div>Something went wrong</div>}>
  <MyComponent />
</ErrorBoundary>
```

### Error Boundary with Reset

```tsx
class ErrorBoundary extends Component<{}, State> {
  state = { hasError: false, error: null }
  
  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div>
          <p>Error: {this.state.error?.message}</p>
          <button onClick={this.handleReset}>Try Again</button>
        </div>
      )
    }
    
    return this.props.children
  }
}
```

## Lazy Loading

### lazy

Dynamically import components to reduce initial bundle size.

```tsx
import { lazy, Suspense } from 'react'

const HeavyComponent = lazy(() => import('./HeavyComponent'))

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <HeavyComponent />
    </Suspense>
  )
}
```

### With Named Export

```tsx
const { Component } = lazy(() => import('./module'))
```

### Preloading

```tsx
import { lazy, useState, useEffect } from 'react'

const Modal = lazy(() => import('./Modal'))

function App() {
  const [showModal, setShowModal] = useState(false)
  
  // Preload on hover
  const handleMouseEnter = () => {
    import('./Modal')
  }
  
  return (
    <button onMouseEnter={handleMouseEnter} onClick={() => setShowModal(true)}>
      Open Modal
    </button>
  )
}
```

## Context

Share state across components without passing props.

### Basic Context

```tsx
import { createContext, useContext, ReactNode } from 'react'

interface ThemeContextValue {
  theme: 'light' | 'dark'
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light')
  }
  
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

function ThemedButton() {
  const { theme, toggleTheme } = useContext(ThemeContext)!
  
  return (
    <button 
      className={theme}
      onClick={toggleTheme}
    >
      Toggle Theme
    </button>
  )
}
```

### Context with Reducer

```tsx
import { createContext, useContext, useReducer, ReactNode } from 'react'

interface State {
  count: number
}

type Action = { type: 'increment' } | { type: 'decrement' }

const initialState: State = { count: 0 }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'increment':
      return { count: state.count + 1 }
    case 'decrement':
      return { count: state.count - 1 }
    default:
      return state
  }
}

interface DispatchContextValue {
  dispatch: React.Dispatch<Action>
}

const StateContext = createContext<State>(initialState)
const DispatchContext = createContext<DispatchContextValue['dispatch']>(() => {})

function Provider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  
  return (
    <StateContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>
        {children}
      </DispatchContext.Provider>
    </StateContext.Provider>
  )
}

function Counter() {
  const state = useContext(StateContext)
  const dispatch = useContext(DispatchContext)
  
  return (
    <div>
      Count: {state.count}
      <button onClick={() => dispatch({ type: 'increment' })}>+</button>
    </div>
  )
}
```

## Refs

### useRef

```tsx
import { useRef } from 'react'

function TextInput() {
  const inputRef = useRef<HTMLInputElement>(null)
  
  const handleClick = () => {
    inputRef.current?.focus()
  }
  
  return (
    <>
      <input ref={inputRef} type="text" />
      <button onClick={handleClick}>Focus Input</button>
    </>
  )
}
```

### Callback Ref

```tsx
function CallbackRef() {
  const elementRef = useRef<HTMLDivElement>(null)
  
  const setRef = (element: HTMLDivElement | null) => {
    elementRef.current = element
  }
  
  return <div ref={setRef}>Content</div>
}
```

### forwardRef + useImperativeHandle

```tsx
import { forwardRef, useImperativeHandle, useRef } from 'react'

interface ModalRef {
  open: () => void
  close: () => void
}

const Modal = forwardRef<ModalRef>((props, ref) => {
  const [isOpen, setIsOpen] = useState(false)
  const dialogRef = useRef<HTMLDialogElement>(null)
  
  useImperativeHandle(ref, () => ({
    open: () => setIsOpen(true),
    close: () => setIsOpen(false)
  }))
  
  if (!isOpen) return null
  
  return (
    <dialog ref={dialogRef}>
      <div>Modal Content</div>
    </dialog>
  )
})

Modal.displayName = 'Modal'
```

## Portals

Render children into a different DOM node.

```tsx
import { createPortal } from 'react-dom'

function Modal({ children, isOpen }: { children: ReactNode; isOpen: boolean }) {
  if (!isOpen) return null
  
  return createPortal(
    <div className="modal-overlay">
      <div className="modal-content">
        {children}
      </div>
    </div>,
    document.body
  )
}
```

### With useEffect for SSR

```tsx
import { createPortal } from 'react-dom'
import { useState, useEffect } from 'react'

function Portal({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
  }, [])
  
  if (!mounted) return null
  
  return createPortal(children, document.body)
}
```

## Server Components (RSC)

React Server Components allow components to render on the server.

```tsx
// This component runs on the server
async function UserList() {
  const users = await db.users.findMany()
  
  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  )
}
```

### 'use client' Directive

Mark components that need to run on the client.

```tsx
'use client'

import { useState } from 'react'

export function Counter() {
  const [count, setCount] = useState(0)
  
  return (
    <button onClick={() => setCount(c => c + 1)}>
      {count}
    </button>
  )
}
```

### 'use server' Directive

Allow server functions to be called from client.

```tsx
// actions.ts
'use server'

export async function createUser(formData: FormData) {
  const name = formData.get('name')
  await db.users.create({ name })
  revalidatePath('/users')
}

// Component
import { createUser } from './actions'

function CreateUserForm() {
  return (
    <form action={createUser}>
      <input name="name" />
      <button type="submit">Create</button>
    </form>
  )
}
```
