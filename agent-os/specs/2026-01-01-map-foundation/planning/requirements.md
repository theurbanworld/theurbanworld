# Spec Requirements: Map Foundation

## Initial Description

Implement deck.gl H3HexagonLayer displaying global population density with MapLibre basemap. This is the foundational map component for The Urban World observatory - the first item in the MVP roadmap.

## Requirements Discussion

### First Round Questions

**Q1:** What should be the initial map view when the page loads?
**Answer:** Global view, centered on world, displaying all cities extents and H3 populations for 2025. Map fills entire viewport.

**Q2:** Should there be a year selector for viewing different time periods?
**Answer:** Yes. Implement a year slider for epochs 1975-2030 in 5-year increments.

**Q3:** What color scale should be used for the density visualization?
**Answer:** See `planning/cartography.md` for the sepia "old atlas" aesthetic. Use logarithmic scale - adjust palette accordingly.

Cartography spec defines:
- Basemap: Parchment land (#F5F1E6), slate blue-gray water (#B8C5CE), warm gray borders (#9A9385)
- Density gradient (6 steps): Cream (#F7F3E8) -> Warm sand (#E8DCC8) -> Tan (#D4C4A8) -> Ochre (#B89F72) -> Sienna (#8B7355) -> Deep brown (#5C4A3D)
- Fonts: Crimson Text (headers), Inter (body/map labels), JetBrains Mono (data)
- Accent: Muted forest green (#4A6741)

**Q4:** How should H3 data be loaded (full file vs viewport-based)?
**Answer:** Implement viewport-based loading (not full 62MB file load).

**Q5:** What basemap solution should be used?
**Answer:** Protomaps CDN for dev, self-hosted PMTiles on R2 for prod. Implement dark mode toggle.

**Q6:** What interactivity is needed for the hexagons and map?
**Answer:**
- Tooltip: Show city NAME when hovering over city extent (not hexagon population)
- Pan/zoom: Standard, NO 3D or angled viewing (keep north up always)

**Q7:** What map controls should be visible?
**Answer:** Visible zoom +/- buttons, NO compass (north always up).

**Q8:** Should city boundaries be included as a separate layer?
**Answer:** Yes - INCLUDE city boundaries layer with nice strong borders overlaid on top of H3 population grid. Visual: H3 hexagons colored by logarithmic density scale, with city boundaries as strong outlines on top. Users see GHSL boundaries AND generated hexagons and how they overlap.

**Q9:** What features are explicitly out of scope?
**Answer:** EXCLUDE: search, panels (separate specs)

### Existing Code to Reference

**Similar Features Identified:**
- Skeleton components exist at `/Users/jonathan/_code/urbanworld/web/app/components/map/`:
  - `GlobalMap.vue` - Main map container (skeleton)
  - `H3PopulationLayer.vue` - H3 hexagon layer (skeleton)
  - `MapControls.vue` - Zoom controls (skeleton)

**Data Files Available:**
- `h3_r8_pop_timeseries.parquet` (62MB, ~1M hexagons) - H3 population data
- `city_boundaries.pmtiles` - City boundary vector tiles
- `cities_index.json` - City metadata index

**Tech Stack Already Configured:**
- deck.gl 9.2.5
- MapLibre 5.14
- pmtiles library
- protomaps-themes-base

### Follow-up Questions

**Q10:** What should the dark mode color palette be?
**Answer:** Inverted sepia - deep brown background with cream/tan hexagon highlights.

**Q11:** How should the year slider be positioned and styled?
**Answer:**
- Position: Bottom center (like a timeline)
- Style: Simple slider with year labels at each stop
- Interaction: Snap immediately to each epoch (no smooth transitions)
- No auto-animate play button (document as possible future feature)

**Q12:** What approach should be used for viewport-based loading?
**Answer:** Recommend based on simplicity and existing infrastructure.

**Recommendation:** Convert H3 data to PMTiles format. This is the simplest approach because:
- PMTiles infrastructure already exists (used for city_boundaries.pmtiles)
- Cloudflare R2 already configured for hosting PMTiles
- pmtiles library already included in the frontend
- MapLibre natively supports PMTiles via protocol handler
- No new server-side infrastructure needed
- Range-request based loading works automatically with viewport

Implementation approach:
1. Pipeline: Convert `h3_r8_pop_timeseries.parquet` to vector tiles with H3 hexagon geometries
2. Pipeline: Package as PMTiles (one file per epoch, or single file with year as property)
3. Frontend: Load via existing pmtiles protocol, render with deck.gl MVTLayer or MapLibre native layer
4. Alternative: Use deck.gl's TileLayer with MVT tiles if H3HexagonLayer is preferred

**Q13:** What styling should city boundaries have?
**Answer:**
- Stroke color: Dark sepia (#4A4238)
- Stroke weight: 3px
- Fill: None, outline only
- Hover state: Yes - highlight boundary when hovering over city

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
N/A - No visual files found in `/Users/jonathan/_code/urbanworld/agent-os/specs/2026-01-01-map-foundation/planning/visuals/`

## Requirements Summary

### Functional Requirements

**Map Display:**
- Full-viewport map displaying H3 hexagons with global population density
- Initial view: Global, centered on world, showing 2025 data
- Logarithmic color scale using sepia "old atlas" palette (6-step gradient)
- 2D view only - north always up, no tilt/rotation

**Year Slider:**
- Position: Bottom center, timeline-style
- Range: 1975-2030 in 5-year increments (12 epochs)
- Style: Simple slider with year labels at each stop
- Behavior: Snap immediately to epochs (no animation)
- Future consideration: Auto-play button (not in scope)

**City Boundaries Layer:**
- Overlaid on top of H3 hexagon grid
- Stroke: Dark sepia (#4A4238), 3px weight
- Fill: None (outline only)
- Hover: Highlight boundary when cursor enters city extent

**Tooltips:**
- Show city NAME when hovering over city boundary
- No hexagon-level population tooltips

**Controls:**
- Zoom +/- buttons visible
- No compass control (north always up)
- Dark mode toggle

**Dark Mode:**
- Inverted sepia palette
- Deep brown background
- Cream/tan hexagon highlights

### Technical Considerations

**Data Loading (Recommended Approach):**
- Convert H3 parquet to PMTiles format in pipeline
- Leverage existing PMTiles infrastructure (already used for city boundaries)
- Host on Cloudflare R2 alongside other PMTiles
- Use range-request based viewport loading (automatic with PMTiles)

**Rendering Stack:**
- deck.gl H3HexagonLayer or MVTLayer for hexagon rendering
- MapLibre GL for basemap and city boundaries
- Protomaps CDN for development basemap
- Self-hosted PMTiles on R2 for production basemap

**Color Scales:**
- Light mode density gradient: Cream -> Warm sand -> Tan -> Ochre -> Sienna -> Deep brown
- Dark mode density gradient: Inverted (deep brown background, light hexagons)
- Logarithmic scale for density values

**Existing Code:**
- Use skeleton components as starting point: GlobalMap.vue, H3PopulationLayer.vue, MapControls.vue
- Nuxt UI v4 components for controls
- protomaps-themes-base for basemap styling (customize for sepia aesthetic)

### Reusability Opportunities
- Skeleton components already exist for GlobalMap, H3PopulationLayer, MapControls
- PMTiles loading pattern from city_boundaries can be reused for H3 data
- Nuxt UI v4 components for slider and buttons
- protomaps-themes-base as foundation for custom sepia theme

### Scope Boundaries

**In Scope:**
- Full-viewport H3 hexagon map with global population density
- Year slider (1975-2030) at bottom center
- City boundaries layer with 3px dark sepia outline
- Hover highlight on city boundaries with city name tooltip
- Sepia color theme (light mode)
- Dark mode with inverted sepia palette
- Zoom +/- controls
- Viewport-based data loading via PMTiles

**Out of Scope:**
- City search functionality (separate spec)
- City info panel (separate spec)
- 3D/tilted map view
- Compass/rotation controls
- Hexagon-level population tooltips
- Click-to-select city functionality (roadmap item 2)
- Year slider auto-play animation (future feature)

### Future Features (Documented for Later)
- Year slider auto-play/animate button
- Smooth transitions between years
- Hexagon-level tooltips with population data
