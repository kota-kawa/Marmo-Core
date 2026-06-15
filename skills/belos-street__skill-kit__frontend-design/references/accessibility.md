---
name: accessibility
description: Web accessibility fundamentals including ARIA, keyboard navigation, screen reader support, and WCAG guidelines for inclusive design.
---

# Accessibility

> A guide to building accessible web interfaces that work for everyone - including users with disabilities.

## Problem

- Content not usable by screen reader users
- Keyboard users can't navigate the interface
- Missing focus indicators
- Inaccessible forms and interactive elements

## Solution

Follow WCAG guidelines and use semantic HTML with proper ARIA attributes.

## Semantic HTML

### The Foundation

Semantic HTML provides built-in accessibility:

```html
<!-- ❌ Bad - meaningless -->
<div class="header"></div>
<div class="btn">Click</div>
<div onclick="submit()">Submit</div>

<!-- ✅ Good - semantic -->
<header></header>
<button>Click</button>
<form><button type="submit">Submit</button></form>
```

### Semantic Elements

```html
<header>    <!-- Page or section header -->
<nav>       <!-- Navigation links -->
<main>      <!-- Main content area -->
<article>   <!-- Self-contained content -->
<section>   <!-- Thematic grouping -->
<aside>     <!-- Sidebar content -->
<footer>    <!-- Page or section footer -->

<button>    <!-- Interactive button -->
<a>         <!-- Link -->
<input>     <!-- Form input -->
<label>     <!-- Input label -->
<select>    <!-- Dropdown -->
<textarea>  <!-- Multi-line input -->
```

## Keyboard Navigation

### Focus Order

```html
<!-- Logical tab order -->
<header>
  <a href="/">Logo</a>
  <nav>
    <a href="/about">About</a>
    <a href="/contact">Contact</a>
  </nav>
</header>
<main>
  <h1>Welcome</h1>
  <button>Get Started</button>
</main>
```

### Skip Links

```html
<body>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  <header>...</header>
  <main id="main-content">
    <!-- Page content -->
  </main>
</body>

<style>
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: blue;
  color: white;
  padding: 8px;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
</style>
```

### Focus Management

```tsx
function Modal({ isOpen, onClose, children }) {
  const modalRef = useRef(null)
  
  useEffect(() => {
    if (isOpen) {
      modalRef.current?.focus()
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])
  
  if (!isOpen) return null
  
  return (
    <div 
      role="dialog" 
      aria-modal="true"
      ref={modalRef}
      tabIndex={-1}
    >
      <button onClick={onClose}>Close</button>
      {children}
    </div>
  )
}
```

## Focus Indicators

### Always Visible

```css
/* ❌ Bad - removes focus */
:focus {
  outline: none;
}

/* ✅ Good - visible focus */
:focus-visible {
  outline: 2px solid blue;
  outline-offset: 2px;
}

/* Custom focus style */
.button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px var(--color-primary-light);
}
```

## ARIA

### When to Use ARIA

1. When semantic HTML isn't enough
2. For custom interactive components
3. For dynamic content updates

### ARIA Roles

```html
<!-- Navigation -->
<nav role="navigation" aria-label="Main">
<nav role="navigation" aria-label="Footer">

<!-- Landmark roles -->
<div role="banner">Header</div>
<div role="main" id="main">Main</div>
<div role="complementary">Sidebar</div>
<div role="contentinfo">Footer</div>
```

### ARIA Attributes

```html
<!-- Hidden content -->
<span aria-hidden="true">Icon</span>
<span class="visually-hidden">Close</span>

<!-- Live regions for dynamic content -->
<div aria-live="polite">Message</div>
<div aria-live="assertive">Error</div>

<!-- Expanded state -->
<button aria-expanded="false" aria-controls="menu">
  Menu
</button>
<div id="menu" hidden>...</div>

<!-- Current page -->
<a href="/current" aria-current="page">Home</a>
```

## Forms

### Labeling

```html
<!-- ❌ Bad -->
<input placeholder="Email">
<div>Name</div>
<input>

<!-- ✅ Good -->
<label for="email">Email</label>
<input id="email" type="email">

<!-- Or implicit -->
<label>
  Email
  <input type="email">
</label>
```

### Error Messages

```html
<label for="password">Password</label>
<input 
  id="password" 
  type="password"
  aria-describedby="password-hint"
  aria-invalid="true"
>
<p id="password-hint" class="error">
  Password must be at least 8 characters
</p>
```

### Required Fields

```html
<label for="name">
  Name
  <span aria-label="required">*</span>
</label>
<input id="name" required aria-required="true">
```

## WCAG Guidelines

### Quick Reference

| Principle | Description |
|-----------|-------------|
| Perceivable | Content must be presentable to users |
| Operable | Interface must be usable |
| Understandable | Information must be understandable |
| Robust | Content must be interpreted reliably |

### Key Requirements

| Level | Contrast | Keyboard | Focus | Labels |
|-------|----------|----------|-------|--------|
| A | 3:1 | Required | Required | Required |
| AA | 4.5:1 | Required | Required | Required |
| AAA | 7:1 | Required | Required | Required |

## Testing Tools

- Chrome DevTools Accessibility Audit
- axe DevTools
- WAVE Web Accessibility Evaluation Tool
- Screen readers (NVDA, VoiceOver)

## Key Takeaways

- Use semantic HTML whenever possible
- Ensure keyboard navigability
- Never remove focus indicators
- Use ARIA only when necessary
- Provide proper form labels
- Test with screen readers
- Follow WCAG guidelines (minimum AA)
