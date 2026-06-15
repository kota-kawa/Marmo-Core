---
name: typography
description: Typography fundamentals including font selection, type scale, line height, readability, and vertical rhythm for web interfaces.
---

# Typography

> A guide to effective typography for web interfaces - choosing fonts, establishing scales, and ensuring readability.

## Problem

- Text is hard to read
- Inconsistent font sizes across the application
- Poor vertical rhythm breaks visual flow
- Inappropriate font weights confuse hierarchy

## Solution

Establish a consistent typography system with proper scale, line height, and spacing.

## Type Scale

### Mathematical Scale

Use a consistent ratio to generate harmonious font sizes:

```css
:root {
  /* Base size: 16px */
  --text-xs:   0.75rem;    /* 12px */
  --text-sm:   0.875rem;   /* 14px */
  --text-base: 1rem;       /* 16px */
  --text-lg:   1.125rem;   /* 18px */
  --text-xl:   1.25rem;    /* 20px */
  --text-2xl:  1.5rem;     /* 24px */
  --text-3xl:  1.875rem;   /* 30px */
  --text-4xl:  2.25rem;    /* 36px */
  --text-5xl:  3rem;       /* 48px */
}
```

### Scale Ratio Options

| Ratio | Use Case |
|-------|----------|
| 1.067 | Subtle, content-focused |
| 1.125 | Default, balanced |
| 1.2 | Classic musical proportion |
| 1.25 | Large display text |
| 1.333 | Dramatic, editorial |

## Line Height

### General Guidelines

- Headings: 1.1 - 1.3
- Body text: 1.5 - 1.7
- Compact text: 1.3 - 1.5
- Large text: 1.1 - 1.2

```css
:root {
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.75;
}

h1, h2, h3 {
  line-height: var(--leading-tight);
}

p, li {
  line-height: var(--leading-normal);
}
```

## Font Selection

### Font Stack Best Practices

Always provide fallbacks:

```css
font-family: 'Inter', 
              system-ui, 
              -apple-system, 
              BlinkMacSystemFont, 
              'Segoe UI', 
              Roboto, 
              sans-serif;
```

### Variable Fonts

Use variable fonts for better performance and flexibility:

```css
@font-face {
  font-family: 'Inter';
  src: url('/fonts/Inter-Variable.woff2') format('woff2-variations');
  font-weight: 100 900;
  font-display: swap;
}

.text-bold {
  font-weight: 750;
}
```

## Vertical Rhythm

### Establishing Baseline Grid

```css
:root {
  --base-size: 4px;
  --baseline: 1.5; /* line-height */
  --rhythm: calc(var(--base-size) * var(--baseline));
}

p {
  margin-bottom: var(--rhythm);
}

h1, h2, h3, h4 {
  margin-top: calc(var(--rhythm) * 2);
  margin-bottom: var(--rhythm);
}
```

### Spacing Scale

```css
:root {
  --space-1: 0.25em;   /* 4px */
  --space-2: 0.5em;    /* 8px */
  --space-3: 0.75em;   /* 12px */
  --space-4: 1em;      /* 16px */
  --space-6: 1.5em;   /* 24px */
  --space-8: 2em;     /* 32px */
  --space-12: 3em;    /* 48px */
}
```

## Readability

### Optimal Line Length

- Minimum: 45 characters
- Maximum: 75-80 characters
- Ideal: 60-65 characters

```css
.article-content {
  max-width: 65ch;
}
```

### Contrast Ratios

Follow WCAG guidelines:

| Level | Ratio | Usage |
|-------|-------|-------|
| AAA | 7:1 | Essential text |
| AA | 4.5:1 | Normal text |
| AA Large | 3:1 | Large text (18px+) |

```css
:root {
  --text-primary: #1f2937;    /* 12.63:1 */
  --text-secondary: #4b5563;  /* 5.89:1 */
  --text-muted: #6b7280;     /* 4.52:1 */
}
```

## Key Takeaways

- Establish a type scale and stick to it
- Use line-height appropriate to text type
- Ensure adequate contrast (minimum 4.5:1)
- Limit line length to 60-75 characters
- Maintain consistent vertical rhythm
- Provide proper font fallbacks
