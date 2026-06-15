---
name: layout-spacing
description: Layout and spacing fundamentals including CSS Grid, Flexbox, spacing scales, and responsive breakpoints for modern web layouts.
---

# Layout & Spacing

> A guide to building responsive layouts using CSS Grid, Flexbox, and consistent spacing systems.

## Problem

- Inconsistent spacing throughout the application
- Difficult to make layouts responsive
- Confusion about when to use Grid vs Flexbox
- Hard to maintain alignment across components

## Solution

Establish clear spacing scales and choose the right layout method for each situation.

## Spacing Scale

### Consistent Spacing System

```css
:root {
  /* Base unit: 4px */
  --space-0: 0;
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
  --space-20: 5rem;     /* 80px */
  --space-24: 6rem;     /* 96px */
}
```

### Spacing Usage Guidelines

| Token | Usage |
|-------|-------|
| space-1 to space-2 | Tight spacing, inline elements |
| space-3 to space-4 | Default component padding |
| space-6 to space-8 | Section spacing |
| space-12+ | Page-level spacing |

## Flexbox

### When to Use Flexbox

- One-dimensional layouts (row OR column)
- Navigation menus
- Card layouts
- Centering content
- Distributing space between items

### Common Patterns

```css
/* Center content */
.center {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Space between */
.space-between {
  display: flex;
  justify-content: space-between;
}

/* Stack items */
.stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Inline flex */
.inline-flex {
  display: inline-flex;
  gap: var(--space-2);
}
```

### Flex Properties Reference

```css
.container {
  display: flex;
  
  /* Direction */
  flex-direction: row | column;
  
  /* Wrapping */
  flex-wrap: wrap | nowrap;
  
  /* Main axis alignment */
  justify-content: flex-start | center | space-between | space-around | space-evenly;
  
  /* Cross axis alignment */
  align-items: stretch | flex-start | center | baseline;
  
  /* Gap */
  gap: var(--space-4);
}
```

## CSS Grid

### When to Use Grid

- Two-dimensional layouts (rows AND columns)
- Page layouts
- Complex card grids
- Dashboard layouts
- Anything requiring precise alignment

### Common Patterns

```css
/* Simple grid */
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

/* Responsive grid */
.responsive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-4);
}

/* Named grid areas */
.page-layout {
  display: grid;
  grid-template-areas:
    "header header"
    "sidebar main"
    "footer footer";
  grid-template-columns: 250px 1fr;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
}

.header { grid-area: header; }
.sidebar { grid-area: sidebar; }
.main { grid-area: main; }
.footer { grid-area: footer; }
```

## Responsive Breakpoints

### Standard Breakpoints

```css
:root {
  /* Mobile: 0 - 639px */
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
  --breakpoint-2xl: 1536px;
}

/* Mobile first approach */
.container {
  padding: var(--space-4);
}

@media (min-width: 768px) {
  .container {
    padding: var(--space-6);
  }
}

@media (min-width: 1024px) {
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--space-8);
  }
}
```

### Common Breakpoint Strategy

| Breakpoint | Width | Device |
|------------|-------|--------|
| sm | 640px | Large phones |
| md | 768px | Tablets |
| lg | 1024px | Laptops |
| xl | 1280px | Desktops |
| 2xl | 1536px | Large screens |

## Layout Patterns

### Card Grid

```css
.card-grid {
  display: grid;
  gap: var(--space-6);
  grid-template-columns: 1fr;
}

@media (min-width: 640px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### Sidebar Layout

```css
.layout {
  display: grid;
  grid-template-columns: 1fr;
  min-height: 100vh;
}

@media (min-width: 768px) {
  .layout {
    grid-template-columns: 250px 1fr;
  }
}
```

## Key Takeaways

- Use a consistent spacing scale throughout
- Use Flexbox for one-dimensional layouts
- Use Grid for two-dimensional layouts
- Prefer Grid with auto-fit for responsive cards
- Use CSS custom properties for spacing
- Mobile-first approach works best
