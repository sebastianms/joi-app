# Bootstrap 5 Component Manifest

Use Bootstrap 5 CSS classes. No JS plugins needed — all interactive behavior is disabled inside the sandbox.

## Layout
- Grid: `container-fluid`, `row`, `col`, `col-md-*`
- Card: `card`, `card-body`, `card-header`, `card-footer`, `card-title`, `card-text`

## Data Display
- Table: `table table-striped table-bordered table-hover table-sm`
- Badge: `badge bg-primary | bg-secondary | bg-success | bg-danger | bg-warning text-dark`
- Progress: `progress` > `progress-bar` with `style="width: X%"`

## Typography
- Headings: `h1`–`h6` or `.h1`–`.h6`
- Muted: `text-muted`
- Colors: `text-primary`, `text-success`, `text-danger`, `text-warning`

## Utilities
- Spacing: `p-3`, `m-2`, `mt-3`, `gap-2`
- Flex: `d-flex`, `align-items-center`, `justify-content-between`
- Text align: `text-start`, `text-center`, `text-end`

## Recharts Integration
Wrap charts in a `<div class="card"><div class="card-body">`. Charts use 100% width.

## Rules
- No network calls, no `import`, no `require`
- Bootstrap CSS is pre-injected in the bundle stylesheet
- Do not use Bootstrap JS (`data-bs-*` attributes are inert)
