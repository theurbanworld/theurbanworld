# Specification: City Selection and Info Panel

## Goal
Enable users to select cities on the map to view detailed statistics in a left sidebar panel, with smooth navigation and epoch-reactive data display.

## User Stories
- As a user, I want to click on a city to see its population, density, and area so that I can explore urban data interactively
- As a user, I want to share a direct link to a specific city view so that others can see the same city information

## Specific Requirements

**City Selection via Map Click**
- Clicking a city boundary or label selects that city and navigates to `/city/[city_id]`
- Use `navigateTo()` for all programmatic navigation to leverage Nuxt's routing
- When a city is already selected, clicking another city navigates to the new city (no deselection on empty space)
- Clicking anywhere except a city does NOT deselect (close button only)
- Register click handler on `city-boundaries-hover-pattern` and `city-boundaries-line` layers via `queryRenderedFeatures`

**Map Pan/Zoom Animation**
- On city selection, smoothly animate the map to fit the selected city's bounding box
- Use MapLibre's `fitBounds()` with the city's `bbox_minx`, `bbox_miny`, `bbox_maxx`, `bbox_maxy` from cities index
- Apply padding (e.g., 50-100px) to ensure boundary is not flush with viewport edges
- Enforce minimum zoom level (e.g., 8) to prevent over-zooming on small cities
- Enforce maximum zoom level (e.g., 14) to prevent zooming in too far on large cities

**Selected City Boundary Highlighting**
- Add a `selected` feature-state to the city boundaries source (similar to existing `hover` state)
- Style selected city with a distinct border (e.g., thicker line width, different color or dashed style)
- Do NOT add a fill to the selected city boundary (future features will display data within bounds)
- Hover effects should continue to work on non-selected cities

**Generic Sidebar Layout Component**
- Create a reusable `AppSidebar.vue` component for left-side full-height panels
- Sidebar should be a fixed-position element that does not push map content
- Width should accommodate two DataPoint components side-by-side (~320-360px)
- Include a close button slot or prop in the top-right corner
- Transition animation for opening/closing (slide from left)

**City Info Panel Content**
- Create `CityInfoPanel.vue` component that uses the generic sidebar
- Display city name (large, prominent heading) and country name below
- Arrange DataPoint components in 2x2 grid:
  - Top row: Population (left) | Density (right)
  - Bottom row: Reserved empty space (left) | Area (right)
- Use existing `DataPoint` component with trends and tooltips
- Source labels should indicate data provenance (e.g., "Source: GHSL")

**Epoch-Reactive City Data**
- Create `useCityStats` composable to fetch and compute city statistics
- Load city population data from `city_populations.parquet` (or a JSON derivative)
- React to `selectedYear` changes from `useSelectedYear` composable
- Compute trend indicators (previous/next epoch growth rates) similar to `useGlobalStats`
- Humanize population values using existing `humanizeNumber` utility
- Format density as "X.X K/km2" or "X/km2" depending on magnitude

**Nuxt Routing**
- Create page at `/city/[city_id].vue` under `web/app/pages/city/`
- Page extracts `city_id` from route params and passes to panel component
- Close button navigates back to `/` (global view) using `navigateTo('/')`
- Support deep-linking (direct URL access to city view should work)

**City Selection State Composable**
- Create `useCitySelection` composable to manage selected city state
- Store the selected city ID as reactive state
- Sync with route - when route is `/city/[city_id]`, set selected city ID
- When route is `/`, clear selected city ID
- Provide methods: `selectCity(cityId)`, `clearSelection()`

## Visual Design

**`planning/visuals/left-sidebar-wireframe.png`**
- Three-column layout: left sidebar, center map, right GlobalContextPanel
- Left sidebar shows city name large at top, country name below in smaller text
- Population and Density DataPoints arranged horizontally in first row
- Area DataPoint positioned in bottom-right of 2x2 grid
- Wireframe shows fill on selected city boundary (override: use border-only per requirements)
- Close button should be in top-right corner of sidebar panel (not header bar)
- Maintain consistent styling with existing parchment/sepia theme and Tailwind classes

## Existing Code to Leverage

**`useMap.ts` - MapLibre integration with city boundaries**
- Existing feature-state implementation for hover (extend with `selected` state)
- `city-boundaries-hover-pattern` and `city-boundaries-line` layers for interaction
- `CITY_BOUNDARIES_SOURCE` constant and `city_boundaries` source-layer
- Pattern for setting up event handlers (`setupCityHoverEvents`)

**`useCityHover.ts` - Reactive hover state pattern**
- Singleton state pattern with `ref` and `readonly` exports
- Simple API: `setHoveredCityId`, `clearHover`, reactive `hoveredCityId`
- Use same pattern for `useCitySelection` composable

**`useCitiesIndex.ts` - City data lookup**
- `CityIndexEntry` interface with id, name, country, centroid, bbox, population
- `getCity(cityId)` method for retrieving city metadata
- Bounding box data available: `bbox: [minx, miny, maxx, maxy]`

**`DataPoint.vue` - Reusable data display component**
- Props: label, value, rawValue, trendPrevious, trendNext, sourceLabel
- Handles humanized values, trend indicators, tooltips
- Follow existing usage pattern from GlobalContextPanel

**`GlobalContextPanel.vue` - Right panel styling reference**
- Positioning pattern: `absolute z-100 p-4 rounded-xl shadow-lg bg-parchment/95`
- Responsive classes: `max-sm:` prefixes for mobile adjustments
- DataPoint usage with spacers and dividers

## Out of Scope
- Chart components (time series graphs, radial density charts) - separate task
- Context rankings (global rank, percentile, regional rank) - Task 7
- Density peers comparison feature - separate task
- City search functionality - separate task
- Shareable URLs with OG meta tags (just basic routing for now)
- Pixel-perfect mobile optimization (best effort only)
- Saving or bookmarking favorite cities
- Comparison mode between multiple cities
- Historical boundary changes visualization
- City detail pages beyond the info panel
