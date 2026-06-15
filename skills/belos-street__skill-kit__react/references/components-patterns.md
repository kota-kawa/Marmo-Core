---
name: components-patterns
description: React function components, props, children, composition, render props, forwardRef, memo patterns
---

# Components & Patterns

## Function Components

Basic function component with TypeScript.

```tsx
import { ReactNode } from 'react'

interface Props {
  title: string
  children?: ReactNode
}

export function MyComponent({ title, children }: Props) {
  return (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  )
}
```

## Props

### Basic Props

```tsx
interface ButtonProps {
  label: string
  onClick: () => void
  variant?: 'primary' | 'secondary'
  disabled?: boolean
}

function Button({ label, onClick, variant = 'primary', disabled }: ButtonProps) {
  return (
    <button 
      className={`btn btn-${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  )
}
```

### Props with Default Values

```tsx
interface CardProps {
  title: string
  content?: string
  // Use default parameter instead of ?
}

function Card({ title, content = 'No content' }: CardProps) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <p>{content}</p>
    </div>
  )
}
```

### Generic Components

```tsx
function List<T>({ items, renderItem }: { 
  items: T[] 
  renderItem: (item: T) => ReactNode 
}) {
  return (
    <ul>
      {items.map((item, index) => (
        <li key={index}>{renderItem(item)}</li>
      ))}
    </ul>
  )
}

// Usage
<List 
  items={['a', 'b', 'c']} 
  renderItem={(item) => <span>{item}</span>}
/>
```

## Children

```tsx
import { ReactNode } from 'react'

interface ContainerProps {
  title: string
  children: ReactNode
}

function Container({ title, children }: ContainerProps) {
  return (
    <div className="container">
      <h2>{title}</h2>
      <div className="content">
        {children}
      </div>
    </div>
  )
}

// Usage
<Container title="Welcome">
  <p>This is child content</p>
  <OtherComponent />
</Container>
```

## Composition Patterns

### Slot Pattern (Component as Props)

```tsx
interface LayoutProps {
  header?: ReactNode
  main: ReactNode
  footer?: ReactNode
}

function Layout({ header, main, footer }: LayoutProps) {
  return (
    <div className="layout">
      {header && <header>{header}</header>}
      <main>{main}</main>
      {footer && <footer>{footer}</footer>}
    </div>
  )
}

// Usage
<Layout
  header={<h1>My App</h1>}
  main={<p>Content here</p>}
  footer={<small>© 2024</small>}
/>
```

### Render Props

```tsx
import { useState, ReactNode } from 'react'

interface MouseTrackerProps {
  children: (state: { x: number; y: number }) => ReactNode
}

function MouseTracker({ children }: MouseTrackerProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 })
  
  return (
    <div
      onMouseMove={(e) => setPosition({ x: e.clientX, y: e.clientY })}
    >
      {children(position)}
    </div>
  )
}

// Usage
<MouseTracker>
  {({ x, y }) => <p>Mouse at {x}, {y}</p>}
</MouseTracker>
```

### Compound Components

```tsx
interface TabsContextValue {
  activeTab: string
  setActiveTab: (tab: string) => void
}

const TabsContext = createContext<TabsContextValue | null>(null)

function Tabs({ defaultTab, children }: { 
  defaultTab: string 
  children: ReactNode 
}) {
  const [activeTab, setActiveTab] = useState(defaultTab)
  
  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </TabsContext.Provider>
  )
}

function TabList({ children }: { children: ReactNode }) {
  return <div className="tab-list">{children}</div>
}

function Tab({ name, children }: { name: string; children: ReactNode }) {
  const { activeTab, setActiveTab } = useContext(TabsContext)!
  const isActive = activeTab === name
  
  return (
    <button 
      className={isActive ? 'active' : ''}
      onClick={() => setActiveTab(name)}
    >
      {children}
    </button>
  )
}

function TabPanel({ name, children }: { name: string; children: ReactNode }) {
  const { activeTab } = useContext(TabsContext)!
  return activeTab === name ? <div>{children}</div> : null
}

Tabs.TabList = TabList
Tabs.Tab = Tab
Tabs.TabPanel = TabPanel

// Usage
<Tabs defaultTab="home">
  <Tabs.TabList>
    <Tabs.Tab name="home">Home</Tabs.Tab>
    <Tabs.Tab name="about">About</Tabs.Tab>
  </Tabs.TabList>
  <Tabs.TabPanel name="home">Home content</Tabs.TabPanel>
  <Tabs.TabPanel name="about">About content</Tabs.TabPanel>
</Tabs>
```

## forwardRef

Expose a DOM ref to the parent component.

```tsx
import { forwardRef, useImperativeHandle, Ref } from 'react'

interface InputRef {
  focus: () => void
  blur: () => void
}

interface InputProps {
  placeholder?: string
}

const Input = forwardRef<InputRef, InputProps>((props, ref) => {
  const inputRef = useRef<HTMLInputElement>(null)
  
  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
    blur: () => inputRef.current?.blur()
  }))
  
  return <input ref={inputRef} {...props} />
})

Input.displayName = 'Input'

// Usage
function Parent() {
  const inputRef = useRef<InputRef>(null)
  
  return (
    <>
      <Input ref={inputRef} placeholder="Type here" />
      <button onClick={() => inputRef.current?.focus()}>Focus</button>
    </>
  )
}
```

## memo

Memoize a component to prevent unnecessary re-renders when props haven't changed.

```tsx
import { memo } from 'react'

interface ButtonProps {
  onClick: () => void
  children: React.ReactNode
}

// Memoized component - only re-renders when props change
const Button = memo(function Button({ onClick, children }: ButtonProps) {
  return <button onClick={onClick}>{children}</button>
})

// With custom comparison
const Button = memo(
  function Button({ onClick, children }: ButtonProps) {
    return <button onClick={onClick}>{children}</button>
  },
  (prevProps, nextProps) => {
    // Return true if re-render should be skipped
    return prevProps.onClick === nextProps.onClick
  }
)
```

## Custom Hooks

Encapsulate stateful logic in a reusable function.

```tsx
import { useState, useEffect } from 'react'

// useMouse hook
function useMouse() {
  const [position, setPosition] = useState({ x: 0, y: 0 })
  
  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      setPosition({ x: e.clientX, y: e.clientY })
    }
    
    window.addEventListener('mousemove', handleMove)
    return () => window.removeEventListener('mousemove', handleMove)
  }, [])
  
  return position
}

// useFetch hook
function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        const res = await fetch(url)
        const json = await res.json()
        setData(json)
      } catch (e) {
        setError(e as Error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [url])
  
  return { data, loading, error }
}

// useLocalStorage hook
function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch {
      return initialValue
    }
  })
  
  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function 
        ? value(storedValue) 
        : value
      setStoredValue(valueToStore)
      window.localStorage.setItem(key, JSON.stringify(valueToStore))
    } catch (e) {
      console.error(e)
    }
  }
  
  return [storedValue, setValue] as const
}
```

## TypeScript Patterns

### Event Handlers

```tsx
// Mouse events
onClick={(e: React.MouseEvent<HTMLButtonElement>) => {}}
onMouseEnter={(e: React.MouseEvent<HTMLDivElement>) => {}}

// Form events
onChange={(e: React.ChangeEvent<HTMLInputElement>) => {}}
onSubmit={(e: React.FormEvent<HTMLFormElement>) => {}}

// Focus events
onFocus={(e: React.FocusEvent<HTMLInputElement>) => {}}
onBlur={(e: React.FocusEvent<HTMLInputElement>) => {}}
```

### CSS Modules

```tsx
import styles from './Button.module.css'

interface ButtonProps {
  variant?: 'primary' | 'secondary'
}

function Button({ variant = 'primary' }: ButtonProps) {
  return (
    <button className={`${styles.button} ${styles[variant]}`}>
      Click me
    </button>
  )
}
```
