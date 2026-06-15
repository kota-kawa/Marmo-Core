---
name: color-theory
description: Color theory fundamentals including color palettes, contrast ratios, semantic colors, and implementing dark mode in web applications.
---

# Color Theory

> A guide to using color effectively in web interfaces - creating palettes, ensuring accessibility, and implementing theming.

## Problem

- Choosing colors that don't work together
- Creating inaccessible color combinations
- Difficult to maintain and update colors
- No support for dark mode or theming

## Solution

Build a systematic color system with semantic naming and proper contrast ratios.

## Color Palette Structure

### Tiered Color System

```css
:root {
  /* Brand Colors */
  --color-brand-50: #eff6ff;
  --color-brand-100: #dbeafe;
  --color-brand-200: #bfdbfe;
  --color-brand-300: #93c5fd;
  --color-brand-400: #60a5fa;
  --color-brand-500: #3b82f6;
  --color-brand-600: #2563eb;
  --color-brand-700: #1d4ed8;
  --color-brand-800: #1e40af;
  --color-brand-900: #1e3a8a;
  
  /* Neutral / Gray Scale */
  --color-gray-50: #f9fafb;
  --color-gray-100: #f3f4f6;
  /* ... more gray steps */
  --color-gray-900: #111827;
}
```

### Semantic Colors

```css
:root {
  /* Success - Green */
  --color-success-50: #f0fdf4;
  --color-success-500: #22c55e;
  --color-success-700: #15803d;
  
  /* Warning - Amber */
  --color-warning-50: #fffbeb;
  --color-warning-500: #f59e0b;
  --color-warning-700: #b45309;
  
  /* Error - Red */
  --color-error-50: #fef2f2;
  --color-error-500: #ef4444;
  --color-error-700: #b91c1c;
  
  /* Info - Blue */
  --color-info-50: #eff6ff;
  --color-info-500: #3b82f6;
  --color-info-700: #1d4ed8;
}
```

## Contrast & Accessibility

### WCAG Requirements

| Level | Normal Text | Large Text |
|-------|-------------|------------|
| AA | 4.5:1 | 3:1 |
| AAA | 7:1 | 4.5:1 |

### Testing Tools

Use tools like:
- WebAIM Contrast Checker
- Chrome DevTools Accessibility pane
- Stark (Figma plugin)

### Accessible Combinations

```css
/* ✅ Passes AA */
--text-primary: #1f2937;   /* on white - 15.9:1 */
--text-secondary: #4b5563;   /* on white - 5.74:1 */

/* ❌ Fails AA */
--text-bad: #6b7280;        /* on white - 3.88:1 */
```

### Large Text Definition

- 18px+ regular (bold 14px+)
- 24px+ bold

## Dark Mode

### CSS Custom Properties Approach

```css
:root {
  --color-bg: #ffffff;
  --color-text: #1f2937;
  --color-border: #e5e7eb;
}

[data-theme="dark"] {
  --color-bg: #111827;
  --color-text: #f9fafb;
  --color-border: #374151;
}

body {
  background-color: var(--color-bg);
  color: var(--color-text);
}
```

### Media Query Approach

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #111827;
    --color-text: #f9fafb;
    --color-border: #374151;
  }
}
```

### Color Adjustments for Dark Mode

```css
/* Don't just invert - adjust saturation */
[data-theme="dark"] {
  /* Reduce white to avoid glare */
  --color-primary-50: #1e3a5f;
  --color-primary-100: #1e40af;
  /* Increase brightness slightly */
  --color-primary-400: #60a5fa;
  --color-primary-500: #3b82f6;
}
```

## Color Psychology

### Common Associations

| Color | Meanings |
|-------|----------|
| Blue | Trust, security, calm |
| Green | Growth, health, success |
| Red | Urgency, danger, passion |
| Yellow | Caution, optimism, energy |
| Purple | Luxury, creativity, wisdom |
| Orange | Friendly, adventurous, bold |

### Semantic Color Usage

```css
/* Status colors */
--color-online: #22c55e;
--color-offline: #6b7280;
--color-busy: #ef4444;
--color-away: #f59e0b;

/* Interactive states */
--color-hover: var(--color-primary-600);
--color-active: var(--color-primary-700);
--color-focus: var(--color-primary-500);
--color-disabled: var(--color-gray-400);
```

## Key Takeaways

- Build colors from a systematic palette
- Use semantic names for maintainability
- Always test contrast ratios (minimum 4.5:1)
- Plan for dark mode from the start
- Don't just invert colors in dark mode - adjust them
- Consider color psychology for emotional impact
