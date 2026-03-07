## 2023-10-27 - Hidden Text Accessibility Trap
**Learning:** Using `hidden sm:inline` to visually hide button text on mobile also hides the text from screen readers by setting `display: none`. This results in buttons having no accessible name on smaller viewports if an `aria-label` isn't provided.
**Action:** Always provide an explicit `aria-label` when using responsive display utilities (like `hidden`, `sm:block`) to visually hide text within interactive elements.
