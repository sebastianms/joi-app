# shadcn/ui Component Manifest

Use these component primitives. All are available as global variables (no imports needed inside the iframe bundle).

## Layout
- `Card`, `CardHeader`, `CardContent`, `CardFooter` — surface container with rounded border
- `Separator` — horizontal/vertical divider

## Data Display
- `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell` — semantic table
- `Badge` — inline label with variant: `default | secondary | destructive | outline`
- `Progress` — value 0–100

## Typography
- Use Tailwind classes: `text-2xl font-bold`, `text-sm text-muted-foreground`
- Muted text: `text-muted-foreground`
- Accent: `text-primary`

## Colors (CSS variables)
- Background: `hsl(var(--background))`
- Foreground: `hsl(var(--foreground))`
- Primary: `hsl(var(--primary))`
- Muted: `hsl(var(--muted))`
- Border: `hsl(var(--border))`

## Recharts Integration
Wrap charts inside `<Card><CardContent>`. Pass `width="100%"` and `height={300}` to chart containers.

## Rules
- No network calls, no `import`, no `require`
- All components are pre-bundled; reference as `window.ShadcnUI.*`
- Use Tailwind utility classes for spacing (`p-4`, `gap-2`, `mt-2`)
