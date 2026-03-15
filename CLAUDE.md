## Design Context

### Users
Multi-user personal health tool shared with others. Users are health-conscious individuals tracking daily dietary intake — logging ingredients, composing meals, and reviewing calorie summaries. The interface should feel polished and intuitive enough for varied users, not just the developer.

### Brand Personality
**Warm, friendly, approachable.** Feels like a helpful companion for building healthy habits. Soft edges, inviting tone, human touch. Not clinical or intimidating.

### Aesthetic Direction
- **Visual tone**: Light, warm, organic. Cream surfaces with teal accents. Earthy and calm.
- **Typography**: Fraunces (serif) for display/headings brings warmth and personality. Space Grotesk (sans-serif) for body/UI keeps things clean and readable.
- **Color palette**: Defined in `frontend/src/index.css` — cream (`--surface`), teal (`--accent`), muted greens (`--ink`, `--muted`). Amber warnings, warm-red errors.
- **Theme**: Light mode only. Maintain the current warm cream palette.
- **Anti-references**: Avoid cold/clinical fitness apps, dark aggressive designs, or overly minimal "developer tool" aesthetics.
- **References**: Think friendly recipe apps, warm wellness tools. Human, not sterile.

### Design Principles
1. **Warmth over precision** — Prefer soft, organic shapes (large radii, pill buttons) over sharp geometric edges. The app should feel welcoming, not technical.
2. **Clarity through hierarchy** — Use the serif/sans-serif pairing, weight, size, and color to create clear visual hierarchy. Every screen should have an obvious focal point.
3. **Quiet interactions** — Animations should be subtle (fade-up, gentle lifts). No flashy transitions. Motion serves orientation, not decoration.
4. **Accessible by default** — Semantic HTML, keyboard navigation, reasonable contrast ratios, visible focus states. Follow standard best practices without targeting a specific WCAG level.
5. **Simple and lightweight** — No UI library dependencies. Vanilla CSS with custom properties. Keep the bundle small and the design system intentional.

### Technical Design Constraints
- React 19 + Vite SPA, vanilla CSS (no Tailwind, no component library)
- CSS custom properties defined in `frontend/src/index.css` `:root`
- All styles in `frontend/src/App.css` and `frontend/src/index.css`
- Design reference guides in `.claude/skills/frontend-design/reference/` (motion, spatial, interaction, responsive)
- Mobile-first responsive design using `clamp()` and `auto-fit` grids
