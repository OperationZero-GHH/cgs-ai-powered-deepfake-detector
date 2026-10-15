# CGS DeepFake Shield design system

## Brand

The interface uses a dark-first, evidence-led visual style. Deep navy establishes the workspace; electric cyan identifies the brand; signal blue marks primary actions. The shield mark combines a geometric outline with image-scan corner brackets.

## Typography

- **Inter** is used for interface and report text. It is self-hosted through Fontsource and supports weights 400–900.
- **IBM Plex Mono** is reserved for hashes, report IDs, timestamps, technical metadata, and model states. The 400, 500, 600, and 700 weights are self-hosted.
- Both font families use system fallbacks. The application makes no third-party font requests.

## Color tokens

| Role | Dark theme | Light theme |
|---|---|---|
| Page background | `#0B1020` | `#F8FAFC` |
| Surface | `#111827` | `#FFFFFF` |
| Raised surface | `#1E293B` | `#F1F5F9` |
| Primary text | `#E5E7EB` | `#0F172A` |
| Secondary text | `#94A3B8` | `#475569` |
| Borders | `#263248` | `#CBD5E1` |
| Brand accent | `#22D3EE` | `#0891B2` |
| Primary action | `#3B82F6` | `#2563EB` |
| AI-specific information | `#818CF8` | `#6366F1` |
| Successful processing | `#34D399` | `#047857` |
| Uncertain findings | `#FBBF24` | `#92400E` |
| Errors | `#F87171` | `#B91C1C` |

The tokens live in `apps/web/src/app/theme.css`. Dark mode is the default. One shared theme control stores a preference in local storage when browser storage is available and synchronizes copies across the current page and other tabs. Public pages, authentication forms, and the administrator workspace use the same control and embossed surface tokens. Switching updates the theme directly without a full-screen ripple; reduced-motion preferences are respected.

## Interface rules

- Use status text as well as color. Amber marks inconclusive evidence; green does not imply authenticity.
- Keep the sample report visibly illustrative. The real report uses actual API observations and clearly marks unavailable detector tasks.
- Keep focus indicators visible, use keyboard-accessible controls, and respect reduced-motion preferences.
- Use the shared raised, inset, and embossed tokens for surfaces and controls instead of one-off theme-specific shadows.
- Use 10–12 px button radii, 12 px card radii, subtle borders, and restrained shadows.
- Responsive layouts collapse the public hero and analysis report to a single column on smaller screens.
