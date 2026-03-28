---
title: "feat: Add city comparison with synced dual maps"
type: feat
status: completed
date: 2026-03-28
origin: docs/brainstorms/2026-03-28-city-comparison-requirements.md
deepened: 2026-03-28
---

# feat: Add city comparison with synced dual maps

## Overview

Add a `/compare/[id1]+[id2]` route that displays two cities side-by-side with synced maps, a metric comparison table, and overlaid radial profile and sparkline charts. Users enter comparison mode via a "Compare with..." button on the city page or by navigating directly to a comparison URL.

## Problem Frame

The app currently supports single-city exploration. Comparison — the most powerful use of a multi-city dataset — requires opening two tabs and mentally correlating data. A dedicated comparison view with synced zoom makes visual comparison of urban form honest and immediate. (see origin: docs/brainstorms/2026-03-28-city-comparison-requirements.md)

## Requirements Trace

- R1. Route at `/compare/[id1]+[id2]` with numeric city IDs
- R2. Direct URL navigation loads both cities without extra interaction
- R3. Two maps side by side, split vertically
- R4. Maps zoom- and pan-synced via shared view state
- R5. Each map centered on its city's bbox with PMTiles boundaries
- R6. Sidebar metric table: population, density, area, growth — larger value highlighted
- R7. Metrics reflect the shared selected epoch
- R8. Radial profiles overlaid on same chart with distinct colors + legend
- R9. Population sparklines overlaid on same chart
- R10. Single shared epoch slider
- R11. "Compare with..." button on city page opens search, navigates to comparison

## Scope Boundaries

- Exactly 2 cities (no 3+)
- Single shared epoch — no per-city epoch selection
- No comparison entry from rankings page in V1
- No SSR or OG images for comparison pages in V1
- Data source toggle remains global (both maps use same source)

## Context & Research

### Relevant Code and Patterns

- **`useViewState.ts`** — Module-level singleton storing `{ longitude, latitude, zoom, pitch, bearing }`. Stores a single center point, which means two maps sharing it would show the same location. For comparison, only the `zoom` should be shared; each map needs its own center. The composable needs to be extended or a new `useComparisonViewState` must manage shared zoom + per-map centers.
- **`useMap.ts`** — Creates MapLibre instance with PMTiles protocol, boundary layers, hover/selection interaction. PMTiles registration is already guarded by singleton flag. The composable stores map in a local `shallowRef`, not module-level, so multiple calls with different containers will create independent instances.
- **`useCityStats(cityId)`** — Accepts `MaybeRef<string>`, composes index + populations + epoch. Can be called twice with different city IDs for comparison data.
- **`RadialProfileChart.client.vue`** — Chart.js `<Line>` with single dataset. Takes `cityId` prop, builds one dataset from `getProfile()`. Extension point: accept array of city IDs, build multiple datasets with distinct colors.
- **`EpochSparkline.client.vue`** — Similar pattern; single city sparkline. Same extension approach.
- **`CitySearch.vue`** — Uses `useCitySearch` + Fuse.js, navigates on selection. Needs callback mode for comparison entry.
- **`default.vue` layout** — Search strip + sidebar + single map. Comparison needs a separate layout.
- **`AppSidebar.vue`** — `w-80` fixed, header + scrollable content slots. Reusable in comparison layout.
- **`useCitySelection.ts`** — Module-level singleton for one city. Comparison needs its own parallel state.

### External References

- MapLibre GL JS v5 supports multiple instances on the same page; the PMTiles protocol is registered globally once.
- Chart.js natively supports multiple datasets per chart with independent colors and legend entries.

## Key Technical Decisions

- **Separate `compare` layout** over conditional `default` layout: The dual-map requirement is fundamentally different from the single-map shell. A new `layouts/compare.vue` avoids conditional complexity in the existing layout, at the cost of duplicating the search strip chrome. The search strip is small (~15 lines of template), making duplication acceptable. (see origin: key decision on sidebar retention)

- **Shared zoom, independent centers for map sync**: The existing `useViewState` singleton stores a single `{ longitude, latitude, zoom }` — sharing it directly would force both maps to show the same location. Instead, comparison maps share only the zoom level via a `sharedZoom` ref, while each map maintains its own center (longitude/latitude). When one map zooms, the other matches. When one pans, only that map moves. This gives honest scale comparison (R4) while allowing each map to frame its own city (R5). A `useComparisonViewState` composable manages this: `{ sharedZoom, centerA, centerB, onZoomChange(zoom, sourceMapId), onPanChange(center, mapId) }`. The `sourceMapId` guard prevents zoom feedback loops — a map ignores zoom changes it caused. The guard flag must persist until the map's `moveend` callback fires (not cleared synchronously) since `easeTo` animations complete asynchronously.

- **New `useComparisonState` composable** over extending `useCitySelection`: The single-selection assumption is deeply embedded — `useMap` internally watches `useCitySelection` for fly-to-city, boundary highlighting, and click-to-navigate (`navigateTo('/city/${cityId}')`). It also reads `useCityHover` for hover highlights. A parallel composable holding `{ cityA: string, cityB: string }` parsed from the route is safer. Comparison maps must use `useMap` with options that override these singleton behaviors: `{ cityId, disableClickNavigation, disableSelectionWatch, disableHoverSync }`.

- **Extend existing chart components** with optional multi-city support rather than creating separate comparison chart components: `RadialProfileChart` and `EpochSparkline` gain an optional `cityIds: string[]` prop; when provided, they render multiple datasets. When only `cityId` is provided, behavior is unchanged. This avoids duplicating chart configuration and options.

- **Canonical URL ordering**: Always sort IDs numerically. `/compare/456+123` redirects to `/compare/123+456`. Left map = lower ID. Prevents duplicate URLs for the same comparison.

- **Mobile: single map with A/B toggle**: On narrow viewports (`< sm`), show one map at a time with a toggle button to switch between city A and city B. The sidebar scrolls below.

- **Same-city redirect**: `/compare/123+123` redirects to `/city/123` since a single shared epoch makes self-comparison meaningless.

- **City A/B visual identity**: A consistent color identity ties each city across maps, table, and charts. City A uses the existing `forest-600` palette; city B uses a warm contrasting color (amber/terracotta). Each map's city label, table column header, and chart dataset share the same color. This identity is defined once in a shared constant and consumed by all comparison components.

- **No deck.gl in comparison maps**: Comparison maps skip deck.gl initialization (no H3 population heatmap or radial ring overlay) to save GPU memory. Radial ring highlighting from chart hover uses a simpler approach — the chart's highlight plugin triggers `useRadialHighlight` which can be read by both maps' boundary layer styling without requiring full deck.gl layers.

- **History behavior in compare mode**: City swaps within comparison use `navigateTo(..., { replace: true })` to avoid back-button pollution.

## Open Questions

### Resolved During Planning

- **Map sync approach** (origin Q1): Share only zoom level between maps, not center. A new `useComparisonViewState` composable manages `sharedZoom` + per-map centers. The `sourceMapId` guard prevents zoom feedback loops, with the flag persisted until `moveend` (not cleared synchronously) to handle async `easeTo` animations.
- **Chart overlay approach** (origin Q2): Extend existing `RadialProfileChart` with optional `cityIds` array prop. Chart.js supports multiple datasets natively — add a second dataset with a distinct color palette.
- **Responsive behavior** (origin Q3): Single map with A/B toggle on mobile. Two synced maps on `sm+`.
- **Compare button placement** (origin Q4): Add below the city header in `CityInfoPanel`, above the data points. Small ghost button with compare icon.

### Deferred to Implementation

- **Exact hex values for city A/B color identity**: Forest-600 vs amber/terracotta direction is set, but exact values need testing against the sepia theme in both light and dark modes.
- **Right-panel padding adjustment**: The `RIGHT_PANEL_WIDTH` constant (256px) in `useMap` will significantly misalign centering on half-width maps (~530px each on 1440px viewport). Must be parameterizable in `useMap` or overridden in comparison mode.
- **Initial zoom level for two cities with very different bbox sizes**: Since maps now have independent centers, the shared zoom is set to the zoom level of the larger city's fitBounds. May need a per-map "Fit" button — test with extreme pairs like Tokyo + a small town.
- **GlobalContextPanel positioning in dual-map layout**: Currently `absolute right-4 top-4 w-56`, overlapping the right map. Needs repositioning — likely centered between the two maps or moved below the maps. The panel's world/urban population stats may be less relevant in comparison context.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
Route: /compare/[pair].vue
  ├── parseRoute("123+456") → { cityA: "123", cityB: "456" }
  ├── validate IDs → redirect if invalid, same, or non-canonical order
  │
  ├── Layout: compare.vue
  │   ├── Search strip (shared chrome)
  │   ├── AppSidebar
  │   │   └── ComparisonPanel
  │   │       ├── ComparisonMetricTable (R6, R7)
  │   │       │   └── rows: population, density, area, growth
  │   │       │       each cell: value + highlight-if-larger + city color identity
  │   │       ├── RadialProfileChart(cityIds=[A, B]) (R8)
  │   │       └── EpochSparkline(cityIds=[A, B]) × 3 metrics (R9)
  │   │
  │   └── Main area
  │       ├── Desktop (sm+): two ComparisonMap side by side (R3)
  │       └── Mobile (<sm): one ComparisonMap + A/B toggle
  │
  │   useComparisonViewState (new)
  │   ├── sharedZoom: ref<number> — synced across both maps
  │   ├── centerA: ref<{lng, lat}> — independent per map A
  │   ├── centerB: ref<{lng, lat}> — independent per map B
  │   ├── onZoomChange(zoom, sourceMapId) — zoom sync with feedback guard
  │   └── onPanChange(center, mapId) — pan updates only the source map's center
  │
  │   ComparisonMap (no deck.gl)
  │   ├── creates MapLibre instance via useMap(container, {
  │   │     cityId, disableClickNavigation, disableSelectionWatch, disableHoverSync
  │   │   })
  │   ├── reads sharedZoom from useComparisonViewState (R4)
  │   ├── manages own center from centerA/centerB (R5)
  │   ├── city name label overlay in top-left corner
  │   └── fits to city bbox on mount, sets initial sharedZoom
```

## Implementation Units

- [ ] **Unit 1: Comparison state and routing**

**Goal:** Create the route, comparison state composable, and page shell with validation/redirects.

**Requirements:** R1, R2

**Dependencies:** None

**Files:**
- Create: `app/pages/compare/[pair].vue`
- Create: `app/composables/useComparisonState.ts`
- Test: `test/composables/useComparisonState.test.ts`

**Approach:**
- `useComparisonState` parses `[pair]` route param by splitting on `+`, validates both IDs against the cities index, and exposes `{ cityA, cityB, isValid, isLoading }` as computed refs
- The page calls data loaders (`useCitiesIndex.execute()`, `useCityPopulations.execute()`, `useRadialProfiles.execute()`) same pattern as existing `pages/city/[city_id].vue`
- Validation: redirect `/compare/456+123` → `/compare/123+456` (canonical order); redirect `/compare/123+123` → `/city/123`; show error state for invalid IDs
- Page uses `definePageMeta({ layout: 'compare' })` (layout created in Unit 2)

**Patterns to follow:**
- `pages/city/[city_id].vue` for data loading and SEO meta pattern
- `useCitySelection.ts` for composable structure (module-level state, thin exported function)

**Test scenarios:**
- Happy path: `"123+456"` parses to cityA="123", cityB="456"
- Happy path: both city IDs validated against cities index
- Edge case: `"456+123"` returns redirect target `"123+456"` (canonical ordering)
- Edge case: `"123+123"` returns redirect target to single city view
- Edge case: `"123"` (no separator) returns invalid state
- Edge case: `"abc+456"` (non-numeric) returns invalid state
- Edge case: `"99999+456"` (unknown city ID) returns invalid state after index loads

**Verification:**
- Navigating to `/compare/123+456` renders the comparison page with both city IDs accessible
- Navigating to `/compare/456+123` redirects to `/compare/123+456` and renders correctly
- Non-canonical and invalid URLs redirect appropriately

---

- [ ] **Unit 2: Comparison layout**

**Goal:** Create the `compare` layout with dual-map main area and sidebar, reusing existing chrome.

**Requirements:** R3, R10

**Dependencies:** Unit 1

**Files:**
- Create: `app/layouts/compare.vue`

**Approach:**
- Structure: search strip (duplicate from default.vue) → flex row with `AppSidebar` + main area
- Main area: two map containers side by side (`flex-1` each) on `sm+`, single container with toggle on `<sm`
- Include `GlobalContextPanel` for the shared epoch slider (R10)
- Sidebar renders a `<slot>` for comparison content (filled by the page)
- Mobile toggle: a simple button that swaps which city's map container is visible, using a reactive `activeMapSide` ref

**Patterns to follow:**
- `layouts/default.vue` for layout shell structure, search strip, sidebar integration
- `AppSidebar.vue` usage (slots: `#header` for comparison header, default for scrollable content)

**Test scenarios:**
- Happy path: layout renders two map containers side by side on desktop viewport
- Happy path: epoch slider (GlobalContextPanel) is present and functional
- Edge case: on narrow viewport, only one map container is visible with a toggle button
- Edge case: toggling A/B on mobile swaps the visible map

**Verification:**
- The layout renders the correct structure at desktop and mobile breakpoints
- Sidebar and map containers are properly sized

---

- [ ] **Unit 3: Dual synced maps**

**Goal:** Render two MapLibre instances with shared zoom and independent centers via `useComparisonViewState`.

**Requirements:** R3, R4, R5

**Dependencies:** Unit 2

**Files:**
- Create: `app/components/compare/ComparisonMap.client.vue`
- Create: `app/composables/useComparisonViewState.ts`
- Modify: `app/composables/useMap.ts` (add options: `{ cityId?, disableClickNavigation?, disableSelectionWatch?, disableHoverSync? }` to override singleton behaviors)
- Test: `test/composables/useComparisonViewState.test.ts`

**Approach:**
- `useComparisonViewState` manages `sharedZoom` (synced) + `centerA`/`centerB` (independent per map). On zoom change from either map, both maps update to the new zoom. On pan, only the source map's center updates. The `sourceMapId` guard prevents zoom feedback loops — the flag persists until the `moveend` callback fires (not cleared synchronously) to handle async `easeTo` animations
- `ComparisonMap` is a client-only component that accepts `cityId` and `mapId` props
- Each map displays a translucent city name label in the top-left corner (city name + country) with the city's identity color (forest for A, amber for B)
- Each instance calls `useMap({ container, cityId, disableClickNavigation: true, disableSelectionWatch: true, disableHoverSync: true })` — these options suppress the singleton `useCitySelection`/`useCityHover` behaviors that would conflict with two maps
- No deck.gl initialization — comparison maps show boundaries only, no H3 heatmap or radial ring overlay
- On mount, each map fits to its city's bbox using `cameraForBounds`. The larger city's zoom level becomes the initial `sharedZoom`
- Each map highlights its own city's boundary using the `cityId` option passed to `useMap`, not the global `useCitySelection` singleton

**Patterns to follow:**
- `GlobalMap.client.vue` for map component structure (but simpler — no deck.gl)
- `useViewState.ts` for reactive state patterns

**Test scenarios:**
- Happy path: two map instances render, each centered on its own city
- Happy path: zooming map A updates map B to the same zoom level (sharedZoom)
- Happy path: panning map A does NOT move map B (independent centers)
- Edge case: rapid zoom gestures on one map do not cause oscillation (feedback loop guard works with async animations)
- Happy path: each map shows its city's boundaries from PMTiles with its city highlighted
- Happy path: clicking a boundary on either map does NOT navigate away from comparison
- Edge case: city name labels are visible and use the correct identity color

**Verification:**
- Two maps render side by side, each centered on a different city at the same zoom level
- Zooming either map syncs; panning does not

---

- [ ] **Unit 4: Comparison sidebar (metric table + panel)**

**Goal:** Build the complete comparison sidebar: metric table, composition panel, and section structure.

**Requirements:** R6, R7

**Dependencies:** Unit 1

**Files:**
- Create: `app/components/compare/ComparisonMetricTable.vue`
- Create: `app/components/compare/ComparisonPanel.vue`

**Approach:**
- `ComparisonPanel` accepts `cityIdA` and `cityIdB` props. Composes: header with both city names (colored with A/B identity colors), `ComparisonMetricTable`, and chart sections (added in Unit 5). Close button navigates to `/`. Scrollable content area
- `ComparisonMetricTable` calls `useCityStats(cityIdA)` and `useCityStats(cityIdB)` for reactive data. Column headers show city names with identity color dots. Rows for: population, density (per km²), area (km²), and growth rate. The larger value in each row gets a subtle highlight (`font-semibold`) — compare raw numeric values, display formatted. Equal values: neither highlighted. Missing data: show fallback gracefully
- All values react to epoch changes via the shared `useSelectedYear` singleton (R7)
- Loading: show skeleton rows while either city is loading

**Patterns to follow:**
- `CityInfoPanel.vue` for sidebar content structure, spacing, and section organization
- `DataPoint` component for value formatting patterns
- Sepia theme color tokens: `forest-700`, `body`, `muted`

**Test scenarios:**
- Happy path: table renders population, density, area, growth for both cities
- Happy path: the larger value in each row is visually highlighted
- Happy path: changing epoch via slider updates all values
- Happy path: city name headers show correct identity colors
- Edge case: one city has no population data for the selected epoch — shows fallback gracefully
- Edge case: values are equal — neither is highlighted
- Edge case: loading state shows skeletons for all sections

**Verification:**
- Metric table shows correct values for both cities at the current epoch
- Full panel renders with correct identity colors linking to maps and charts

---

- [ ] **Unit 5: Overlay charts (radial profiles + sparklines)**

**Goal:** Extend `RadialProfileChart` and `EpochSparkline` to overlay two cities' data on the same axes.

**Requirements:** R8, R9

**Dependencies:** Unit 4

**Files:**
- Modify: `app/components/city/RadialProfileChart.client.vue`
- Modify: `app/components/city/EpochSparkline.client.vue`

**Approach:**
- Both components gain an optional `cityIds?: string[]` prop alongside existing `cityId` prop. When `cityIds` is provided (length 2), build two Chart.js datasets with the city A/B identity colors and a visible legend showing city names from `useCitiesIndex`
- **RadialProfileChart**: City A dataset uses the existing ring-color gradient fill; city B uses the contrasting identity color palette. The radial highlight plugin should work in comparison mode, triggering ring highlights on both map instances via `useRadialHighlight`. Tooltip shows both cities' values at the hovered ring distance
- **EpochSparkline**: Each dataset shows the full epoch range (1975-2030) for its city. The `metric` prop already determines which field to chart. Tooltip shows both cities' values at the hovered epoch
- Both components: existing single-city usage (`cityId` prop only) works identically — no regression

**Patterns to follow:**
- Existing `RadialProfileChart.client.vue` and `EpochSparkline.client.vue` for Chart.js config
- `useCitiesIndex.getCity(id).name` for city name labels in legends

**Test scenarios:**
- Happy path: two radial profiles render as distinct colored lines/areas on the same chart
- Happy path: two sparklines render on same axes with distinct colors for a given metric
- Happy path: legends display both city names with correct identity colors
- Happy path: tooltips at a ring/epoch show values for both cities
- Edge case: one city has a radial profile, the other does not — show single profile with a "no data" note
- Edge case: profiles have different lengths — shorter profile ends, longer continues
- Edge case: one city has missing epoch data — line gaps or interpolation
- Integration: existing single-city usage (`cityId` prop only) works identically in both components

**Verification:**
- Two overlaid profiles and sparklines are visually distinguishable with identity colors
- Single-city mode is unchanged (no regression)

---

- [ ] **Unit 6: "Compare with..." entry point**

**Goal:** Add a compare button to the city page and wire up the city picker flow.

**Requirements:** R11

**Dependencies:** Units 1, 4

**Files:**
- Modify: `app/components/city/CityInfoPanel.vue`
- Create: `app/components/compare/CompareSearchModal.vue`

**Approach:**
- Add a small "Compare with..." ghost button below the city header in `CityInfoPanel`, above the data points grid
- Clicking opens `CompareSearchModal` — a modal dialog with the existing `CitySearch` fuzzy search, but configured to call a callback on selection instead of navigating directly
- On selection, navigate to `/compare/{currentCityId}+{selectedCityId}` (with canonical ordering)
- The modal should exclude the current city from search results (or disable it with "Currently viewing" label)

**Patterns to follow:**
- `CitySearch.vue` for the search input and Fuse.js integration
- `InfoModal` (global modal pattern in app.vue) for modal structure
- Nuxt UI `UModal` or `UDialog` component

**Test scenarios:**
- Happy path: clicking "Compare with..." opens a search modal
- Happy path: selecting a city navigates to `/compare/{id1}+{id2}` with canonical ordering
- Edge case: the current city is excluded or disabled in search results
- Edge case: closing the modal without selecting returns to the city page unchanged

**Verification:**
- The compare flow from city page to comparison view works end-to-end

## System-Wide Impact

- **Interaction graph:** `useMap.ts` gains optional parameters (`cityId`, `disableClickNavigation`, `disableSelectionWatch`, `disableHoverSync`) to override singleton behaviors. All parameters are optional with defaults matching current behavior, so existing callers (`GlobalMap`) are unaffected. A new `useComparisonViewState` composable is independent from the existing `useViewState` — no changes to `useViewState` needed.
- **Error propagation:** Invalid comparison URLs redirect to `/` with no error toast (consistent with how invalid `/city/[id]` URLs behave).
- **State lifecycle risks:** When navigating from `/compare/...` back to `/city/...`, the comparison layout unmounts and the default layout mounts. `useViewState` was never touched by comparison mode (comparison uses its own `useComparisonViewState`), so the single map resumes from its last state cleanly.
- **API surface parity:** No API changes. All data comes from the same JSON/PMTiles endpoints.
- **Integration coverage:** The zoom sync mechanism (Unit 3) is the highest-risk integration — two MapLibre instances sharing a `sharedZoom` ref with async animation guards. Manual testing with rapid zoom gestures is essential.
- **Unchanged invariants:** The existing city page (`/city/[id]`), rankings page (`/`), `useCitySelection` singleton, `useViewState` singleton, and `GlobalMap` component are not modified (except the small addition to CityInfoPanel in Unit 6 and optional parameters on `useMap`).

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Zoom sync feedback loop (map A zooms → sharedZoom → map B zooms → sharedZoom → oscillation) | `sourceMapId` guard in `useComparisonViewState`; flag persists until `moveend` callback (not cleared synchronously) to handle async `easeTo` animations. Pan is independent so no feedback risk there. |
| Two MapLibre instances double memory/GPU usage | Acceptable for desktop; mobile shows only one map at a time. Monitor performance with large cities (many boundary polygons). |
| `useMap` singleton composable state | Review all module-level state in `useMap.ts`. PMTiles registration is already guarded. Boundary layer IDs are per-MapLibre-instance (independent GL contexts) so they do not conflict. The real risk is singleton composable state (`useCitySelection`, `useCityHover`) that `useMap` reads internally — these need to be overridable or bypassed in comparison mode. |
| Chart.js overlay legibility | Two overlapping area charts could be hard to read. Use line + transparent fill for city B to layer visually. Test with cities that have similar vs. very different profiles. |
| `+` character in URL routing | Nuxt file-based routing treats `[pair]` as a single param. The `+` is a valid URL character (no encoding needed). Verify Nuxt does not decode `+` as space. |

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-28-city-comparison-requirements.md](docs/brainstorms/2026-03-28-city-comparison-requirements.md)
- Related code: `app/composables/useViewState.ts` (sync mechanism), `app/composables/useMap.ts` (map creation), `app/components/city/RadialProfileChart.client.vue` (chart extension)
- Related code: `app/layouts/default.vue` (layout pattern to follow), `app/pages/city/[city_id].vue` (page pattern)
