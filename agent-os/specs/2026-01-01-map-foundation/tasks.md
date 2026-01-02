# Task Breakdown: Map Foundation

## Overview

**Sprint Duration:** 72 hours (MVP)
**Total Tasks:** 24 tasks across 5 task groups
**Target Outcome:** Interactive global population density map with H3 hexagons, year slider (1975-2030), city boundary overlays, and dark mode support.

## Data URLs (Reference)

- H3 Population Data: `https://data.theurban.world/data/h3_r8_pop_timeseries.parquet` (62MB)
- City Boundaries: `https://data.theurban.world/tiles/city_boundaries.pmtiles`
- Cities Index: `https://data.theurban.world/data/cities_index.json`

## Task List

### Task Group 1: Map Infrastructure Setup
**Dependencies:** None
**Estimated Time:** 3-4 hours
**Specialist:** Frontend engineer with MapLibre/deck.gl experience

This group establishes the foundational map rendering pipeline: MapLibre basemap with PMTiles, deck.gl overlay integration, and view state management.

- [x] 1.0 Complete map infrastructure setup
  - [x] 1.1 Implement `useMap.ts` composable for MapLibre initialization
    - Register PMTiles protocol with MapLibre
    - Configure Protomaps CDN for development (`https://api.protomaps.com/tiles/v3/{z}/{x}/{y}.mvt?key={protomapsKey}`)
    - Configure self-hosted PMTiles URL for production (via `runtimeConfig.public.r2BaseUrl`)
    - Initialize map with sepia basemap theme using protomaps-themes-base
    - Apply theme customizations: land (#F5F1E6), water (#B8C5CE), borders (#9A9385), labels (#4A4238)
    - Lock bearing to 0, pitch to 0 (2D only, north always up)
    - Return map instance ref and loading state
    - Handle cleanup on unmount
  - [x] 1.2 Implement `useDeckGL.ts` composable for deck.gl integration
    - Initialize deck.gl MapboxOverlay for interleaved mode with MapLibre
    - Provide `setLayers(layers)` method for updating visualization layers
    - Synchronize view state between deck.gl and MapLibre
    - Forward hover/click events to layer handlers
    - Handle cleanup on unmount
  - [x] 1.3 Implement `useViewState.ts` composable for view state management
    - Define ViewState type: { longitude, latitude, zoom, pitch, bearing }
    - Initialize with global view: center [0, 15], zoom 1.5
    - Provide reactive view state that syncs with map changes
    - Expose `setViewState()` for programmatic control
    - Lock pitch to 0 and bearing to 0 in all state updates
  - [x] 1.4 Implement base `GlobalMap.vue` component
    - Create full-viewport container (`position: fixed`, `inset: 0`)
    - Initialize MapLibre via `useMap` composable
    - Initialize deck.gl via `useDeckGL` composable
    - Show loading indicator during map initialization
    - Add MapLibre GL CSS import in nuxt.config.ts
    - Handle SSR: wrap map initialization in `onMounted` / client-only
  - [x] 1.5 Verify map infrastructure renders correctly
    - Basemap displays with sepia theme colors
    - Map fills entire viewport without scroll
    - Pan and zoom controls work (scroll wheel, drag)
    - No console errors during initialization

**Acceptance Criteria:**
- MapLibre basemap renders with sepia "old atlas" theme
- Map fills entire viewport with no margins
- Pan/zoom via mouse/trackpad works smoothly
- View locked to 2D (no tilt or rotation)
- No errors in browser console

---

### Task Group 2: H3 Population Layer
**Dependencies:** Task Group 1
**Estimated Time:** 4-5 hours
**Specialist:** Frontend engineer with deck.gl and data loading experience

This group implements the core visualization: loading 62MB parquet file, rendering H3 hexagons with deck.gl, and applying the sepia color gradient.

- [x] 2.0 Complete H3 population layer implementation
  - [x] 2.1 Implement `useH3Data.ts` composable for parquet data loading
    - Load `h3_r8_pop_timeseries.parquet` from R2 using @loaders.gl/parquet
    - Parse parquet to extract: `h3_index`, `year`, `population` columns
    - Store full dataset in memory for instant year switching
    - Provide `getDataForYear(year: number)` method that filters in-memory
    - Return loading state, error state, and data availability
    - Handle loading progress (optional: show percentage)
  - [x] 2.2 Create logarithmic color scale utility
    - Create `/web/app/utils/colorScale.ts` utility
    - Implement logarithmic scale for population values
    - Map to 6-step sepia gradient:
      - Level 1 (very low): #F7F3E8 (cream)
      - Level 2 (low): #E8DCC8 (warm sand)
      - Level 3 (medium-low): #D4C4A8 (tan)
      - Level 4 (medium-high): #B89F72 (ochre)
      - Level 5 (high): #8B7355 (sienna)
      - Level 6 (very high): #5C4A3D (deep brown)
    - Export `getColorForPopulation(population: number, isDarkMode: boolean)` function
    - Invert gradient for dark mode (deep brown background, light highlights)
  - [x] 2.3 Implement H3HexagonLayer configuration in `H3PopulationLayer.vue`
    - Convert to renderless composable pattern (returns layer config, not template)
    - Use deck.gl H3HexagonLayer from @deck.gl/geo-layers
    - Configure layer with filtered data from `useH3Data`
    - Apply `getH3Hexagon` accessor for H3 index
    - Apply `getFillColor` using logarithmic color scale utility
    - Set appropriate elevation (0 for 2D), opacity, and extruded: false
  - [x] 2.4 Add selected year state management
    - Create `useSelectedYear.ts` composable
    - Initialize to 2025 (default year)
    - Define year epochs: [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
    - Provide `selectedYear` ref and `setYear(year)` method
    - Trigger H3 layer data update when year changes
  - [x] 2.5 Integrate H3 layer into GlobalMap
    - Connect `H3PopulationLayer` to `GlobalMap` via `useDeckGL.setLayers()`
    - Show loading state during initial parquet load
    - Display progress indicator for 62MB download
    - Update layer when selected year changes
  - [x] 2.6 Verify H3 layer renders correctly
    - Hexagons display at global zoom level
    - Color gradient correctly represents density (light = low, dark = high)
    - Year change updates hexagons immediately (no lag)
    - Zoom in/out shows appropriate hexagon detail

**Acceptance Criteria:**
- H3 hexagons render over the basemap
- Logarithmic color scale shows clear density differentiation
- Year switching is instant (data already in memory)
- Loading indicator shown during initial 62MB download
- Performance acceptable at global and city zoom levels

---

### Task Group 3: Year Slider Timeline
**Dependencies:** Task Group 2
**Estimated Time:** 2-3 hours
**Specialist:** Frontend/UI engineer

This group implements the year slider control using Nuxt UI v4, positioned at bottom center, with snap-to-epoch behavior.

- [x] 3.0 Complete year slider implementation
  - [x] 3.1 Create `YearSlider.vue` component
    - Position: fixed bottom center, 16px from bottom edge
    - Width: responsive, ~60% viewport width, max-width 600px
    - Use Nuxt UI v4 `USlider` component (or `URange` if more appropriate)
    - Configure min: 1975, max: 2030, step: 5
    - Style slider track and thumb to match sepia theme
    - Emit `update:year` event on change
  - [x] 3.2 Add year epoch labels to slider
    - Display labels below slider track
    - At minimum show: 1975, 2000, 2030
    - Optionally show all epochs if space permits
    - Style labels with JetBrains Mono font, #4A4238 color
  - [x] 3.3 Implement snap behavior
    - Snap immediately to nearest 5-year epoch on change
    - No smooth transitions or animations between years
    - Debounce rapid sliding to prevent excessive updates (optional)
  - [x] 3.4 Connect slider to year state
    - Bind to `useSelectedYear` composable
    - Update H3 layer data on year change
    - Display current year prominently (larger font, centered above slider)
  - [x] 3.5 Style slider for sepia theme
    - Track: warm gray (#9A9385) background
    - Filled track: forest green (#4A6741)
    - Thumb: forest green (#4A6741) with hover (#3A5233)
    - Ensure dark mode compatibility (invert appropriately)

**Acceptance Criteria:**
- Slider renders at bottom center of viewport
- Dragging slider changes displayed year immediately
- Year snaps to 5-year increments (no in-between values)
- Current year clearly displayed
- Slider styled to match sepia/forest green theme

---

### Task Group 4: City Boundaries & Hover Interaction
**Dependencies:** Task Group 1 (map infrastructure)
**Estimated Time:** 3-4 hours
**Specialist:** Frontend engineer with MapLibre experience

This group adds the city boundary layer from PMTiles and implements hover highlighting with city name tooltips.

- [x] 4.0 Complete city boundaries layer
  - [x] 4.1 Add city boundaries source to MapLibre
    - Add PMTiles source for `city_boundaries.pmtiles` URL
    - Configure as vector source type with PMTiles protocol
    - Add to `useMap.ts` composable after map loads
  - [x] 4.2 Create city boundaries layer style
    - Add MapLibre layer of type `line` for boundary outlines
    - Stroke color: #4A4238 (dark sepia)
    - Stroke width: 3px
    - No fill (outline only)
    - Render above H3 hexagon layer (proper layer ordering)
  - [x] 4.3 Implement hover detection
    - Add `mouseenter` and `mouseleave` event handlers on city_boundaries layer
    - Track hovered city feature ID in reactive state
    - Apply hover style: increase stroke width to 4px and/or add subtle glow
    - Use MapLibre feature state for dynamic styling
  - [x] 4.4 Create `CityTooltip.vue` component
    - Position: follows cursor, offset to avoid overlap
    - Background: dark sepia (#4A4238)
    - Text: cream (#F7F3E8), Inter font
    - Rounded corners (8px border-radius)
    - Padding: 8px 12px
    - Content: city name from feature properties
    - Ensure tooltip stays within viewport bounds
  - [x] 4.5 Connect hover state to tooltip
    - Show tooltip when hovering over city boundary
    - Update tooltip position on mouse move
    - Hide tooltip when mouse leaves city boundary
    - Extract city name from `feature.properties.city_id` and look up in cities index
  - [x] 4.6 Verify city boundaries and hover work correctly
    - Boundaries display as dark outlines over hexagons
    - Hover highlights the boundary
    - Tooltip shows city name
    - Layer ordering correct (boundaries on top of hexagons)

**Acceptance Criteria:**
- City boundaries render as 3px dark sepia outlines
- Hovering highlights the boundary (visible change)
- Tooltip displays city name in styled popup
- Tooltip follows cursor and stays in viewport
- Works correctly at various zoom levels

---

### Task Group 5: UI Controls & Dark Mode
**Dependencies:** Task Groups 1-4
**Estimated Time:** 3-4 hours
**Specialist:** Frontend/UI engineer

This group implements the zoom controls, dark mode toggle, and ensures all components respond correctly to theme changes.

- [x] 5.0 Complete UI controls and dark mode
  - [x] 5.1 Implement `MapControls.vue` with zoom buttons
    - Position: fixed bottom-right, 16px from edges
    - Two buttons: zoom in (+) and zoom out (-)
    - Use Nuxt UI v4 `UButton` components
    - Style with forest green (#4A6741) background, cream text
    - Hover state: darker green (#3A5233)
    - No compass control (explicitly omitted per spec)
    - Connect to view state to update zoom level
  - [x] 5.2 Add keyboard shortcuts for zoom
    - `+` or `=` key: zoom in
    - `-` key: zoom out
    - Scroll wheel already handled by MapLibre
    - Register keyboard event listeners in `GlobalMap.vue`
  - [x] 5.3 Create `DarkModeToggle.vue` component
    - Position: fixed top-right, 16px from edges
    - Toggle button with sun (light mode) / moon (dark mode) icon
    - Use Nuxt UI v4 `UButton` with icon slot
    - Use Lucide icons: `sun` and `moon`
    - Integrate with Nuxt color mode or custom state
  - [x] 5.4 Persist dark mode preference
    - Save preference to localStorage
    - Read preference on app load
    - Apply preference before first render (avoid flash)
    - Use Nuxt color mode module if available, or custom implementation
  - [x] 5.5 Implement dark mode theme changes
    - Basemap: switch to dark variant of protomaps theme
    - H3 hexagons: invert color scale (deep brown bg, cream/tan highlights)
    - City boundaries: adjust stroke color for visibility
    - UI controls: invert button colors appropriately
    - Year slider: adjust track and thumb colors
  - [x] 5.6 Add sepia color variables to CSS theme
    - Add cartography colors to `/web/app/assets/css/main.css`
    - Define CSS variables for basemap, density gradient, boundaries
    - Define light and dark mode variants
    - Reference variables in component styles for consistency
  - [x] 5.7 Final integration and polish
    - Ensure all controls are accessible (keyboard, screen reader)
    - Test responsive behavior on mobile viewports
    - Verify no z-index conflicts between controls, tooltip, and map
    - Performance check: no jank when switching modes or years

**Acceptance Criteria:**
- Zoom +/- buttons work and are styled correctly
- Keyboard shortcuts +/- zoom the map
- Dark mode toggle switches theme
- Dark mode preference persists across page reloads
- All layers (basemap, hexagons, boundaries) update on mode change
- Controls are visually consistent with sepia/forest theme

---

## Execution Order

Recommended implementation sequence based on dependencies:

```
Week/Day 1 (Foundation):
  1. Task Group 1: Map Infrastructure Setup (3-4 hours)
     - Core MapLibre + deck.gl pipeline

  2. Task Group 2: H3 Population Layer (4-5 hours)
     - Data loading and hexagon rendering

Week/Day 2 (Interactivity):
  3. Task Group 3: Year Slider Timeline (2-3 hours)
     - Timeline control UI

  4. Task Group 4: City Boundaries & Hover (3-4 hours)
     - Boundary layer and tooltips

Week/Day 3 (Polish):
  5. Task Group 5: UI Controls & Dark Mode (3-4 hours)
     - Zoom controls, theme switching, polish
```

**Total Estimated Time:** 15-20 hours of focused implementation

---

## Key Technical Decisions

1. **Full parquet load (62MB)**: Load entire timeseries upfront for instant year switching. Acceptable for MVP; viewport-based loading deferred.

2. **deck.gl H3HexagonLayer**: Native H3 support provides best performance for hexagon rendering.

3. **PMTiles protocol**: Both basemap (Protomaps) and city boundaries use PMTiles for efficient vector tile delivery.

4. **Renderless composables**: Layer logic in composables (not Vue components) for cleaner deck.gl integration.

5. **No 3D/tilt**: View locked to 2D with north always up - simplifies implementation and matches spec.

---

## Files to Create/Modify

### New Files
- `/web/app/utils/colorScale.ts` - Logarithmic color scale utility
- `/web/app/composables/useSelectedYear.ts` - Year state management
- `/web/app/composables/useH3Layer.ts` - H3 layer composable
- `/web/app/components/map/YearSlider.vue` - Timeline slider component
- `/web/app/components/map/CityTooltip.vue` - Hover tooltip component
- `/web/app/components/map/DarkModeToggle.vue` - Theme toggle button
- `/web/app/composables/useCitiesIndex.ts` - Cities index loading for city names
- `/web/app/composables/useCityHover.ts` - City hover state management
- `/web/app/composables/useDarkMode.ts` - Dark mode state management

### Files to Implement (from skeletons)
- `/web/app/composables/useMap.ts` - MapLibre initialization
- `/web/app/composables/useDeckGL.ts` - deck.gl integration
- `/web/app/composables/useViewState.ts` - View state management
- `/web/app/composables/useH3Data.ts` - Parquet data loading
- `/web/app/components/map/GlobalMap.vue` - Main map container
- `/web/app/components/map/H3PopulationLayer.vue` - H3 layer logic
- `/web/app/components/map/MapControls.vue` - Zoom buttons

### Files to Modify
- `/web/app/pages/index.vue` - Mount GlobalMap and controls
- `/web/app/assets/css/main.css` - Add sepia theme variables
- `/web/nuxt.config.ts` - Add MapLibre CSS import
- `/web/app/app.config.ts` - Add map configuration values
- `/web/types/h3.ts` - H3 hexagon data types

---

## Out of Scope (Documented for Reference)

Per spec, the following are explicitly excluded from this sprint:
- City search functionality (separate spec)
- City info panel / sidebar (separate spec)
- 3D/tilted map view
- Compass/rotation controls
- Hexagon-level population tooltips
- Click-to-zoom to city extent
- Year slider auto-play animation
- Smooth year transitions with interpolation
- Viewport-based loading optimization
- PMTiles conversion for H3 data
