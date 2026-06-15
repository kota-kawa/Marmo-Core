---
name: motion-animation
description: Motion design fundamentals including CSS transitions, animations, micro-interactions, and performance optimization for web interfaces.
---

# Motion & Animation

> A guide to effective use of animations and transitions - enhancing UX without compromising performance.

## Problem

- Animations that distract or annoy users
- Performance issues from excessive animation
- No consideration for users who prefer reduced motion
- Inconsistent animation timing across the application

## Solution

Use purposeful animations that enhance user experience while maintaining performance and accessibility.

## Animation Principles

### Purposeful Motion

Animations should:

- Provide feedback (user actions)
- Orient users (state changes)
- Guide attention (focus)
- Create continuity (transitions)

### When to Animate

| Situation | Animation |
|-----------|-----------|
| Button click | Scale/fade feedback |
| Page transitions | Fade/slide |
| Modal open/close | Scale/fade |
| Loading states | Spinner/pulse |
| Hover states | Color/transform |
| Focus states | Focus ring |

## CSS Transitions

### Basic Syntax

```css
.button {
  transition: property duration timing-function;
}

/* Common patterns */
.element {
  transition: background-color 200ms ease;
  transition: transform 150ms ease-out;
  transition: opacity 300ms ease-in-out;
}
```

### Timing Functions

```css
/* Common timing functions */
ease           /* Default - slow start, fast, slow end */
linear         /* Constant speed */
ease-in        /* Slow start, fast end */
ease-out       /* Fast start, slow end */
ease-in-out    /* Slow start, fast, slow end */

/* CSS custom easing */
.element {
  transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

### Transition Properties

```css
.element {
  /* Shorthand */
  transition: all 200ms ease;
  
  /* Or individual */
  transition-property: opacity, transform;
  transition-duration: 200ms;
  transition-timing-function: ease;
  transition-delay: 0;
}
```

## CSS Animations

### Keyframes

```css
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.element {
  animation: fadeIn 300ms ease forwards;
}
```

### Common Animation Patterns

```css
/* Pulse */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Spin (for loading) */
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Shake (for errors) */
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
  20%, 40%, 60%, 80% { transform: translateX(5px); }
}
```

## Micro-interactions

### Button Feedback

```css
.button {
  transition: transform 100ms ease;
}

.button:hover {
  transform: scale(1.02);
}

.button:active {
  transform: scale(0.98);
}
```

### Focus Transitions

```css
.input {
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}
```

### List Item Stagger

```css
.list-item {
  animation: fadeInUp 300ms ease backwards;
}

.list-item:nth-child(1) { animation-delay: 0ms; }
.list-item:nth-child(2) { animation-delay: 50ms; }
.list-item:nth-child(3) { animation-delay: 100ms; }
.list-item:nth-child(4) { animation-delay: 150ms; }
/* etc */
```

## Performance

### Animating Expensive Properties

| Animate | Avoid animating |
|---------|------------------|
| transform | width, height |
| opacity | top, left |
| rotate | margin, padding |
| scale | border-radius |
| | background-color |

### Use transform and opacity

```css
/* ❌ Bad - triggers layout */
.animate {
  animation: moveElement 1s;
}

@keyframes moveElement {
  from { left: 0; }
  to { left: 100px; }
}

/* ✅ Good - uses compositor */
.animate {
  animation: moveElement 1s;
}

@keyframes moveElement {
  from { transform: translateX(0); }
  to { transform: translateX(100px); }
}
```

### will-change

Use sparingly:

```css
/* Only when needed */
.modal {
  will-change: opacity, transform;
}

/* Remove after animation */
.modal.done {
  will-change: auto;
}
```

## Reduced Motion

### Respect User Preference

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Implementation

```tsx
function AnimatedComponent({ children }) {
  const prefersReducedMotion = useReducedMotion()
  
  return (
    <div className={prefersReducedMotion ? 'no-motion' : 'animate'}>
      {children}
    </div>
  )
}
```

## Animation Duration Guidelines

| Duration | Use Case |
|----------|----------|
| 100-150ms | Micro-interactions, hover states |
| 200-300ms | Standard transitions |
| 400-500ms | Complex transitions, modals |
| 500ms+ | Page transitions (rarely) |

## Key Takeaways

- Animations should have purpose - feedback, orientation, or guidance
- Keep animations short (200-300ms typical)
- Animate only transform and opacity for performance
- Always respect prefers-reduced-motion
- Test on low-end devices
- Use consistent easing functions
- Consider stagger for list animations
