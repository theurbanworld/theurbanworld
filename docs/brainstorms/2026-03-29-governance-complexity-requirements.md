---
date: 2026-03-29
topic: governance-complexity
---

# Governance Complexity

## Problem Frame

Urban World defines cities as population phenomena (GHSL urban centres), not administrative constructs. But users naturally think of cities as governed places. A single GHSL urban centre like New York spans 50+ municipalities across three US states. This gap between the physical city and its political reality is invisible in the current product.

Showing governance complexity makes Urban World's functional definition more powerful — not by replacing it, but by contrasting it with administrative reality. It also establishes a pattern for methodologies with partial geographic coverage, since municipal boundary data won't be available for all 11,000+ cities.

## Requirements

**Data & Methodology**

- R1. Overlay geoBoundaries municipal boundaries with GHSL urban centre extents to identify which municipalities intersect each city
- R2. For each city with coverage, compute: raw municipality count, population share per municipality (estimated from GHSL population grid cells within each municipality slice), and Berry Index (1 − sum of squared population shares) scaled to 0–100 as the "Governance Complexity Score"
- R3. Store per-city governance data: list of municipality names, their population shares, the raw count, and the complexity score
- R4. Identify the admin level that corresponds to municipalities per country in geoBoundaries (this varies — admin level 2 in some countries, 3 or 4 in others)

**City Detail Page**

- R5. Add a "Governance Complexity" section below radial profiles on the city detail page, following the same pattern (collapsible, with map toggle)
- R6. Display the headline stat prominently: "This city spans N municipalities" (with country/state breakdown where applicable)
- R7. Show the Governance Complexity Score (0–100) with a distribution strip showing rank among cities with data
- R8. Map layer toggle: show municipal boundary outlines overlaid on the urban extent, color-coded by population share, with municipality name labels
- R9. Link to a methodology page explaining the approach, data source, Berry Index derivation, and interpretation guidance

**Partial Coverage Pattern**

- R10. When governance data is unavailable for a city, render the section with a message explaining why (e.g., "Municipal boundary data is not yet available for [country] in our current data sources")
- R11. Establish this as a reusable pattern: methodology sections declare their coverage, and the UI handles missing data consistently across all methodologies
- R12. Rankings and comparisons gracefully handle cities with and without governance data (filter indicators, coverage counts)

**Rankings & Comparison**

- R13. Add Governance Complexity Score as a sortable column in city rankings, available only when filtering to cities with governance data
- R14. Include governance metrics in the city comparison view when both cities have data

## Success Criteria

- Users visiting a city page immediately grasp how many administrative jurisdictions govern the urban area
- The map overlay visually communicates fragmentation more powerfully than the score alone
- Cities without coverage see a clear, honest explanation rather than a missing section
- The Berry Index scoring enables meaningful cross-city comparison (e.g., "Paris is more fragmented than London")

## Scope Boundaries

- No vertical fragmentation (overlapping layers like counties, school districts) in v1 — horizontal municipal fragmentation only
- No time-series governance data — treat boundaries as static (current)
- No governance quality or outcome metrics — this measures structural complexity, not effectiveness
- No OSM or GADM fallback in v1 — geoBoundaries only, accept coverage gaps
- Population shares are estimates derived from GHSL grid cells, not official census figures per municipality

## Key Decisions

- **geoBoundaries as sole data source**: Open license (CC-BY) aligns with project ethos. Accept that coverage will be partial — this is okay and establishes a pattern for future partial-coverage methodologies.
- **Berry Index for the comparative score**: Established in the literature (Ostrom, Tiebout & Warren 1961; Grassmueck & Shields 2010), captures distribution not just count. Renamed "Governance Complexity Score" and scaled 0–100 for general audience.
- **Layered presentation**: Raw count for the "wow" moment, Berry Index for comparison, map overlay for visual comprehension. Each layer serves a different user need.
- **Transparency over completeness**: Show the section even without data, explain why. Builds trust and invites future contribution.

## Dependencies / Assumptions

- geoBoundaries provides sufficiently granular municipal boundaries for a meaningful number of countries (need to validate coverage during planning)
- GHSL population grid cells can be spatially intersected with geoBoundaries polygons to estimate per-municipality population shares
- Municipal boundary PMTiles can be generated and served alongside existing boundary tiles

## Outstanding Questions

### Resolve Before Planning

(none)

### Deferred to Planning

- [Affects R1, R4][Needs research] How many of our ~11,400 cities have usable municipal-level coverage in geoBoundaries? What admin levels map to municipalities per country?
- [Affects R2][Technical] Best approach for spatial intersection: DuckDB spatial extension, GeoPandas, or H3-based approximation?
- [Affects R3][Technical] Data format for per-city governance output — extend existing city parquet files or new governance-specific files?
- [Affects R8][Technical] PMTiles generation strategy for municipal boundary overlays — per-city tiles or global tileset with filtering?
- [Affects R11][Technical] How to implement the partial-coverage pattern in the dataset/methodology composable system?

## Next Steps

-> `/ce:plan` for structured implementation planning
