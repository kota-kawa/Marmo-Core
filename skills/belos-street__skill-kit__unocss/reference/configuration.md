# Configuration and Core Features

Learn how to configure UnoCSS and understand its core features.

## Installation

```bash
npm install -D unocss
```

## Basic Configuration

Create `uno.config.ts`:

```ts
// uno.config.ts
import { defineConfig, presetUno } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
  ],
})
```

Add to your entry file:

```ts
// main.ts
import 'virtual:uno.css'
```

## Rule Configuration

### Adding Custom Rules

```ts
// uno.config.ts
import { defineConfig, presetUno } from 'unocss'

export default defineConfig({
  presets: [presetUno()],
  rules: [
    ['flex-center', { display: 'flex', 'justify-content': 'center', 'align-items': 'center' }],
    [/^custom-(\w+)$/, ([, value]) => ({ 'custom-property': value })],
  ],
})
```

### Dynamic Rules

```ts
// uno.config.ts
export default defineConfig({
  rules: [
    [/^grid-cols-(\d+)$/, ([, d]) => ({ 'grid-template-columns': `repeat(${d}, minmax(0, 1fr))` })],
    [/^size-(\d+)$/, ([, d]) => ({ width: `${d}px`, height: `${d}px` })],
  ],
})
```

## Shortcuts

Create reusable class combinations:

```ts
// uno.config.ts
export default defineConfig({
  shortcuts: {
    'btn': 'px-4 py-2 rounded-lg font-medium transition-colors duration-200',
    'btn-primary': 'btn bg-blue-500 text-white hover:bg-blue-600',
    'btn-secondary': 'btn bg-gray-200 text-gray-800 hover:bg-gray-300',
    'flex-center': 'flex justify-center items-center',
    'flex-between': 'flex justify-between items-center',
    'card': 'bg-white rounded-lg shadow-md p-4',
  },
})
```

```html
<!-- Usage -->
<button class="btn-primary">Click Me</button>
<div class="card">Card Content</div>
```

## Theme Configuration

### Colors

```ts
// uno.config.ts
export default defineConfig({
  theme: {
    colors: {
      primary: '#3b82f6',
      secondary: '#8b5cf6',
      success: '#10b981',
    },
  },
})
```

### Breakpoints

```ts
// uno.config.ts
export default defineConfig({
  theme: {
    breakpoints: {
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
    },
  },
})
```

### Font Family

```ts
// uno.config.ts
export default defineConfig({
  theme: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['Fira Code', 'monospace'],
    },
  },
})
```

## Variants

### Custom Variants

```ts
// uno.config.ts
export default defineConfig({
  variants: [
    // Hover variant
    (matcher) => {
      if (!matcher.startsWith('hover:'))
        return matcher
      return {
        matcher: matcher.slice(6),
        selector: (s) => `${s}:hover`,
      }
    },
  ],
})
```

### Using Variants

```html
<div class="hover:bg-blue-500">Hover me</div>
<div class="group-hover:opacity-100">Group hover</div>
```

## Auto-Import

Import utilities automatically:

```ts
// uno.config.ts
import { defineConfig, presetUno, transformerDirectives } from 'unocss'

export default defineConfig({
  presets: [presetUno()],
  transformers: [
    transformerDirectives(),
  ],
})
```

## Class Order

Recommended class order:

```html
<div 
  class="
    /* 布局 */
    relative flex items-center justify-between
    
    /* 盒子模型 */
    p-4 m-2 w-full h-16
    
    /* 边框 */
    border border-gray-200 rounded-lg
    
    /* 背景 */
    bg-white dark:bg-gray-800
    
    /* 文字 */
    text-sm font-medium text-gray-700
    
    /* 阴影 */
    shadow-md
    
    /* 过渡 */
    transition-all duration-200
  "
>
```

## Best Practices

1. **Use shortcuts**: For reusable patterns
2. **Organize rules**: Keep custom rules organized
3. **Use theme**: Define colors and fonts in theme
4. **Use presets**: Start with preset-uno
5. **Use transformers**: For better DX

## Common Mistakes

❌ **Not using shortcuts**

```html
<div class="px-4 py-2 rounded-lg font-medium bg-blue-500 text-white">
  Button
</div>
```

✅ **Using shortcuts**

```ts
// uno.config.ts
shortcuts: {
  'btn': 'px-4 py-2 rounded-lg font-medium bg-blue-500 text-white',
}

<!-- Usage -->
<div class="btn">Button</div>
```

❌ **Hardcoding colors**

```html
<div style={{ color: '#3b82f6' }}>Content</div>
```

✅ **Using theme colors**

```ts
// uno.config.ts
theme: {
  colors: { primary: '#3b82f6' }
}

<!-- Usage -->
<div class="text-primary">Content</div>
```
