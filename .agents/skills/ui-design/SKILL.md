---
name: ui-design
description: Production-grade UI/UX design and frontend implementation skill for modern web applications. Use when creating, redesigning, reviewing, or polishing pages, dashboards, forms, tables, cards, navigation, modals, drawers, responsive layouts, design systems, interaction states, accessibility, or frontend visual consistency.
---

# Production UI Design & Frontend Engineering

## Mission

Create polished, production-ready interfaces that are:

- visually clear
- consistent
- responsive
- accessible
- maintainable
- performant
- aligned with the existing product
- safe to integrate into an existing codebase

The objective is not simply to make the interface "look better."

The objective is to improve usability, hierarchy, consistency, accessibility, maintainability, and product quality without breaking existing functionality.

Treat every UI task as production work.

---

# 1. Core Principles

Always prioritize:

1. User goals
2. Functional correctness
3. Information hierarchy
4. Usability
5. Accessibility
6. Consistency
7. Responsive behavior
8. Maintainability
9. Performance
10. Visual polish

A visually attractive interface that damages usability or application behavior is not acceptable.

Do not sacrifice functionality for appearance.

---

# 2. Preserve Existing Application Behavior

UI work must not unintentionally change business logic.

Unless explicitly requested:

- do not change API contracts
- do not modify backend behavior
- do not change authentication logic
- do not change authorization rules
- do not remove validation
- do not change routing behavior
- do not change database-related logic
- do not alter data-fetching semantics
- do not change state-management architecture
- do not remove existing features
- do not silently change user workflows
- do not hardcode production data
- do not bypass error handling
- do not replace working functionality with mock data

When redesigning an existing page, preserve all functional behavior unless the requested UX improvement explicitly requires a change.

If functionality and visual redesign conflict, preserve functionality and adapt the design.

---

# 3. Inspect the Repository Before Designing

Before implementing significant UI changes, inspect the existing project.

Understand:

- framework
- language
- routing
- component architecture
- styling approach
- design system
- icon library
- state management
- form library
- validation library
- table library
- charting library
- existing layouts
- existing reusable components
- existing responsive patterns
- theme implementation
- design tokens
- API patterns
- loading patterns
- error handling
- accessibility conventions

Relevant files may include:

- `package.json`
- Tailwind configuration
- global CSS
- theme files
- component directories
- layout components
- existing pages
- shared hooks
- utility functions
- type definitions

Do not assume a package or library exists.

Check before using it.

---

# 4. Reuse Before Creating

Before creating a new component, search for an existing one.

Prefer reusing existing:

- Button
- Input
- Select
- Checkbox
- Radio
- Switch
- Badge
- Card
- Dialog
- Drawer
- Sheet
- Tooltip
- Dropdown
- Table
- Tabs
- Avatar
- Date picker
- Pagination
- Skeleton
- Toast
- Alert
- Navigation components
- Layout components

Avoid creating visually similar duplicates.

If an existing component requires a small extension, prefer extending it rather than creating another competing implementation.

New reusable components should only be introduced when they provide clear value.

---

# 5. Respect the Existing Design System

If the project already has a design system, follow it.

Reuse:

- color tokens
- typography
- spacing
- border radius
- shadows
- component variants
- icon conventions
- animation conventions
- breakpoints
- container widths

Do not introduce a second visual language into an established application.

If no formal design system exists, infer one from the strongest existing patterns and apply it consistently.

---

# 6. Visual Hierarchy

Every screen must communicate hierarchy immediately.

Users should quickly understand:

1. Where they are
2. What the page is for
3. What information is most important
4. What action they should take
5. What information is secondary
6. Where additional actions are located

Use:

- position
- typography
- spacing
- grouping
- contrast
- size
- alignment

Do not depend on decoration alone.

---

# 7. Layout

Prefer clear and predictable layout structures.

Typical application page:

```text
Page Header
├── Breadcrumb / context
├── Title
├── Description
└── Primary actions

Primary Content
├── Summary / KPIs
├── Filters / controls
├── Main content
└── Supporting content

Secondary Content
├── Activity
├── Related information
└── Supplemental actions