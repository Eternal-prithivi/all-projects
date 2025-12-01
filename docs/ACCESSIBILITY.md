# Accessibility Guidelines

## Overview
This document outlines the accessibility features implemented in the Cloud Resource Optimization Platform to ensure compliance with WCAG 2.1 Level AA standards.

## Implemented Features

### 1. Keyboard Navigation
- **Skip to Main Content**: Press `Tab` on any page to reveal a "Skip to main content" link
- **All interactive elements**: Fully keyboard accessible with proper tab order
- **Keyboard shortcuts**: 
  - `?` - Show keyboard shortcuts help
  - `/` or `Cmd/Ctrl + K` - Open global search
  - `Alt/Option + Shift + N` - Navigate to VM Cluster

### 2. Screen Reader Support

#### Semantic HTML
- Proper use of `<main>`, `<nav>`, `<aside>`, and `<header>` landmarks
- All forms have associated `<label>` elements
- Headings follow proper hierarchy (h1 → h2 → h3)

#### ARIA Attributes
- **Forms**: All inputs have `aria-required`, `aria-describedby`, and `aria-label` attributes
- **Navigation**: Sidebar has `role="navigation"` and `aria-label="Main navigation"`
- **Alerts**: Error/success messages use `role="alert"` and `aria-live` regions
- **Buttons**: All action buttons have descriptive `aria-label` attributes
- **Icons**: Decorative icons marked with `aria-hidden="true"`

#### Examples
```jsx
// Login form
<form aria-label="Login form">
  <input 
    aria-required="true"
    aria-describedby="login-error"
    autoComplete="username"
  />
</form>

// Navigation menu
<nav role="navigation" aria-label="Main navigation">
  <ul role="menu">
    <li role="none">
      <NavLink role="menuitem" aria-label="Dashboard overview">
        Overview
      </NavLink>
    </li>
  </ul>
</nav>

// Action buttons
<button aria-label="Release VM instance-1">Release</button>
<button aria-label="Download SSH key for instance-1">Download</button>
```

### 3. Form Accessibility

#### All Forms Include:
- `autocomplete` attributes for browser autofill
- `aria-required="true"` for required fields
- `aria-describedby` linking to help text/error messages
- Helper text with unique IDs for screen readers
- Proper input types (`email`, `password`, etc.)
- Minimum length validation feedback

#### Login Form Example:
```jsx
<input 
  type="text"
  id="login-username"
  aria-required="true"
  autoComplete="username"
  aria-describedby={error ? "login-error" : undefined}
/>
{error && <p id="login-error" role="alert">{error}</p>}
```

### 4. Color Contrast
- **Background/Text**: All text meets WCAG AA contrast ratio (4.5:1 minimum)
- **Buttons**: High contrast for all states (normal, hover, disabled)
- **Status indicators**: Not relying solely on color (icons + text)

### 5. Focus Management
- **Visible focus indicators**: All interactive elements have visible focus outlines
- **Skip link**: Hidden until focused, appears at top of page
- **Modal dialogs**: Focus trapped within modal when open
- **Form validation**: Focus moved to first error on submit

### 6. Live Regions
Toast notifications use `aria-live="polite"` for non-critical alerts and `aria-live="assertive"` for errors:
```jsx
<ToastContainer 
  role="alert"
  aria-live="polite"
/>
```

### 7. Alternative Text
- All decorative SVG icons: `aria-hidden="true"`
- All functional images: Descriptive `alt` text or `aria-label`
- User avatars: Initials visible to screen readers

## Testing Checklist

### Manual Testing
- [ ] Tab through entire page (logical order)
- [ ] Use only keyboard to complete all tasks
- [ ] Test skip link (Tab on page load)
- [ ] Verify focus visible on all elements
- [ ] Check all buttons have descriptive labels

### Screen Reader Testing
- [ ] Test with NVDA (Windows)
- [ ] Test with JAWS (Windows)
- [ ] Test with VoiceOver (macOS)
- [ ] Verify form errors announced
- [ ] Check navigation menu readable

### Automated Testing
```bash
# Install axe-core for automated accessibility testing
npm install --save-dev @axe-core/react

# Run Lighthouse accessibility audit
npm run build
npx lighthouse http://localhost:5173 --view
```

## Browser Support
- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Screen reader compatibility: NVDA, JAWS, VoiceOver

## Known Issues & Future Improvements

### Current Limitations
1. Focus indicators could be more prominent (consider custom focus styles)
2. Some complex charts may need `aria-describedby` for data tables
3. Keyboard shortcuts not customizable by users

### Planned Enhancements
- [ ] Add high contrast theme toggle
- [ ] Implement focus trap for all modal dialogs
- [ ] Add configurable font size controls
- [ ] Provide keyboard shortcut customization
- [ ] Add announcement region for dynamic content updates
- [ ] Implement roving tabindex for complex widgets
- [ ] Add skip navigation for repeated content blocks

## Compliance Statement
This platform strives to meet WCAG 2.1 Level AA standards. We continuously work to improve accessibility and welcome feedback at support@zenith.com.

## Resources
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
