# Specification: Map Foundation

## Goal

Implement the foundational interactive map for The Urban World observatory, displaying global population density via deck.gl H3HexagonLayer with a MapLibre basemap, year slider for temporal exploration (1975-2030), and city boundary overlays with hover tooltips.

## User Stories

- As a visitor, I want to see a full-screen map of global population density so that I can explore urbanization patterns worldwide
- As a researcher, I want to scrub through years 1975-2030 so that I can observe population growth trends over time

## Specific Requirements

**Full-Viewport Map Container**
- Map fills entire browser viewport with no margins or padding
- Container must resize responsively on window resize
- Use `position: fixed` or equivalent to prevent scroll
- Initialize at global view: center [0, 15], zoom 1.5 (showing all continents)
- Default to year 2025 on initial load

**MapLibre Basemap with Sepia Theme**
- Use Protomaps CDN (`https://api.protomaps.com/tiles/v3/{z}/{x}/{y}.mvt?key={protomapsKey}`) for development
- Self-hosted PMTiles from R2 for production (URL: configured via runtime config)
- Customize protomaps-themes-base to achieve sepia "old atlas" aesthetic
- Basemap colors: Parchment land (#F5F1E6), Slate blue-gray water (#B8C5CE), Warm gray borders (#9A9385)
- Lock bearing to 0 (north up), pitch to 0 (no tilt) - 2D only

**H3 Population Hexagon Layer**
- Use deck.gl H3HexagonLayer for native H3 rendering performance
- Load full `h3_r8_pop_timeseries.parquet` (62MB) upfront via @loaders.gl/parquet
- Store all year data in memory for instant year switching
- Filter displayed hexagons by selected year using in-memory filtering
- Apply logarithmic color scale using 6-step sepia gradient
- Light mode: Cream (#F7F3E8) to Deep brown (#5C4A3D)
- Dark mode: Inverted - Deep brown background with cream/tan highlights

**Year Slider Timeline**
- Position: fixed bottom center, 16px from bottom edge
- Range: 1975-2030 in 5-year increments (12 epochs: 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030)
- Display year labels at each stop (at minimum show: 1975, 2000, 2030)
- Snap immediately to epochs on change (no interpolation or animation)
- Use Nuxt UI v4 slider component styled to match sepia theme
- Width: responsive, approximately 60% of viewport width, max 600px

**City Boundaries Layer**
- Load city boundaries from PMTiles: `https://data.theurban.world/tiles/city_boundaries.pmtiles`
- Render as outline-only polygons overlaid on top of H3 hexagons
- Stroke: Dark sepia (#4A4238), 3px weight
- Fill: transparent (no fill)
- Add to MapLibre as a vector source with PMTiles protocol

**City Hover Interaction**
- Detect hover via MapLibre layer events on city_boundaries layer
- On hover: highlight city boundary (increase stroke width to 4px or add subtle glow)
- Display tooltip with city name (from feature properties)
- Tooltip styling: dark sepia background (#4A4238), cream text (#F7F3E8), rounded corners
- Position tooltip near cursor, ensure it stays within viewport bounds

**Zoom Controls**
- Position: fixed bottom-right, 16px from edges
- Include zoom in (+) and zoom out (-) buttons only
- NO compass control (north always up)
- Use Nuxt UI v4 button components with forest green accent (#4A6741)
- Keyboard shortcuts: +/- or scroll wheel for zoom

**Dark Mode Toggle**
- Position: fixed top-right, 16px from edges
- Toggle button with sun/moon icon
- Persist preference in localStorage
- Dark mode palette: invert sepia gradient (deep brown background, light hexagons)
- Dark basemap: use dark variant of protomaps theme or custom inversion

## Visual Design

No visual assets provided. Reference `planning/cartography.md` for complete design system:

**Color Palette Summary**
- Basemap land: #F5F1E6 (parchment)
- Basemap water: #B8C5CE (slate blue-gray)
- Density gradient (6 steps): #F7F3E8, #E8DCC8, #D4C4A8, #B89F72, #8B7355, #5C4A3D
- City boundaries: #4A4238 (dark sepia)
- Primary accent: #4A6741 (muted forest green)
- Hover accent: #3A5233 (darker green)

## Existing Code to Leverage

**Skeleton Components in `/web/app/components/map/`**
- `GlobalMap.vue` - Main container skeleton with TODO comments for deck.gl/MapLibre integration
- `H3PopulationLayer.vue` - Renderless component skeleton for H3 layer management
- `MapControls.vue` - Control overlay skeleton for zoom buttons

**Composables in `/web/app/composables/`**
- `useMap.ts` - Skeleton for MapLibre initialization with PMTiles protocol
- `useDeckGL.ts` - Skeleton for deck.gl initialization and layer management
- `useH3Data.ts` - Skeleton for parquet loading via @loaders.gl
- `useViewState.ts` - Skeleton for view state synchronization

**Configured Dependencies in `package.json`**
- deck.gl 9.2.5, @deck.gl/geo-layers (includes H3HexagonLayer)
- maplibre-gl 5.14, pmtiles 4.3.0, protomaps-themes-base 4.5.0
- @loaders.gl/core 4.3.4, @loaders.gl/parquet 4.3.4
- @nuxt/ui 4.2.1 for UI components

**CSS Theme in `/web/app/assets/css/main.css`**
- Forest green color scale already defined (--color-forest-*)
- Typography colors defined (espresso, body, data)
- Fonts configured: Crimson Pro, Inter, JetBrains Mono via Bunny Fonts

## Out of Scope

- City search functionality (separate spec)
- City info panel / sidebar (separate spec)
- 3D/tilted map view (not wanted)
- Compass/rotation controls (not wanted - north always up)
- Hexagon-level population tooltips on hover (deferred to future)
- Click-to-zoom to city extent (deferred to future)
- Year slider auto-play/animate button (documented as future feature)
- Smooth year transitions with interpolation (deferred)
- Viewport-based loading optimization (deferred - load full file for MVP)
- PMTiles conversion for H3 data (deferred)
