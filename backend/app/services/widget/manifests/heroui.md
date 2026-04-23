# HeroUI Component Manifest

Use HeroUI (formerly NextUI) components. All pre-bundled as global variables.

## Layout
- `Card`, `CardHeader`, `CardBody`, `CardFooter` — glassmorphism-style surface
- `Divider` — horizontal separator

## Data Display
- `Table`, `TableHeader`, `TableBody`, `TableColumn`, `TableRow`, `TableCell` — semantic table with built-in styles
- `Chip` — compact label with color: `default | primary | secondary | success | warning | danger`
- `Progress` — value 0–100 with label support

## Typography
Use HeroUI's `className` prop for Tailwind classes (HeroUI is Tailwind-based).
- Large value: `text-4xl font-bold text-default-900`
- Label: `text-small text-default-500`

## Colors
HeroUI uses semantic color tokens:
- `text-default-900`, `text-default-500` — primary/secondary text
- `bg-default-100` — subtle background
- `text-primary`, `text-success`, `text-danger`, `text-warning`

## Recharts Integration
Wrap charts in `<Card><CardBody>`. Use `width="100%"` and numeric `height`.

## Rules
- No network calls, no `import`, no `require`
- All components available as `window.HeroUI.*`
- Use Tailwind utility classes; the design system token scale is pre-configured
