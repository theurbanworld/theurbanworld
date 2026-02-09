# Pipeline Organization & Data Lineage

**Date:** 2026-02-08
**Status:** Brainstorm complete, ready for planning

## What We're Building

A reorganization of the data pipeline to make it understandable, maintainable, and fast to evolve as the project grows. Three pillars:

1. **Domain-grouped pipeline structure** — Replace numbered flat scripts with domain directories that match frontend concepts
2. **Single lineage document** — One source-of-truth doc with mermaid diagrams showing data flow from raw sources through R2 to web composables
3. **Citation & methodology reference** — Document data sources and aggregation methods so the frontend can cite them and you can reason about correctness

## Why This Approach

- **Solo dev optimized** — Lightweight, no build tooling, manually maintained docs
- **Names match across boundaries** — Pipeline directories/scripts use the same vocabulary as web components and composables
- **Mermaid diagrams** — Visual lineage that lives in markdown, renders on GitHub
- **Docs first, validation later** — Clear documentation of aggregation logic now; automated validation checks as the pipeline grows

## Key Decisions

### 1. Group scripts by domain, not execution order

**Current:** `s01_download_ghsl.py`, `s02a_extract_city_attributes.py`, ..., `s11_generate_hover_sprites.py`

**Proposed:** Domain directories under `pipeline/src/`:

```
src/
  download/       # Raw data acquisition (GHSL, basemaps)
  cities/         # City extraction, metadata, populations, rankings, growth
  h3/             # H3 hex conversion, timeseries merging
  radial/         # Radial density profiles (Bertaud)
  tiles/          # PMTiles generation (boundaries), font glyphs, sprites
  web_export/     # Final formats for R2: city index JSON, city populations JSON
  validate/       # Schema validation, integrity checks
```

Script names within each domain should be descriptive verbs that match what they produce:
- `cities/extract_attributes.py` not `s02a_extract_city_attributes.py`
- `cities/compute_populations.py` not `s04a_compute_city_populations.py`
- `web_export/generate_city_index.py` not `s09_generate_city_json.py`

Execution order is captured in the lineage doc, not in filenames.

### 2. Single DATA_LINEAGE.md at repo root

Contains:
- Mermaid diagram showing full pipeline flow (raw -> interim -> processed -> R2 -> web)
- Table mapping each R2 artifact to its pipeline source and web consumer
- Column/field contract between pipeline outputs and web types
- Known naming transformations (e.g., `city_id` -> `id` in JSON)

### 3. Citation & methodology in the lineage doc

A reference table listing:
- Each dataset's original source (e.g., "GHSL JRC R2024A")
- The aggregation/transformation method used (e.g., "Modal H3 res-8 cell assignment, population summed within city MTUC boundary")
- The frontend component that displays it

This serves dual purposes: user-facing attribution on the frontend, and developer understanding of how numbers are derived.

### 4. Naming alignment across pipeline and web

Key vocabulary that should be consistent:

| Concept | Pipeline | R2 Key | Web Composable | Web Component |
|---------|----------|--------|----------------|---------------|
| City metadata | `cities.parquet` | `data/cities_index.json` | `useCitiesIndex` | `CitySearch` |
| City populations | `city_populations.parquet` | `data/city_populations.json` | `useCityPopulations` | `CityInfoPanel` |
| H3 population grid | `h3_r8_pop_timeseries.parquet` | `data/h3_r8_pop_timeseries.parquet` | `useH3Data` | `H3PopulationLayer` |
| City boundaries | `city_boundaries.pmtiles` | `tiles/city_boundaries.pmtiles` | `useMap` | `GlobalMap` |
| Radial profiles | `radial_profiles.parquet` | TBD | TBD | TBD |

### 5. Data integrity: documentation now, validation later

Document aggregation methods in DATA_LINEAGE.md so correctness can be reasoned about. Existing `s99_validate_cities.py` already covers schema validation. Add integrity checks (e.g., "city population equals sum of H3 cells within boundary") as a future step.

## Open Questions

- **Pipeline runner:** With domain directories, how do you run the pipeline? A simple shell script listing steps in order? A Makefile? Or just document the order in DATA_LINEAGE.md and run manually? (Decide during planning)
- **R2 upload:** Currently some scripts upload directly to R2. Should uploads be a separate concern (a dedicated `deploy/` step) or stay embedded in each script?
- **Shared utilities:** Some scripts share helpers (R2 upload, parquet reading). Where do shared modules live in the new structure? Probably `src/shared/` or `src/utils/`.

## What This Does NOT Cover

- Filling data gaps (city_populations.json, radial profiles for web) — separate front-end implementation work
- Automated pipeline orchestration (Airflow, Prefect, etc.) — not needed at current scale
- CI/CD for the pipeline — future consideration
