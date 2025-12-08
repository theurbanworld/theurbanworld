# Urban Data Pipeline

A data processing pipeline that transforms GHSL (Global Human Settlement Layer) raster data into web-ready formats for urban visualization.

## Overview

This pipeline processes ~13,000 cities globally from the European Commission's GHSL dataset, generating:
- **H3 hexagonal grids** for map visualization
- **City boundary polygons** as H3 cell sets
- **Radial density profiles** (Bertaud-style analysis)
- **Population time series** (1975-2020)
- **Web-ready JSON/GeoParquet** for frontend consumption

## Quick Start

```bash
# Install dependencies with uv
uv sync

# Run pipeline for test cities (fast iteration)
make test-cities

# Run full pipeline
make all

# Check status
make status
```

## Pipeline Stages

| Stage | Script | Description |
|-------|--------|-------------|
| 1. Download | `01_download_ghsl.py` | Download GHSL-POP tiles and UCDB |
| 2. Extract | `02_extract_urban_centers.py` | Parse urban center metadata |
| 3. H3 100m | `03_raster_to_h3_100m.py` | Convert 100m raster to H3 res-9 |
| 4. H3 1km | `04_raster_to_h3_1km.py` | Convert 1km rasters for time series |
| 5. Boundaries | `05_extract_city_boundaries.py` | Extract city extents as H3 cells |
| 6. Profiles | `06_compute_radial_profiles.py` | Compute Bertaud radial profiles |
| 7. Export | `07_export_web_formats.py` | Generate web-ready JSON/Parquet |

## Data Sources

- **GHSL-POP R2023A**: Population grids at 100m and 1km resolution
- **GHSL-UCDB R2024A**: Urban Centre Database with 11,422 cities
- Source: [European Commission Joint Research Centre](https://human-settlement.emergency.copernicus.eu/)

## Output Formats

### City JSON (`data/processed/cities/{city_id}.json`)
```json
{
  "id": "nyc_usa",
  "name": "New York",
  "country": "United States",
  "location": {"lat": 40.7128, "lon": -74.006},
  "population_2020": 18823000,
  "boundary_h3": {
    "resolution": 9,
    "cells": ["891e204d21fffff", ...],
    "cell_count": 3421
  },
  "time_series": [{"year": 1975, "population": 15880000}, ...],
  "radial_profile": [{"distance_km": 0.5, "density_per_km2": 27000}, ...]
}
```

### City Index (`data/processed/city_index.json`)
Lightweight index for search/autocomplete with basic city metadata.

### H3 Population Grid (`data/processed/h3_tiles/h3_pop_2020_res9.parquet`)
GeoParquet with H3 cell IDs and population values.

## Configuration

Key settings in `src/utils/config.py`:
- `H3_RESOLUTION_MAP = 9` (~0.1 km² cells)
- `RADIAL_MAX_DISTANCE_KM = 50` (50 rings at 1km intervals)
- `BOUNDARY_POPULATION_THRESHOLD = 100` (min pop per cell)

Override via environment variables with `URBAN_` prefix:
```bash
URBAN_H3_RESOLUTION_MAP=8 make all
```

## Test Cities

Development uses 6 test cities covering diverse urban forms:
- **NYC** - Large, dense, polycentric
- **Paris** - European, monocentric
- **Singapore** - Compact city-state
- **Lagos** - Rapidly growing African megacity
- **Rio de Janeiro** - Coastal, complex topography
- **Geneva** - Cross-border metro area (Switzerland/France)

## Hardware Requirements

- **Memory**: 16GB RAM minimum (32GB recommended)
- **Storage**: ~150GB for full dataset
- **Time**: ~1.5 hours for test cities, ~24 hours for full pipeline

Optimized for Apple Silicon (M1/M2/M3) with thread-based parallelization.

## Project Structure

```
pipeline/
├── pyproject.toml          # Dependencies
├── Makefile               # Build orchestration
├── src/
│   ├── s01_download_ghsl.py
│   ├── s02_extract_urban_centers.py
│   ├── s03_raster_to_h3_100m.py
│   ├── s04_raster_to_h3_1km.py
│   ├── s05_extract_city_boundaries.py
│   ├── s06_compute_radial_profiles.py
│   ├── s07_export_web_formats.py
│   └── utils/
│       ├── config.py       # Configuration
│       ├── h3_utils.py     # H3 operations
│       ├── raster_utils.py # Raster processing
│       └── progress.py     # Checkpointing
└── data/
    ├── raw/                # Downloaded GHSL files
    ├── interim/            # Intermediate outputs
    └── processed/          # Final web-ready files
```

## Make Targets

```bash
make setup        # Create Python environment
make download     # Download GHSL data
make extract      # Extract urban centers
make convert      # Run H3 conversions
make boundaries   # Extract city boundaries
make radial       # Compute radial profiles
make export       # Export web formats
make test-cities  # Run for test cities only
make status       # Show pipeline progress
make clean        # Remove generated data
make help         # Show all targets
```

## License

Pipeline code: MIT License
GHSL Data: CC BY 4.0 (European Commission)
