# Task Breakdown: City Selection and Info Panel

## Overview
Total Tasks: 26 (across 5 task groups)

This spec implements two foundational MVP features:
1. **City Selection** - Click a city on the map to select it, highlight boundary, pan/zoom to extent
2. **City Info Panel** - Display selected city's name, country, population, area, and density in a left sidebar

## Task List

### Foundation Layer

#### Task Group 1: Routing and State Management
**Dependencies:** None
**Complexity:** Medium
**Rationale:** Routing and state composables are foundational - all other features depend on URL-based city selection state.

- [x] 1.0 Complete routing and state management layer
  - [x] 1.1 Write 4-6 focused tests for routing and state
    - Test `useCitySelection` composable: selectCity sets ID, clearSelection clears ID
    - Test route sync: `/city/[city_id]` route sets selected city ID
    - Test route sync: `/` route clears selected city ID
    - Test `navigateTo` integration for city selection
  - [x] 1.2 Create `useCitySelection` composable
    - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useCitySelection.ts`
    - Follow singleton pattern from `useCityHover.ts`
    - Reactive state: `selectedCityId: Ref<string | null>`
    - Methods: `selectCity(cityId: string)`, `clearSelection()`
    - Computed: `isSelected`, `hasSelection`
    - Export readonly refs for external use
  - [x] 1.3 Create city page route
    - Path: `/Users/jonathan/_code/urbanworld/web/app/pages/city/[city_id].vue`
    - Extract `city_id` from route params via `useRoute()`
    - Sync route param to `useCitySelection` on mount
    - Use `watchEffect` to keep composable in sync with route changes
  - [x] 1.4 Update index page for route awareness
    - Path: `/Users/jonathan/_code/urbanworld/web/app/pages/index.vue`
    - Clear city selection on mount (when at `/`)
    - Ensure GlobalMap, GlobalContextPanel, ZoomSlider still render
  - [x] 1.5 Ensure routing tests pass
    - Run ONLY the tests written in 1.1
    - Verify route navigation works correctly
    - Verify state syncs with URL

**Acceptance Criteria:**
- `useCitySelection` composable manages selected city ID
- `/city/[city_id]` route sets selected city ID from URL
- `/` route clears selected city ID
- Tests from 1.1 pass

---

### Data Layer

#### Task Group 2: City Statistics Composable
**Dependencies:** Task Group 1
**Complexity:** Medium
**Rationale:** The `useCityStats` composable provides epoch-reactive city data needed by the info panel UI.

- [x] 2.0 Complete city statistics data layer
  - [x] 2.1 Write 4-6 focused tests for city stats
    - Test population lookup by city_id and epoch year
    - Test density calculation (population / area)
    - Test epoch reactivity: changing `selectedYear` updates stats
    - Test trend calculation (previous/next epoch growth rates)
    - Test humanization of population values
  - [x] 2.2 Create `useCityStats` composable
    - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useCityStats.ts`
    - Accept `cityId` as parameter (reactive or string)
    - Use `useCitiesIndex` for city metadata (name, country, bbox, area)
    - Use `useSelectedYear` for epoch reactivity
    - Load city population data from cities index (population field per epoch)
  - [x] 2.3 Implement computed city statistics
    - `cityName`: string from cities index
    - `countryName`: string from cities index
    - `population`: number for selected epoch
    - `populationHumanized`: string using `humanizeNumber` utility
    - `area`: number in km2 (from cities index or computed from bbox)
    - `areaFormatted`: string with "km2" suffix
    - `density`: number (population / area)
    - `densityFormatted`: string as "X.X K/km2" or "X/km2"
  - [x] 2.4 Implement trend calculations
    - `populationTrendPrevious`: annualized rate from previous epoch
    - `populationTrendNext`: annualized rate to next epoch
    - `densityTrendPrevious`: annualized rate from previous epoch
    - `densityTrendNext`: annualized rate to next epoch
    - Reuse `toAnnualRate` from `useGlobalStats.ts`
  - [x] 2.5 Ensure city stats tests pass
    - Run ONLY the tests written in 2.1
    - Verify all computed values are correct
    - Verify epoch reactivity works

**Acceptance Criteria:**
- `useCityStats(cityId)` returns all required statistics
- Statistics update reactively when `selectedYear` changes
- Trend calculations match `useGlobalStats` pattern
- Tests from 2.1 pass

---

### Map Interaction Layer

#### Task Group 3: Map Selection and Animation
**Dependencies:** Task Group 1
**Complexity:** High
**Rationale:** Map click handling and fitBounds animation require extending existing `useMap.ts` patterns. This must be complete before the UI layer can show selection state.

- [x] 3.0 Complete map selection and animation
  - [x] 3.1 Write 4-6 focused tests for map selection
    - Test click on city boundary triggers `navigateTo('/city/[city_id]')`
    - Test feature-state `selected: true` is set on selected city
    - Test `fitBounds` is called with correct bbox and padding
    - Test min/max zoom constraints are applied
    - Test hover continues to work on non-selected cities
  - [x] 3.2 Add city click handler to `useMap.ts`
    - Register click handler on `city-boundaries-hover-pattern` and `city-boundaries-line` layers
    - Use `queryRenderedFeatures` to get clicked city
    - Extract `city_id` from feature properties
    - Call `navigateTo(\`/city/\${cityId}\`)` for navigation
    - Do NOT handle deselection on empty space clicks (close button only)
  - [x] 3.3 Implement selected city feature-state
    - Add `selected` feature-state alongside existing `hover` state
    - Track `selectedFeatureId` module-level variable (like `hoveredFeatureId`)
    - Watch `useCitySelection().selectedCityId` for changes
    - Set `{ selected: true }` on selected city, `{ selected: false }` on deselection
    - Clear previous selection when selecting a new city
  - [x] 3.4 Add selected boundary styling to city-boundaries-line layer
    - Update `line-width` expression: selected = 6, hover = 4, default = 3
    - Update `line-color` or add dashed style for selected state
    - Consider adding `line-dasharray` for selected cities (e.g., `[8, 4]`)
    - Do NOT add fill to selected cities (per requirements)
  - [x] 3.5 Implement fitBounds animation
    - Create `flyToCity(cityId: string)` function in `useMap.ts`
    - Get bbox from `useCitiesIndex().getCity(cityId).bbox`
    - Convert bbox `[minx, miny, maxx, maxy]` to MapLibre LngLatBounds
    - Call `map.fitBounds()` with padding (e.g., 80px)
    - Set `minZoom: 8` and `maxZoom: 14` in fitBounds options
    - Watch `selectedCityId` and trigger `flyToCity` on change
  - [x] 3.6 Ensure map selection tests pass
    - Run ONLY the tests written in 3.1
    - Verify click navigation works
    - Verify boundary highlighting works
    - Verify pan/zoom animation works

**Acceptance Criteria:**
- Clicking a city navigates to `/city/[city_id]`
- Selected city has distinct boundary style (thicker, possibly dashed)
- Map smoothly animates to fit selected city's bounding box
- Min/max zoom constraints (8-14) are enforced
- Hover effects continue to work on non-selected cities
- Tests from 3.1 pass

---

### UI Layer

#### Task Group 4: Sidebar and Info Panel Components
**Dependencies:** Task Groups 1, 2, 3
**Complexity:** Medium-High
**Rationale:** UI components depend on routing, data, and map selection being functional. Build generic sidebar first, then specialized city info content.

- [x] 4.0 Complete sidebar and info panel UI
  - [x] 4.1 Write 4-6 focused tests for UI components
    - Test `AppSidebar` renders when open, hides when closed
    - Test `AppSidebar` close button emits close event
    - Test `CityInfoPanel` displays city name and country
    - Test `CityInfoPanel` displays population, density, area DataPoints
    - Test DataPoints update when epoch changes
  - [x] 4.2 Create generic `AppSidebar.vue` component
    - Path: `/Users/jonathan/_code/urbanworld/web/app/components/layout/AppSidebar.vue`
    - Props: `open: boolean` (controls visibility)
    - Emit: `close` event when close button clicked
    - Fixed position: `fixed left-0 top-0 h-full z-200`
    - Width: `w-80` (~320px) to accommodate 2x DataPoints
    - Background: `bg-parchment/95 dark:bg-espresso/95 backdrop-blur-sm`
    - Shadow and border: `shadow-lg rounded-r-xl`
    - Close button in top-right corner (UIcon with `i-lucide-x`)
    - Slide-in animation: CSS transition `transform translateX`
    - Slot for content
  - [x] 4.3 Create `CityInfoPanel.vue` component
    - Path: `/Users/jonathan/_code/urbanworld/web/app/components/city/CityInfoPanel.vue`
    - Props: `cityId: string`
    - Use `useCityStats(cityId)` for reactive data
    - Use `useCitiesIndex().getCity(cityId)` for metadata
    - Layout: flex column with padding
  - [x] 4.4 Implement city header section
    - City name: `text-2xl font-bold text-forest-700 dark:text-forest-300`
    - Country name: `text-sm text-body/70 dark:text-cream/70`
    - Follow typography from `GlobalContextPanel.vue`
  - [x] 4.5 Implement DataPoint 2x2 grid
    - Container: `grid grid-cols-2 gap-4 mt-6`
    - Top-left: Population DataPoint with trends
    - Top-right: Density DataPoint with trends
    - Bottom-left: Empty/reserved space
    - Bottom-right: Area DataPoint (no trends, static value)
    - Source labels: "Source: GHSL"
  - [x] 4.6 Integrate sidebar into city page
    - Path: `/Users/jonathan/_code/urbanworld/web/app/pages/city/[city_id].vue`
    - Render `AppSidebar` with `open="true"`
    - Render `CityInfoPanel` inside sidebar slot
    - Close button handler: `navigateTo('/')`
    - Continue rendering GlobalMap, GlobalContextPanel, ZoomSlider
  - [x] 4.7 Implement responsive/mobile layout
    - Mobile: sidebar covers full width (`max-sm:w-full`)
    - Mobile: consider covering map entirely or using bottom sheet pattern
    - Use existing `max-sm:` responsive classes from GlobalContextPanel
  - [x] 4.8 Ensure UI component tests pass
    - Run ONLY the tests written in 4.1
    - Verify sidebar opens/closes correctly
    - Verify city info displays correctly
    - Verify epoch reactivity works

**Acceptance Criteria:**
- `AppSidebar` is a reusable generic sidebar component
- `CityInfoPanel` displays city name, country, population, density, area
- DataPoints show trend indicators and respond to epoch changes
- Close button navigates back to `/`
- Sidebar has slide-in animation
- Mobile layout is functional (best effort)
- Tests from 4.1 pass

---

### Integration Layer

#### Task Group 5: Integration Testing and Polish
**Dependencies:** Task Groups 1-4
**Complexity:** Low-Medium
**Rationale:** Final integration ensures all pieces work together, with focus on critical user workflows.

- [x] 5.0 Complete integration and polish
  - [x] 5.1 Review existing tests from Task Groups 1-4
    - Review ~16-24 tests written during development
    - Identify any critical gaps in end-to-end workflows
  - [x] 5.2 Write up to 6 integration tests (if needed)
    - Test full flow: click city -> sidebar opens -> data displays -> epoch changes -> data updates
    - Test full flow: click city A -> click city B -> navigates to B, sidebar updates
    - Test full flow: close button -> navigates to /, selection clears
    - Test deep linking: direct URL to `/city/[id]` loads city view
    - Test boundary interaction: selected city has distinct style, hover works on others
  - [x] 5.3 Verify visual design alignment
    - Compare implementation against `planning/visuals/left-sidebar-wireframe.png`
    - Verify city name typography matches wireframe
    - Verify DataPoint layout matches 2x2 grid
    - Verify sepia/parchment theme consistency
  - [x] 5.4 Test dark mode compatibility
    - Verify sidebar uses dark mode classes
    - Verify selected boundary styling works in dark mode
    - Verify all text is readable in both modes
  - [x] 5.5 Run all feature-specific tests
    - Run ONLY tests from Task Groups 1-5 (approximately 22-30 tests)
    - Do NOT run entire application test suite
    - Fix any failing tests
  - [x] 5.6 Manual smoke test
    - Test on desktop viewport
    - Test on mobile viewport (best effort)
    - Verify no console errors
    - Verify smooth animations

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 22-30 tests)
- Visual design matches wireframe (layout, not pixel-perfect)
- Dark mode works correctly
- No regressions in existing functionality (GlobalContextPanel, hover, etc.)
- Critical user workflows verified

---

## Execution Order

Recommended implementation sequence:

1. **Task Group 1: Routing and State Management** (Foundation)
   - Must be first - everything else depends on route-based selection state
   - Creates `useCitySelection` composable and city page route

2. **Task Group 2: City Statistics Composable** (Data)
   - Can start after Task Group 1 is complete
   - Provides data needed by UI components

3. **Task Group 3: Map Selection and Animation** (Interaction)
   - Can start after Task Group 1 is complete
   - Can run in parallel with Task Group 2 since they're independent
   - Extends `useMap.ts` with click handling and selection styling

4. **Task Group 4: Sidebar and Info Panel Components** (UI)
   - Depends on Task Groups 1, 2, and 3
   - Builds the visual interface using data from composables

5. **Task Group 5: Integration Testing and Polish** (Quality)
   - Final step after all features are implemented
   - Focuses on end-to-end testing and visual polish

## File Summary

**New Files to Create:**
- `/Users/jonathan/_code/urbanworld/web/app/composables/useCitySelection.ts`
- `/Users/jonathan/_code/urbanworld/web/app/composables/useCityStats.ts`
- `/Users/jonathan/_code/urbanworld/web/app/pages/city/[city_id].vue`
- `/Users/jonathan/_code/urbanworld/web/app/components/layout/AppSidebar.vue`
- `/Users/jonathan/_code/urbanworld/web/app/components/city/CityInfoPanel.vue`

**Existing Files to Modify:**
- `/Users/jonathan/_code/urbanworld/web/app/composables/useMap.ts` (add click handler, selection state, fitBounds)
- `/Users/jonathan/_code/urbanworld/web/app/pages/index.vue` (clear selection on mount)

**Reference Files (patterns to follow):**
- `/Users/jonathan/_code/urbanworld/web/app/composables/useCityHover.ts` (singleton state pattern)
- `/Users/jonathan/_code/urbanworld/web/app/composables/useGlobalStats.ts` (trend calculations, humanization)
- `/Users/jonathan/_code/urbanworld/web/app/composables/useCitiesIndex.ts` (city data lookup)
- `/Users/jonathan/_code/urbanworld/web/app/components/map/GlobalContextPanel.vue` (styling patterns)
- `/Users/jonathan/_code/urbanworld/web/app/components/ui/DataPoint.vue` (reusable data display)

## Notes

- **Testing Approach:** Per project standards, focus on minimal tests during development (2-8 per task group), testing only core user flows. Edge cases and comprehensive coverage are deferred.
- **Tailwind CSS:** Use Tailwind classes exclusively per `web/CLAUDE.md`. No custom `<style>` blocks unless absolutely necessary.
- **Tech Stack:** Nuxt 4, Vue, Tailwind CSS 4, Nuxt UI 4, pnpm
- **Vue Components Order:** Follow `web/CLAUDE.md` section order: `<script>`, `<template>`, `<style>`
- **Dark Mode:** All components must support dark mode using existing patterns (`dark:` classes)
- **Mobile:** Best effort responsive layout - not pixel-perfect optimization
