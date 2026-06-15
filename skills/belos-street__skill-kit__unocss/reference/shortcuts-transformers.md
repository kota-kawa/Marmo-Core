# Shortcuts and Transformers

Learn how to use shortcuts and transformers in UnoCSS.

## Shortcuts

Shortcuts allow you to create reusable class combinations.

### Basic Shortcuts

```ts
// uno.config.ts
export default defineConfig({
  shortcuts: {
    'btn': 'px-4 py-2 rounded-lg font-medium transition-colors duration-200',
    'card': 'bg-white rounded-lg shadow-md p-4',
  },
})
```

```html
<button class="btn">Click me</button>
<div class="card">Card content</div>
```

### Shortcuts with Variants

```ts
export default defineConfig({
  shortcuts: [
    ['btn', 'px-4 py-2 rounded-lg font-medium transition-colors duration-200'],
    ['btn-primary', 'btn bg-blue-500 text-white hover:bg-blue-600'],
    ['btn-secondary', 'btn bg-gray-200 text-gray-800 hover:bg-gray-300'],
  ],
})
```

### Dynamic Shortcuts

```ts
export default defineConfig({
  shortcuts: [
    [/^btn-(.*)$/, ([, color]) => `px-4 py-2 rounded-lg font-medium bg-${color} text-white`],
    [/^text-(.*)$/, ([, color]) => `text-${color} font-semibold`],
  ],
})
```

```html
<button class="btn-blue">Blue Button</button>
<button class="btn-red">Red Button</button>
<h1 class="text-primary">Title</h1>
```

## Shortcuts Examples

### Button Variants

```ts
export default defineConfig({
  shortcuts: {
    'btn': 'px-4 py-2 rounded-lg font-medium transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-primary': 'btn bg-blue-500 text-white hover:bg-blue-600 active:bg-blue-700',
    'btn-secondary': 'btn bg-gray-200 text-gray-800 hover:bg-gray-300',
    'btn-danger': 'btn bg-red-500 text-white hover:bg-red-600',
    'btn-outline': 'btn border-2 border-blue-500 text-blue-500 hover:bg-blue-500 hover:text-white',
  },
})
```

### Layout Shortcuts

```ts
export default defineConfig({
  shortcuts: {
    'flex-center': 'flex justify-center items-center',
    'flex-between': 'flex justify-between items-center',
    'flex-start': 'flex items-start',
    'flex-col': 'flex flex-col',
    'flex-wrap': 'flex flex-wrap',
    'grid-center': 'grid place-items-center',
    'container-center': 'mx-auto px-4 max-w-7xl',
  },
})
```

### Card Shortcuts

```ts
export default defineConfig({
  shortcuts: {
    'card': 'bg-white rounded-xl shadow-sm border border-gray-100',
    'card-hover': 'card transition-shadow duration-300 hover:shadow-lg',
    'card-interactive': 'card-hover cursor-pointer hover:border-blue-200',
  },
})
```

### Input Shortcuts

```ts
export default defineConfig({
  shortcuts: {
    'input': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
    'input-error': 'input border-red-500 focus:ring-red-500',
  },
})
```

## Transformers

Transformers modify your code to enhance UnoCSS functionality.

### transformer-directives

Enables `@apply` directive:

```ts
import { defineConfig, presetUno, transformerDirectives } from 'unocss'

export default defineConfig({
  presets: [presetUno()],
  transformers: [transformerDirectives()],
})
```

```css
/* Use @apply */
.custom-class {
  @apply flex justify-center items-center px-4 py-2;
}
```

### transformer-variant-group

Groups variants:

```ts
import { defineConfig, presetUno, transformerVariantGroup } from 'unocss'

export default defineConfig({
  presets: [presetUno()],
  transformers: [transformerVariantGroup()],
})
```

```html
<!-- Before -->
<div class="hover:(text-white bg-blue-500) focus:(outline-none ring-2)">

<!-- After transformation -->
<div class="hover:text-white hover:bg-blue-500 focus-outline-none focus-ring-2">
```

### transformer-compile-class

Compile class names:

```ts
import { defineConfig, presetUno, transformerCompileClass } from 'unocss'

export default defineConfig({
  presets: [presetUno()],
  transformers: [
    transformerCompileClass({
      classPrefix: 'uno-',
    }),
  ],
})
```

```html
<div class="uno-flex uno-justify-center">
```

## Combining Transformers

```ts
import { defineConfig, presetUno } from 'unocss'
import { transformerDirectives } from 'unocss/transformer-directives'
import { transformerVariantGroup } from 'unocss/transformer-variant-group'

export default defineConfig({
  presets: [presetUno()],
  transformers: [
    transformerDirectives(),
    transformerVariantGroup(),
  ],
})
```

## Best Practices

1. **Use shortcuts**: For repeated patterns
2. **Group variants**: Use transformer-variant-group
3. **Use @apply**: For custom CSS with transformer-directives
4. **Organize shortcuts**: Group by category

## Common Mistakes

❌ **Not using shortcuts**

```html
<div class="flex justify-center items-center px-4 py-2 bg-white rounded-lg shadow-md">
  Content
</div>
```

✅ **Using shortcuts**

```ts
// uno.config.ts
shortcuts: {
  'card': 'flex justify-center items-center px-4 py-2 bg-white rounded-lg shadow-md',
}

<!-- Usage -->
<div class="card">Content</div>
```

❌ **Not using transformers**

```html
<div class="hover:text-white hover:bg-blue-500 hover:opacity-100">
```

✅ **Using transformer-variant-group**

```html
<div class="hover:(text-white bg-blue-500 opacity-100)">
```

❌ **Too many shortcuts**

```ts
shortcuts: {
  'mt-1': 'mt-1', // ❌ Redundant
  'mt-2': 'mt-2', // ❌ Redundant
}
```

✅ **Selective shortcuts**

```ts
shortcuts: {
  'card': 'bg-white rounded-lg shadow-md p-4', // ✅ Meaningful combination
  'btn': 'px-4 py-2 rounded-lg font-medium', // ✅ Reusable pattern
}
```
