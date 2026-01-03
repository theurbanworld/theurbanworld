# Specification: Global View Controls

## Goal

Add a right-side Global Context Panel displaying aggregate global data (epoch year, world population, urban population) with an integrated epoch slider, and a vertical zoom slider with named scale levels for map navigation.

## User Stories

- As a user, I want to see global population statistics that update as I change the time epoch so that I can understand urbanization trends over time
- As a user, I want to quickly identify and navigate to specific map scale levels so that I can explore data at the appropriate granularity

## Specific Requirements

**Global Context Panel**
- Always-visible right-side panel with fixed positioning (similar to existing DarkModeToggle pattern)
- Contains epoch year display, horizontal slider, and two data points (World Population, Urban Population)
- Panel width approximately 200-240px to accommodate content without crowding
- Styled with parchment background (light mode) / espresso background (dark mode) with opacity
- No regional breakdown - only global aggregate data
- Panel positioned to avoid overlap with existing header/controls

**Epoch Year Display and Slider**
- Prominent year display at top of panel using mono font (matching existing YearSlider pattern)
- Horizontal slider always visible below year (not hidden on hover)
- Maintains existing functionality: 1975-2030 range in 5-year increments
- Reuse existing `useSelectedYear` composable for state management
- Remove existing bottom-center YearSlider component entirely from index.vue

**DataPoint Component**
- Create reusable component in `components/ui/DataPoint.vue` for app-wide use
- Props: label (string), value (string/number), rawValue (number), sourceLabel (string)
- Structure: small label text (sans-serif), large humanized value (mono font), source link (sans-serif)
- Humanized numbers show exact value in tooltip on hover (mono font for number in tooltip)
- Use Nuxt UI UTooltip component for hover behavior
- Design for future extension when comprehensive source attribution system is added

**World Population Data**
- Display humanized format (e.g., "8.2 billion") with exact value on hover
- Data source: Pipeline `WORLD_POPULATION` constant from `s04b_compute_city_rankings.py`
- Create `useGlobalStats` composable to provide population data by epoch
- Store data as TypeScript constant (static data, not fetched from R2)
- Source link shows "Source" placeholder text (links to be added in future attribution system)

**Urban Population Data**
- Display humanized format (e.g., "3.6 billion") with exact value on hover
- Data source: Aggregated from `city_populations.parquet` (values provided in requirements)
- Include in same `useGlobalStats` composable alongside world population
- Source link shows "Source" placeholder text

**Zoom Slider Component**
- Vertical slider floating above the map, positioned to the left of the Global Context Panel
- Use fixed positioning with appropriate z-index to float above map
- Bidirectional synchronization with map zoom via `useViewState` composable
- Create new `useZoomLevel` composable for zoom-to-level mapping logic
- Remove existing MapControls.vue component entirely (superseded by zoom slider)

**Zoom Level Indicators**
- Five named zoom levels with associated Lucide icons always visible along slider track:
  - Metropolitan (zoom 0-5): `i-lucide-globe`
  - City (zoom 5-10): `i-lucide-building-2`
  - Neighborhood (zoom 10-13): `i-lucide-trees`
  - Street (zoom 13-16): `i-lucide-road`
  - Building (zoom 16-18+): `i-lucide-building`
- Icons are clickable to snap to the center zoom of that level
- Level names shown only on hover (since labels are long and slider is thin/vertical)
- Current level displayed prominently above slider: small "Scale" label, large level name below

**Mobile Layout**
- Best effort, not a priority
- Year and slider displayed above the map (horizontal bar)
- Zoom slider remains on right side
- Global data points may be hidden or collapsed on small screens

## Visual Design

**`planning/visuals/sidebar-and-zoom-scale-wireframe.png`**
- Right sidebar shows clear vertical hierarchy: year (2025), horizontal slider, data points
- Year displayed prominently in large text at top of panel
- Data points follow pattern: small label, large humanized value, source link below
- Zoom slider labeled "Scale" is vertical with thumb indicator
- Zoom slider floats between map and sidebar, not inside sidebar
- Yellow annotation confirms humanized numbers show exact values on hover
- Panel uses white/light background (adapt to parchment/espresso theme)

## Existing Code to Leverage

**YearSlider.vue**
- Reuse slider styling patterns (track, thumb, range colors)
- Adapt year display typography (mono font, forest green accent)
- Move functionality to GlobalContextPanel, then delete original component
- Preserve the click-to-snap behavior for year labels

**useSelectedYear.ts**
- Use directly without modification for epoch state management
- Provides selectedYear, setYear, yearEpochs, and navigation helpers
- Singleton pattern ensures consistent state across components

**useViewState.ts**
- Extend to support zoom level change callbacks
- Use viewState.zoom for bidirectional sync with zoom slider
- May need to add setZoom convenience method for snap-to-level functionality

**MapControls.vue**
- Reference styling patterns (44x44px touch targets, forest green buttons)
- Component will be removed entirely after zoom slider implementation
- Zoom in/out functionality moves to zoom slider interactions

**DarkModeToggle.vue**
- Reference fixed positioning pattern for overlay components
- Use same z-index layering approach (z-100)

## Out of Scope

- Animated transitions between epochs
- City-specific data in global panel
- Regional breakdown data (only global aggregates)
- Comprehensive source attribution system (placeholder links only)
- Polished mobile experience (best effort only)
- Fetching data from R2 (use static TypeScript constants)
- Custom slider component (use Nuxt UI USlider)
- Keyboard shortcuts for zoom levels
- Zoom level persistence in URL/localStorage
