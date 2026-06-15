---
name: design-systems
description: Design systems fundamentals, component libraries, design tokens, and theming strategies for scalable frontend applications.
---

# Design Systems

> A comprehensive guide to building and maintaining design systems for consistent and scalable user interfaces.

## Problem

- Inconsistent UI across different parts of the application
- Hard to maintain and update styles
- Difficult to onboard new team members
- Scaling design and development becomes challenging

## Solution

A design system is a collection of reusable components, guided by clear standards, that can be assembled to build any number of applications.

## Design Tokens

### What are Design Tokens

Design tokens are atomic design decisions stored as data - colors, spacing, typography, shadows, etc.

```css
/* Primitive tokens */
--color-blue-500: #3b82f6;
--color-blue-600: #2563eb;

/* Semantic tokens */
--color-primary: var(--color-blue-600);
--color-text-primary: #1f2937;
--color-text-secondary: #6b7280;

/* Component tokens */
--button-bg-primary: var(--color-primary);
--button-text-color: #ffffff;
--button-padding: 0.5rem 1rem;
```

### Token Categories

| Category | Examples | Usage |
|----------|----------|-------|
| Colors | Primary, secondary, semantic | Backgrounds, text, borders |
| Typography | Font family, size, weight | Text styling |
| Spacing | Margins, paddings | Layout gaps |
| Shadows | Elevation levels | Depth perception |
| Borders | Radius, width | Component styling |
| Animation | Duration, easing | Transitions |

## Component Library Structure

### Atomic Design

```
design-system/
├── tokens/           # Design tokens
│   ├── colors.css
│   ├── typography.css
│   └── spacing.css
├── atoms/            # Basic building blocks
│   ├── Button/
│   ├── Input/
│   └── Badge/
├── molecules/        # Simple component groups
│   ├── FormField/
│   ├── Card/
│   └── Modal/
├── organisms/        # Complex UI sections
│   ├── Header/
│   ├── Sidebar/
│   └── Footer/
└── utilities/        # Helper classes
    ├── flexbox.css
    └── grid.css
```

### Component Props Schema

```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost'
  size: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  icon?: React.ReactNode
  children: React.ReactNode
}
```

## Best Practices

### 1. Start with Tokens

Always build from design tokens up, never hardcode values:

```css
/* ❌ Bad */
.button {
  background-color: #3b82f6;
  padding: 12px 24px;
}

/* ✅ Good */
.button {
  background-color: var(--button-bg-primary);
  padding: var(--button-padding);
}
```

### 2. Semantic Naming

Use meaningful names that describe purpose, not appearance:

```css
/* ❌ Bad */
--blue-text: #3b82f6;
--large-margin: 2rem;

/* ✅ Good */
--color-link: #3b82f6;
--spacing-section: 2rem;
```

### 3. Composition over Inheritance

Build complex components from simpler ones:

```tsx
function Card({ title, children, footer }) {
  return (
    <div className="card">
      {title && <CardHeader>{title}</CardHeader>}
      <CardBody>{children}</CardBody>
      {footer && <CardFooter>{footer}</CardFooter>}
    </div>
  )
}
```

### 4. Document Everything

Include usage examples and do's/don'ts:

```md
## Button

### Usage

```tsx
// Primary button
<Button variant="primary">Click me</Button>

// With icon
<Button icon={<Icon />}>With Icon</Button>
```

### Do's
- Use primary for main actions
- Use ghost for secondary actions

### Don'ts
- Don't use more than one primary button per section
```

## Key Takeaways

- Design tokens are the foundation - build everything from them
- Use semantic names that describe purpose
- Document components with usage examples
- Version your design system
- Maintain a changelog for updates
