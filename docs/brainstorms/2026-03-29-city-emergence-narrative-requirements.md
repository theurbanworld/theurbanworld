---
date: 2026-03-29
topic: city-emergence-narrative
---

# City Emergence Narrative

## Problem Frame

When users scrub through epochs, cities with later birth years abruptly appear — jumping from nothing to a populated urban center. This is confusing and hides the most interesting part of the GHSL story: *how* a cluster of populated cells gradually crosses the urban center threshold and "becomes" a city.

Currently, H3 population data only covers cells *within* MTUC city boundaries. This means we can't show what was happening in a location *before* GHSL recognized it as a city. Expanding the H3 grid to cover the entire world (and serving per-city extracts with buffer zones) unlocks a compelling narrative: watch population accumulate in an area until it crosses the threshold.

## Requirements

**Pipeline: Whole-World H3 Processing**
- R1. Process the entire GHSL-POP raster into H3-R8 cells globally, not just within MTUC boundaries. This produces a complete population-by-cell dataset for all 12 epochs.
- R2. Per-city web exports include H3 cells in a buffer zone beyond the MTUC boundary (e.g., 20-50km), so the frontend can show surrounding population context without loading the full global dataset.
- R3. Pre-compute a "proto-city summary" per city: for each pre-birth epoch, sum the population of H3 cells within the city's birth-epoch MTUC boundary. This provides the sparkline data for pre-city epochs without requiring the frontend to do spatial queries.

**Frontend: Pre-City State**
- R4. When the selected epoch is before a city's birth year, the sidebar displays a "pre-city" state instead of showing zero population or hiding the city. This state communicates that the location existed with population but wasn't yet classified as an urban center by GHSL.
- R5. The population sparkline/chart shows pre-city epoch data with a visually distinct treatment (e.g., dashed line, muted color) and a clear marker at the birth year indicating when the area became a city.
- R6. The H3 heatmap layer shows cells in the buffer zone around a city, not just cells within the MTUC boundary. This lets users see surrounding population density and the "proto-urban fringe."

**Data Integrity**
- R7. GHSL MTUC boundaries remain the authoritative definition of what constitutes a "city" and when it is born. We do not re-derive city boundaries from H3 cells. Buffer-zone H3 cells provide spatial context but do not define or extend city membership.
- R8. The existing density outlier filter continues to apply to city rankings and web exports. The raw whole-world H3 dataset is unfiltered; filtering applies only at the city-aggregate level.

**Pipeline: City Index**
- R9. Export `ucdb_year_of_birth` to the frontend city index JSON so the frontend can distinguish "pre-city epoch" from "missing data."

## User Flow

```
User selects a city (born in 2000) → epoch is 2025
  Sidebar: normal city view with population, density, area
  Sparkline: full line 2000-2030, dashed/muted line 1975-1995 showing pre-city population
  Map: H3 heatmap shows city cells + buffer zone

User scrubs epoch back to 1990
  Sidebar: "pre-city" state — shows area population, notes "Becomes urban center in 2000"
  Sparkline: current epoch marker moves to 1990 (in the pre-city zone)
  Map: H3 heatmap shows cells in the area with their 1990 population — no MTUC boundary overlay

User scrubs forward to 2000
  Sidebar: transitions to normal city state — population, density, area appear
  Sparkline: marker crosses the birth-year threshold
  Map: MTUC boundary appears, H3 cells now labeled as part of the city
```

## Success Criteria

- Users can watch a city "form" by scrubbing through epochs and seeing population accumulate in H3 cells before the GHSL birth year
- Cities that don't exist at the selected epoch show a meaningful pre-city state instead of 0 population or abrupt appearance
- The sparkline tells the full story: pre-city growth, birth-year threshold, and post-city trajectory
- The whole-world H3 dataset exists in the pipeline and can serve future use cases (global tiling, non-city analysis)

## Scope Boundaries

- No re-derivation of city boundaries from H3 cells (deferred — may revisit later)
- No global tiling / full-world browser exploration in this phase — per-city extracts only
- No changes to the 1km grid dataset — this is H3-only
- No changes to city rankings or growth calculations — those continue to use MTUC-bounded data

## Key Decisions

- **Whole-world H3 processing**: Process everything in the pipeline even though the frontend only serves per-city slices. The global dataset enables future features and is a one-time compute cost (Modal).
- **GHSL boundaries as authoritative**: H3 is a visualization layer, not a competing city definition. Avoids methodological divergence from GHSL.
- **Per-city extracts with buffer**: Keeps frontend data loading manageable. The existing lazy-load-per-city pattern extends naturally.
- **Proto-city summary pre-computed**: The pipeline computes pre-birth population sums so the sparkline doesn't need to do spatial queries client-side.

## Outstanding Questions

### Deferred to Planning
- [Affects R1][Technical] What's the optimal approach for whole-world H3 rasterization? The existing Modal script generates H3 cells from city polygons and cannot scale to 200M+ global cells — it needs replacement, not extension. Planning should design a tiling strategy.
- [Affects R4, R6][Technical] Frontend H3 data loading architecture fork: the current `useH3Data.ts` loads a monolithic parquet and filters by `city_id`. Per-city buffered extracts need a different loading path. Should the monolith be kept for non-buffered use, or replaced entirely?
- [Affects R2][Needs research] What buffer distance (km) produces a good visual result without excessive data? Likely needs experimentation — 20km, 30km, 50km.
- [Affects R2][Technical] What format/structure for per-city H3 extracts? Extend the existing timeseries parquet with a `city_id` + buffer flag, or separate files per city?
- [Affects R3][Technical] Proto-city area uses the birth-epoch MTUC boundary projected backward (decided during brainstorm). Planning should validate this works for edge cases (cities with very different early vs. late boundaries).
- [Affects R5][Design] Exact visual treatment for pre-city sparkline data — dashed line, different color, shaded background region?
- [Affects R6][Technical] How large can per-city H3 extracts (with buffer) get before the frontend loading pattern breaks? Need to estimate cell counts for large cities + buffer.

## Next Steps

→ `/ce:plan` for structured implementation planning
