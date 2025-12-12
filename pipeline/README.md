# Urban Data Pipeline

A data processing pipeline that transforms GHSL (Global Human Settlement Layer) raster data into web-ready formats for urban visualization.

## Overview

This pipeline processes ~13,000 cities globally from the European Commission's GHSL dataset, generating:
- **H3 hexagonal grids** for map visualization
- **City boundary polygons** as H3 cell sets
- **Radial density profiles** (Bertaud-style analysis)
- **Population time series** (1975-2030)
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
| 1. Download | `s01_download_ghsl.py` | Download GHSL-POP tiles and UCDB |
| 2. Extract | `s02_extract_urban_centers.py` | Parse urban center metadata |
| 3. H3 100m | `s03_raster_100m_to_h3_r9.py` | Convert 100m raster to H3 res-9 (Modal cloud) |
| 4. H3 1km | `s04_raster_1km_to_h3_r8.py` | Convert 1km rasters to H3 (Modal cloud) |
| 5. Boundaries | `s05_extract_city_boundaries.py` | Extract city extents as H3 cells |
| 6. Profiles | `s06_compute_radial_profiles.py` | Compute Bertaud radial profiles |
| 7. Export | `s07_export_web_formats.py` | Generate web-ready JSON/Parquet |
| 10. Basemap | `s10_download_basemap.py` | Download Protomaps planet PMTiles |
| 20. Upload | `s20_upload_to_r2.py` | Upload processed data to R2 |
| 21. CORS | `s21_configure_r2_cors.py` | Configure R2 bucket CORS |

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
  "population_2025": 18823000,
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

### H3 Population Grid (`data/processed/h3_tiles/h3_pop_2025_res9.parquet`)
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

## R2 Upload Configuration

Data is served from Cloudflare R2. To configure uploads:

```bash
# Copy the example env file
cp .env.example .env

# Edit with your R2 credentials (from Cloudflare dashboard)
# R2_ACCOUNT_ID=your_account_id
# R2_ACCESS_KEY_ID=your_access_key
# R2_SECRET_ACCESS_KEY=your_secret_key

# One-time CORS setup
make r2-cors

# Upload all data
make upload
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
├── .env.example           # R2 credentials template
├── src/
│   ├── s01_download_ghsl.py
│   ├── s02_extract_urban_centers.py
│   ├── s03_raster_100m_to_h3_r9.py
│   ├── s04_raster_1km_to_h3_r8.py
│   ├── s05_extract_city_boundaries.py
│   ├── s06_compute_radial_profiles.py
│   ├── s07_export_web_formats.py
│   ├── s10_download_basemap.py
│   ├── s20_upload_to_r2.py
│   ├── s21_configure_r2_cors.py
│   └── utils/
│       ├── config.py       # Configuration
│       ├── r2_config.py    # R2/S3 settings
│       ├── h3_utils.py     # H3 operations
│       ├── raster_utils.py # Raster processing
│       └── progress.py     # Checkpointing
└── data/
    ├── raw/                # Downloaded GHSL files
    ├── interim/            # Intermediate outputs
    └── processed/          # Final web-ready files
        ├── basemap/        # Protomaps PMTiles (~70GB)
        ├── h3_tiles/       # H3 population grids
        └── cities/         # City JSON files
```

## Make Targets

```bash
# Pipeline
make setup        # Create Python environment
make download     # Download GHSL data
make extract      # Extract urban centers
make convert      # Run H3 conversions
make boundaries   # Extract city boundaries
make radial       # Compute radial profiles
make export       # Export web formats
make test-cities  # Run for test cities only
make all          # Run full pipeline

# Basemap
make basemap      # Download Protomaps planet PMTiles (~70GB)
make basemap-force # Force re-download
make basemap-info # Show basemap metadata

# R2 Upload
make upload       # Upload all processed data to R2
make upload-dry   # Preview what would be uploaded
make upload-force # Force full re-upload
make r2-cors      # One-time CORS setup for R2 bucket

# Utilities
make status       # Show pipeline progress
make clean        # Remove generated data
make help         # Show all targets
```

## License

Pipeline code: MIT License
GHSL Data: CC BY 4.0 (European Commission)
