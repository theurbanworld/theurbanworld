# Urban Data Pipeline

A data processing pipeline that transforms GHSL (Global Human Settlement Layer) raster data into web-ready formats for urban visualization.

## Overview

This pipeline processes ~13,000 cities globally from the European Commission's GHSL dataset, generating:
- **H3 hexagonal grids** for map visualization
- **City boundary polygons** as PMTiles
- **Radial density profiles** (Bertaud-style analysis)
- **Population time series** (1975-2030)
- **Web-ready JSON** for frontend consumption

## Quick Start

```bash
# Install dependencies with uv
uv sync

# Run a script
uv run python -m src.download.download_ghsl

# Validate outputs
uv run python -m src.validate.validate_cities -v
```

## Pipeline Scripts

Scripts are organized by domain under `src/`:

### download/ — Data retrieval
| Script | Description |
|--------|-------------|
| `download_ghsl.py` | Download GHSL-POP tiles, UCDB, and MTUC from JRC |
| `download_h3_r8.py` | Download pre-computed H3 res-8 population data from R2 |

### cities/ — City extraction and computation
| Script | Description |
|--------|-------------|
| `extract_attributes.py` | Extract city attributes from UCDB GeoPackage |
| `extract_geometries.py` | Extract multi-temporal city boundaries from MTUC |
| `generate_cities.py` | Merge attributes + geometries into cities.parquet |
| `compute_populations.py` | Sum H3 cell populations within city boundaries |
| `compute_rankings.py` | Compute rankings, growth metrics, density peers |

### h3/ — H3 hexagonal grid processing
| Script | Description |
|--------|-------------|
| `modal_raster_to_h3.py` | Convert 1km rasters to H3 res-8 (Modal cloud) |
| `load_to_psql.py` | Load H3 data to PostGIS for QGIS visualization |
| `merge_timeseries.py` | Merge per-epoch H3 files into single timeseries |

### radial/ — Radial density analysis
| Script | Description |
|--------|-------------|
| `compute_profiles.py` | Compute Bertaud-style radial density profiles |

### tiles/ — Map tile generation
| Script | Description |
|--------|-------------|
| `modal_download_basemap.py` | Download Protomaps planet PMTiles (Modal cloud) |
| `generate_boundaries.py` | Generate city boundary PMTiles with tippecanoe |
| `generate_font_glyphs.py` | Generate MapLibre font glyph PBF files |
| `generate_hover_sprites.py` | Generate hover pattern sprite sheets |

### web_export/ — Frontend JSON generation
| Script | Description |
|--------|-------------|
| `generate_city_index.py` | City metadata JSON for search/navigation |
| `generate_city_populations.py` | Per-epoch population JSON for sidebar |

### validate/ — Data quality checks
| Script | Description |
|--------|-------------|
| `validate_cities.py` | Pandera schema validation across all outputs |

### explore/ — Data exploration
| Script | Description |
|--------|-------------|
| `app_explore.py` | Streamlit app for browsing city data |

## Data Sources

- **GHSL-POP R2023A**: Population grids at 1km resolution, 12 epochs (1975-2030)
- **GHSL-UCDB R2024A**: Urban Centre Database with city attributes
- **GHSL-MTUC R2024A**: Multi-temporal urban center boundaries
- Source: [European Commission Joint Research Centre](https://human-settlement.emergency.copernicus.eu/)

## Configuration

Key settings in `src/utils/config.py`:
- `H3_RESOLUTION_MAP = 9` (~0.1 km² cells)
- `RADIAL_MAX_DISTANCE_KM = 50` (50 rings at 1km intervals)
- `BOUNDARY_POPULATION_THRESHOLD = 100` (min pop per cell)

Override via environment variables with `URBAN_` prefix:
```bash
URBAN_H3_RESOLUTION_MAP=8 uv run python -m src.radial.compute_profiles
```

## R2 Upload Configuration

Data is served from Cloudflare R2. To configure uploads:

```bash
# Copy the example env file
cp .env.example .env

# Edit with your R2 credentials (from Cloudflare dashboard)
# R2_ENDPOINT_URL=...
# R2_ACCESS_KEY_ID=...
# R2_SECRET_ACCESS_KEY=...
# R2_BUCKET_NAME=...
```

## Project Structure

```
pipeline/
├── pyproject.toml          # Dependencies and entry points
├── CLAUDE.md               # Development instructions
├── .env.example            # R2 credentials template
├── src/
│   ├── download/           # Data retrieval from JRC and R2
│   ├── cities/             # City extraction, population, rankings
│   ├── h3/                 # H3 hexagonal grid processing
│   ├── radial/             # Radial density profiles
│   ├── tiles/              # Map tiles, fonts, sprites
│   ├── web_export/         # Frontend JSON generation
│   ├── validate/           # Data quality validation
│   ├── explore/            # Streamlit data explorer
│   └── utils/              # Shared config, geometry, H3, R2 upload
└── data/
    ├── raw/                # Downloaded GHSL files
    ├── interim/            # Intermediate outputs
    └── processed/          # Final web-ready files
        ├── tiles/          # PMTiles, JSON, sprites
        └── cities/         # Parquet tables
```

## Hardware Requirements

- **Memory**: 16GB RAM minimum (32GB recommended)
- **Storage**: ~150GB for full dataset
- Optimized for Apple Silicon (M1/M2/M3) with thread-based parallelization.

## License

Pipeline code: MIT License
GHSL Data: CC BY 4.0 (European Commission)
