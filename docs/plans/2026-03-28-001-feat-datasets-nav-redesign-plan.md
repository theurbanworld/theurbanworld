---
title: "feat: Introduce dataset abstraction and navigation redesign"
type: feat
status: completed
date: 2026-03-28
origin: docs/brainstorms/2026-03-28-datasets-nav-requirements.md
---

# feat: Introduce dataset abstraction and navigation redesign

## Overview

Replace the low-level Grid/H3 toggle with a first-class "dataset" concept, restructure the search strip to hold a dataset dropdown and compact epoch display, and reposition the epoch slider and global stats into a right-anchored eyebrow panel.

## Problem Frame

Users currently see a "Grid 1km / H3 R8" toggle that exposes internal spatial details. These actually represent two fundamentally different things: raw GHSL data vs a curated Urban World product. The current floating GlobalContextPanel competes with map space, and the "Cities" button is redundant since rankings is the default home view. (see origin: docs/brainstorms/2026-03-28-datasets-nav-requirements.md)

## Requirements Trace

- R1. Dataset abstraction replacing Grid/H3 toggle
- R2. Two datasets: GHSL R2024 (grid-1km), Urban World v1 (h3-r8, default)
- R3. Version display-only, no switching
- R4. Methodologies scoped to datasets
- R5. Per-dataset content pages under /data/
- R6. Dataset dropdown replaces Cities button (left of strip)
- R7. Dropdown with info links per dataset
- R8. Search bar remains centered
- R9. Epoch year on right side of strip (compact, read-only)
- R10. Remove Cities button
- R11. Eyebrow panel replaces GlobalContextPanel
- R12. Eyebrow ~250-300px, always visible, right-anchored: slider + stats
- R13. Sidebar unchanged on left
- R14. Dataset switch: stay on city if exists, else fall back to rankings
- R15. Epoch reset to nearest available if current unavailable in new dataset

## Scope Boundaries

- No version switching UI (see origin)
- No methodology content changes — just scoping to Urban World
- No new datasets beyond GHSL R2024 and Urban World v1
- Frontend only — pipeline out of scope
- No grid-specific population overlay layer (GHSL R2024 shows boundary outlines only, no deck.gl density fill)
- No mobile-specific eyebrow redesign in this iteration (existing responsive behavior preserved)

## Context & Research

### Relevant Code and Patterns

- **Composable singleton pattern**: All global state uses module-level `ref()` outside the composable function, returned as `readonly()`. Examples: `useDataSource`, `useSelectedYear`, `useDarkMode`. New `useDataset` composable must follow this pattern.
- **`useDataSource.ts`**: Current source of truth for Grid/H3. Defines `DataSource = 'h3-r8' | 'grid-1km'`, consumed by 3 places: `GlobalContextPanel.vue`, `useCityPopulations.ts`, `useMap.ts`.
- **`BOUNDARIES_CONFIG` in `useMap.ts`** (line ~30): Maps data source slugs to PMTiles URLs and source layers. Destructive swap on change (removes + re-adds 3 MapLibre layers).
- **`useSelectedYear.ts`**: `YEAR_EPOCHS = [1975..2030]` hardcoded. Both datasets share these epochs.
- **`useGlobalStats.ts`**: Hardcoded world/urban population lookup tables. Source-independent.
- **`GlobalContextPanel.vue`**: Currently absolute-positioned `right-4 top-4 w-56`. Contains epoch slider, source toggle, year display, and population stats.
- **`default.vue` layout**: Search strip has `[Cities button (w-80)] | [CitySearch (centered)]`. Sidebar is `w-80` fixed left.
- **`useMap.ts` RIGHT_PANEL_WIDTH = 256**: Used in `fitBounds` padding. Must update to match new eyebrow width.
- **Content collections**: `content.config.ts` defines `data` collection from `content/data/**`. Currently has `index.md` and `source-ghsl.md`.
- **H3-only features**: `useH3Data`, `useH3Layer`, `useRadialProfiles`, `useRadialLayer`, `RadialProfileSection` — all hardcoded to H3. Must be conditionally hidden for GHSL R2024.
- **No Nuxt UI select/dropdown in current use**: The project uses hand-rolled `<button>` and `<select>` elements. The dataset dropdown will use Nuxt UI `UDropdownMenu` (new pattern for this codebase).
- **Slug conventions**: `DataSource` uses hyphens (`h3-r8`), `sourceSlug` uses underscores (`h3_r8`). New dataset identifiers must maintain this dual convention.

### External References

- Nuxt UI v3 UDropdownMenu component for the dataset selector

## Key Technical Decisions

- **Dataset config as TypeScript object in `useDataset.ts`**: Follows the existing composable singleton pattern. A config array defines each dataset's properties (id, name, version, slug, spatial type, epochs, features, content path). Chosen over JSON file (no runtime flexibility needed) and content collection (datasets are code-level config, not CMS content).
- **`useDataset` wraps `useDataSource`**: The new composable provides the dataset abstraction and delegates to the existing `useDataSource` for backward compatibility with `useCityPopulations` and `useMap`. This avoids rewriting all consumers at once.
- **H3-only features gated by dataset config**: Each dataset declares which features it supports (e.g., `features: ['radialProfiles', 'h3Overlay']`). Components check the active dataset's feature list. Chosen over hardcoding `if (dataset === 'urban-world-v1')` checks because it scales to future datasets.
- **Eyebrow is a new standalone component**: `EyebrowPanel.vue` in `components/map/`. Not part of the sidebar or map overlay system. Positioned via layout grid, not absolute positioning.
- **Epoch stays global, not per-dataset**: Both current datasets share the same 1975-2030 epochs. R15 (epoch reset) is implemented defensively but is a no-op for now. `YEAR_EPOCHS` stays in `useSelectedYear.ts` but gets referenced through the dataset config so it can diverge per-dataset later.
- **Global stats remain source-independent**: They derive from UN WPP, not from dataset methodology. No changes to `useGlobalStats`.

## Open Questions

### Resolved During Planning

- **Dataset config structure** (origin Q1): TypeScript config in `useDataset.ts`. Follows existing composable pattern. No need for JSON/content collection since datasets are code-level definitions.
- **Grid 1km feature support** (origin Q2): Rankings, city detail (population/area/density stats, sparklines) work for both. Radial profiles and H3 overlay are H3-only — hidden for GHSL R2024.
- **Eyebrow component approach** (origin Q3): Standalone component positioned via layout grid. Simpler than integrating into the map overlay system.
- **Methodology scoping** (origin Q4): Add `dataset` frontmatter field to methodology content pages. The methodology index page and nav link remain visible for all datasets but methodology subpages show a note when the active dataset doesn't support them.
- **Navigation back to rankings** (flow analysis): The logo/AppLogo in AppHeader already links to `/`. This is sufficient — confirmed in brainstorm that the logo serves as nav home.
- **Epoch sets per dataset**: Both datasets share 1975-2030. R15 logic is defensive future-proofing, implemented but currently a no-op.

### Deferred to Implementation

- **Exact Nuxt UI UDropdownMenu API**: Verify props/slots available in @nuxt/ui v4.5 for the dataset dropdown. May need to fall back to a custom dropdown if UDropdownMenu doesn't support info links per item.
- **Loading state during dataset switch**: The async population refetch creates a brief window where city existence is unknown. Implementation should determine the simplest approach (likely a brief loading overlay using the existing `LoadingOverlay` component).
- **Map fitBounds padding value**: The current `RIGHT_PANEL_WIDTH = 256` needs adjustment. Exact value depends on final eyebrow width determined during implementation.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
Dataset Config (useDataset.ts)
┌─────────────────────────────────────────────┐
│ datasets: [                                 │
│   { id: 'urban-world-v1',                  │
│     name: 'Urban World',                    │
│     version: 'v1',                          │
│     dataSource: 'h3-r8',                    │
│     slug: 'h3_r8',                          │
│     features: ['radialProfiles','h3Overlay'],│
│     contentPath: '/data/urban-world-v1',    │
│     epochs: YEAR_EPOCHS },                  │
│   { id: 'ghsl-r2024',                      │
│     name: 'GHSL',                           │
│     version: 'R2024',                       │
│     dataSource: 'grid-1km',                 │
│     slug: 'grid_1km',                       │
│     features: [],                           │
│     contentPath: '/data/ghsl-r2024',        │
│     epochs: YEAR_EPOCHS }                   │
│ ]                                           │
└──────────────┬──────────────────────────────┘
               │ setDataset() calls setDataSource()
               ▼
┌─ useDataSource (unchanged) ─────────────────┐
│  dataSource: 'h3-r8' | 'grid-1km'          │
│  sourceSlug: 'h3_r8' | 'grid_1km'          │
└──────┬──────────────┬───────────────────────┘
       │              │
       ▼              ▼
  useMap.ts    useCityPopulations.ts
  (boundaries)  (population JSON)
```

```
Layout (default.vue)
┌─ Search Strip ────────────────────────────────────────────┐
│  [Dataset ▾ (dropdown)]  |  🔍 CitySearch  |  2025       │
├───────────────────────┬───────────────────┬───────────────┤
│                       │                   │ EyebrowPanel  │
│  AppSidebar (w-80)    │                   │ (~280px)      │
│  Rankings / Detail    │      Map          │ Epoch slider  │
│                       │                   │ World pop     │
│                       │                   │ Urban pop     │
│                       │                   └───────────────┤
│                       │                                   │
└───────────────────────┴───────────────────────────────────┘
```

## Implementation Units

- [ ] **Unit 1: Dataset config and composable**

**Goal:** Create the dataset abstraction that replaces `useDataSource` as the primary API for components.

**Requirements:** R1, R2, R3, R15

**Dependencies:** None

**Files:**
- Create: `web/app/composables/useDataset.ts`
- Create: `web/types/dataset.ts`
- Modify: `web/app/composables/useDataSource.ts` (keep as internal, called by useDataset)
- Test: `web/test/unit/useDataset.test.ts`

**Approach:**
- Define a `Dataset` interface in `types/dataset.ts` with: id, name, version, dataSource, slug, features, contentPath, epochs
- Define a `DATASETS` config array with the two datasets
- `useDataset()` composable follows the singleton pattern: module-level `ref<string>` for active dataset ID, computed `activeDataset` deriving the full config object
- `setDataset(id)` updates the active dataset and delegates to `useDataSource().setDataSource()` internally
- Expose `hasFeature(feature)` computed helper for gating H3-only UI
- Export `DATASETS` for dropdown rendering
- `useDataSource` remains unchanged internally — `useDataset` is the new public API

**Patterns to follow:**
- `useDataSource.ts` singleton pattern (module-level ref, readonly export)
- `useSelectedYear.ts` for the computed helper pattern

**Test scenarios:**
- Happy path: default dataset is 'urban-world-v1', dataSource is 'h3-r8'
- Happy path: setDataset('ghsl-r2024') changes dataSource to 'grid-1km'
- Happy path: hasFeature('radialProfiles') returns true for Urban World, false for GHSL
- Edge case: setDataset with unknown ID does not change the active dataset
- Happy path: activeDataset computed returns full config object matching the active ID

**Verification:** `useDataset()` can be imported and used; setting dataset changes the underlying data source; feature gating works correctly.

---

- [ ] **Unit 2: Search strip restructure — dataset dropdown and epoch display**

**Goal:** Replace the Cities button with a dataset dropdown on the left and add a compact epoch year display on the right.

**Requirements:** R6, R7, R8, R9, R10

**Dependencies:** Unit 1

**Files:**
- Create: `web/app/components/search/DatasetDropdown.vue`
- Modify: `web/app/layouts/default.vue` (search strip section)
- Modify: `web/app/components/search/CitySearch.vue` (if layout adjustments needed)

**Approach:**
- Create `DatasetDropdown.vue` using Nuxt UI's `UDropdownMenu` (or hand-rolled dropdown if UDropdownMenu doesn't support custom item templates with info links). Shows dataset name + version, checkmark on active, info icon linking to contentPath.
- In `default.vue`, replace the Cities button with `<DatasetDropdown>`. Restructure the strip as a 3-column grid: `[dropdown | search | epoch-year]`.
- The epoch year display is a simple read-only span showing `selectedYear` from `useSelectedYear()`.
- Remove the `goToRankings()` function and Cities button logic entirely.

**Patterns to follow:**
- Existing hand-rolled `<button>` styling in `GlobalContextPanel.vue` for consistent theme
- `UDropdownMenu` from Nuxt UI if API supports custom item slots

**Test scenarios:**
- Happy path: dataset dropdown renders with both dataset options, Urban World selected by default
- Happy path: selecting GHSL R2024 from dropdown calls setDataset('ghsl-r2024')
- Happy path: info icon click navigates to the dataset's content page
- Happy path: epoch year displays the current selected year
- Edge case: search bar remains functional and centered after layout change

**Verification:** Strip shows dropdown (left), search (center), year (right). Dataset selection works. No "Cities" button remains.

---

- [ ] **Unit 3: Eyebrow panel — epoch slider and global stats**

**Goal:** Replace the floating GlobalContextPanel with a right-anchored eyebrow panel containing the epoch slider and population stats.

**Requirements:** R11, R12, R13

**Dependencies:** Unit 1 (for dataset-aware epoch range), Unit 2 (strip must exist for eyebrow to anchor below)

**Files:**
- Create: `web/app/components/map/EyebrowPanel.vue`
- Modify: `web/app/layouts/default.vue` (add eyebrow to layout grid)
- Modify: `web/app/composables/useMap.ts` (update RIGHT_PANEL_WIDTH)
- Delete or gut: `web/app/components/map/GlobalContextPanel.vue`

**Approach:**
- Create `EyebrowPanel.vue` containing: epoch slider (from GlobalContextPanel), world/urban population stats (from GlobalContextPanel), and year labels. Remove the source toggle and large year display (those are now in the strip).
- Position via layout: the eyebrow sits in the map area, anchored top-right, ~280px wide. Use `absolute right-0 top-0` within the map container (not the full page).
- Update `RIGHT_PANEL_WIDTH` in `useMap.ts` to match the eyebrow width for correct `fitBounds` padding.
- Remove `GlobalContextPanel.vue` from the layout (or delete if fully replaced).
- Preserve existing dark mode and responsive behavior from GlobalContextPanel.

**Patterns to follow:**
- `GlobalContextPanel.vue` for epoch slider and stats rendering
- Existing `USlider` usage for the epoch control

**Test scenarios:**
- Happy path: eyebrow panel renders with epoch slider, world pop, urban pop
- Happy path: changing epoch via slider updates selectedYear globally
- Happy path: eyebrow is visible and does not overlap the sidebar
- Edge case: map fitBounds correctly accounts for eyebrow width (cities don't center under the panel)

**Verification:** Epoch slider and stats are accessible in the eyebrow. GlobalContextPanel is removed. Map centering works correctly.

---

- [ ] **Unit 4: Dataset switching behavior**

**Goal:** Handle dataset switch gracefully — preserve city context when possible, reset when not.

**Requirements:** R14, R15

**Dependencies:** Unit 1

**Files:**
- Modify: `web/app/composables/useDataset.ts` (add switch logic)
- Modify: `web/app/composables/useCityPopulations.ts` (expose city existence check)
- Modify: `web/app/composables/useCitySelection.ts` (if it needs to participate in fallback)

**Approach:**
- When `setDataset()` is called and a city is currently selected:
  1. Trigger the data source change (populations refetch automatically via watcher)
  2. After population data loads, check if the current city exists in the new dataset's populations
  3. If yes, stay on the city (no navigation)
  4. If no, clear city selection and navigate to `/` (rankings)
- For epoch: check if current selectedYear exists in the new dataset's epochs array. If not, snap to the nearest available epoch. (Currently a no-op since both share the same epochs.)
- Use the existing `LoadingOverlay` component during the transition if there's a noticeable delay.

**Patterns to follow:**
- `useCityPopulations.ts` watch pattern for async refetch
- `useCitySelection.ts` for city state management

**Test scenarios:**
- Happy path: switch datasets while on a city that exists in both — stays on same city
- Happy path: switch datasets while on a city that only exists in one — falls back to rankings
- Happy path: switch datasets while on rankings — stays on rankings
- Edge case: switch datasets when no city is selected — no navigation change
- Edge case: epoch available in both datasets — epoch unchanged
- Integration: population data refetch completes before city existence is evaluated

**Verification:** Switching datasets preserves or gracefully transitions the user's view state.

---

- [ ] **Unit 5: Gate H3-only features by dataset**

**Goal:** Hide radial profiles and H3 overlay when the active dataset doesn't support them.

**Requirements:** R2, R4

**Dependencies:** Unit 1

**Files:**
- Modify: `web/app/components/city/CityInfoPanel.vue` (conditional RadialProfileSection)
- Modify: `web/app/components/map/GlobalMap.client.vue` (conditional H3 layer, if referenced)
- Modify: `web/app/composables/useH3Layer.ts` (disable when not H3 dataset)

**Approach:**
- In `CityInfoPanel.vue`, wrap `<RadialProfileSection>` in a `v-if="hasFeature('radialProfiles')"` using `useDataset()`.
- In `useH3Layer.ts` (or wherever the H3 deck.gl layer is toggled), skip layer creation when `hasFeature('h3Overlay')` is false.
- When features are hidden, the city detail panel simply shows fewer sections — no "unavailable" message needed.

**Patterns to follow:**
- Existing conditional rendering patterns in CityInfoPanel (e.g., loading states)

**Test scenarios:**
- Happy path: Urban World v1 shows RadialProfileSection in city detail
- Happy path: GHSL R2024 hides RadialProfileSection in city detail
- Happy path: H3 overlay layer is not created when dataset is GHSL R2024
- Edge case: switching from Urban World to GHSL while viewing a city — radial section disappears without error

**Verification:** H3-only features are invisible and produce no errors under GHSL R2024.

---

- [ ] **Unit 6: Per-dataset content pages and methodology scoping**

**Goal:** Create content pages for each dataset and scope methodology pages to their applicable datasets.

**Requirements:** R4, R5, R7

**Dependencies:** Unit 1 (for dataset config contentPath)

**Files:**
- Create: `web/content/data/urban-world-v1.md`
- Create: `web/content/data/ghsl-r2024.md`
- Modify: `web/content/data/index.md` (update to reference dataset pages)
- Modify: `web/content/methodology/index.md` (add dataset applicability note)
- Modify: `web/content/methodology/density-outliers.md` (add dataset frontmatter)
- Modify: `web/content/methodology/bertaud-radial.md` (add dataset frontmatter)
- Modify: `web/pages/data.vue` or create `web/pages/data/[slug].vue` (dynamic routing for dataset pages)

**Approach:**
- Create markdown content pages for each dataset documenting sources, processing, and characteristics.
- Add `dataset: urban-world-v1` frontmatter to methodology pages that are Urban World-specific.
- Update the /data page to either use dynamic routing (`/data/[slug]`) or render dataset subpages. Since the current pattern renders all sections on one page, adding a `[slug].vue` dynamic page alongside the existing `data.vue` index is cleanest.
- The methodology pages remain accessible from all datasets but display a note when the active dataset doesn't match (e.g., "This methodology applies to the Urban World dataset").

**Patterns to follow:**
- Existing content collection pattern in `content.config.ts`
- Existing `data.vue` and `methodology.vue` page patterns
- `source-ghsl.md` as template for dataset content pages

**Test scenarios:**
- Happy path: /data/urban-world-v1 renders Urban World dataset documentation
- Happy path: /data/ghsl-r2024 renders GHSL dataset documentation
- Happy path: dataset dropdown info link navigates to correct /data/ subpage
- Happy path: methodology pages show dataset applicability note when on non-matching dataset

**Verification:** Each dataset has its own documentation page accessible from the dropdown and from /data. Methodology pages indicate which dataset they apply to.

## System-Wide Impact

- **Interaction graph:** `useDataset` wraps `useDataSource`, which is consumed by `useCityPopulations`, `useMap`, and (formerly) `GlobalContextPanel`. All existing data-source watchers continue to work unchanged. New consumers should use `useDataset` instead of `useDataSource`.
- **Error propagation:** Dataset switch triggers async population refetch. If the fetch fails, the existing error handling in `useCityPopulations` applies. No new error paths introduced.
- **State lifecycle risks:** During dataset switch, there's a brief window where boundaries are swapping and populations are refetching. Map click handlers during this window could reference stale feature IDs. The existing `cityBoundariesLoaded` flag mitigates this.
- **API surface parity:** The `useDataSource` composable remains functional for backward compatibility but `useDataset` is the new primary API. Both are available during transition.
- **Unchanged invariants:** `useCitiesIndex` (single cities_index.json), `useGlobalStats` (hardcoded constants), `useSelectedYear` (shared epoch array) — all remain unchanged.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Nuxt UI UDropdownMenu may not support custom item templates with info links | Fall back to a hand-rolled dropdown using the same button styling pattern already in the codebase |
| Grid 1km population JSON may not exist on R2 | Verify data files exist before merging; pipeline team can generate if missing |
| Removing GlobalContextPanel breaks existing responsive behavior | Port existing max-sm:hidden and responsive classes to the new EyebrowPanel |
| Map padding constant change causes mis-centered city views | Test with several cities at different zoom levels to verify fitBounds padding |

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-28-datasets-nav-requirements.md](docs/brainstorms/2026-03-28-datasets-nav-requirements.md)
- Related code: `web/app/composables/useDataSource.ts`, `web/app/components/map/GlobalContextPanel.vue`, `web/app/layouts/default.vue`
- Nuxt UI components: UDropdownMenu, USlider
