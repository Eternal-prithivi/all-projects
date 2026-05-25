# Zenith Design System Guidelines

> 🎨 **Notice to all future AI Agents:**
> You MUST follow these design principles and utilize the CSS tokens defined in `frontend/src/index.css`. The application has a premium, modern, glassmorphic aesthetic ("Pro Dashboard"). Do NOT introduce generic styling or override these foundations.

---

## 1. Core Philosophy

Zenith is a premium cloud management tool. It should feel **slick, expensive, and dynamic.**
- **Depth:** Elements should appear layered (elevated cards floating over a subtle radial background).
- **Glassmorphism:** Use heavy blurs (`backdrop-filter: blur(16px)` or higher) combined with semi-transparent backgrounds to create frosted glass effects.
- **Interactivity:** Every clickable element or card must respond to hover with a slight lift (`transform: translateY()`), a glowing drop-shadow, and micro-animations.

---

## 2. Global Tokens (Use These, Don't Hardcode!)

All colors, spacing, and shadows are defined in `frontend/src/index.css` as `--var` tokens.

### Colors
- **Backgrounds:** `--bg-base` (deep space black), `--bg-surface` (translucent), `--bg-card` (frosted glass base).
- **Accents:** `--gold-primary` (`#d4af37`), `--gold-light`, `--gold-dark`.
- **States:** `--success` (green), `--warning` (amber), `--danger` (red), `--info` (blue).
- **Text:** `--text-primary` (bright white/off-white), `--text-secondary` (grey), `--text-muted` (darker grey).
- **Borders:** `--border-default` (`rgba(255, 255, 255, 0.08)` for subtle card borders).

### Shadows
- `--shadow-card`: Standard subtle drop shadow.
- `--shadow-gold`: Glowing gold shadow for hover states.

### Radii
- `--radius-sm` (6px), `--radius-md` (10px), `--radius-lg` (14px).

---

## 3. UI Component Standards

### Cards (Glassmorphism)
When creating a new dashboard widget or settings panel, it must match the `stat-card` or `info-card` aesthetic:
```css
.my-new-card {
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-default);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  transition: transform var(--duration-normal) var(--ease-spring),
              box-shadow var(--duration-normal) var(--ease-out);
}

.my-new-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-gold);
  border-color: var(--gold-border);
}
```

### Typography
- We use `Inter` and `Outfit`. Headers (`h1`, `h2`) should often use gradient text if they are primary focal points.
- Never use `#FFF` for standard text; use `var(--text-primary)` which is slightly softer.

### Animations
Leverage the utility classes in `index.css`:
- `.animate-fade-in-up` (for cards entering the screen)
- `.stagger-children` (to make grid items load sequentially)
- `.gold-shimmer-line` (for decorative dividers)

---

## 4. Anti-Patterns (What to Avoid)

❌ **Do NOT** use solid gray backgrounds (`#333`, `#222`) for cards. It ruins the glass effect.
❌ **Do NOT** use flat borders without hover states.
❌ **Do NOT** introduce new generic accent colors (e.g., standard CSS `blue` or `red`). Always use the variables.
❌ **Do NOT** forget to add `transition` properties when adding `:hover` states. Immediate snaps feel cheap; use `var(--duration-normal) var(--ease-out)`.
❌ **Do NOT** use `#f4c542` or `#f5d063` for gold — the correct gold is `var(--gold-primary)` = `#d4af37`.
❌ **Do NOT** define duplicate `:root` variables in individual CSS files. All tokens live in `index.css`.
❌ **Do NOT** use purple/pink/indigo accent glows (e.g., `rgba(99, 102, 241, ...)`) — those are from a pre-Zenith theme. Always use gold tones.

---

## 5. File Upgrade Status

### Current UI Polish Session — 2026-05-25

Pre-polish design score: **78/100**.

Post-polish score for dashboard-focused surfaces: **86/100**.

Post-production-standards pass for dashboard-adjacent surfaces: **91/100**.

Completed improvements:
- Tightened dashboard overview hierarchy and visual polish while preserving Mission Control layout.
- Replaced casual emoji-based dashboard/VM controls with established SVG/icon components where practical.
- Removed obvious legacy purple/blue/pink gradients and hardcoded colors from high-traffic dashboard and VM surfaces.
- Brought VM cluster, global search, breadcrumbs, loading, empty states, and base typography closer to Zenith tokens.
- Added `sr-only`, focus-visible outlines, dialog labelling, explicit button types, and better ARIA labels on key controls.
- Tokenized Cost Simulator, Cost Optimization, Storage process cards, Profile stats, and Cost Analysis command controls.
- Verified with frontend lint and production build. Lint warning count is down from 354 to 43; remaining warnings are pre-existing outside this focused design pass.

Files that have been upgraded to the Zenith Design System:

| File | Status | Notes |
|------|--------|-------|
| `index.css` | ✅ Upgraded | Design tokens, radial bg, glassmorphism utils |
| `dashboard-enhanced.css` | ✅ Upgraded | Glassmorphism cards, spring transitions |
| `dashboard.css` | ✅ Upgraded | Gold shimmer, fade-in |
| `sidebar.css` | ✅ Upgraded | Active states, hover gradient |
| `footer.css` | ✅ Upgraded | Gold gradient top border |
| `auth.css` | ✅ Already premium | Gold mesh gradients, glass form |
| `login.css` | ✅ Upgraded | Fixed purple→gold backgrounds |
| `home.css` | ✅ Upgraded | Glass feature cards, pricing cards |
| `storage.css` | ✅ Upgraded | Removed duplicate :root, uses tokens |
| `profile.css` | ✅ Upgraded | Glass cards, correct gold, hover states |
| `error-pages.css` | ✅ Upgraded | 404 page particles |
| `settings.css` | ⚠️ Partial | BYOC section is premium, rest needs audit |
| `billing.css` | ⚠️ Needs audit | May have old hardcoded colors |
| `vmcluster.css` | ✅ Upgraded | Header, topology, process cards, metrics, modals, buttons, badges, and workload guidance use Zenith tokens/glass |
| `global-search.css` | ✅ Upgraded | Tokenized modal, search result icons, and corrected dashboard routes |
| `emptystate.css` | ✅ Upgraded | Tokenized glass empty states with SVG icon support |
| `breadcrumbs.css` | ✅ Upgraded | Tokenized navigation color states |
| `loading.css` | ✅ Upgraded | Tokenized spinner and loading text |
| `costsimulator.css` | ✅ Upgraded | Tokenized workbench UI, service selector, price cards, badges, and notes |
| `costoptimization.css` | ✅ Upgraded | Tokenized guide layout, SVG icons, provider marks, strategy cards, and monitoring cards |
| `costanalysis.css` | ⚠️ Partial | Command controls and visible emoji UI cleaned; deeper report/table styling still needs full audit |
| `security-settings.css` | ⚠️ Needs audit | Check for consistent theming |

---

## 6. Mission Control Layout (Phase 2.5 — Pending)

> **STATUS:** ✅ Implemented (2026-05-24). All components, CSS, and layout are live.

### Navigation Rail (replaces sidebar)
- Default width: `56px` (icon-only, icons centered)
- Hover width: `220px` (text labels slide in with `opacity` + `translateX`)
- Active indicator: 3px gold vertical bar on left edge
- Mobile (< 768px): transforms into bottom tab bar
- Component: `Sidebar.jsx` → complete rewrite
- CSS: `sidebar.css` → complete rewrite

### Bento Grid
- CSS Grid: `grid-template-columns: repeat(3, 1fr)`
- Large cards: `grid-column: span 2; grid-row: span 2`
- Medium cards: `grid-column: span 1; grid-row: span 1`
- Gap: `var(--space-lg)`
- Cards must use `.bento-card` class with `.size-lg`, `.size-md`, `.size-sm` modifiers

### Charting (Recharts)
- Library: `recharts` (React-native, tree-shakable)
- Chart color: Gold gradient (`#ffd700` → `var(--gold-primary)`)
- Tooltip: Glassmorphism styled (dark glass background, gold border)
- Component: `SparklineChart.jsx` wraps Recharts `AreaChart`
- Data: Initially synthetic (7-day split from monthly total). Real data via `/api/dashboard/cost-trend` in Phase 4.

### Progress Rings
- SVG-based, pure CSS animation (`stroke-dashoffset` transition)
- Component: `ProgressRing.jsx` accepts `percentage`, `color`, `size`
- Used in: Storage card, VM Health card

### Animated Numbers
- Hook: `useCountUp(targetValue, duration)` 
- Uses `requestAnimationFrame` with ease-out deceleration
- Duration: 1200ms default
- All stat card values must use this hook

### Greeting
- Time-aware tone kicker: morning operations / cloud command active / evening optimization / night watch online
- Font: Outfit, responsive hero-scale, weight 800, gold gradient text
- Subtitle: friendly date format with cloud overview context
