# Task Breakdown: Global View Controls

## Overview
Total Tasks: 5 Task Groups with 34 sub-tasks

This spec implements three main features:
1. Global Context Panel (right sidebar with epoch year, slider, and population data)
2. Reusable DataPoint component for displaying humanized values with tooltips
3. Vertical Zoom Slider with named scale levels

## Task List

### Testing Infrastructure

#### Task Group 0: Vitest Testing Setup
**Dependencies:** None
**Status:** COMPLETED

- [x] 0.1 Install test dependencies
  - Packages: `@nuxt/test-utils`, `vitest`, `@vue/test-utils`, `happy-dom`
  - Command: `pnpm add -D @nuxt/test-utils vitest @vue/test-utils happy-dom`
- [x] 0.2 Create vitest.config.ts
  - Path: `/Users/jonathan/_code/urbanworld/web/vitest.config.ts`
  - Use `defineVitestConfig` from `@nuxt/test-utils/config`
  - Set environment to 'nuxt' for full Nuxt runtime support
- [x] 0.3 Update nuxt.config.ts
  - Add `@nuxt/test-utils/module` to modules array
- [x] 0.4 Add test scripts to package.json
  - `test`: `vitest` (watch mode)
  - `test:run`: `vitest run` (single run)
  - `coverage`: `vitest run --coverage`
- [x] 0.5 Create test directory structure
  - `web/test/unit/` - Pure functions (formatNumber, colorScale)
  - `web/test/nuxt/` - Composables and components requiring Nuxt runtime

**Acceptance Criteria:**
- `pnpm test:run` executes without configuration errors
- Test directories exist and are tracked by git
- Nuxt test-utils module is registered

---

### Data & Composables Layer

#### Task Group 1: Composables and Data Constants
**Dependencies:** None
**Status:** COMPLETED

- [x] 1.0 Complete data and composables layer
  - [x] 1.1 Write 3-4 focused tests for composable functionality
    - Test `useGlobalStats` returns correct population data for a given epoch
    - Test `useZoomLevel` maps zoom values to correct named levels
    - Test `useZoomLevel` returns correct center zoom for snap-to-level functionality
    - Test `useViewState` setZoom convenience method updates zoom correctly
  - [x] 1.2 Create `useGlobalStats` composable
    - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useGlobalStats.ts`
    - Export function that returns world population and urban population for selected year
    - Store data as TypeScript constants (static data, not fetched from R2)
    - World Population data (from pipeline `WORLD_POPULATION`):
      ```
      1975: 4,069,437,259 | 1980: 4,444,007,748 | 1985: 4,861,730,652
      1990: 5,316,175,909 | 1995: 5,743,219,510 | 2000: 6,148,899,024
      2005: 6,558,176,175 | 2010: 6,985,603,172 | 2015: 7,426,597,609
      2020: 7,840,952,947 | 2025: 8,191,988,536 | 2030: 8,546,141,407
      ```
    - Urban Population data (from city_populations.parquet aggregation):
      ```
      1975: 1,178,323,105 | 1980: 1,346,953,243 | 1985: 1,532,907,872
      1990: 1,741,456,510 | 1995: 2,012,230,273 | 2000: 2,306,333,391
      2005: 2,556,795,633 | 2010: 2,819,883,050 | 2015: 3,095,854,703
      2020: 3,350,187,245 | 2025: 3,569,570,193 | 2030: 3,759,831,609
      ```
    - Use existing `useSelectedYear` composable for epoch selection
    - Include helper function to humanize numbers (e.g., "8.2 billion")
  - [x] 1.3 Create `useZoomLevel` composable
    - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useZoomLevel.ts`
    - Define zoom level mapping with ranges:
      - Metropolitan: zoom 0-5, center: 2.5, icon: `i-lucide-globe`
      - City: zoom 5-10, center: 7.5, icon: `i-lucide-building-2`
      - Neighborhood: zoom 10-13, center: 11.5, icon: `i-lucide-trees`
      - Street: zoom 13-16, center: 14.5, icon: `i-lucide-road`
      - Building: zoom 16-18+, center: 17, icon: `i-lucide-building`
    - Export function to get current level name from zoom value
    - Export function to get center zoom for a given level (for snap-to)
    - Export array of all levels with name, icon, and zoom range
  - [x] 1.4 Extend `useViewState` composable with setZoom method
    - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useViewState.ts`
    - Add `setZoom(zoom: number)` convenience method for snap-to-level functionality
    - Preserve existing functionality (setViewState, onViewStateChange, resetViewState)
  - [x] 1.5 Ensure composable tests pass
    - Run ONLY the 3-4 tests written in 1.1
    - Verify data constants are correct
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 3-4 tests written in 1.1 pass
- `useGlobalStats` returns correct population data for all epochs
- `useZoomLevel` correctly maps zoom ranges to named levels
- `useViewState.setZoom` updates zoom while preserving other view state
- Humanize function formats numbers correctly (e.g., 8,191,988,536 -> "8.2 billion")

---

### Reusable UI Components

#### Task Group 2: DataPoint Component
**Dependencies:** Task Group 1
**Status:** COMPLETED

- [x] 2.0 Complete DataPoint component
  - [x] 2.1 Write 3-4 focused tests for DataPoint component
    - Test component renders label, humanized value, and source link
    - Test tooltip displays exact value on hover (using rawValue prop)
    - Test mono font applied to value, sans-serif to label
    - Test component handles missing sourceLabel gracefully
  - [x] 2.2 Create DataPoint component
    - Path: `/Users/jonathan/_code/urbanworld/web/app/components/ui/DataPoint.vue`
    - Props interface:
      - `label: string` - Small label text (e.g., "World Population")
      - `value: string` - Humanized display value (e.g., "8.2 billion")
      - `rawValue: number` - Exact value for tooltip (e.g., 8191988536)
      - `sourceLabel?: string` - Source link text (defaults to "Source")
    - Structure hierarchy:
      - Small label text (sans-serif, muted color)
      - Large humanized value (mono font, primary color)
      - Source link below (sans-serif, small, link styling)
    - Use Nuxt UI `UTooltip` component for hover behavior
    - Tooltip shows exact rawValue formatted with locale number separators
    - Tooltip text uses mono font for the number
  - [x] 2.3 Apply Tailwind CSS styling
    - Use Tailwind CSS classes exclusively (per project standards)
    - Support dark mode with appropriate color transitions
    - Typography: `font-mono` for values, default sans-serif for labels
    - Spacing: Appropriate vertical spacing between elements
    - Colors: Use CSS variables for theming (forest green accents, parchment/espresso backgrounds)
  - [x] 2.4 Ensure DataPoint component tests pass
    - Run ONLY the 3-4 tests written in 2.1
    - Verify component renders correctly in both light and dark modes
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 3-4 tests written in 2.1 pass
- Component displays label, value, and source link correctly
- Tooltip shows exact value on hover with mono font
- Component follows existing design system (forest green, parchment/espresso)
- Component is reusable for future data display needs

---

### Main Feature Components

#### Task Group 3: GlobalContextPanel and ZoomSlider Components
**Dependencies:** Task Groups 1, 2
**Status:** COMPLETED

- [x] 3.0 Complete GlobalContextPanel component
  - [x] 3.1 Write 2-3 focused tests for GlobalContextPanel
    - Test panel displays current epoch year prominently
    - Test population data points update when epoch changes
    - Test epoch slider changes selected year
  - [x] 3.2 Create GlobalContextPanel component
    - Path: `/Users/jonathan/_code/urbanworld/web/app/components/map/GlobalContextPanel.vue`
    - Fixed positioning on right side (similar to DarkModeToggle pattern)
    - Width: 200-240px
    - Z-index: 100 (consistent with other overlays)
    - Contains:
      - Prominent year display at top (mono font, large size like existing YearSlider)
      - Horizontal epoch slider (reuse USlider patterns from YearSlider.vue)
      - World Population DataPoint
      - Urban Population DataPoint
    - Use `useSelectedYear` for epoch state
    - Use `useGlobalStats` for population data
  - [x] 3.3 Style GlobalContextPanel with Tailwind CSS
    - Background: parchment (light) / espresso (dark) with opacity
    - Border radius and shadow matching existing YearSlider styling
    - Position: fixed, right: 16px, top offset to avoid header overlap
    - Responsive: Consider mobile layout (best effort)
  - [x] 3.4 Integrate epoch slider functionality
    - Migrate slider logic from YearSlider.vue
    - Horizontal slider always visible below year display
    - Maintain 1975-2030 range in 5-year increments
    - Preserve click-to-snap behavior for year labels (optional, space permitting)

- [x] 3.5 Complete ZoomSlider component
  - [x] 3.6 Write 2-3 focused tests for ZoomSlider
    - Test slider value syncs with map zoom level
    - Test clicking level icon snaps map to that zoom level
    - Test current level name displays correctly above slider
  - [x] 3.7 Create ZoomSlider component
    - Path: `/Users/jonathan/_code/urbanworld/web/app/components/map/ZoomSlider.vue`
    - Vertical slider floating above map
    - Fixed positioning to left of GlobalContextPanel
    - Z-index: 100 (consistent with other overlays)
    - Bidirectional sync with map via `useViewState` composable
    - Use `useZoomLevel` for level mapping
  - [x] 3.8 Implement zoom level indicators
    - Five Lucide icons always visible along slider track:
      - Metropolitan: `i-lucide-globe`
      - City: `i-lucide-building-2`
      - Neighborhood: `i-lucide-trees`
      - Street: `i-lucide-road`
      - Building: `i-lucide-building`
    - Icons are clickable to snap to center zoom of that level
    - Level names shown only on hover (UTooltip)
    - Current level display above slider:
      - Small "Scale" label (sans-serif)
      - Large level name below (sans-serif)
  - [x] 3.9 Style ZoomSlider with Tailwind CSS
    - Vertical orientation for slider
    - Touch-friendly targets (44x44px for icons)
    - Forest green accent colors matching existing controls
    - Dark mode support
    - Background panel with parchment/espresso theming

- [x] 3.10 Ensure component tests pass
    - Run ONLY the 4-6 tests written in 3.1 and 3.6
    - Verify GlobalContextPanel and ZoomSlider render correctly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 4-6 tests written in 3.1 and 3.6 pass
- GlobalContextPanel displays epoch year, slider, and population data points
- Population data updates correctly when epoch changes
- ZoomSlider syncs bidirectionally with map zoom
- Clicking zoom level icons snaps to appropriate zoom level
- Current scale level is prominently displayed above zoom slider
- Both components support dark mode

---

### Integration & Cleanup

#### Task Group 4: Page Integration and Component Removal
**Dependencies:** Task Group 3
**Status:** COMPLETED

- [x] 4.0 Complete integration and cleanup
  - [x] 4.1 Write 2-3 focused integration tests
    - Test GlobalContextPanel and ZoomSlider render on index page
    - Test changing epoch updates both year display and population values
    - Test zoom slider reflects map zoom changes after user interaction
  - [x] 4.2 Update index.vue page
    - Path: `/Users/jonathan/_code/urbanworld/web/app/pages/index.vue`
    - Add GlobalContextPanel component
    - Add ZoomSlider component
    - Remove YearSlider component reference
    - Remove MapControls component reference and related zoom handlers
    - Update component documentation comment at top of script
  - [x] 4.3 Remove deprecated components
    - Delete `/Users/jonathan/_code/urbanworld/web/app/components/map/YearSlider.vue`
    - Delete `/Users/jonathan/_code/urbanworld/web/app/components/map/MapControls.vue`
    - Verify no other files import these deleted components
  - [x] 4.4 Verify zoom integration with GlobalMap
    - Ensure ZoomSlider's snap-to-level triggers map zoom change
    - Ensure map user interactions (scroll/pinch zoom) update ZoomSlider
    - Test that `useViewState.setZoom` properly triggers map update
  - [x] 4.5 Mobile layout adjustments (best effort)
    - GlobalContextPanel: Consider collapsing data points on small screens
    - ZoomSlider: Ensure remains accessible on right side
    - Test at common breakpoints (320px, 768px, 1024px)
  - [x] 4.6 Ensure integration tests pass
    - Run ONLY the 2-3 tests written in 4.1
    - Verify all components work together correctly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-3 tests written in 4.1 pass
- GlobalContextPanel and ZoomSlider appear correctly on page
- YearSlider and MapControls components are fully removed
- No console errors or warnings related to removed components
- Epoch changes propagate to population data display
- Zoom changes sync bidirectionally between slider and map
- Basic mobile layout functions (best effort)

---

### Final Verification

#### Task Group 5: Test Review and Final Validation
**Dependencies:** Task Groups 1-4
**Status:** COMPLETED

- [x] 5.0 Review and validate all tests
  - [x] 5.1 Review existing tests from Task Groups 1-4
    - Review 3-4 composable tests (Task 1.1)
    - Review 3-4 DataPoint component tests (Task 2.1)
    - Review 4-6 GlobalContextPanel/ZoomSlider tests (Task 3.1, 3.6)
    - Review 2-3 integration tests (Task 4.1)
    - Total existing: approximately 12-17 tests
  - [x] 5.2 Identify critical gaps (if any)
    - Focus on end-to-end user workflows
    - Ensure humanized number formatting is covered
    - Verify tooltip behavior for exact values
  - [x] 5.3 Add up to 5 additional tests if needed
    - Only add tests for critical gaps identified
    - Do NOT write comprehensive coverage
    - Focus on user-facing behaviors
  - [x] 5.4 Run all feature-specific tests
    - Run all tests related to this spec (approximately 12-22 tests total)
    - Verify all pass
    - Do NOT run entire application test suite

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 12-22 tests)
- Critical user workflows are covered
- No more than 5 additional tests added in gap analysis
- Feature is fully functional and matches spec requirements

---

## Execution Order

Recommended implementation sequence:

1. **Task Group 1: Composables and Data Constants** - Foundation layer with data and state management
2. **Task Group 2: DataPoint Component** - Reusable UI component needed by GlobalContextPanel
3. **Task Group 3: GlobalContextPanel and ZoomSlider** - Main feature components
4. **Task Group 4: Page Integration and Cleanup** - Wire everything together, remove old components
5. **Task Group 5: Test Review and Final Validation** - Ensure quality and fill gaps

## Files to Create

| File Path | Description |
|-----------|-------------|
| `/Users/jonathan/_code/urbanworld/web/app/composables/useGlobalStats.ts` | Global population data by epoch |
| `/Users/jonathan/_code/urbanworld/web/app/composables/useZoomLevel.ts` | Zoom level mapping and utilities |
| `/Users/jonathan/_code/urbanworld/web/app/components/ui/DataPoint.vue` | Reusable data display component |
| `/Users/jonathan/_code/urbanworld/web/app/components/map/GlobalContextPanel.vue` | Right sidebar with epoch and data |
| `/Users/jonathan/_code/urbanworld/web/app/components/map/ZoomSlider.vue` | Vertical zoom control |

## Files to Modify

| File Path | Changes |
|-----------|---------|
| `/Users/jonathan/_code/urbanworld/web/app/composables/useViewState.ts` | Add setZoom convenience method |
| `/Users/jonathan/_code/urbanworld/web/app/pages/index.vue` | Add new components, remove old ones |

## Files to Delete

| File Path | Reason |
|-----------|--------|
| `/Users/jonathan/_code/urbanworld/web/app/components/map/YearSlider.vue` | Superseded by GlobalContextPanel |
| `/Users/jonathan/_code/urbanworld/web/app/components/map/MapControls.vue` | Superseded by ZoomSlider |

## Visual Reference

Wireframe: `/Users/jonathan/_code/urbanworld/agent-os/specs/2026-01-02-global-view-controls/planning/visuals/sidebar-and-zoom-scale-wireframe.png`

Key visual elements:
- Right sidebar with year (2025), horizontal slider, population data points
- Vertical zoom slider labeled "Scale" floating between map and sidebar
- Data points pattern: small label, large humanized value, source link
- Humanized numbers show exact values on hover (tooltip)

## Technical Notes

- **Tailwind CSS**: Use Tailwind classes exclusively; avoid `<style>` blocks per project standards
- **Nuxt UI**: Leverage USlider, UTooltip, and UButton components
- **State Management**: Use singleton composables pattern (existing pattern in codebase)
- **Dark Mode**: Support via CSS variables and Tailwind dark: variants
- **Typography**: Mono font for numbers, sans-serif for labels (no serif in this spec)
- **Touch Targets**: Maintain 44x44px minimum for interactive elements
