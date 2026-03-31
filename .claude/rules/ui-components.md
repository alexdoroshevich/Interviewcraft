# UI Component Library

This project uses **Base UI** (`@base-ui/react`) + custom wrappers in `frontend/components/ui/`.
Do NOT suggest installing shadcn/ui — it is NOT used. Components are custom-built on Base UI primitives.

## Available Components

Import from `@/components/ui/<name>`:

| Component | File | Key props / notes |
|-----------|------|-------------------|
| `Alert`, `AlertDescription` | `alert.tsx` | `variant="default"\|"destructive"` |
| `Badge` | `badge.tsx` | `variant="default"\|"secondary"\|"outline"\|"destructive"` |
| `Button` | `button.tsx` | `variant`, `size` — or use Tailwind classes `btn-primary`, `btn-secondary` |
| `Card`, `CardContent` | `card.tsx` | `size="sm"` available on Card |
| `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription` | `dialog.tsx` | Modal overlay |
| `Input` | `input.tsx` | Standard text input |
| `Label` | `label.tsx` | Form label |
| `Progress` | `progress.tsx` | `value={0-100}` |
| `RadioGroup`, `RadioGroupItem` | `radio-group.tsx` | |
| `ScrollArea` | `scroll-area.tsx` | Scrollable container |
| `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue` | `select.tsx` | |
| `Separator` | `separator.tsx` | Horizontal divider |
| `Skeleton` | `skeleton.tsx` | Loading placeholder |
| `Switch` | `switch.tsx` | Toggle |
| `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` | `tabs.tsx` | Base UI tabs — active state uses `data-[active]:*`, hidden panels use `data-[hidden]:hidden` |
| `Textarea` | `textarea.tsx` | Multi-line input |
| `Tooltip`, `TooltipContent`, `TooltipProvider`, `TooltipTrigger` | `tooltip.tsx` | |

## Custom Components (project-specific)

| Component | File | Purpose |
|-----------|------|---------|
| `AnimatedScore` | `ui/AnimatedScore.tsx` | Animated number display for scores |
| `DeltaBadge` | `ui/DeltaBadge.tsx` | Score change indicator (+5, -3) |
| `EmptyState` | `ui/EmptyState.tsx` | Empty list placeholder with CTA |
| `ScoreBenchmark` | `ui/ScoreBenchmark.tsx` | Score vs benchmark comparison |

## Shared Components

Located in `frontend/components/` (not `ui/`):

- `AppNav` — top navigation bar, includes dark mode toggle
- `SkillRadar`, `SkillList`, `SkillSparkline` — skill graph components
- `BeatYourBest` — personal best challenge UI
- `CodeNotebook` — in-session code editor
- `DrawingCanvas` — in-session system design canvas

## CSS Utility Classes (globals.css)

- `btn-primary` — indigo filled button
- `btn-secondary` — slate outlined button
- `card` — base card with border + bg
- `animate-fade-in` — fade-in on mount

## Rules

- **Never** add new npm UI packages without checking this list first.
- **Never** use `shadcn/ui` CLI (`npx shadcn add`) — it would overwrite our custom wrappers.
- For a missing component: build it using Base UI primitives + Tailwind classes.
- Tabs active state: `data-[active]:*` (NOT `data-active:*` — Tailwind needs bracket syntax).
- Dark mode: use `dark:` Tailwind variants. CSS variables in `globals.css` cover radar colors.
