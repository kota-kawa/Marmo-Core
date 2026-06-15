# Presets

Learn how to use and configure UnoCSS presets.

## preset-uno

The default preset, compatible with Tailwind CSS:

```ts
import { defineConfig, presetUno } from 'unocss'

export default defineConfig({
  presets: [presetUno()],
})
```

Includes all common utilities:
- Flexbox
- Grid
- Spacing
- Typography
- Border
- Background
- And more...

## preset-mini

Minimal preset with essential utilities:

```ts
import { defineConfig, presetMini } from 'unocss'

export default defineConfig({
  presets: [presetMini()],
})
```

## preset-wind

Compatible with Tailwind CSS Wind CSS:

```ts
import { defineConfig, presetWind } from 'unocss'

export default defineConfig({
  presets: [presetWind()],
})
```

## preset-icons

Icon preset using Iconify:

```ts
import { defineConfig, presetIcons } from 'unocss'

export default defineConfig({
  presets: [
    presetIcons({
      scale: 1.2,
      cdn: 'https://esm.sh/',
    }),
  ],
})
```

```html
<!-- Usage -->
<div class="i-carbon-sun dark:i-carbon-moon" />
<div class="i-logos-vue" />
<div class="i-logos-typescript-icon" />
```

### Icon Collections

```ts
export default defineConfig({
  presets: [
    presetIcons({
      collections: {
        custom: {
          logo: '<svg>...</svg>',
        },
      },
    }),
  ],
})
```

## preset-attributify

Use attributes instead of classes:

```ts
import { defineConfig, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [presetAttributify()],
})
```

```html
<!-- Class syntax -->
<button class="px-4 py-2 bg-blue-500 text-white rounded-lg">Button</button>

<!-- Attributify syntax -->
<button px="4" py="2" bg="blue-500" text="white" rounded="lg">Button</button>
```

## preset-web-fonts

Web font loading:

```ts
import { defineConfig, presetWebFonts } from 'unocss'

export default defineConfig({
  presets: [
    presetWebFonts({
      provider: 'google',
      fonts: {
        sans: 'Inter:400,600,700',
        mono: 'Fira Code:400',
      },
    }),
  ],
})
```

## preset-typography

Typography utilities:

```ts
import { defineConfig, presetTypography } from 'unocss'

export default defineConfig({
  presets: [presetTypography()],
})
```

```html
<article class="prose prose-lg dark:prose-invert">
  <h1>Title</h1>
  <p>Content...</p>
</article>
```

## Combining Presets

```ts
import { defineConfig, presetUno, presetIcons, presetAttributify, presetTypography } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
    presetIcons({
      scale: 1.2,
      cdn: 'https://esm.sh/',
    }),
    presetTypography(),
  ],
})
```

## Custom Presets

```ts
import { defineConfig, createPreset } from 'unocss'

const myPreset = createPreset({
  name: 'my-preset',
  rules: [
    ['custom-class', { color: 'red' }],
  ],
  shortcuts: {
    'btn': 'custom-class px-4 py-2',
  },
})

export default defineConfig({
  presets: [myPreset],
})
```

## Best Practices

1. **Start with preset-uno**: Most common utilities
2. **Add icons**: preset-icons for icon needs
3. **Use attributify**: For cleaner template
4. **Combine presets**: Only add what you need

## Common Mistakes

❌ **Not specifying icon CDN**

```ts
presetIcons() // ❌ No CDN configured
```

✅ **Specifying CDN**

```ts
presetIcons({
  cdn: 'https://esm.sh/',
})
```

❌ **Too many presets**

```ts
presets: [
  presetUno(),
  presetMini(), // ❌ Redundant
  presetWind(), // ❌ Redundant
]
```

✅ **Selective presets**

```ts
presets: [
  presetUno(), // ✅ Main preset
  presetIcons(), // ✅ Icons only
]
```
