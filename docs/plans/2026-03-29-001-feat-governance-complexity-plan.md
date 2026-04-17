---
title: "feat: Add governance complexity analysis with municipal boundary overlays"
type: feat
status: active
date: 2026-03-29
origin: docs/brainstorms/2026-03-29-governance-complexity-requirements.md
---

# feat: Add governance complexity analysis with municipal boundary overlays

## Overview

Add a "Governance Complexity" feature that overlays geoBoundaries municipal boundaries with GHSL urban centre extents to reveal how many administrative jurisdictions govern each city. Computes a Berry Index-based complexity score, displays results on city detail pages with an interactive map overlay, and integrates into rankings and comparison views. Establishes a reusable partial-coverage pattern for methodologies that don't cover all cities.

## Problem Frame

Urban World defines cities as population phenomena (GHSL urban centres), not administrative constructs. A single GHSL urban centre like New York spans 50+ municipalities across three US states. This gap between the physical city and its political reality is currently invisible. Showing governance complexity makes the functional definition more powerful by contrasting it with administrative reality. (see origin: docs/brainstorms/2026-03-29-governance-complexity-requirements.md)

## Requirements Trace

- R1. Overlay geoBoundaries ADM2 boundaries with GHSL urban centre extents
- R2. Compute municipality count, population shares, and Berry Index (scaled 0–100) per city
- R3. Store per-city governance data with municipality names, shares, count, and score
- R4. Map admin levels to municipalities per country (use ADM2 globally as baseline)
- R5. Add governance section below radial profiles on city detail page
- R6. Display "spans N municipalities" headline
- R7. Show complexity score with distribution strip
- R8. Map layer with color-coded municipal boundaries and labels
- R9. Methodology page for governance complexity
- R10. Show explanatory message when data unavailable
- R11. Establish reusable partial-coverage pattern
- R12. Rankings/comparisons handle partial coverage gracefully
- R13. Add complexity score as sortable ranking column
- R14. Include governance metrics in comparison view

## Scope Boundaries

- Horizontal municipal fragmentation only — no vertical layers (counties, school districts)
- Static boundaries — no time-series governance data
- Structural complexity only — no governance quality or outcome metrics
- geoBoundaries only — no OSM or GADM fallback
- Population shares estimated from GHSL grid cells, not official census figures
- ADM2 globally as the municipal level — no per-country admin level customization in v1

## Context & Research

### Relevant Code and Patterns

- **Pipeline domain pattern**: `pipeline/src/radial/` — single script domain with `generate_radial_profiles.py`
- **Web export pattern**: `pipeline/src/web_export/generate_radial_profiles.py` — parquet → JSON → R2
- **PMTiles pattern**: `pipeline/src/tiles/generate_boundaries.py` — GeoDataFrame → tippecanoe → PMTiles → R2
- **Frontend section pattern**: `web/app/components/city/RadialProfileSection.vue` — section with map toggle, info modal link
- **Map layer pattern**: `web/app/lib/map/useRadialLayer.ts` — deck.gl layer with reactive state
- **Feature gating**: `web/types/dataset.ts` `DatasetFeature` type + `useDataset().hasFeatureComputed()`
- **Rankings**: `web/app/composables/useRankingFilters.ts` `RankingStat` type, `CityRankings.vue`
- **Distribution strip**: `web/app/composables/useDistributionData.ts` — sorts all cities, computes rank
- **Section composition**: `web/app/components/city/CityInfoPanel.vue` — stacks DataPoints + RadialProfileSection

### External References

- **geoBoundaries CGAZ ADM2**: `https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/CGAZ/geoBoundariesCGAZ_ADM2.gpkg` (~250 MB GeoPackage, CC-BY 4.0)
- **Berry Index**: `Berry = 1 − Σ(sᵢ²)` where sᵢ = municipality i's share of total urban population. Range 0 (one municipality) to ~1 (many equal municipalities). Scaled to 0–100 for display.
- **DuckDB spatial**: `JOIN ON ST_Intersects()` with automatic bounding box optimization (~42x faster than cross join + filter)
- **tippecanoe**: Use `--no-simplification-of-shared-nodes` (replaces deprecated `--detect-shared-borders`) + `--convert-polygons-to-label-points` for municipality labels

## Key Technical Decisions

- **geoBoundaries CGAZ ADM2 as global municipal layer**: The CGAZ product provides a single pre-composited GeoPackage covering 199 countries at ADM2. ADM2 is labeled "municipality level" by geoBoundaries and is the most consistently available level globally. Per-country admin level customization would be a significant manual effort for marginal accuracy gains. (see origin: Key Decisions)

- **DuckDB spatial for overlay computation**: The pipeline already uses DuckDB for analytical queries. DuckDB spatial's `JOIN ON ST_Intersects()` provides automatic spatial index optimization. GeoPandas overlay is the alternative but DuckDB keeps the pipeline in a consistent toolchain and handles the ~11,400 × ~100,000 polygon intersection efficiently.

- **Cell centroid assignment for population estimation**: Assign each GHSL grid cell to the municipality slice containing its centroid, then sum population per slice. This is consistent with the existing pipeline pattern (cells already assigned to cities). Centroid assignment error is negligible at 1km resolution for municipalities larger than ~5 km². No need for area-weighted or exactextract approaches.

- **Minimum overlap threshold**: Require ≥1% of city area OR ≥1 km² overlap (whichever is smaller) to count a municipality. This eliminates false positives from boundary slivers while keeping genuinely overlapping small municipalities.

- **Single-municipality cities are valid data, not "unavailable"**: A city with one municipality gets a complexity score of 0 (Berry Index = 0 when one share = 100%). The "unavailable" state is reserved for cities where geoBoundaries has no ADM2 coverage for their country.

- **Cross-border cities included**: The spatial join naturally finds municipalities in both countries. This is correct behavior — cross-border metros genuinely span multiple jurisdictions. The existing city deduplication (keeping one country_code) doesn't affect the spatial overlay.

- **Governance available for both datasets**: Governance data is independent of the population grid method (H3 vs grid-1km). It attaches to city boundaries, which are the same for both datasets. This makes it the first feature available across both datasets but gated by per-city data availability.

- **Map layers are mutually exclusive**: Activating the governance map layer deactivates the radial profile layer and vice versa. Both color the map area with different semantics; simultaneous display would be visual noise.

- **Separate governance parquet files**: New domain `pipeline/src/governance/` with its own output directory `data/processed/governance/`. Keeps governance data independent from city population files.

- **Global PMTiles tileset**: One `governance_boundaries.pmtiles` tileset with `city_id` attribute for client-side filtering, matching the existing pattern for city boundaries. tippecanoe generates label points from polygons automatically.

## Open Questions

### Resolved During Planning

- **Spatial intersection approach**: DuckDB spatial — consistent with pipeline toolchain, handles scale well with automatic bounding box optimization.
- **Population estimation method**: Cell centroid assignment — consistent with existing pipeline, negligible error at 1km resolution.
- **Data format**: Separate governance-specific parquet files in new `data/processed/governance/` directory.
- **PMTiles strategy**: Global tileset with city_id filtering, matching existing boundary tiles pattern.
- **Partial coverage mechanism**: Extend `DatasetFeature` with `'governance'` and add per-city availability checking via the governance data itself (cities present in the governance JSON have data; absent cities don't).
- **Admin level mapping**: Use ADM2 globally. geoBoundaries CGAZ ADM2 covers 199 countries at the municipality-equivalent level.
- **Single-municipality handling**: Valid data with complexity score 0, not "unavailable".

### Deferred to Implementation

- **Exact geoBoundaries coverage**: How many of the ~11,400 GHSL cities have usable ADM2 coverage? Discoverable only by running the spatial join. If coverage is very low for certain regions, the methodology page should note this.
- **Country-specific label for "municipality"**: Some countries call ADM2 "communes", "districts", "LGAs", etc. The UI could say "municipalities" generically or look up the local term. Defer to implementation — start with "municipalities" and revisit if it feels wrong.
- **Governance data file size**: The JSON for ~11,400 cities with municipality lists could be large. May need to split into a summary file (scores/counts for rankings) and per-city detail files (municipality lists for the section). Discoverable during web export implementation.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
Pipeline data flow:

  geoBoundaries CGAZ ADM2 (.gpkg)
         │
         ▼
  ┌─────────────────────┐     ┌──────────────────────┐
  │ download_geoboundaries │     │ cities.parquet        │
  │ → data/raw/geoboundaries/ │  │ (GHSL urban extents)  │
  └─────────┬───────────┘     └──────────┬───────────┘
            │                            │
            ▼                            ▼
  ┌─────────────────────────────────────────────┐
  │ compute_governance                           │
  │                                              │
  │ 1. Load ADM2 polygons + city boundaries      │
  │ 2. DuckDB spatial: JOIN ON ST_Intersects()   │
  │ 3. Filter: ≥1% city area OR ≥1 km² overlap  │
  │ 4. Assign GHSL grid cells to slices          │
  │    (cell centroid → sjoin into slices)        │
  │ 5. Sum population per slice                  │
  │ 6. Compute Berry Index per city              │
  │                                              │
  │ → data/processed/governance/                 │
  │   city_governance.parquet (scores + counts)  │
  │   city_governance_municipalities.parquet      │
  │     (per-municipality details)               │
  └──────────────┬──────────────────────────────┘
                 │
         ┌───────┴────────┐
         ▼                ▼
  ┌──────────────┐  ┌──────────────────┐
  │ web_export/   │  │ tiles/            │
  │ generate_     │  │ generate_         │
  │ governance.py │  │ governance_       │
  │               │  │ boundaries.py     │
  │ → JSON to R2  │  │ → PMTiles to R2   │
  └──────────────┘  └──────────────────┘

Frontend data flow:

  R2: governance.json ──→ useGovernance composable
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
  GovernanceSection    CityRankings      ComparisonPanel
  (city detail page)   (new stat)        (side-by-side)
              │
              ▼
  useGovernanceLayer (deck.gl)
  ← R2: governance_boundaries.pmtiles
```

## Implementation Units

### Phase 1: Pipeline — Data Acquisition and Computation

- [ ] **Unit 1: Download geoBoundaries CGAZ ADM2**

  **Goal:** Add a download script for the geoBoundaries CGAZ ADM2 GeoPackage, following the existing download domain pattern.

  **Requirements:** R1, R4

  **Dependencies:** None

  **Files:**
  - Create: `pipeline/src/download/download_geoboundaries.py`
  - Create: `pipeline/src/governance/__init__.py`

  **Approach:**
  - Download `geoBoundariesCGAZ_ADM2.gpkg` (~250 MB) to `data/raw/geoboundaries/`
  - Use httpx with streaming (matching existing download scripts)
  - Skip download if file already exists
  - Click CLI with `@click.command()`
  - Print summary: file size, feature count, country count

  **Patterns to follow:**
  - `pipeline/src/download/download_ghsl.py` — download script structure
  - `pipeline/src/download/download_h3_r8.py` — streaming download with progress

  **Test scenarios:**
  - Happy path: Script downloads GeoPackage, file exists at expected path, prints summary with country count
  - Edge case: File already exists → skip download, print "already downloaded"

  **Verification:**
  - `data/raw/geoboundaries/geoBoundariesCGAZ_ADM2.gpkg` exists and is readable by GeoPandas/DuckDB

- [ ] **Unit 2: Compute governance fragmentation**

  **Goal:** Create the core governance computation script that overlays city boundaries with ADM2 municipalities, estimates population shares, and computes Berry Index scores.

  **Requirements:** R1, R2, R3, R4

  **Dependencies:** Unit 1

  **Files:**
  - Create: `pipeline/src/governance/compute_governance.py`

  **Approach:**
  - Load city boundaries (all epochs use 2025 boundaries for governance, since admin boundaries are static)
  - Load ADM2 GeoPackage via DuckDB spatial or GeoPandas
  - Spatial intersection: DuckDB `JOIN ON ST_Intersects()` to find city-municipality overlaps
  - Compute intersection areas using `ST_Area_Spheroid()`
  - Apply minimum overlap threshold: ≥1% of city area OR ≥1 km² (whichever smaller)
  - Load GHSL population grid cells for epoch 2025
  - Assign cell centroids to intersection slices via spatial join
  - Sum population per slice → compute population shares per municipality
  - Compute Berry Index: `1 − Σ(sᵢ²)`, scale to 0–100
  - Output two parquet files:
    - `city_governance.parquet`: city_id, municipality_count, complexity_score, has_coverage (bool)
    - `city_governance_municipalities.parquet`: city_id, muni_name, country_iso3, pop_share, area_km2

  **Patterns to follow:**
  - `pipeline/src/radial/generate_radial_profiles.py` — domain script structure, docstring schema table
  - `pipeline/src/cities/compute_populations.py` — loading city data, aggregation pattern
  - `pipeline/src/utils/config.py` — path helpers

  **Test scenarios:**
  - Happy path: Known city (e.g., a European city with good ADM2 coverage) produces expected municipality count and reasonable Berry Index (0–100 range)
  - Edge case: City with exactly one municipality → complexity_score = 0, municipality_count = 1
  - Edge case: City where no ADM2 polygons intersect (coverage gap) → not present in output (has_coverage distinguishes from single-municipality)
  - Edge case: Tiny sliver overlap below threshold → municipality excluded from count
  - Edge case: Cross-border city → municipalities from both countries appear in output
  - Integration: Output parquet schema matches expected columns and types

  **Verification:**
  - Both parquet files exist in `data/processed/governance/`
  - Summary printed: N cities with governance data, N total municipalities found, coverage percentage
  - Spot check: a well-known city (Paris, NYC, London) has a plausible municipality count

- [ ] **Unit 3: Validate governance data**

  **Goal:** Add Pandera schema validation for governance output files.

  **Requirements:** R3

  **Dependencies:** Unit 2

  **Files:**
  - Modify: `pipeline/src/validate/validate_cities.py`

  **Approach:**
  - Add `CityGovernanceSchema` and `CityGovernanceMunicipalitiesSchema` DataFrameModel classes
  - Add foreign key check: all city_ids in governance files exist in `cities.parquet`
  - Add data quality checks: complexity_score in [0, 100], pop_share sums ≈ 1.0 per city

  **Patterns to follow:**
  - Existing schema classes in `validate_cities.py` (CityPopulationSchema, RadialProfileSchema)

  **Test scenarios:**
  - Happy path: Validation passes on correctly computed governance data
  - Error path: Missing city_id foreign key → validation fails with clear message
  - Error path: pop_shares don't sum to ~1.0 for a city → quality check flags it

  **Verification:**
  - `uv run python -m src.validate.validate_cities --source h3-r8 -v` passes including governance schemas

### Phase 2: Pipeline — Export and Tiles

- [ ] **Unit 4: Web export for governance data**

  **Goal:** Generate JSON files for frontend consumption and upload to R2.

  **Requirements:** R3, R6, R7

  **Dependencies:** Unit 2

  **Files:**
  - Create: `pipeline/src/web_export/generate_governance.py`

  **Approach:**
  - Generate two JSON outputs:
    - `governance_summary.json`: `Record<city_id, { municipality_count, complexity_score }>` — lightweight for rankings and distribution strips
    - `governance_municipalities.json`: `Record<city_id, Array<{ name, country_iso3, pop_share }>>` — detailed for city page section
  - If the municipalities file is too large (>5 MB), split into per-city files under `data/governance/{city_id}.json` (matching the `city_cells/` pattern)
  - Upload to R2 under `data/` prefix
  - `--local` flag to skip upload

  **Patterns to follow:**
  - `pipeline/src/web_export/generate_radial_profiles.py` — JSON generation + R2 upload
  - `pipeline/src/web_export/generate_city_cells.py` — per-city file pattern (if needed)

  **Test scenarios:**
  - Happy path: JSON files generated, parseable, match expected schema
  - Happy path: R2 upload succeeds (or skipped with --local)
  - Edge case: Single-municipality city appears in summary with score 0
  - Edge case: Cities without coverage are absent from output (not present with null values)

  **Verification:**
  - JSON files exist in `data/processed/tiles/`
  - File sizes are reasonable (summary < 1 MB, municipalities < 10 MB or per-city files < 50 KB each)

- [ ] **Unit 5: Generate governance boundary PMTiles**

  **Goal:** Create a PMTiles tileset of municipality boundary slices overlaid per city, for the map layer.

  **Requirements:** R8

  **Dependencies:** Unit 2

  **Files:**
  - Create: `pipeline/src/tiles/generate_governance_boundaries.py`

  **Approach:**
  - Load city-municipality intersection geometries from the governance computation
  - Include attributes: city_id, muni_name, pop_share (as integer permille 0–1000), population, area_km2
  - Export to temporary GeoJSON
  - Run tippecanoe with: `--layer=governance_boundaries`, `--no-simplification-of-shared-nodes`, `--convert-polygons-to-label-points`, `--minimum-zoom=0`, `--maximum-zoom=12`
  - Upload `governance_boundaries.pmtiles` to R2 under `tiles/`

  **Patterns to follow:**
  - `pipeline/src/tiles/generate_boundaries.py` — tippecanoe subprocess, GeoJSON export, R2 upload

  **Test scenarios:**
  - Happy path: PMTiles file generated, non-empty, correct layer name
  - Happy path: tippecanoe succeeds without errors
  - Edge case: Large city with many municipality slices renders without tile size errors

  **Verification:**
  - `governance_boundaries.pmtiles` exists and is loadable by PMTiles reader
  - Spot-check in a tile viewer: municipality boundaries visible, label points present

### Phase 3: Frontend — Data Layer and Partial Coverage

- [ ] **Unit 6: Governance data composable and partial coverage pattern**

  **Goal:** Create the `useGovernance` composable to load governance data from R2, and extend the dataset feature system for partial per-city coverage.

  **Requirements:** R10, R11, R12

  **Dependencies:** Unit 4

  **Files:**
  - Create: `web/app/composables/useGovernance.ts`
  - Modify: `web/types/dataset.ts` — add `'governance'` to `DatasetFeature`
  - Modify: `web/app/composables/useDataset.ts` — add `'governance'` to both datasets' features arrays

  **Approach:**
  - `useGovernance()` composable: fetches `governance_summary.json` from R2 (lazy, singleton pattern matching `useCityPopulations`)
  - Exposes: `getGovernance(cityId)` → `{ municipality_count, complexity_score } | null`
  - `hasCityGovernance(cityId)` → boolean (city present in data)
  - `governanceCities` → set of city_ids with governance data (for ranking filters and distribution)
  - For municipality details: separate fetch of `governance_municipalities.json` or per-city file, loaded on demand when governance section mounts
  - Add `'governance'` to `DatasetFeature` union type
  - Add it to both datasets' features arrays (governance is dataset-independent)
  - The partial-coverage pattern: feature is "available" at the dataset level, but per-city availability is checked via `hasCityGovernance(cityId)`

  **Patterns to follow:**
  - `web/app/composables/useCityPopulations.ts` — R2 data loading, singleton state
  - `web/app/composables/useRadialProfiles.ts` — feature-gated data loading

  **Test scenarios:**
  - Happy path: Composable loads governance data, returns correct values for a city with data
  - Happy path: `hasCityGovernance` returns false for a city without coverage
  - Edge case: Data not yet loaded → returns null/loading state
  - Error path: R2 fetch fails → error state, section shows graceful fallback

  **Verification:**
  - Composable correctly loads and exposes governance data for cities with coverage
  - Cities without coverage return null, not an error

- [ ] **Unit 7: Governance section component on city detail page**

  **Goal:** Add the GovernanceSection component below radial profiles, showing headline stat, complexity score with distribution strip, and map toggle.

  **Requirements:** R5, R6, R7, R9, R10

  **Dependencies:** Unit 6

  **Files:**
  - Create: `web/app/components/city/GovernanceSection.vue`
  - Create: `web/app/components/city/GovernanceMunicipalityList.vue`
  - Modify: `web/app/components/city/CityInfoPanel.vue` — add GovernanceSection below RadialProfileSection
  - Modify: `web/app/composables/useDistributionData.ts` — add `'complexity_score'` metric support with governance-specific city subset

  **Approach:**
  - GovernanceSection pattern mirrors RadialProfileSection:
    - Header with "Governance Complexity" label + info modal link (→ methodology page)
    - "Show on map" toggle button
    - Content area with:
      - Headline: "This city spans N municipalities" (prominent)
      - Complexity score DataPoint with distribution strip (rank among cities with governance data only)
      - Collapsible municipality list showing name + population share bar
  - When no governance data: render section with explanatory message (R10) — "Municipal boundary data is not yet available for [country_name] in our current data sources"
  - Feature-gated via `hasFeatureComputed('governance')` in CityInfoPanel
  - Distribution strip: extend `useDistributionData` to accept governance-specific data source, ranking only among `governanceCities` subset
  - Deactivate map layer on unmount and city change (matching radial pattern)

  **Patterns to follow:**
  - `web/app/components/city/RadialProfileSection.vue` — section structure, map toggle, info modal
  - `web/app/components/ui/DataPoint.vue` — stat display
  - `web/app/components/ui/DistributionStrip.client.vue` — rank visualization

  **Test scenarios:**
  - Happy path: City with governance data → headline shows correct count, score displays, distribution strip renders
  - Happy path: Info icon opens governance methodology modal
  - Edge case: City without governance data → explanatory message shown with country name
  - Edge case: City with exactly 1 municipality → shows "spans 1 municipality" (singular), score 0
  - Edge case: Distribution strip shows "Rank X of Y" where Y = number of cities with governance data, not total cities
  - Integration: Toggling map on activates governance layer; deactivates radial layer if active

  **Verification:**
  - Governance section visible on city pages for cities with data
  - Unavailable message visible for cities without data
  - Map toggle works, layers are mutually exclusive with radial

- [ ] **Unit 8: Governance map layer**

  **Goal:** Add a deck.gl/MapLibre layer that renders municipal boundary slices color-coded by population share with name labels.

  **Requirements:** R8

  **Dependencies:** Unit 5, Unit 7

  **Files:**
  - Create: `web/app/lib/map/useGovernanceLayer.ts`
  - Create: `web/app/composables/useGovernanceHighlight.ts`
  - Modify: `web/app/lib/map/useMap.ts` — add governance PMTiles source config
  - Modify: `web/app/lib/map/useRadialLayer.ts` — deactivate when governance layer activates (mutual exclusion)

  **Approach:**
  - PMTiles source: add `GOVERNANCE_BOUNDARIES_CONFIG` to useMap, pointing to R2 governance_boundaries.pmtiles
  - Layer: MapLibre vector tile source filtered by `city_id` matching selected city
  - Fill layer: polygons color-coded by `pop_share` (gradient from light to dark, e.g., sand-100 → forest-700)
  - Line layer: boundary outlines
  - Symbol layer: municipality name labels using existing font glyphs
  - Reactive state in `useGovernanceHighlight.ts`: `isGovernanceLayerActive` ref shared between section and layer
  - Mutual exclusion: when governance activates, deactivate radial (and vice versa) via a shared layer controller or direct ref watching

  **Patterns to follow:**
  - `web/app/lib/map/useRadialLayer.ts` — deck.gl layer creation, reactive state
  - `web/app/composables/useRadialHighlight.ts` — highlight state management
  - `web/app/lib/map/useMap.ts` — PMTiles source configuration (BOUNDARIES_CONFIG pattern)

  **Test scenarios:**
  - Happy path: Toggle on → municipal boundaries appear for selected city, color-coded by share, labels visible
  - Happy path: Toggle off → layer removed
  - Edge case: Switch city while layer active → layer updates to new city's municipalities
  - Edge case: Activate governance → radial layer deactivates automatically
  - Edge case: City without governance data → toggle button disabled or hidden

  **Verification:**
  - Municipal boundaries visible on map when toggled, filtered to selected city
  - Color gradient distinguishes high-share vs low-share municipalities
  - Labels are readable at appropriate zoom levels

### Phase 4: Frontend — Rankings and Comparison Integration

- [ ] **Unit 9: Governance in rankings**

  **Goal:** Add governance complexity score as a sortable ranking stat with partial-data awareness.

  **Requirements:** R12, R13

  **Dependencies:** Unit 6

  **Files:**
  - Modify: `web/app/composables/useRankingFilters.ts` — add `'governance'` to `RankingStat`
  - Modify: `web/app/components/rankings/StatToggle.vue` — add governance button
  - Modify: `web/app/components/rankings/CityRankings.vue` — governance sort logic, filter to cities with data

  **Approach:**
  - Add `'governance'` to `RankingStat` union type
  - StatToggle: add button with appropriate label (e.g., "Governance" or "Complexity")
  - CityRankings: when governance is active stat, filter city list to `governanceCities` from useGovernance, sort by complexity_score
  - Show count indicator: "N cities with governance data" when governance stat is active
  - When country filter + governance results in zero cities: show message "No governance data available for [Country]"

  **Patterns to follow:**
  - Existing stat buttons and sort logic in `StatToggle.vue` and `CityRankings.vue`
  - `useRankingFilters.ts` — filter state pattern

  **Test scenarios:**
  - Happy path: Select governance stat → list shows cities sorted by complexity score, highest first
  - Happy path: Sort direction toggle works (highest/lowest governance complexity)
  - Edge case: Country filter active + governance → shows intersection of both filters
  - Edge case: Country filter + governance → zero results → informative empty state message
  - Edge case: Switch from governance to another stat → all cities reappear (no phantom filtering)

  **Verification:**
  - Governance appears as a ranking option
  - Cities without governance data are excluded from the list when governance is the active stat
  - Count label accurately reflects filtered set size

- [ ] **Unit 10: Governance in comparison view**

  **Goal:** Show governance metrics in the city comparison view when both cities have data.

  **Requirements:** R14

  **Dependencies:** Unit 6

  **Files:**
  - Modify: `web/app/components/compare/ComparisonMetricTable.vue` — add governance row
  - Modify: `web/app/components/compare/ComparisonPanel.vue` — include governance section

  **Approach:**
  - Add a governance row to ComparisonMetricTable: municipality count and complexity score for each city
  - When one city has governance data and the other doesn't: show the value for one and "N/A" for the other
  - When neither has data: hide the governance row entirely

  **Patterns to follow:**
  - Existing metric rows in `ComparisonMetricTable.vue`

  **Test scenarios:**
  - Happy path: Both cities have governance data → side-by-side municipality count and complexity score
  - Edge case: One city has data, other doesn't → show value and "N/A"
  - Edge case: Neither city has data → governance row hidden

  **Verification:**
  - Governance metrics appear in comparison when applicable

### Phase 5: Content — Methodology Page

- [ ] **Unit 11: Governance methodology content**

  **Goal:** Create the methodology page explaining governance complexity — data source, Berry Index derivation, interpretation guidance.

  **Requirements:** R9

  **Dependencies:** None (can be done in parallel with pipeline work)

  **Files:**
  - Create: `web/content/methodology/governance-complexity.md`

  **Approach:**
  - Frontmatter: `dataset: "urban-world-v1"` (or both datasets), `modalTitle: "Governance Complexity"`, `parentPage: "/methodology"`
  - Sections: what governance complexity measures, data source (geoBoundaries), how the score is computed (Berry Index formula), how to interpret scores (0 = one municipality, 100 = maximally fragmented), data coverage and limitations
  - Use `::citation-card` MDC component for Berry (1971) and geoBoundaries (Runfola et al., 2020) references
  - Tone matching existing methodology pages: clear, educational, no jargon without explanation

  **Patterns to follow:**
  - `web/content/methodology/bertaud-radial.md` — structure, frontmatter, citation cards
  - `web/content/methodology/density-outliers.md` — tone and explanation style

  **Test scenarios:**
  - Happy path: Page renders at `/methodology/governance-complexity`
  - Happy path: Info modal opens with `modalTitle` content when triggered from governance section
  - Happy path: Citation cards render correctly

  **Verification:**
  - Methodology page accessible and renders correctly
  - Info modal link from governance section opens this content

## System-Wide Impact

- **Interaction graph:** GovernanceSection ↔ useGovernanceHighlight ↔ useGovernanceLayer ↔ useMap. Also: useGovernanceHighlight ↔ useRadialHighlight (mutual exclusion). Rankings: useRankingFilters ↔ CityRankings ↔ useGovernance.
- **Error propagation:** R2 fetch failure in useGovernance → null governance data for all cities → all sections show "unavailable" state. This is graceful degradation, not a crash.
- **State lifecycle risks:** Governance layer must deactivate on city change and unmount (matching radial pattern). Governance data is static (no epoch reactivity), so no stale-data risk from epoch changes.
- **API surface parity:** The governance JSON files are a new R2 data contract. The PMTiles source is a new map source. Both are additive — no existing contracts change.
- **Integration coverage:** The mutual exclusion between governance and radial map layers needs integration testing beyond unit tests.
- **Unchanged invariants:** Existing city data pipeline, city populations JSON, city index, and all existing PMTiles tilesets are unchanged. The governance feature is purely additive.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| geoBoundaries ADM2 coverage may be low for some regions (Africa, parts of Asia) | Accept partial coverage as a design decision. Methodology page documents limitations. Coverage count shown in rankings. |
| Spatial intersection at scale (~11,400 × ~100,000 polygons) may be slow | DuckDB spatial's automatic bounding box optimization handles this. Process single epoch (2025) only for governance since boundaries are static. |
| Governance JSON file size may be large with municipality lists for all cities | Split into summary (scores) and detail (municipalities) files. Per-city detail files if needed (matching city_cells pattern). |
| tippecanoe may struggle with complex intersection geometries | Simplification flags handle this. Test with a representative subset first. |
| Berry Index produces score 0 for single-municipality cities, which could dominate "lowest complexity" rankings | This is correct behavior. The ranking by complexity score naturally separates fragmented from non-fragmented cities. |

## Documentation / Operational Notes

- Methodology page (Unit 11) serves as user-facing documentation
- DATA_LINEAGE.md should be updated with the governance data flow
- pipeline/CLAUDE.md should be updated with governance pipeline commands
- R2 gets two new JSON files and one new PMTiles file — additive, no migration needed

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-29-governance-complexity-requirements.md](docs/brainstorms/2026-03-29-governance-complexity-requirements.md)
- **geoBoundaries**: Runfola et al. (2020), "geoBoundaries: A global database of political administrative boundaries", PLOS ONE. Data: https://www.geoboundaries.org/
- **Berry Index**: Berry (1971), used in metropolitan fragmentation research. Formula: `1 − Σ(sᵢ²)`
- **DuckDB spatial**: https://duckdb.org/docs/stable/core_extensions/spatial/overview
- **tippecanoe**: https://github.com/felt/tippecanoe — label points via `--convert-polygons-to-label-points`
- Related pipeline patterns: `pipeline/src/radial/`, `pipeline/src/tiles/generate_boundaries.py`
- Related frontend patterns: `web/app/components/city/RadialProfileSection.vue`, `web/app/lib/map/useRadialLayer.ts`
