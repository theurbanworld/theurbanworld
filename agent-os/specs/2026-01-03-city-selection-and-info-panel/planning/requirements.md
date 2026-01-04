# Spec Requirements: City Selection and Info Panel

## Initial Description
This spec covers two related features from Phase 1 of the Urban World observatory roadmap:

**Task 2: City Selection** - Click or tap a city on the map to select it; highlight selected city boundary; pan/zoom to city extent

**Task 3: City Info Panel** - Display selected city's name, country, population, area, and density with clean typography and layout

These are foundational MVP features for the Urban World interactive observatory. The map foundation (Task 1) is already complete with deck.gl H3HexagonLayer displaying population density and MapLibre basemap with city boundaries and labels. Users can currently hover over cities to see boundary highlighting, but cannot select cities or see detailed information.

## Requirements Discussion

### First Round Questions

**Q1:** I assume clicking on a city boundary or label should select that city, and clicking elsewhere on the map (empty space or water) should deselect. Is that correct, or should deselection require an explicit close button only?
**Answer:** Explicit close button only. Clicking on another city while in city view should pan to that city and show its information.

**Q2:** I'm thinking the map should smoothly animate to fit the selected city's bounding box with some padding (e.g., 10-20% margin). Should we also set a minimum/maximum zoom level for this fit, or let the city extent fully determine the zoom?
**Answer:** Smoothly animate to city's bounding box with padding. Set min/max zoom levels as well.

**Q3:** Currently, hovering a city highlights its boundary with a diagonal stripe pattern. I assume a selected city should have a distinctly different visual treatment (perhaps a solid fill with reduced opacity, or a thicker/different colored border). Should the hover effect still work when a city is selected (showing on other cities), or should selection "lock" the highlight?
**Answer:** Do something different to the border of a selected city, but ideally NO fill (as they will eventually display data and other things WITHIN the bounds of the city when selected).

**Q4:** I assume the City Info Panel should appear on the left side of the screen (since GlobalContextPanel is on the right) as a slide-out panel. Should it be a full-height sidebar that pushes map content, or an overlay card that floats above the map?
**Answer:** Full-height sidebar. It should be its own route as a Nuxt Page at `/city/[city_id]`. Not an overlay card. The sidebar implementation should be generic/reusable so other routes can use it - create a generic sidebar component filled with specialized components for different routes/views.

**Q5:** For the initial MVP panel, I'm planning to show: city name, country, population, area (km2), and density (per km2) - all using the DataPoint component pattern with trend indicators and tooltips. Should we also include the city's global/regional ranking from the start, or save that for the "Context Rankings" task (Task 7)?
**Answer:** Show city name, country, population, area (km2), and density (per km2). Everything else is OUT OF SCOPE.

**Q6:** The existing DataPoint component shows trends relative to epoch changes. For the city info panel, should the data update when the user changes the epoch year slider (showing that city's stats for 1975-2030), or always show "current" (2025) data regardless of epoch?
**Answer:** Yes, all city DataPoints should update when epoch changes.

**Q7:** Is there anything about city selection or the info panel that you specifically want to exclude from this spec (e.g., deep-linking/URLs, chart components, mobile-specific layouts)?
**Answer:** Exclude chart components. Give best effort for mobile view. Given limited real estate, think about how the map can be covered when the sidebar is open on mobile.

### Existing Code to Reference

**Similar Features Identified:**
- Component: `GlobalContextPanel.vue` - Path: `/Users/jonathan/_code/urbanworld/web/app/components/map/GlobalContextPanel.vue` - Right-side panel with epoch controls and data points; similar layout and styling patterns
- Component: `DataPoint.vue` - Path: `/Users/jonathan/_code/urbanworld/web/app/components/ui/DataPoint.vue` - Reusable data display component with trends and tooltips; will be used in city info panel
- Composable: `useCityHover.ts` - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useCityHover.ts` - Hover state management pattern; similar pattern needed for selection state
- Composable: `useCitiesIndex.ts` - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useCitiesIndex.ts` - City data lookup by ID; will be extended or complemented for full city data
- Composable: `useSelectedYear.ts` - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useSelectedYear.ts` - Epoch state management; city data should react to this
- Composable: `useViewState.ts` - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useViewState.ts` - Map view state management; needed for pan/zoom to city
- Component: `useMap.ts` - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useMap.ts` - MapLibre integration with city boundaries layer and feature-state for hover; will need selection state added

### Follow-up Questions

**Follow-up 1:** The wireframe shows a relatively narrow left sidebar. I'm thinking around 280-320px width on desktop. Does that feel right, or do you have a specific width preference?
**Answer:** No specific width imagined, though it should be wide enough for two DataPoint components to align side-by-side.

**Follow-up 2:** The wireframe shows a "Button" in the header area. Should the close button (to exit city view and return to global view) be in the header bar (as shown in wireframe), inside the sidebar panel itself (e.g., top-right corner of the sidebar), or both locations?
**Answer:** Top-right corner of the sidebar panel.

**Follow-up 3:** The wireframe shows Population and Density but not Area. You mentioned Area (km2) should be included. Should it be a third data point in a row, or should the layout be different (e.g., stacked vertically)?
**Answer:** Area should be placed below the density. Think of it as a 2x2 grid: Top row: Population | Density. Bottom row: [blank space] | Area. (They'll add something to the blank space later)

**Follow-up 4:** When a user is viewing a city (at `/city/[city_id]`) and clicks another city on the map, should the URL update to the new city's route (e.g., `/city/new_city_id`), maintaining the sidebar open?
**Answer:** Yes, URL should definitely update. Clicking on the map should essentially navigate to the URL of that city view. Take advantage of all native Nuxt helpers like `navigateTo`.

## Visual Assets

### Files Provided:
- `left-sidebar-wireframe.png`: Low-fidelity wireframe showing the overall layout with left sidebar for city info and right panel for global context

### Visual Insights:
- **Layout structure:** Three-column layout - left sidebar (city info), center (map), right panel (global context/epoch controls)
- **Header:** "The Urban World" title bar spans full width with a button placeholder in top-right
- **Left sidebar content:** City name (large, prominent), country name below, data points arranged in grid
- **Data point display:** Population and Density shown side-by-side with humanized values and source attribution
- **Map interaction:** Selected city shown with boundary highlight (wireframe shows fill, but user specified NO fill - border only)
- **Right panel:** Existing GlobalContextPanel with epoch slider (horizontal in wireframe, vertical in current implementation), zoom slider, and global data points
- **Fidelity level:** Low-fidelity wireframe - treat as layout and structure guide, use application's existing styling (sepia/parchment theme, Tailwind classes, Nuxt UI components)

## Requirements Summary

### Functional Requirements

**City Selection:**
- Click/tap on city boundary or label to select a city
- Clicking another city while one is selected navigates to the new city (no deselection on empty space click)
- Smooth animated pan/zoom to fit selected city's bounding box with padding
- Enforce min/max zoom levels during fit animation
- Selected city boundary has distinct visual treatment (different border style, NO fill)
- Hover effects continue to work on non-selected cities
- Selection state persists via URL route (`/city/[city_id]`)

**City Info Panel:**
- Full-height left sidebar panel
- Displays: city name, country, population, area (km2), density (per km2)
- Data points arranged in 2x2 grid layout:
  - Top row: Population | Density
  - Bottom row: [reserved space] | Area
- Uses existing DataPoint component with trends and tooltips
- Data updates reactively when epoch year changes
- Close button in top-right corner of sidebar navigates back to global view (`/`)
- Sidebar component should be generic/reusable for other routes

**Routing:**
- City view is a Nuxt page at `/city/[city_id]`
- Clicking cities on map uses `navigateTo()` to update URL
- Close button navigates to `/` (global view)
- Deep-linking supported (direct URL access to city view)

**Mobile:**
- Best effort responsive layout
- Consider how sidebar covers map on small screens (full-screen takeover likely)

### Reusability Opportunities
- Generic sidebar layout component that can be reused by other routes/views
- City selection state composable (similar pattern to `useCityHover`)
- City data fetching composable (extend or complement `useCitiesIndex`)
- DataPoint component already exists and should be reused

### Scope Boundaries

**In Scope:**
- City selection via click/tap on map
- Pan/zoom animation to selected city
- Selected city boundary highlighting (border only, no fill)
- Left sidebar with city info (name, country, population, density, area)
- Epoch-reactive data display
- Nuxt routing at `/city/[city_id]`
- Generic reusable sidebar component
- Close button to return to global view
- Best-effort mobile layout

**Out of Scope:**
- Chart components (time series, radial density)
- Context rankings (global rank, percentile, regional rank)
- Density peers comparison
- City search functionality
- Shareable URLs with OG meta tags (just basic routing)
- Pixel-perfect mobile optimization

### Technical Considerations
- Use Nuxt's `navigateTo()` for programmatic navigation
- Extend MapLibre feature-state to support selection (in addition to hover)
- City boundaries PMTiles source already loaded; add selection layer styling
- City data available in `cities_index.json` (loaded by `useCitiesIndex`) and `city_populations.parquet` for epoch-specific data
- Bounding box data available in cities.parquet (`bbox_minx`, `bbox_miny`, `bbox_maxx`, `bbox_maxy`)
- Use `fitBounds` from MapLibre for pan/zoom animation with padding and zoom constraints
- Follow existing component patterns: Tailwind CSS, Nuxt UI components, sepia/parchment theme colors
- Sidebar width should accommodate two DataPoint components side-by-side (estimate ~320-360px)
