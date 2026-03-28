---
date: 2026-03-28
topic: city-comparison
---

# City Comparison

## Problem Frame

The Urban World app currently lets users explore one city at a time. There's no way to directly compare two cities across population, density, area, growth trends, radial profiles, and urban form — which is arguably the most powerful use of the dataset. A URL-driven comparison feature makes comparisons shareable, bookmarkable, and linkable from articles or research.

## Requirements

**URL and Routing**
- R1. Comparison lives at `/compare/[id1]+[id2]` where IDs are numeric city IDs (e.g., `/compare/10933+5472`)
- R2. The URL is the source of truth — navigating directly to a comparison URL loads both cities without extra interaction

**Map**
- R3. Two maps displayed side by side in the main content area, split vertically (each city gets roughly half the width)
- R4. Maps are zoom- and pan-synced — interacting with either map moves both, ensuring the same scale for fair visual comparison
- R5. Each map is centered on its respective city's bounding box and shows that city's boundaries from PMTiles

**Sidebar — Metric Table**
- R6. Sidebar shows a comparison metric table at the top: city names as column headers, rows for population, density (per km²), area (km²), and growth rate — with the larger value visually highlighted
- R7. Metrics reflect the currently selected epoch (shared epoch slider)

**Sidebar — Overlay Charts**
- R8. Radial density profiles for both cities overlaid on the same chart with distinct colors and a legend
- R9. Population time-series sparklines for both cities overlaid on the same chart, showing trajectories across all epochs

**Epoch Control**
- R10. A single shared epoch slider controls both cities simultaneously (same year for both)

**Entry Points**
- R11. A "Compare with..." button on the existing city page (`/city/[id]`) opens a city search; selecting a second city navigates to `/compare/[id1]+[id2]`
- R12. Direct URL navigation works without requiring any prior interaction

## Success Criteria

- A user can land on a comparison URL and immediately see two synced maps + unified comparison data without extra clicks
- The same-zoom-level constraint makes visual area and density comparison honest and intuitive
- Overlaid radial profiles clearly show how density gradients differ between two cities

## Scope Boundaries

- Exactly 2 cities per comparison (no 3+ city grids)
- No independent epoch selection per city — single shared epoch
- No comparison from the rankings page in V1 (entry is via city page button or direct URL)
- No server-side rendering or OG image generation for comparison pages in V1

## Key Decisions

- **Synced split maps** over single map or independent maps: same zoom level is essential for honest visual comparison of urban extent and density
- **Overlay charts** over side-by-side panels: overlaid radial profiles and sparklines on shared axes make differences immediately visible
- **Sidebar retained** for comparison data: keeps the layout consistent with the single-city experience
- **`+` separator in URL** (e.g., `id1+id2`): readable, does not require encoding, unambiguous

## Outstanding Questions

### Deferred to Planning
- [Affects R4][Technical] Best approach to sync two MapLibre GL instances (shared camera state via events, or a wrapper library?)
- [Affects R8][Technical] How to overlay two radial profile datasets on the existing chart component (extend RadialProfileChart or new ComparisonRadialChart?)
- [Affects R3][Technical] Responsive behavior — how should the split maps degrade on narrow viewports (stack vertically, or hide one map?)
- [Affects R11][Needs research] Where exactly to place the "Compare with..." button in CityInfoPanel without cluttering the existing UI

## Next Steps

-> `/ce:plan` for structured implementation planning
