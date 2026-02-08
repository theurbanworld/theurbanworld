---
title: "Fix city sidebar data: epoch reactivity and map alignment"
type: fix
date: 2026-02-08
---

# Fix city sidebar data: epoch reactivity and map alignment

## Overview

The CityInfoPanel sidebar shows population, density, and area that (1) never update when the user changes the epoch slider, and (2) don't match the values shown on the map. Both bugs share a single root cause: the `city_populations.json` file that the frontend expects **does not exist** on R2 because no pipeline script generates it.

## Root Cause Analysis

### Data flow diagram

```
Pipeline                          R2                           Frontend
────────                          ──                           ────────

s04a → city_populations.parquet                                useCityPopulations
       (city_id, epoch,                                          fetches city_populations.json
        population, area_km2,          ❌ MISSING FILE             → 404 → empty Map
        density_per_km2)                                           → fallback fires

s07  → city_boundaries.pmtiles  → tiles/city_boundaries.pmtiles → useMap
       (per-epoch features with                                    filters by epoch
        population, density,                                       ✅ WORKS CORRECTLY
        pop_trend, density_trend)

s09  → cities_index.json        → data/cities_index.json       → useCitiesIndex
       (ucdb_population_2025,                                     static metadata
        centroid, bbox, name)                                     ✅ WORKS (but no epochs)
```

### Bug 1: Sidebar doesn't update on epoch change

The reactivity chain in `useCityStats.ts` is correctly wired — `epochData` is a `computed` that reads `selectedYear.value`. But `useCityPopulations` always returns an empty Map because `city_populations.json` doesn't exist (404). The fallback in `useCityStats` uses `city.value.population` from `cities_index.json`, which is always the static `ucdb_population_2025` value regardless of epoch.

**Key files:**
- `web/app/composables/useCityPopulations.ts:54-58` — 404 handler returns `[]`
- `web/app/composables/useCityStats.ts:119-147` — fallback always fires

### Bug 2: Sidebar numbers don't match map

| Metric | Map (PMTiles) | Sidebar (fallback) |
|--------|---------------|---------------------|
| Population | GHSL H3-aggregated, per epoch | UCDB 2025 estimate (different methodology) |
| Area | Sum of exact H3 cell areas | Bounding box rectangle approximation |
| Density | GHSL pop / H3 area | UCDB pop / bbox area |

These are fundamentally different data sources. The bbox area approximation (`useCityStats.ts:128-137`) can be 50%+ larger than actual urban extent for irregularly shaped cities.

## Proposed Solution

Create a single new pipeline script that converts `city_populations.parquet` → `city_populations.json` and uploads to R2. **No frontend changes needed** — the composables and reactivity are already correct.

### New file: `pipeline/src/s10_generate_city_populations_json.py`

Converts the existing parquet (long format: one row per city-epoch) into the nested JSON structure the frontend expects.

**Input:** `data/processed/cities/city_populations.parquet`

```
city_id | epoch | population | area_km2 | density_per_km2 | cell_count
--------|-------|------------|----------|-----------------|----------
ABC123  | 1975  | 50000      | 12.5     | 4000.0          | 19
ABC123  | 1980  | 55000      | 13.1     | 4198.5          | 20
...
```

**Output:** `data/processed/tiles/city_populations.json` → R2 key `data/city_populations.json`

Must match the TypeScript interface in `useCityPopulations.ts:20-32`:

```json
[
  {
    "city_id": "ABC123",
    "epochs": {
      "1975": { "population": 50000, "area_km2": 12.5, "density_per_km2": 4000.0 },
      "1980": { "population": 55000, "area_km2": 13.1, "density_per_km2": 4198.5 }
    }
  }
]
```

**Key decisions:**
- Population as integer (round from float), area/density as float rounded to 1 decimal
- Omit epoch keys where data is missing (frontend handles `undefined` return from `getCityPopulationData` gracefully — falls back to static data per city)
- Compact JSON (`separators=(",", ":")`) to minimize file size
- Follow existing patterns from `s09_generate_city_json.py` (argparse `--local` flag, boto3 upload, `ContentType: application/json`)

### Estimated file size

~10,000 cities x 12 epochs x ~80 bytes per epoch entry = ~10 MB uncompressed. With compact JSON and gzip from CDN, expect ~1-2 MB transfer. Acceptable for a single SSR-compatible fetch.

## Acceptance Criteria

- [ ] New script `pipeline/src/s10_generate_city_populations_json.py` exists
- [ ] Script reads `city_populations.parquet`, pivots to nested JSON matching `CityPopulationRecord` interface
- [ ] Script uploads to R2 at `data/city_populations.json` (with `--local` flag to skip upload)
- [ ] JSON validates: every city has `city_id` (string) and `epochs` (object with numeric keys)
- [ ] After upload, sidebar population/density/area update when epoch slider changes
- [ ] Sidebar values match map label values for the same city and epoch

## Implementation

### `pipeline/src/s10_generate_city_populations_json.py`

```python
"""
Generate city populations JSON for frontend.

Purpose: Convert city_populations.parquet (long format) to nested JSON
         for epoch-aware population lookups in the frontend.

Usage:
  uv run python -m src.s10_generate_city_populations_json           # Generate and upload
  uv run python -m src.s10_generate_city_populations_json --local   # Generate only

Date: 2026-02-08
"""

import json
import os
from collections import defaultdict
from pathlib import Path

import boto3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

POPULATIONS_PARQUET = Path("data/processed/cities/city_populations.parquet")
OUTPUT_JSON = Path("data/processed/tiles/city_populations.json")
R2_KEY = "data/city_populations.json"


def load_populations() -> pd.DataFrame:
    """Load city populations from parquet."""
    print(f"Loading populations from {POPULATIONS_PARQUET}...")
    df = pd.read_parquet(POPULATIONS_PARQUET)
    print(f"  Loaded {len(df):,} records ({df['city_id'].nunique():,} cities)")
    return df


def generate_json(df: pd.DataFrame) -> list[dict]:
    """Pivot long-format DataFrame to nested JSON structure."""
    print("Generating nested JSON...")

    cities = defaultdict(dict)
    for _, row in df.iterrows():
        city_id = str(row["city_id"])
        epoch = str(int(row["epoch"]))
        cities[city_id][epoch] = {
            "population": int(round(row["population"])),
            "area_km2": round(float(row["area_km2"]), 1),
            "density_per_km2": round(float(row["density_per_km2"]), 1),
        }

    result = [
        {"city_id": cid, "epochs": epochs}
        for cid, epochs in cities.items()
    ]

    print(f"  Generated {len(result):,} city records")
    return result


def save_json(data: list[dict], output_path: Path) -> None:
    """Save to compact JSON."""
    print(f"Saving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    file_size = output_path.stat().st_size / 1e6
    print(f"  Saved {output_path} ({file_size:.1f} MB)")


def upload_to_r2(local_path: Path, r2_key: str) -> str:
    """Upload JSON to R2."""
    # (same pattern as s09)
    ...


def main(local_only: bool = False) -> None:
    print("=" * 60)
    print("City Populations JSON Generator")
    print("=" * 60)

    df = load_populations()
    data = generate_json(df)
    save_json(data, OUTPUT_JSON)

    if not local_only:
        upload_to_r2(OUTPUT_JSON, R2_KEY)
    else:
        print(f"\nLocal only mode - skipping R2 upload")
        print(f"Output: {OUTPUT_JSON}")

    print("\nDone!")
```

## Context

### Files to create
- `pipeline/src/s10_generate_city_populations_json.py` — new pipeline script

### Files that already work correctly (no changes needed)
- `web/app/composables/useCityPopulations.ts` — fetches and parses JSON, builds lookup Map
- `web/app/composables/useCityStats.ts` — reads from populations Map with fallback, reactive to `selectedYear`
- `web/app/components/city/CityInfoPanel.vue` — renders stats from `useCityStats`
- `web/app/pages/city/[city_id].vue` — triggers `loadPopulations()` on mount

### Pipeline dependency
```
s04a (city_populations.parquet) → s10 (city_populations.json) → R2 upload
```

## References

- Frontend interface: `web/app/composables/useCityPopulations.ts:20-32`
- Existing JSON generator pattern: `pipeline/src/s09_generate_city_json.py`
- Source parquet schema: `pipeline/src/s04a_compute_city_populations.py:11-19`
- PMTiles data for comparison: `pipeline/src/s07_generate_boundary_pmtiles.py:117-119`
