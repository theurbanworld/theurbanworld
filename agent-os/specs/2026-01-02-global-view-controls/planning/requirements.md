# Spec Requirements: Global View Controls

## Initial Description

Phase 2, steps 10-12 from the roadmap:

**Step 10**: Global Context Panel — Add a right-side panel displaying aggregate global data: total urban population, number of cities, regional breakdowns (M effort)

**Step 11**: Epoch Slider Improvements — Move the epoch slider into the global context panel on the right, placing it at the top. Make the current year prominent, with the slider below the year (or shown when hovered). In this way a user can quickly see in the top right what epoch they are on, and the rest of the global sidebar shows data for that year (S effort)

**Step 12**: Zoom Slider — Add a vertical zoom level slider over the map, to the left of the global context panel. This slider should move when a user zooms up or down. It should have notches with named levels as follows (with text to give you what users would explore at that zoom level):
- **Building**: Individual structures, heights, typologies
- **Street**: Network patterns, walkability, public space
- **Neighborhood**: Local amenities, 15-minute city
- **City**: Overall form, radial profiles, growth patterns
- **Metropolitan**: Regional connections, polycentric structure
(S effort)

## Requirements Discussion

### First Round Questions

**Q1:** I assume the Global Context Panel should appear on the right side at all times (not collapsible like a slide-out panel), matching the fixed positioning of existing controls like the DarkModeToggle. Is that correct, or should it be collapsible/toggleable?
**Answer:** Always visible. No regional breakdown - just global data.

**Q2:** For the regional breakdowns, I see your data has 9 regions. Should we display all 9 regions, or focus on a subset?
**Answer:** No regional breakdown needed - just global aggregate data.

**Q3:** I assume the aggregate data should update when the user changes the epoch year. Is that the intended behavior?
**Answer:** Yes. Data to show per epoch (from wireframe):
- Epoch year (prominent)
- World Population (with humanized display like "8.4 billion")
- Urban Population (with humanized display like "3.7 billion")
- Each data point has a "Source" link (placeholder for now - app-wide attribution system coming later)
- Humanized numbers should show exact values on hover

**Q4:** For making the year "prominent" at the top of the global panel, should the slider always be visible below the year, or hidden until the user hovers/taps the year?
**Answer:** Slider should always be visible (not hidden on hover). Remove bottom slider entirely, move to global context sidebar.

**Q5:** The current YearSlider is positioned at the bottom-center. When we move it to the global panel, should we remove the bottom slider entirely?
**Answer:** Yes, remove the bottom slider entirely.

**Q6:** I assume the zoom slider should be synchronized bidirectionally with the map. Is this correct?
**Answer:** Yes, synchronized bidirectionally with map.

**Q7:** For the named zoom levels, should these be clickable labels that snap to specific zoom levels, or purely informational?
**Answer:** Zoom level labels should be clickable to snap. Display current zoom level prominently. Since labels are long and slider is thin/vertical: only display names on hover. Find icons to represent each level using Lucide icons.

**Q8:** Should we display the current zoom level name prominently?
**Answer:** Yes, display current zoom level prominently - user suggests positioning above the zoom slider, with "Scale" as small text above the larger level name (same pattern as "World Population" being small text above "8.4 billion").

**Q9:** On mobile screens, should we hide or collapse the Global Context Panel?
**Answer:** Show year and slider above the map, keep zoom slider to the right. Best effort, not a priority.

**Q10:** Is there anything that should be explicitly excluded from this spec?
**Answer:** Animated transitions between epochs, city-specific data in global panel.

### Existing Code to Reference

**Similar Features Identified:**
- Component: `YearSlider.vue` - Path: `/Users/jonathan/_code/urbanworld/web/app/components/map/YearSlider.vue` - Current epoch slider implementation to be relocated
- Component: `MapControls.vue` - Path: `/Users/jonathan/_code/urbanworld/web/app/components/map/MapControls.vue` - Existing zoom buttons pattern
- Component: `DarkModeToggle.vue` - Path: `/Users/jonathan/_code/urbanworld/web/app/components/map/DarkModeToggle.vue` - Fixed positioning pattern
- Composable: `useSelectedYear.ts` - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useSelectedYear.ts` - Year state management
- Composable: `useViewState.ts` - Path: `/Users/jonathan/_code/urbanworld/web/app/composables/useViewState.ts` - Map view state including zoom
- Pipeline: `s04b_compute_city_rankings.py` - Path: `/Users/jonathan/_code/urbanworld/pipeline/src/s04b_compute_city_rankings.py` - Contains `WORLD_POPULATION` constant with UN WPP 2022 calibrated data

### Follow-up Questions

**Follow-up 1:** The wireframe shows the zoom slider labeled "Scale" between the map and the sidebar. You mentioned displaying the current zoom level name in the "top-right corner of map" - should this be a separate label element above/near the zoom slider, or integrated into the slider itself?
**Answer:** Put the zoom label ABOVE (not integrated into) the zoom slider. The word "Scale" should be small text above the larger label name - same pattern as "World Population" being small text above the larger number "8.4 billion".

**Follow-up 2:** For the World Population data, should both data points show their actual sources now, or should we use a generic placeholder?
**Answer:** Use a generic placeholder "Source" for now. A comprehensive source system will be implemented soon.

**Follow-up 3:** For the zoom level icons, do you have preferences?
**Answer:** Use Option A:
- Building: `i-lucide-building`
- Street: `i-lucide-road`
- Neighborhood: `i-lucide-trees`
- City: `i-lucide-building-2`
- Metropolitan: `i-lucide-globe`

## Visual Assets

### Files Provided:
- `sidebar-and-zoom-scale-wireframe.png`: Low-fidelity wireframe showing the overall layout with:
  - Right sidebar containing epoch year (2025), horizontal slider, World Population (8.4 billion, Source: UN), Urban Population (3.7 billion, Source: EU)
  - Vertical zoom slider labeled "Scale" positioned between map and sidebar, floating above the map
  - Yellow annotation noting humanized numbers show exact values on hover

### Visual Insights:
- Panel layout follows a clear hierarchy: year at top, slider below, then data points
- Data points use consistent pattern: small label text, large humanized value, source link
- Zoom slider is vertical, floats above the map, positioned to left of sidebar
- Wireframe is low-fidelity; use application's existing styling (forest green accents, parchment/espresso themes)

## Requirements Summary

### Functional Requirements

**Global Context Panel (Step 10):**
- Always-visible right-side panel
- Displays aggregate global data that updates with epoch selection
- Contains: epoch year display, epoch slider, World Population, Urban Population
- No regional breakdown

**Reusable DataPoint Component:**
- Create a flexible component for displaying data points
- Shows: small label text (sans-serif), large humanized value (mono font), source link (sans-serif)
- Humanized numbers display exact value on hover (tooltip, mono font for the number)
- Will be extended later for app-wide use

**Epoch Slider (Step 11):**
- Move from bottom-center to global context panel
- Remove existing bottom YearSlider entirely
- Prominent year display at top of panel (mono font for year number)
- Horizontal slider always visible below year
- Maintains existing functionality (1975-2030, 5-year increments)

**Zoom Slider (Step 12):**
- Vertical slider floating above the map, positioned to left of the global context panel
- Bidirectional synchronization with map zoom
- Five named zoom levels with clickable snap-to functionality:
  - Building (zoom ~18): `i-lucide-building`
  - Street (zoom ~15): `i-lucide-road`
  - Neighborhood (zoom ~12): `i-lucide-trees`
  - City (zoom ~8): `i-lucide-building-2`
  - Metropolitan (zoom ~4): `i-lucide-globe`
- Icons always visible along slider track; level names shown on hover only
- Current level displayed prominently above slider:
  - Small "Scale" label (sans-serif)
  - Large level name below (sans-serif, e.g., "City")

### Typography Guidelines
- **Mono font**: All data numbers (population values, year numbers, exact values in tooltips)
- **Sans-serif**: All descriptions, labels, and general text (e.g., "World Population", "Scale", zoom level names, "Source")
- **Serif**: City names only (not applicable in this spec since no city-specific data)

### Reusability Opportunities
- DataPoint component designed for app-wide reuse
- Source attribution pattern to be extended with comprehensive system later
- Zoom level composable could be reused for other scale-dependent features

### Scope Boundaries

**In Scope:**
- Global Context Panel with epoch year, slider, and two data points
- DataPoint component with humanized values and hover tooltips
- Relocation of epoch slider from bottom to sidebar
- Vertical zoom slider with bidirectional map sync (floating above map)
- Clickable zoom level icons with names on hover
- Current zoom level display above slider
- Basic mobile layout (year/slider above map, zoom slider on right)

**Out of Scope:**
- Animated transitions between epochs
- City-specific data in global panel
- Regional breakdown data
- Comprehensive source attribution system (placeholder only)
- Polished mobile experience (best effort only)

### Technical Considerations

**Data Sources:**
- World Population: Available in pipeline at `/Users/jonathan/_code/urbanworld/pipeline/src/s04b_compute_city_rankings.py` as `WORLD_POPULATION` constant (GHSL Table 20 - UN WPP 2022 calibrated). This data needs to be extracted and made available to the frontend, either as:
  - A static JSON file generated by the pipeline and served from R2
  - A TypeScript constant file in the web app (duplicating the data)
  - Recommendation: Generate a `global_stats.json` file in the pipeline that includes world population per epoch, to allow future expansion
- Urban Population: Calculated from existing `city_populations.parquet` by epoch (already computed in pipeline, needs aggregation)

**Available World Population Data (from pipeline):**
```
1975: 4,069,437,259
1980: 4,444,007,748
1985: 4,861,730,652
1990: 5,316,175,909
1995: 5,743,219,510
2000: 6,148,899,024
2005: 6,558,176,175
2010: 6,985,603,172
2015: 7,426,597,609
2020: 7,840,952,947
2025: 8,191,988,536
2030: 8,546,141,407
```

**Available Urban Population Data (from city_populations.parquet aggregation):**
```
1975: 1,178,323,105
1980: 1,346,953,243
1985: 1,532,907,872
1990: 1,741,456,510
1995: 2,012,230,273
2000: 2,306,333,391
2005: 2,556,795,633
2010: 2,819,883,050
2015: 3,095,854,703
2020: 3,350,187,245
2025: 3,569,570,193
2030: 3,759,831,609
```

**State Management:**
- Extend `useSelectedYear` composable or create new composable for global data
- Create `useZoomLevel` composable for zoom slider state and level mapping
- Leverage existing `useViewState` for zoom synchronization

**Zoom Level Mapping:**
- Define zoom ranges that correspond to each named level
- Suggested ranges (to be refined):
  - Metropolitan: zoom 0-5
  - City: zoom 5-10
  - Neighborhood: zoom 10-13
  - Street: zoom 13-16
  - Building: zoom 16-18+

**Component Structure:**
- `GlobalContextPanel.vue` - Main sidebar container
- `DataPoint.vue` - Reusable data display component (in `components/ui/` for app-wide use)
- `ZoomSlider.vue` - Vertical zoom control with level indicators (floating above map)
- Modify `YearSlider.vue` or create new `EpochSlider.vue` for sidebar variant
- Update `index.vue` to integrate new components and remove old YearSlider
- Remove `MapControls.vue` entirely. It is superceded by `ZoomSlider.vue`

**Styling:**
- Follow existing design system (forest green accents, parchment/espresso dark mode)
- Use Tailwind CSS utilities
- Maintain 44x44px minimum touch targets
- Support dark mode throughout
